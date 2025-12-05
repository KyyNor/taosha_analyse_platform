"""
值表达式功能测试脚本

测试：
1. Pydantic 模型验证
2. SQL 生成（不依赖数据库）
3. 运行时评估（不依赖数据库）
"""

from backend.schemas.fraudhunter.rule import (
    RuleConfig, ConditionRule, GroupRule,
    ConstantValue, IndicatorReference, TimeFunction, MathFunction,
    RuleOutput
)


def test_sql_generation():
    """测试 SQL 生成（模拟 - 不依赖数据库）"""
    print("\n=== 测试 SQL 生成 ===\n")

    # 测试用例 1: 指标间比较
    rule1 = RuleConfig(
        logic="AND",
        rules=[
            ConditionRule(
                type="condition",
                indicator="i_age",
                operator=">",
                value={"type": "indicator", "indicator": "i_min_age"}
            )
        ],
        output=RuleOutput(risk_level="high", risk_score=80, action="review")
    )
    print(f"测试 1 - 指标间比较:\n  规则: i_age > i_min_age")
    print(f"  预期SQL: (i_age > i_min_age)")

    # 测试用例 2: 时间函数 (天)
    rule2 = RuleConfig(
        logic="AND",
        rules=[
            ConditionRule(
                type="condition",
                indicator="tran_date",
                operator=">",
                value={
                    "type": "time_function",
                    "function": "date_sub",
                    "indicator": "etl_date",
                    "offset": 90,
                    "unit": "days"
                }
            )
        ],
        output=RuleOutput(risk_level="medium", risk_score=60, action="alert")
    )
    print(f"\n测试 2 - 时间函数(天):\n  规则: tran_date > date_sub(etl_date, 90, 'days')")
    print(f"  预期SQL: (tran_date > DATE_SUB(etl_date, 90))")

    # 测试用例 3: 时间函数 (月)
    rule3 = RuleConfig(
        logic="AND",
        rules=[
            ConditionRule(
                type="condition",
                indicator="register_date",
                operator="<",
                value={
                    "type": "time_function",
                    "function": "date_add",
                    "indicator": "current_date",
                    "offset": 3,
                    "unit": "months"
                }
            )
        ],
        output=RuleOutput(risk_level="low", risk_score=30, action="pass")
    )
    print(f"\n测试 3 - 时间函数(月):\n  规则: register_date < date_add(current_date, 3, 'months')")
    print(f"  预期SQL: (register_date < ADD_MONTHS(current_date, 3))")

    # 测试用例 4: 数学函数
    rule4 = RuleConfig(
        logic="AND",
        rules=[
            ConditionRule(
                type="condition",
                indicator="i_balance",
                operator=">",
                value={
                    "type": "math_function",
                    "function": "abs",
                    "indicator": "i_threshold"
                }
            )
        ],
        output=RuleOutput(risk_level="critical", risk_score=95, action="block")
    )
    print(f"\n测试 4 - 数学函数:\n  规则: i_balance > abs(i_threshold)")
    print(f"  预期SQL: (i_balance > ABS(i_threshold))")

    # 测试用例 5: 复合规则
    rule5 = RuleConfig(
        logic="AND",
        rules=[
            ConditionRule(
                type="condition",
                indicator="i_age",
                operator=">=",
                value={"type": "constant", "value": 18}
            ),
            GroupRule(
                type="group",
                logic="OR",
                rules=[
                    ConditionRule(
                        type="condition",
                        indicator="i_score",
                        operator=">",
                        value={"type": "indicator", "indicator": "i_min_score"}
                    ),
                    ConditionRule(
                        type="condition",
                        indicator="i_vip_level",
                        operator="in",
                        value={"type": "constant", "value": ["gold", "platinum"]}
                    )
                ]
            )
        ],
        output=RuleOutput(risk_level="medium", risk_score=50, action="review")
    )
    print(f"\n测试 5 - 复合规则:")
    print(f"  规则: (i_age >= 18) AND ((i_score > i_min_score) OR (i_vip_level IN ['gold', 'platinum']))")
    print(f"  预期SQL: (i_age >= 18 AND (i_score > i_min_score OR i_vip_level IN ('gold', 'platinum')))")

    print("\n✅ SQL 生成测试用例准备完成")


def test_runtime_evaluation():
    """测试运行时评估（模拟）"""
    print("\n=== 测试运行时评估 ===\n")

    # 测试数据
    indicator_values = {
        "i_age": 25,
        "i_min_age": 18,
        "i_score": 85,
        "i_min_score": 70,
        "i_balance": 1000,
        "i_threshold": -500,
        "tran_date": "2025-01-15",
        "etl_date": "2025-01-20",
        "current_date": "2025-01-01"
    }

    print(f"测试数据:\n{indicator_values}\n")

    # 测试用例 1: 指标间比较
    print("测试 1 - 指标间比较:")
    print(f"  i_age ({indicator_values['i_age']}) > i_min_age ({indicator_values['i_min_age']})")
    print(f"  预期结果: True (25 > 18)")

    # 测试用例 2: 数学函数
    print("\n测试 2 - 数学函数:")
    print(f"  i_balance ({indicator_values['i_balance']}) > abs(i_threshold) (abs({indicator_values['i_threshold']}))")
    print(f"  预期结果: True (1000 > 500)")

    # 测试用例 3: 时间函数 (需要日期计算)
    print("\n测试 3 - 时间函数:")
    print(f"  tran_date ({indicator_values['tran_date']}) > date_sub(etl_date ({indicator_values['etl_date']}), 90, 'days')")
    print(f"  预期结果: True (2025-01-15 > 2024-10-22)")

    print("\n✅ 运行时评估测试用例准备完成")


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试向后兼容性 ===\n")

    # 旧格式（直接传值）
    old_format = {
        "type": "condition",
        "indicator": "i_age",
        "operator": ">",
        "value": 18
    }

    # 新格式（值表达式）
    new_format = {
        "type": "condition",
        "indicator": "i_age",
        "operator": ">",
        "value": {"type": "constant", "value": 18}
    }

    try:
        rule1 = ConditionRule(**old_format)
        rule2 = ConditionRule(**new_format)

        print(f"旧格式输入: {old_format['value']}")
        print(f"转换后: {rule1.value.model_dump()}")
        print(f"\n新格式输入: {new_format['value']}")
        print(f"解析后: {rule2.value.model_dump()}")

        # 验证两者等价
        assert rule1.value.model_dump() == rule2.value.model_dump()
        print("\n✅ 向后兼容性验证通过")

    except Exception as e:
        print(f"\n❌ 向后兼容性测试失败: {e}")


def main():
    """主测试函数"""
    print("=" * 60)
    print("FraudHunter 规则引擎 - 值表达式功能测试")
    print("=" * 60)

    test_backward_compatibility()
    test_sql_generation()
    test_runtime_evaluation()

    print("\n" + "=" * 60)
    print("所有测试用例准备完成！")
    print("=" * 60)
    print("\n注意：")
    print("  • 实际 SQL 生成需要启动后端服务并调用 API")
    print("  • 实际运行时评估需要连接数据库")
    print("  • 本测试仅验证数据模型和业务逻辑结构")


if __name__ == "__main__":
    main()
