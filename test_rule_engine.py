#!/usr/bin/env python3
"""
规则引擎API测试脚本

用途: 测试规则引擎的各个API端点
运行: python test_rule_engine.py
"""

import requests
import json
from typing import Dict, Any

# 配置
BASE_URL = "http://localhost:50020/api/taosha/v1/fraudhunter/models"

# 测试数据
TEST_RULE_CONFIG = {
    "logic": "AND",
    "rules": [
        {
            "type": "condition",
            "indicator": "i_login_cnt_7d",
            "operator": ">",
            "value": 10
        },
        {
            "type": "condition",
            "indicator": "i_user_status",
            "operator": "in",
            "value": ["suspended", "banned", "frozen"]
        },
        {
            "type": "group",
            "logic": "OR",
            "rules": [
                {
                    "type": "condition",
                    "indicator": "i_device_change_cnt",
                    "operator": ">=",
                    "value": 3
                },
                {
                    "type": "condition",
                    "indicator": "i_user_name",
                    "operator": "regexp",
                    "value": "^admin|^test|^demo"
                }
            ]
        }
    ],
    "output": {
        "risk_level": "high",
        "risk_score": 85,
        "action": "review",
        "description": "高风险登录行为，需人工审核"
    }
}

TEST_INDICATOR_VALUES = {
    "i_login_cnt_7d": 15,
    "i_user_status": "suspended",
    "i_device_change_cnt": 5,
    "i_user_name": "admin_user"
}


