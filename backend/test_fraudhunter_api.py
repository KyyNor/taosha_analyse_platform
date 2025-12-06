"""
FraudHunter API 快速测试脚本

使用方法:
1. 启动后端服务: uv run uvicorn main:app --host 0.0.0.0 --port 50020
2. 运行测试: uv run python test_fraudhunter_api.py
"""

import requests
import json
import time

BASE_URL = "http://localhost:50020/api/taosha/v1/fraudhunter"


def print_response(name, response):
    """打印响应结果"""
    print(f"\n{'='*60}")
    print(f"{name}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    try:
        print(f"响应内容:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"响应内容:\n{response.text}")


def test_indicator_group_crud():
    """测试指标组CRUD功能"""
    print("\n" + "="*80)
    print("测试1: 指标组CRUD功能")
    print("="*80)

    # 1. 创建指标组
    create_data = {
        "group_code": "test_login_behavior",
        "group_name": "测试登录行为指标组",
        "description": "这是一个测试指标组",
        "logic_type": "sql",
        "logic_content": """
SELECT
    account_id,
    indicator_code,
    indicator_value,
    CURRENT_DATE as dt
FROM (
    SELECT
        account_id,
        'i_login_cnt_7d' as indicator_code,
        COUNT(*) as indicator_value
    FROM user_login
    WHERE login_date >= DATE_SUB(CURRENT_DATE, 7)
    GROUP BY account_id
) t
        """.strip(),
        "source_tables": "user_login",
        "output_table": "anti_fraud.indicator_result_row"
    }

    response = requests.post(f"{BASE_URL}/indicator-groups", json=create_data)
    print_response("1.1 创建指标组", response)

    if response.status_code != 200:
        print("❌ 创建指标组失败")
        return None

    group_id = response.json()['id']
    print(f"\n✅ 创建指标组成功, ID: {group_id}")

    # 2. 获取指标组列表
    response = requests.get(f"{BASE_URL}/indicator-groups")
    print_response("1.2 获取指标组列表", response)

    # 3. 获取指标组详情
    response = requests.get(f"{BASE_URL}/indicator-groups/{group_id}")
    print_response("1.3 获取指标组详情", response)

    # 4. 更新指标组
    update_data = {
        "group_name": "测试登录行为指标组(已更新)",
        "description": "更新后的描述"
    }
    response = requests.put(f"{BASE_URL}/indicator-groups/{group_id}", json=update_data)
    print_response("1.4 更新指标组", response)

    return group_id


def test_indicator_dry_run(group_id):
    """测试指标组试运行"""
    if not group_id:
        print("\n⏭️  跳过试运行测试（没有有效的指标组ID）")
        return

    print("\n" + "="*80)
    print("测试2: 指标组试运行功能")
    print("="*80)

    # 1. 提交试运行任务
    dry_run_data = {
        "etl_date": "2025-10-20",
        "sample_size": 100
    }

    response = requests.post(f"{BASE_URL}/indicator-groups/{group_id}/dry-run", json=dry_run_data)
    print_response("2.1 提交试运行任务", response)

    if response.status_code != 200:
        print("❌ 提交试运行任务失败")
        return

    task_id = response.json()['task_id']
    print(f"\n✅ 任务已提交, Task ID: {task_id}")

    # 2. 轮询任务进度
    max_retries = 10
    for i in range(max_retries):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/tasks/{task_id}/progress")
        print_response(f"2.2 查询任务进度 (第{i+1}次)", response)

        if response.status_code == 200:
            status = response.json()['status']
            if status in ['success', 'failed']:
                break

    # 3. 获取任务结果
    response = requests.get(f"{BASE_URL}/tasks/{task_id}/result")
    print_response("2.3 获取任务结果", response)


def test_indicator_crud(group_id):
    """测试指标定义CRUD功能"""
    if not group_id:
        print("\n⏭️  跳过指标定义测试（没有有效的指标组ID）")
        return

    print("\n" + "="*80)
    print("测试3: 指标定义CRUD功能")
    print("="*80)

    # 1. 创建指标
    create_data = {
        "indicator_code": "test_i_login_cnt_7d",
        "indicator_name": "测试7天登录次数",
        "indicator_type": "offline",
        "description": "统计用户最近7天的登录次数",
        "data_type": "numeric",
        "indicator_group_id": group_id
    }

    response = requests.post(f"{BASE_URL}/indicators", json=create_data)
    print_response("3.1 创建指标", response)

    if response.status_code != 200:
        print("❌ 创建指标失败")
        return

    indicator_id = response.json()['id']
    print(f"\n✅ 创建指标成功, ID: {indicator_id}")

    # 2. 获取指标列表
    response = requests.get(f"{BASE_URL}/indicators")
    print_response("3.2 获取指标列表", response)

    # 3. 获取指标详情
    response = requests.get(f"{BASE_URL}/indicators/{indicator_id}")
    print_response("3.3 获取指标详情", response)

    # 4. 更新指标
    update_data = {
        "indicator_name": "测试7天登录次数(已更新)",
        "description": "更新后的描述"
    }
    response = requests.put(f"{BASE_URL}/indicators/{indicator_id}", json=update_data)
    print_response("3.4 更新指标", response)


def test_task_management():
    """测试任务管理功能"""
    print("\n" + "="*80)
    print("测试4: 任务管理功能")
    print("="*80)

    # 1. 查询任务执行历史
    response = requests.get(f"{BASE_URL}/tasks/executions", params={"page": 1, "page_size": 10})
    print_response("4.1 查询任务执行历史", response)


def main():
    """主测试流程"""
    print("\n" + "="*80)
    print("FraudHunter API 功能测试")
    print("="*80)
    print(f"API基础URL: {BASE_URL}")

    try:
        # 测试1: 指标组CRUD
        group_id = test_indicator_group_crud()

        # 测试2: 试运行
        test_indicator_dry_run(group_id)

        # 测试3: 指标定义CRUD
        test_indicator_crud(group_id)

        # 测试4: 任务管理
        test_task_management()

        print("\n" + "="*80)
        print("✅ 所有测试完成!")
        print("="*80)
        print("\n提示:")
        print("- 可以访问 http://localhost:50020/docs 查看API文档")
        print("- 数据库文件位置: backend/database/metadata.db")

    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到后端服务")
        print("请先启动后端服务: uv run uvicorn main:app --host 0.0.0.0 --port 50020")
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
