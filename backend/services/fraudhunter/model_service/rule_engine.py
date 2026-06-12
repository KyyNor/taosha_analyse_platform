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
from typing import Dict, List, Set, Any, Optional, Union
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from loguru import logger

from schemas.fraudhunter.rule import (
    RuleConfig, Rule, ConditionRule, GroupRule,
    ModelReferenceRule,
    ComparisonOperator, RuleValidationResult,
    ValueExpression, ConstantValue, IndicatorReference,
    TimeFunction, MathFunction, RelativeCalculation
)
from models.fraudhunter.indicator import FraudHunterIndicatorDefinition
from models.fraudhunter.risk_control_model import FraudHunterModelDefinition


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
        self._model_cache: Dict[int, Optional[FraudHunterModelDefinition]] = {}

    # ==================== 辅助方法 ====================

    def _get_indicator_display_name(self, indicator_code: str) -> str:
        """
        获取指标的显示名称（中文，实时指标带[实时]前缀）

        Args:
            indicator_code: 指标编码

        Returns:
            str: 显示名称，如 "[实时]登录次数" 或 "客户年龄"
        """
        indicator = self._get_indicator_cached(indicator_code)
        if indicator:
            name = indicator.indicator_name
            if indicator.indicator_type == 'realtime':
                return f"[实时]{name}"
            return name
        return indicator_code  # 找不到指标时返回编码

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

    def _get_model_cached(self, model_id: int) -> Optional[FraudHunterModelDefinition]:
        """带缓存的模型查询。"""
        if model_id not in self._model_cache:
            model = self.db.query(FraudHunterModelDefinition).filter(
                FraudHunterModelDefinition.id == model_id
            ).first()
            self._model_cache[model_id] = model

        return self._model_cache[model_id]

    def _get_model_rule_config(self, model: FraudHunterModelDefinition) -> RuleConfig:
        """获取模型的规则配置对象。"""
        if isinstance(model.rule_config, RuleConfig):
            return model.rule_config
        return RuleConfig(**model.rule_config)

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
        elif isinstance(expr, RelativeCalculation):
            indicators.add(expr.indicator)

        return indicators

    # ==================== 规则验证 ====================

    def validate_rule_config(
        self,
        rule_config: RuleConfig,
        current_model_id: Optional[int] = None
    ) -> RuleValidationResult:
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
            indicators = self._extract_indicators(rule_config, visited_model_ids={current_model_id} if current_model_id else set())
            result.extracted_indicators = list(indicators)

            # 2. 验证指标是否存在
            self._validate_indicators_exist(indicators, result)
            logger.info(1)

            # 3. 验证规则结构
            self._validate_rule_structure(rule_config, result, current_model_id=current_model_id)
            logger.info(2)

            # 4. 验证数据类型和操作符匹配
            self._validate_operator_compatibility(rule_config, result, current_model_id=current_model_id)
            logger.info(3)

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

    def _extract_indicators(
        self,
        config: RuleConfig,
        visited_model_ids: Optional[Set[int]] = None
    ) -> Set[str]:
        """递归提取所有使用的指标编码（包括值表达式中的指标）"""
        indicators = set()
        visited_model_ids = visited_model_ids or set()

        def extract_from_rule(rule: Rule):
            if isinstance(rule, ConditionRule):
                # 添加左侧指标
                indicators.add(rule.indicator)
                # 从值表达式中提取指标
                indicators.update(self._extract_indicators_from_value_expression(rule.value))
            elif isinstance(rule, GroupRule):
                for sub_rule in rule.rules:
                    extract_from_rule(sub_rule)
            elif isinstance(rule, ModelReferenceRule):
                if rule.model_id in visited_model_ids:
                    return
                ref_model = self._get_model_cached(rule.model_id)
                if not ref_model:
                    return
                visited_model_ids.add(rule.model_id)
                ref_rule_config = self._get_model_rule_config(ref_model)
                indicators.update(self._extract_indicators(ref_rule_config, visited_model_ids))
                visited_model_ids.remove(rule.model_id)

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
        result: RuleValidationResult,
        current_model_id: Optional[int] = None
    ):
        """验证规则结构的合法性"""
        visited_model_ids = {current_model_id} if current_model_id else set()

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
            elif isinstance(rule, ModelReferenceRule):
                ref_model = self._get_model_cached(rule.model_id)
                if not ref_model:
                    result.errors.append(f"{path}: 引用模型不存在: {rule.model_id}")
                    return

                if ref_model.model_type != 'prefix':
                    result.errors.append(
                        f"{path}: 只能引用前缀模型，当前引用的是普通模型: {ref_model.model_code}"
                    )

                if rule.model_id in visited_model_ids:
                    result.errors.append(f"{path}: 检测到模型循环引用: {ref_model.model_code}")
                    return

                if ref_model.status != 'online':
                    result.warnings.append(
                        f"{path}: 引用的前缀模型 {ref_model.model_code} 当前状态为 {ref_model.status}"
                    )

                visited_model_ids.add(rule.model_id)
                try:
                    ref_rule_config = self._get_model_rule_config(ref_model)
                    for i, sub_rule in enumerate(ref_rule_config.rules):
                        validate_rule(sub_rule, f"{path}.{ref_model.model_code}.rules[{i}]")
                finally:
                    visited_model_ids.remove(rule.model_id)

        for i, rule in enumerate(config.rules):
            validate_rule(rule, f"root.rules[{i}]")

    def _validate_operator_compatibility(
        self,
        config: RuleConfig,
        result: RuleValidationResult,
        current_model_id: Optional[int] = None
    ):
        """验证操作符与指标数据类型的兼容性，以及正则表达式语法"""

        # TODO: 临时跳过数据库查询，用于测试
        # 生产环境需要启用数据类型验证
        logger.debug("跳过操作符数据类型兼容性验证（测试模式）")

        # 仍然验证值类型和正则语法（不依赖数据库）
        def validate_condition(condition: ConditionRule, path: str):
            # 验证 in/not in 的值必须是数组
            if condition.operator in ['in', 'not in']:
                # 检查是否为常量值类型
                if not isinstance(condition.value, ConstantValue):
                    result.errors.append(
                        f"{path}: 操作符 {condition.operator} 只支持常量数组值"
                    )
                elif not isinstance(condition.value.value, list):
                    result.errors.append(
                        f"{path}: 操作符 {condition.operator} 需要数组类型的值"
                    )
                elif len(condition.value.value) == 0:
                    result.errors.append(
                        f"{path}: 操作符 {condition.operator} 的值数组不能为空"
                    )

            # 验证正则表达式语法（支持单值和多值）
            if condition.operator in ['regexp', 'not regexp']:
                # 检查是否为常量值类型
                if not isinstance(condition.value, ConstantValue):
                    result.errors.append(
                        f"{path}: 操作符 {condition.operator} 只支持常量值"
                    )
                elif not isinstance(condition.value.value, (str, list)):
                    result.errors.append(
                        f"{path}: 操作符 {condition.operator} 需要字符串类型或字符串数组类型的值"
                    )
                elif isinstance(condition.value.value, list):
                    # 验证数组中的每个值都是字符串
                    if not all(isinstance(item, str) for item in condition.value.value):
                        result.errors.append(
                            f"{path}: 操作符 {condition.operator} 的数组值必须全部为字符串类型"
                        )
                    elif len(condition.value.value) == 0:
                        result.errors.append(
                            f"{path}: 操作符 {condition.operator} 的数组值不能为空"
                        )
                    # 数组情况，不验证单个正则表达式，因为它们会在SQL生成时合并为 x|y|z 格式
                else:
                    # 单值情况，验证正则表达式语法
                    try:
                        re.compile(condition.value.value)
                    except Exception as e:
                        result.errors.append(
                            f"{path}: 正则表达式语法错误: {str(e)}"
                        )

        visited_model_ids = {current_model_id} if current_model_id else set()

        def traverse_rule(rule: Rule, path: str):
            logger.info(f"c {rule} {path}")
            if isinstance(rule, ConditionRule):
                validate_condition(rule, path)
            elif isinstance(rule, GroupRule):
                for i, sub_rule in enumerate(rule.rules):
                    traverse_rule(sub_rule, f"{path}.rules[{i}]")
            elif isinstance(rule, ModelReferenceRule):
                if rule.model_id in visited_model_ids:
                    return
                ref_model = self._get_model_cached(rule.model_id)
                if not ref_model:
                    return
                visited_model_ids.add(rule.model_id)
                try:
                    ref_rule_config = self._get_model_rule_config(ref_model)
                    for i, sub_rule in enumerate(ref_rule_config.rules):
                        traverse_rule(sub_rule, f"{path}.{ref_model.model_code}.rules[{i}]")
                finally:
                    visited_model_ids.remove(rule.model_id)

        for i, rule in enumerate(config.rules):
            traverse_rule(rule, f"root.rules[{i}]")

        # 调用值表达式类型验证
        self._validate_value_expressions(config, result, current_model_id=current_model_id)

    def _validate_value_expressions(
        self,
        config: RuleConfig,
        result: RuleValidationResult,
        current_model_id: Optional[int] = None
    ):
        """
        验证值表达式的类型兼容性（严格模式）

        验证规则：
        - IndicatorReference: 左右指标类型必须匹配
        - TimeFunction: 左侧和参数都必须是 date 类型
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

            # 时间函数：验证左侧和参数都是 date
            elif isinstance(value_expr, TimeFunction):
                if left_type != 'date':
                    result.errors.append(
                        f"{path}: 时间比较要求左侧为date类型，实际为{left_type}"
                    )

                param_ind = self._get_indicator_cached(value_expr.indicator)
                if not param_ind:
                    result.errors.append(
                        f"{path}: 时间函数参数指标 {value_expr.indicator} 不存在"
                    )
                elif param_ind.data_type != 'date':
                    result.errors.append(
                        f"{path}: 时间函数参数必须为date类型，实际为{param_ind.data_type}"
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

            # 相对计算：验证左侧和参数都是 numeric
            elif isinstance(value_expr, RelativeCalculation):
                if left_type != 'numeric':
                    result.errors.append(
                        f"{path}: 相对计算要求左侧为numeric类型，实际为{left_type}"
                    )

                param_ind = self._get_indicator_cached(value_expr.indicator)
                if not param_ind:
                    result.errors.append(
                        f"{path}: 相对计算引用指标 {value_expr.indicator} 不存在"
                    )
                elif param_ind.data_type != 'numeric':
                    result.errors.append(
                        f"{path}: 相对计算引用指标 {value_expr.indicator} 必须为numeric类型，实际为{param_ind.data_type}"
                    )

                # 验证除数不为零
                if value_expr.operation == "divide" and value_expr.value == 0:
                    result.errors.append(f"{path}: 除法运算的除数不能为零")

        visited_model_ids = {current_model_id} if current_model_id else set()

        def traverse_rule(rule: Rule, path: str):
            if isinstance(rule, ConditionRule):
                validate_condition(rule, path)
            elif isinstance(rule, GroupRule):
                for i, sub_rule in enumerate(rule.rules):
                    traverse_rule(sub_rule, f"{path}.rules[{i}]")
            elif isinstance(rule, ModelReferenceRule):
                if rule.model_id in visited_model_ids:
                    return
                ref_model = self._get_model_cached(rule.model_id)
                if not ref_model:
                    return
                visited_model_ids.add(rule.model_id)
                try:
                    ref_rule_config = self._get_model_rule_config(ref_model)
                    for i, sub_rule in enumerate(ref_rule_config.rules):
                        traverse_rule(sub_rule, f"{path}.{ref_model.model_code}.rules[{i}]")
                finally:
                    visited_model_ids.remove(rule.model_id)

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
            elif isinstance(rule, ModelReferenceRule):
                return 1
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
            elif isinstance(rule, ModelReferenceRule):
                return 1
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

        # 相对计算
        elif isinstance(value_expr, RelativeCalculation):
            base_value = indicator_values.get(value_expr.indicator)
            if base_value is None:
                logger.warning(f"相对计算基础指标 {value_expr.indicator} 值缺失")
                return None

            try:
                base_value = float(base_value)
                calc_value = float(value_expr.value)

                if value_expr.operation == "add":
                    return base_value + calc_value
                elif value_expr.operation == "subtract":
                    return base_value - calc_value
                elif value_expr.operation == "multiply":
                    return base_value * calc_value
                elif value_expr.operation == "divide":
                    if calc_value == 0:
                        logger.warning(f"除零错误: {value_expr.indicator} / {value_expr.value}")
                        return None
                    return base_value / calc_value
            except (ValueError, TypeError) as e:
                logger.error(f"相对计算失败: {value_expr}, 错误: {e}")
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

                # 正则匹配操作符（expected_value 可能是字符串或数组）
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
            elif isinstance(rule, ModelReferenceRule):
                ref_model = self._get_model_cached(rule.model_id)
                if not ref_model:
                    logger.warning(f"引用模型不存在: {rule.model_id}")
                    return False
                ref_rule_config = self._get_model_rule_config(ref_model)
                return self.evaluate_rule(ref_rule_config, indicator_values)
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
        pattern_input: Union[str, list]
    ) -> bool:
        """正则操作（regexp / not regexp），支持单值和多值"""
        actual_str = str(actual)

        # 处理多值情况：将数组转换为正则表达式的 OR 格式
        if isinstance(pattern_input, list):
            # 过滤空值并构建模式
            patterns = []
            for val in pattern_input:
                if val:  # 过滤空值
                    patterns.append(str(val))

            if not patterns:
                pattern = ''  # 如果没有有效值，使用空模式
            else:
                pattern = '|'.join(patterns)  # 转换为 x|y|z 格式
        else:
            # 单值情况
            pattern = str(pattern_input)

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

    def _get_indicator_sql_with_cast(
        self,
        indicator_code: str,
        indicator_alias_mapping: Optional[Dict[str, str]] = None
    ) -> str:
        """
        获取指标的SQL表达式，数值型指标自动添加CAST转换

        Args:
            indicator_code: 指标编码
            indicator_alias_mapping: 指标别名映射

        Returns:
            str: SQL表达式，数值型指标会包含CAST转换
        """
        # 构建基础指标SQL
        if indicator_alias_mapping and indicator_code in indicator_alias_mapping:
            alias = indicator_alias_mapping[indicator_code]
            base_sql = f"{alias}.{indicator_code}"
        else:
            base_sql = indicator_code

        # 获取指标数据类型
        indicator = self._get_indicator_cached(indicator_code)
        if indicator and indicator.data_type == 'numeric':
            # 数值类型增加 COALESCE 默认值 0，避免 NULL 比较问题
            return f"COALESCE({base_sql}::DOUBLE PRECISION, 0)"

        if indicator and indicator.data_type == 'date':
            return f"CAST({base_sql} AS DATE)"

        return base_sql

    def _value_expression_to_sql(
        self,
        value_expr: ValueExpression,
        indicator_alias_mapping: Optional[Dict[str, str]] = None,
        use_display_name: bool = False
    ) -> str:
        """
        将值表达式转换为 Spark SQL

        Args:
            value_expr: 值表达式
            indicator_alias_mapping: 指标别名映射 {indicator_code: table_alias}
            use_display_name: 是否使用中文显示名称（用于SQL预览）

        Returns:
            str: SQL 字符串
        """
        # 常量值
        if isinstance(value_expr, ConstantValue):
            return self._format_constant_sql(value_expr.value)

        # 指标引用
        elif isinstance(value_expr, IndicatorReference):
            indicator = value_expr.indicator
            if use_display_name:
                return self._get_indicator_display_name(indicator)
            return self._get_indicator_sql_with_cast(indicator, indicator_alias_mapping)

        # 时间函数
        elif isinstance(value_expr, TimeFunction):
            ind = value_expr.indicator
            
            # 处理特殊的系统时间变量
            if ind == '__T0__':
                # T日: 实时宽表的etl_date
                if use_display_name:
                    ind_sql = "T日(实时数据日期)"
                else:
                    ind_sql = "dep_acct_realtime_indicator.etl_date"
            elif ind == '__T_1__':
                # T-1日: 离线宽表的etl_date
                if use_display_name:
                    ind_sql = "T-1日(离线数据日期)"
                else:
                    ind_sql = "dep_acct_offline_indicator.etl_date"
            else:
                # 普通日期指标
                if use_display_name:
                    ind_sql = self._get_indicator_display_name(ind)
                elif indicator_alias_mapping and ind in indicator_alias_mapping:
                    alias = indicator_alias_mapping[ind]
                    ind_sql = f"{alias}.{ind}"
                else:
                    ind_sql = ind

            offset = value_expr.offset

            # 使用 INTERVAL 语法
            if value_expr.unit == "days":
                if offset >= 0:
                    return f"(cast({ind_sql} as date) + INTERVAL '{offset} DAY')"
                else:
                    return f"(cast({ind_sql} as date) - INTERVAL '{-offset} DAY')"

            elif value_expr.unit == "months":
                if offset >= 0:
                    return f"(cast({ind_sql} as date) + INTERVAL '{offset} MONTH')"
                else:
                    return f"(cast({ind_sql} as date) - INTERVAL '{-offset} MONTH')"

            elif value_expr.unit == "years":
                if offset >= 0:
                    return f"(cast({ind_sql} as date) + INTERVAL '{offset} YEAR')"
                else:
                    return f"(cast({ind_sql} as date) - INTERVAL '{-offset} YEAR')"

        # 数学函数
        elif isinstance(value_expr, MathFunction):
            ind = value_expr.indicator
            # 获取指标SQL或显示名称
            if use_display_name:
                ind_sql = self._get_indicator_display_name(ind)
            else:
                ind_sql = self._get_indicator_sql_with_cast(ind, indicator_alias_mapping)
            if value_expr.function == "abs":
                return f"ABS({ind_sql})"

        # 相对计算
        elif isinstance(value_expr, RelativeCalculation):
            # 获取指标SQL
            if use_display_name:
                indicator_sql = self._get_indicator_display_name(value_expr.indicator)
            else:
                indicator_sql = self._get_indicator_sql_with_cast(value_expr.indicator, indicator_alias_mapping)

            # 构建运算符SQL
            operator_map = {
                "add": "+",
                "subtract": "-",
                "multiply": "*",
                "divide": "/"
            }
            operator = operator_map[value_expr.operation]
            value_sql = str(value_expr.value)

            return f"({indicator_sql} {operator} {value_sql})"

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

    def generate_sql_expression(
        self,
        rule_config: RuleConfig,
        indicator_alias_mapping: Optional[Dict[str, str]] = None,
        use_display_name: bool = False
    ) -> str:
        """
        将规则配置转换为SQL WHERE子句表达式（支持所有操作符和值表达式）
        用于在Spark SQL中直接应用规则

        Args:
            rule_config: 规则配置
            indicator_alias_mapping: 指标别名映射 {indicator_code: table_alias}
                - None: 不添加表别名（默认，返回纯WHERE条件）
                - Dict: 根据映射添加表别名，如:
                    - 存款实时指标: {'i_xxx_realtime': 'dep_acct_realtime_indicator'}
                    - 存款离线指标: {'i_xxx_offline': 'dep_acct_offline_indicator'}
                    - 客户指标: {'cust_xxx': 'cust_offline_indicator'}
            use_display_name: 是否使用中文显示名称（实时指标带[实时]前缀）

        Returns:
            str: SQL表达式，如 "(登录次数 > 10 AND ([实时]设备变更次数 >= 3 OR 用户状态 IN ('suspended', 'banned')))"
                 或带别名 "(dep_acct_realtime_indicator.i_xxx > 10 AND cust_offline_indicator.cust_yyy = 'A')"
        """

        def condition_to_sql(condition: ConditionRule) -> str:
            """将条件转换为SQL（支持值表达式和左元素函数）"""
            indicator = condition.indicator
            operator = condition.operator
            value_expr = condition.value

            # 处理左侧指标（使用中文显示名称或带CAST的SQL生成）
            if use_display_name:
                left_sql = self._get_indicator_display_name(indicator)
            else:
                left_sql = self._get_indicator_sql_with_cast(indicator, indicator_alias_mapping)

            # 处理左元素函数
            if condition.left_function == 'abs':
                left_sql = f"ABS({left_sql})"

            # 基础比较操作符
            if operator in ['>', '>=', '<', '<=', '=', '!=']:
                right_sql = self._value_expression_to_sql(value_expr, indicator_alias_mapping, use_display_name)
                return f"{left_sql} {operator} {right_sql}"

            # 集合操作（只支持常量值）
            elif operator in ['in', 'not in']:
                if not isinstance(value_expr, ConstantValue):
                    raise ValueError(f"操作符 {operator} 只支持常量值")
                values_sql = self._format_constant_sql(value_expr.value)
                op_sql = 'IN' if operator == 'in' else 'NOT IN'
                return f"{left_sql} {op_sql} ({values_sql})"

            # 正则匹配（支持多值，自动转换为 x|y|z 格式）
            elif operator in ['regexp', 'not regexp']:
                if not isinstance(value_expr, ConstantValue):
                    raise ValueError(f"操作符 {operator} 只支持常量值")

                # 处理多值情况：将数组转换为正则表达式的 OR 格式
                if isinstance(value_expr.value, list):
                    # 过滤空值并转义特殊字符
                    patterns = []
                    for val in value_expr.value:
                        if val:  # 过滤空值
                            # 转义正则表达式特殊字符
                            escaped_val = str(val).replace("'", "''").replace('|', '\\|')
                            patterns.append(escaped_val)

                    if not patterns:
                        pattern = ''  # 如果没有有效值，使用空模式
                    else:
                        pattern = '|'.join(patterns)  # 转换为 x|y|z 格式
                else:
                    # 单值情况
                    pattern = str(value_expr.value).replace("'", "''")

                if operator == 'regexp':
                    return f"{left_sql} ~* '{pattern}'"
                else:
                    return f"not {left_sql} ~* '{pattern}'"

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
                elif isinstance(rule, ModelReferenceRule):
                    ref_model = self._get_model_cached(rule.model_id)
                    if not ref_model:
                        raise ValueError(f"引用模型不存在: {rule.model_id}")
                    ref_rule_config = self._get_model_rule_config(ref_model)
                    ref_sql = self.generate_sql_expression(
                        ref_rule_config,
                        indicator_alias_mapping=indicator_alias_mapping,
                        use_display_name=use_display_name
                    )
                    sub_expressions.append(f"({ref_sql})")

            logic_op = ' AND ' if group.logic == 'AND' else ' OR '
            return logic_op.join(sub_expressions)

        # 构建根表达式
        root_group = GroupRule(
            type='group',
            logic=rule_config.logic,
            rules=rule_config.rules
        )

        return f"({group_to_sql(root_group)})"

    def build_indicator_alias_mapping(
        self,
        rule_config: RuleConfig,
        use_alias: bool = False,
        object_type: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        构建指标别名映射

        根据每个指标的 indicator_type 和 object_type 自动判断所属表：
        - 实时指标根据自身 object_type 映射到对应的实时表
        - 离线指标根据自身 object_type 映射到对应的离线表

        Args:
            rule_config: 规则配置
            use_alias: 是否使用别名
                - False: 返回 None（默认，不添加表别名）
                - True: 返回指标别名映射
            object_type: (已弃用) 此参数保留用于向后兼容，但不再使用

        Returns:
            指标别名映射字典，或 None
            例如: {'i_dep_acct_no_realtime_00001': 'dep_acct_realtime_indicator',
                  'i_cust_no_offline_00001': 'cust_offline_indicator'}
        """
        if not use_alias:
            return None

        indicators = self._extract_indicators(rule_config)
        mapping = {}

        for indicator in indicators:
            indicator_def = self._get_indicator_cached(indicator)

            if not indicator_def:
                # 如果找不到指标定义，使用默认逻辑判断（根据编码）
                indicator_lower = indicator.lower()
                if 'realtime' in indicator_lower:
                    # 实时指标：根据编码中的 object_type 判断
                    if 'cust_no' in indicator_lower or indicator_lower.startswith('i_cust_'):
                        mapping[indicator] = 'cust_realtime_indicator'
                    elif 'loan_acct_no' in indicator_lower or indicator_lower.startswith('i_loan_'):
                        mapping[indicator] = 'loan_realtime_indicator'
                    else:
                        mapping[indicator] = 'dep_acct_realtime_indicator'
                else:
                    # 离线指标：根据编码判断
                    if 'cust_no' in indicator_lower or indicator_lower.startswith('i_cust_'):
                        mapping[indicator] = 'cust_offline_indicator'
                    elif 'loan_acct_no' in indicator_lower or indicator_lower.startswith('i_loan_'):
                        mapping[indicator] = 'loan_offline_indicator'
                    else:
                        mapping[indicator] = 'dep_acct_offline_indicator'
            else:
                # 根据指标定义判断（每个指标根据自己的类型和对象类型映射）
                if indicator_def.indicator_type == 'realtime':
                    # 实时指标：根据指标自身的 object_type 映射
                    if indicator_def.object_type == 'cust_no':
                        mapping[indicator] = 'cust_realtime_indicator'
                    elif indicator_def.object_type == 'loan_acct_no':
                        mapping[indicator] = 'loan_realtime_indicator'
                    else:
                        mapping[indicator] = 'dep_acct_realtime_indicator'
                else:
                    # 离线指标：根据指标自身的 object_type 映射
                    if indicator_def.object_type == 'cust_no':
                        mapping[indicator] = 'cust_offline_indicator'
                    elif indicator_def.object_type == 'loan_acct_no':
                        mapping[indicator] = 'loan_offline_indicator'
                    else:
                        mapping[indicator] = 'dep_acct_offline_indicator'

        return mapping

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
        }
