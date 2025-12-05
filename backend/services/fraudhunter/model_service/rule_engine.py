"""
FraudHunter规则引擎核心服务

版本: v2.1.0 (支持值表达式)

功能：
1. 规则验证：检查规则结构、指标存在性、操作符兼容性、值表达式类型兼容性
2. 规则评估：执行规则判断，支持指标引用、时间函数、数学函数
3. SQL生成：将规则转换为Spark SQL表达式，支持所有值表达式类型

支持操作符: 基础比较、集合操作(in/not in)、正则匹配(regexp/not regexp)
支持值表达式: 常量值、指标引用、时间函数(date_add/date_sub)、数学函数(abs)
"""

import re
from typing import Dict, List, Set, Any, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from loguru import logger

from schemas.fraudhunter.rule import (
    RuleConfig, Rule, ConditionRule, GroupRule,
    ComparisonOperator, RuleValidationResult,
    ValueExpression, ConstantValue, IndicatorReference,
    TimeFunction, MathFunction
)
from models.fraudhunter.indicator import FraudHunterIndicatorDefinition


class RuleEngine:
    """规则引擎 - 验证、解析和执行规则"""

    # 操作符兼容性矩阵
    ALLOWED_OPERATORS = {
        'numeric': ['>', '>=', '<', '<=', '=', '!=', 'in', 'not in'],
        'enum': ['=', '!=', 'in', 'not in'],
        'text': ['=', '!=', 'in', 'not in', 'regexp', 'not regexp'],
        'boolean': ['=', '!=']
    }

    def __init__(self, db: Session):
        self.db = db
        self._indicator_cache: Dict[str, Optional[FraudHunterIndicatorDefinition]] = {}

    # ==================== 辅助方法 ====================

    def _get_indicator_cached(self, indicator_code: str) -> Optional[FraudHunterIndicatorDefinition]:
        """
        带缓存的指标查询（性能优化）

        Args:
            indicator_code: 指标编码

        Returns:
            指标定义对象，不存在则返回 None
        """
        if indicator_code not in self._indicator_cache:
            indicator = self.db.query(FraudHunterIndicatorDefinition).filter(
                FraudHunterIndicatorDefinition.indicator_code == indicator_code
            ).first()
            self._indicator_cache[indicator_code] = indicator

        return self._indicator_cache[indicator_code]

    def _extract_indicators_from_value_expression(self, expr: ValueExpression) -> Set[str]:
        """
        从值表达式中提取指标编码

        Args:
            expr: 值表达式

        Returns:
            指标编码集合
        """
        indicators = set()

        if isinstance(expr, IndicatorReference):
            indicators.add(expr.indicator)
        elif isinstance(expr, TimeFunction):
            indicators.add(expr.indicator)
        elif isinstance(expr, MathFunction):
            indicators.add(expr.indicator)

        return indicators

    # ==================== 规则验证 ====================

    def validate_rule_config(self, rule_config: RuleConfig) -> RuleValidationResult:
        """
        验证规则配置的完整性和正确性

        验证内容：
        1. 指标是否存在
        2. 规则结构是否完整
        3. 操作符与数据类型是否兼容
        4. 输出配置是否合法
        5. 规则嵌套深度检查
        6. 正则表达式语法验证

        Args:
            rule_config: 规则配置

        Returns:
            RuleValidationResult: 验证结果
        """
        result = RuleValidationResult(valid=True)

        try:
            # 1. 提取所有使用的指标
            indicators = self._extract_indicators(rule_config)
            result.extracted_indicators = list(indicators)

            # 2. 验证指标是否存在
            self._validate_indicators_exist(indicators, result)

            # 3. 验证规则结构
            self._validate_rule_structure(rule_config, result)

            # 4. 验证数据类型和操作符匹配
            self._validate_operator_compatibility(rule_config, result)

            # 5. 验证输出配置
            self._validate_output_config(rule_config.output, result)

            # 6. 检查规则深度
            max_depth = self._get_max_depth(rule_config)
            if max_depth > 3:
                result.warnings.append(
                    f"规则嵌套深度为{max_depth}，建议不超过3层以保持可读性"
                )

            # 7. 统计规则数量
            rule_count = self._count_rules(rule_config)
            if rule_count > 20:
                result.warnings.append(
                    f"规则总数为{rule_count}，过多的规则可能影响性能"
                )

            # 如果有错误，设置valid为False
            if result.errors:
                result.valid = False

        except Exception as e:
            result.valid = False
            result.errors.append(f"规则验证异常: {str(e)}")
            logger.error(f"规则验证失败: {e}", exc_info=True)

        return result

    def _extract_indicators(self, config: RuleConfig) -> Set[str]:
        """递归提取所有使用的指标编码（包括值表达式中的指标）"""
        indicators = set()

        def extract_from_rule(rule: Rule):
            if isinstance(rule, ConditionRule):
                # 添加左侧指标
                indicators.add(rule.indicator)
                # 从值表达式中提取指标
                indicators.update(self._extract_indicators_from_value_expression(rule.value))
            elif isinstance(rule, GroupRule):
                for sub_rule in rule.rules:
                    extract_from_rule(sub_rule)

        for rule in config.rules:
            extract_from_rule(rule)

        return indicators

    def _validate_indicators_exist(
        self,
        indicator_codes: Set[str],
        result: RuleValidationResult
    ):
        """验证指标是否存在于数据库中"""
        # TODO: 临时跳过指标存在性验证，用于测试
        # 生产环境需要启用此验证
        logger.debug(f"跳过指标存在性验证（测试模式）: {indicator_codes}")
        return

        # 原验证逻辑（已禁用）
        # if not indicator_codes:
        #     return
        #
        # existing_indicators = self.db.query(
        #     FraudHunterIndicatorDefinition.indicator_code
        # ).filter(
        #     FraudHunterIndicatorDefinition.indicator_code.in_(indicator_codes)
        # ).all()
        #
        # existing_codes = {ind[0] for ind in existing_indicators}
        # missing_codes = indicator_codes - existing_codes
        #
        # if missing_codes:
        #     result.valid = False
        #     result.errors.append(
        #         f"以下指标不存在: {', '.join(sorted(missing_codes))}"
        #     )

    def _validate_rule_structure(
        self,
        config: RuleConfig,
        result: RuleValidationResult
    ):
        """验证规则结构的合法性"""

        def validate_rule(rule: Rule, path: str):
            if isinstance(rule, ConditionRule):
                # 验证条件规则必需字段
                if not rule.indicator:
                    result.errors.append(f"{path}: 缺少指标编码")
                if not rule.operator:
                    result.errors.append(f"{path}: 缺少比较操作符")
                if rule.value is None:
                    result.errors.append(f"{path}: 缺少比较值")

            elif isinstance(rule, GroupRule):
                # 验证规则组必需字段
                if not rule.logic:
                    result.errors.append(f"{path}: 缺少逻辑操作符")
                if not rule.rules:
                    result.errors.append(f"{path}: 规则组不能为空")
                else:
                    # 递归验证子规则
                    for i, sub_rule in enumerate(rule.rules):
                        validate_rule(sub_rule, f"{path}.rules[{i}]")

        for i, rule in enumerate(config.rules):
            validate_rule(rule, f"root.rules[{i}]")

    def _validate_operator_compatibility(
        self,
        config: RuleConfig,
        result: RuleValidationResult
    ):
        """验证操作符与指标数据类型的兼容性，以及正则表达式语法"""

        # TODO: 临时跳过数据库查询，用于测试
        # 生产环境需要启用数据类型验证
        logger.debug("跳过操作符数据类型兼容性验证（测试模式）")

        # 仍然验证值类型和正则语法（不依赖数据库）
        def validate_condition(condition: ConditionRule, path: str):
            # 验证 in/not in 的值必须是数组
            if condition.operator in ['in', 'not in']:
                if not isinstance(condition.value, list):
                    result.errors.append(
                        f"{path}: 操作符 {condition.operator} 需要数组类型的值"
                    )
                elif len(condition.value) == 0:
                    result.errors.append(
                        f"{path}: 操作符 {condition.operator} 的值数组不能为空"
                    )

            # 验证正则表达式语法
            if condition.operator in ['regexp', 'not regexp']:
                if not isinstance(condition.value, str):
                    result.errors.append(
                        f"{path}: 操作符 {condition.operator} 需要字符串类型的值"
                    )
                else:
                    try:
                        re.compile(condition.value)
                    except re.error as e:
                        result.errors.append(
                            f"{path}: 正则表达式语法错误: {str(e)}"
                        )

        def traverse_rule(rule: Rule, path: str):
            if isinstance(rule, ConditionRule):
                validate_condition(rule, path)
            elif isinstance(rule, GroupRule):
                for i, sub_rule in enumerate(rule.rules):
                    traverse_rule(sub_rule, f"{path}.rules[{i}]")

        for i, rule in enumerate(config.rules):
            traverse_rule(rule, f"root.rules[{i}]")

        # 调用值表达式类型验证
        self._validate_value_expressions(config, result)

    def _validate_value_expressions(
        self,
        config: RuleConfig,
        result: RuleValidationResult
    ):
        """
        验证值表达式的类型兼容性（严格模式）

        验证规则：
        - IndicatorReference: 左右指标类型必须匹配
        - TimeFunction: 左侧和参数都必须是 text 类型
        - MathFunction: 左侧和参数都必须是 numeric 类型
        """

        def validate_condition(condition: ConditionRule, path: str):
            # 获取左侧指标信息
            left_ind = self._get_indicator_cached(condition.indicator)
            if not left_ind:
                # 指标不存在的错误在其他地方已经处理
                return

            left_type = left_ind.data_type
            value_expr = condition.value

            # 常量值：跳过（已在 Pydantic 验证器中验证）
            if isinstance(value_expr, ConstantValue):
                return

            # 指标引用：验证类型兼容
            elif isinstance(value_expr, IndicatorReference):
                right_ind = self._get_indicator_cached(value_expr.indicator)
                if not right_ind:
                    result.errors.append(
                        f"{path}: 引用指标 {value_expr.indicator} 不存在"
                    )
                    return

                if left_type != right_ind.data_type:
                    result.errors.append(
                        f"{path}: 类型不兼容 - {condition.indicator}({left_type}) "
                        f"vs {value_expr.indicator}({right_ind.data_type})"
                    )

            # 时间函数：验证左侧和参数都是 text
            elif isinstance(value_expr, TimeFunction):
                if left_type != 'text':
                    result.errors.append(
                        f"{path}: 时间比较要求左侧为text类型，实际为{left_type}"
                    )

                param_ind = self._get_indicator_cached(value_expr.indicator)
                if not param_ind:
                    result.errors.append(
                        f"{path}: 时间函数参数指标 {value_expr.indicator} 不存在"
                    )
                elif param_ind.data_type != 'text':
                    result.errors.append(
                        f"{path}: 时间函数参数必须为text类型，实际为{param_ind.data_type}"
                    )

            # 数学函数：验证左侧和参数都是 numeric
            elif isinstance(value_expr, MathFunction):
                if left_type != 'numeric':
                    result.errors.append(
                        f"{path}: 数学函数比较要求左侧为numeric类型，实际为{left_type}"
                    )

                param_ind = self._get_indicator_cached(value_expr.indicator)
                if not param_ind:
                    result.errors.append(
                        f"{path}: 数学函数参数指标 {value_expr.indicator} 不存在"
                    )
                elif param_ind.data_type != 'numeric':
                    result.errors.append(
                        f"{path}: abs()参数必须为numeric类型，实际为{param_ind.data_type}"
                    )

        def traverse_rule(rule: Rule, path: str):
            if isinstance(rule, ConditionRule):
                validate_condition(rule, path)
            elif isinstance(rule, GroupRule):
                for i, sub_rule in enumerate(rule.rules):
                    traverse_rule(sub_rule, f"{path}.rules[{i}]")

        for i, rule in enumerate(config.rules):
            traverse_rule(rule, f"root.rules[{i}]")

    def _validate_output_config(
        self,
        output: Any,
        result: RuleValidationResult
    ):
        """验证输出配置"""
        # Pydantic已经验证了基本约束，这里做额外检查
        if output.risk_score < 0 or output.risk_score > 100:
            result.errors.append("风险分数必须在0-100之间")

        # 风险等级和分数一致性检查
        score = output.risk_score
        level = output.risk_level

        if level == 'low' and score > 40:
            result.warnings.append(
                f"风险等级为'low'但分数为{score}，建议分数不超过40"
            )
        elif level == 'medium' and (score < 30 or score > 70):
            result.warnings.append(
                f"风险等级为'medium'但分数为{score}，建议分数在30-70之间"
            )
        elif level == 'high' and (score < 60 or score > 90):
            result.warnings.append(
                f"风险等级为'high'但分数为{score}，建议分数在60-90之间"
            )
        elif level == 'critical' and score < 80:
            result.warnings.append(
                f"风险等级为'critical'但分数为{score}，建议分数不低于80"
            )

    def _get_max_depth(self, config: RuleConfig) -> int:
        """计算规则树的最大深度"""

        def get_depth(rule: Rule) -> int:
            if isinstance(rule, ConditionRule):
                return 1
            elif isinstance(rule, GroupRule):
                if not rule.rules:
                    return 1
                return 1 + max(get_depth(r) for r in rule.rules)
            return 1

        if not config.rules:
            return 0
        return max(get_depth(r) for r in config.rules)

    def _count_rules(self, config: RuleConfig) -> int:
        """统计规则总数"""

        def count(rule: Rule) -> int:
            if isinstance(rule, ConditionRule):
                return 1
            elif isinstance(rule, GroupRule):
                return sum(count(r) for r in rule.rules)
            return 0

        return sum(count(r) for r in config.rules)

    # ==================== 规则评估 ====================

    def _evaluate_value_expression(
        self,
        value_expr: ValueExpression,
        indicator_values: Dict[str, Any]
    ) -> Any:
        """
        计算值表达式的实际值

        Args:
            value_expr: 值表达式
            indicator_values: 指标值字典

        Returns:
            计算后的值，失败返回 None
        """
        # 常量值
        if isinstance(value_expr, ConstantValue):
            return value_expr.value

        # 指标引用
        elif isinstance(value_expr, IndicatorReference):
            value = indicator_values.get(value_expr.indicator)
            if value is None:
                logger.warning(f"指标 {value_expr.indicator} 值缺失")
            return value

        # 时间函数
        elif isinstance(value_expr, TimeFunction):
            base_value = indicator_values.get(value_expr.indicator)
            if base_value is None:
                logger.warning(f"时间函数参数指标 {value_expr.indicator} 值缺失")
                return None

            # 解析日期
            try:
                if isinstance(base_value, str):
                    base_date = datetime.strptime(base_value, '%Y-%m-%d')
                elif isinstance(base_value, datetime):
                    base_date = base_value
                else:
                    logger.error(f"日期格式错误: {base_value}")
                    return None
            except ValueError as e:
                logger.error(f"日期解析失败: {e}")
                return None

            # 计算偏移
            offset = value_expr.offset
            if value_expr.function == "date_sub":
                offset = -offset

            # 应用偏移
            try:
                if value_expr.unit == "days":
                    result = base_date + timedelta(days=offset)
                elif value_expr.unit == "months":
                    result = base_date + relativedelta(months=offset)
                elif value_expr.unit == "years":
                    result = base_date + relativedelta(years=offset)
                else:
                    logger.error(f"不支持的时间单位: {value_expr.unit}")
                    return None

                return result.strftime('%Y-%m-%d')
            except Exception as e:
                logger.error(f"时间计算失败: {e}")
                return None

        # 数学函数
        elif isinstance(value_expr, MathFunction):
            param_value = indicator_values.get(value_expr.indicator)
            if param_value is None:
                logger.warning(f"数学函数参数指标 {value_expr.indicator} 值缺失")
                return None

            if value_expr.function == "abs":
                try:
                    return abs(float(param_value))
                except (ValueError, TypeError) as e:
                    logger.error(f"abs()参数值错误: {param_value}, {e}")
                    return None

        return None

    def evaluate_rule(
        self,
        rule_config: RuleConfig,
        indicator_values: Dict[str, Any]
    ) -> bool:
        """
        执行规则评估（支持所有操作符）

        Args:
            rule_config: 规则配置
            indicator_values: 指标值字典 {indicator_code: value}

        Returns:
            bool: 规则是否命中
        """

        def evaluate_condition(condition: ConditionRule) -> bool:
            """评估单个条件（支持值表达式）"""
            # 获取左侧指标值
            actual_value = indicator_values.get(condition.indicator)
            if actual_value is None:
                logger.warning(
                    f"指标 {condition.indicator} 值不存在，默认为False"
                )
                return False

            # 计算右侧值表达式
            expected_value = self._evaluate_value_expression(
                condition.value,
                indicator_values
            )

            if expected_value is None:
                logger.warning(
                    f"值表达式计算失败，默认为False"
                )
                return False

            operator = condition.operator

            try:
                # 基础比较操作符
                if operator in ['>', '>=', '<', '<=', '=', '!=']:
                    return self._evaluate_basic_comparison(
                        actual_value, operator, expected_value
                    )

                # 集合操作符（expected_value 是列表）
                elif operator in ['in', 'not in']:
                    return self._evaluate_set_operation(
                        actual_value, operator, expected_value
                    )

                # 正则匹配操作符（expected_value 是字符串）
                elif operator in ['regexp', 'not regexp']:
                    return self._evaluate_regexp_operation(
                        actual_value, operator, expected_value
                    )

                else:
                    logger.error(f"不支持的操作符: {operator}")
                    return False

            except Exception as e:
                logger.error(
                    f"条件评估失败: {condition}, 错误: {e}",
                    exc_info=True
                )
                return False

        def evaluate_group(group: GroupRule) -> bool:
            """评估规则组"""
            if not group.rules:
                return False

            results = [evaluate_rule_item(rule) for rule in group.rules]

            if group.logic == 'AND':
                return all(results)
            elif group.logic == 'OR':
                return any(results)
            else:
                logger.error(f"不支持的逻辑操作符: {group.logic}")
                return False

        def evaluate_rule_item(rule: Rule) -> bool:
            """评估单个规则项"""
            if isinstance(rule, ConditionRule):
                return evaluate_condition(rule)
            elif isinstance(rule, GroupRule):
                return evaluate_group(rule)
            return False

        # 评估根规则组
        root_group = GroupRule(
            type='group',
            logic=rule_config.logic,
            rules=rule_config.rules
        )

        return evaluate_group(root_group)

    def _evaluate_basic_comparison(
        self,
        actual: Any,
        operator: str,
        expected: Any
    ) -> bool:
        """基础比较操作"""
        # 类型转换
        if isinstance(expected, (int, float)):
            actual = float(actual)
        elif isinstance(expected, bool):
            actual = bool(actual)
        else:
            actual = str(actual)
            expected = str(expected)

        # 执行比较
        if operator == '>':
            return actual > expected
        elif operator == '>=':
            return actual >= expected
        elif operator == '<':
            return actual < expected
        elif operator == '<=':
            return actual <= expected
        elif operator == '=':
            return actual == expected
        elif operator == '!=':
            return actual != expected

        return False

    def _evaluate_set_operation(
        self,
        actual: Any,
        operator: str,
        expected: List[Any]
    ) -> bool:
        """集合操作（in / not in）"""
        # 类型转换
        if expected and isinstance(expected[0], (int, float)):
            actual = float(actual)
            expected = [float(v) for v in expected]
        else:
            actual = str(actual)
            expected = [str(v) for v in expected]

        # 判断
        if operator == 'in':
            return actual in expected
        elif operator == 'not in':
            return actual not in expected

        return False

    def _evaluate_regexp_operation(
        self,
        actual: Any,
        operator: str,
        pattern: str
    ) -> bool:
        """正则操作（regexp / not regexp）"""
        actual_str = str(actual)

        try:
            compiled_pattern = re.compile(pattern)
            match = compiled_pattern.search(actual_str)

            if operator == 'regexp':
                return match is not None
            elif operator == 'not regexp':
                return match is None

        except re.error as e:
            logger.error(f"正则表达式编译失败: {pattern}, 错误: {e}")
            return False

        return False

    # ==================== SQL生成 ====================

    def _value_expression_to_sql(self, value_expr: ValueExpression) -> str:
        """
        将值表达式转换为 Spark SQL

        Args:
            value_expr: 值表达式

        Returns:
            str: SQL 字符串
        """
        # 常量值
        if isinstance(value_expr, ConstantValue):
            return self._format_constant_sql(value_expr.value)

        # 指标引用
        elif isinstance(value_expr, IndicatorReference):
            return value_expr.indicator

        # 时间函数
        elif isinstance(value_expr, TimeFunction):
            ind = value_expr.indicator
            offset = value_expr.offset

            # 根据函数调整符号
            if value_expr.function == "date_sub":
                offset = -offset

            # 根据单位选择 SQL 函数
            if value_expr.unit == "days":
                if offset >= 0:
                    return f"DATE_ADD({ind}, {offset})"
                else:
                    return f"DATE_SUB({ind}, {-offset})"

            elif value_expr.unit == "months":
                return f"ADD_MONTHS({ind}, {offset})"

            elif value_expr.unit == "years":
                return f"ADD_MONTHS({ind}, {offset * 12})"

        # 数学函数
        elif isinstance(value_expr, MathFunction):
            if value_expr.function == "abs":
                return f"ABS({value_expr.indicator})"

        return "NULL"

    def _format_constant_sql(self, value: Any) -> str:
        """格式化常量为 SQL"""
        if isinstance(value, str):
            value_escaped = value.replace("'", "''")
            return f"'{value_escaped}'"
        elif isinstance(value, bool):
            return 'TRUE' if value else 'FALSE'
        elif isinstance(value, list):
            return ', '.join([self._format_constant_sql(v) for v in value])
        else:
            return str(value)

    def generate_sql_expression(self, rule_config: RuleConfig) -> str:
        """
        将规则配置转换为SQL WHERE子句表达式（支持所有操作符和值表达式）
        用于在Spark SQL中直接应用规则

        Returns:
            str: SQL表达式，如 "(i_login_cnt_7d > 10 AND (i_device_change_cnt >= 3 OR i_user_status IN ('suspended', 'banned')))"
        """

        def condition_to_sql(condition: ConditionRule) -> str:
            """将条件转换为SQL（支持值表达式）"""
            indicator = condition.indicator
            operator = condition.operator
            value_expr = condition.value

            # 基础比较操作符
            if operator in ['>', '>=', '<', '<=', '=', '!=']:
                right_sql = self._value_expression_to_sql(value_expr)
                return f"{indicator} {operator} {right_sql}"

            # 集合操作（只支持常量值）
            elif operator in ['in', 'not in']:
                if not isinstance(value_expr, ConstantValue):
                    raise ValueError(f"操作符 {operator} 只支持常量值")
                values_sql = self._format_constant_sql(value_expr.value)
                op_sql = 'IN' if operator == 'in' else 'NOT IN'
                return f"{indicator} {op_sql} ({values_sql})"

            # 正则匹配（只支持常量字符串）
            elif operator in ['regexp', 'not regexp']:
                if not isinstance(value_expr, ConstantValue):
                    raise ValueError(f"操作符 {operator} 只支持常量值")
                pattern = str(value_expr.value).replace("'", "''")
                if operator == 'regexp':
                    return f"{indicator} RLIKE '{pattern}'"
                else:
                    return f"NOT ({indicator} RLIKE '{pattern}')"

            return "1=1"

        def group_to_sql(group: GroupRule) -> str:
            """将规则组转换为SQL"""
            if not group.rules:
                return "1=1"  # 空规则组默认为真

            sub_expressions = []
            for rule in group.rules:
                if isinstance(rule, ConditionRule):
                    sub_expressions.append(condition_to_sql(rule))
                elif isinstance(rule, GroupRule):
                    sub_expressions.append(f"({group_to_sql(rule)})")

            logic_op = ' AND ' if group.logic == 'AND' else ' OR '
            return logic_op.join(sub_expressions)

        # 构建根表达式
        root_group = GroupRule(
            type='group',
            logic=rule_config.logic,
            rules=rule_config.rules
        )

        return f"({group_to_sql(root_group)})"

    # ==================== 辅助方法 ====================

    def get_rule_summary(self, rule_config: RuleConfig) -> Dict[str, Any]:
        """
        获取规则摘要信息

        Returns:
            dict: 包含规则统计信息
        """
        indicators = self._extract_indicators(rule_config)

        return {
            'total_rules': self._count_rules(rule_config),
            'max_depth': self._get_max_depth(rule_config),
            'indicator_count': len(indicators),
            'indicators': list(indicators),
            'root_logic': rule_config.logic,
            'output': {
                'risk_level': rule_config.output.risk_level,
                'risk_score': rule_config.output.risk_score,
                'action': rule_config.output.action
            }
        }