def print_separator(title: str = ""):
    """打印分隔线"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'-'*60}\n")


def print_response(response: requests.Response, title: str = ""):
    """格式化打印响应"""
    if title:
        print(f"\n🔍 {title}")
        print_separator()

    print(f"状态码: {response.status_code}")
    print(f"\n响应数据:")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text)


def test_health_check():
    """测试健康检查"""
    print_separator("测试1: 健康检查")

    try:
        response = requests.get(f"{BASE_URL}/health")
        print_response(response, "健康检查")

        if response.status_code == 200:
            print("\n✅ 健康检查通过")
        else:
            print("\n❌ 健康检查失败")

        return response.status_code == 200

    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        return False


def test_validate_rule():
    """测试规则验证"""
    print_separator("测试2: 规则验证")

    try:
        response = requests.post(
            f"{BASE_URL}/validate-rule",
            json=TEST_RULE_CONFIG,
            headers={"Content-Type": "application/json"}
        )
        print_response(response, "规则验证")

        if response.status_code == 200:
            data = response.json()
            if data.get("valid"):
                print("\n✅ 规则验证通过")
                print(f"提取的指标: {data.get('extracted_indicators')}")
                if data.get('warnings'):
                    print(f"警告: {data.get('warnings')}")
            else:
                print("\n❌ 规则验证失败")
                print(f"错误: {data.get('errors')}")
        else:
            print("\n❌ 请求失败")

        return response.status_code == 200

    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        return False


def test_preview_sql():
    """测试SQL预览"""
    print_separator("测试3: SQL预览")

    try:
        response = requests.post(
            f"{BASE_URL}/preview-sql",
            json=TEST_RULE_CONFIG,
            headers={"Content-Type": "application/json"}
        )
        print_response(response, "SQL预览")

        if response.status_code == 200:
            data = response.json()
            print("\n✅ SQL生成成功")
            print(f"\nSQL表达式:")
            print(f"  {data.get('sql_expression')}")
            print(f"\n规则摘要:")
            summary = data.get('rule_summary', {})
            print(f"  - 规则总数: {summary.get('total_rules')}")
            print(f"  - 最大深度: {summary.get('max_depth')}")
            print(f"  - 指标数量: {summary.get('indicator_count')}")
        else:
            print("\n❌ SQL生成失败")

        return response.status_code == 200

    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        return False


def test_evaluate_rule():
    """测试规则评估"""
    print_separator("测试4: 规则评估")

    payload = {
        "rule_config": TEST_RULE_CONFIG,
        "indicator_values": TEST_INDICATOR_VALUES
    }

    try:
        response = requests.post(
            f"{BASE_URL}/evaluate-rule",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print_response(response, "规则评估")

        if response.status_code == 200:
            data = response.json()
            is_hit = data.get('is_hit')
            print(f"\n{'✅' if is_hit else '❌'} 规则{'命中' if is_hit else '未命中'}")

            if is_hit:
                output = data.get('output', {})
                print(f"\n输出配置:")
                print(f"  - 风险等级: {output.get('risk_level')}")
                print(f"  - 风险分数: {output.get('risk_score')}")
                print(f"  - 处理动作: {output.get('action')}")
                print(f"  - 描述: {output.get('description')}")
        else:
            print("\n❌ 评估失败")

        return response.status_code == 200

    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        return False


def test_error_cases():
    """测试错误情况"""
    print_separator("测试5: 错误处理")

    # 测试1: 空规则
    print("\n📝 测试空规则列表...")
    invalid_config = {
        "logic": "AND",
        "rules": [],
        "output": TEST_RULE_CONFIG["output"]
    }

    try:
        response = requests.post(
            f"{BASE_URL}/validate-rule",
            json=invalid_config,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 422:
            print("✅ 正确拒绝空规则")
        else:
            print(f"❌ 未正确处理空规则 (status: {response.status_code})")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # 测试2: 无效操作符
    print("\n📝 测试无效操作符...")
    invalid_config = {
        "logic": "AND",
        "rules": [
            {
                "type": "condition",
                "indicator": "i_login_cnt_7d",
                "operator": "invalid_op",
                "value": 10
            }
        ],
        "output": TEST_RULE_CONFIG["output"]
    }

    try:
        response = requests.post(
            f"{BASE_URL}/validate-rule",
            json=invalid_config,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 422:
            print("✅ 正确拒绝无效操作符")
        else:
            print(f"❌ 未正确处理无效操作符 (status: {response.status_code})")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # 测试3: 无效正则表达式
    print("\n📝 测试无效正则表达式...")
    invalid_config = {
        "logic": "AND",
        "rules": [
            {
                "type": "condition",
                "indicator": "i_user_name",
                "operator": "regexp",
                "value": "[[["  # 无效的正则表达式
            }
        ],
        "output": TEST_RULE_CONFIG["output"]
    }

    try:
        response = requests.post(
            f"{BASE_URL}/validate-rule",
            json=invalid_config,
            headers={"Content-Type": "application/json"}
        )
        data = response.json()
        if not data.get("valid") and any("正则表达式" in err for err in data.get("errors", [])):
            print("✅ 正确检测无效正则表达式")
        else:
            print("❌ 未正确检测无效正则表达式")
    except Exception as e:
        print(f"❌ 请求失败: {e}")


def main():
    """主测试函数"""
    print("\n")
    print("="*60)
    print("  FraudHunter 规则引擎 API 测试")
    print("="*60)
    print(f"\n🌐 测试URL: {BASE_URL}")
    print(f"⏰ 开始时间: {requests.utils.default_headers()}")

    results = []

    # 运行所有测试
    results.append(("健康检查", test_health_check()))
    results.append(("规则验证", test_validate_rule()))
    results.append(("SQL预览", test_preview_sql()))
    results.append(("规则评估", test_evaluate_rule()))

    # 错误处理测试
    test_error_cases()

    # 打印测试结果总结
    print_separator("测试结果总结")

    total = len(results)
    passed = sum(1 for _, success in results if success)

    print(f"\n总测试数: {total}")
    print(f"通过: {passed} ✅")
    print(f"失败: {total - passed} ❌")

    print("\n详细结果:")
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  - {test_name}: {status}")

    print("\n" + "="*60 + "\n")

    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查日志")
        return 1


if __name__ == "__main__":
    exit(main())
