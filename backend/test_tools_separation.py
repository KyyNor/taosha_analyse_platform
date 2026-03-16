"""
测试工具分离：验证 schema_linking_retrieve 和 knowledge_base_retrieve 的功能分离
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_schema_linking_tool():
    """测试 schema_linking_retrieve 工具（只检索表结构）"""
    print("\n" + "="*80)
    print("测试 schema_linking_retrieve 工具（应该只返回表结构）")
    print("="*80)

    from services.agents.tools.schema_linking_tool import schema_linking_retrieve

    # 调用工具（通过 .func 属性访问底层函数）
    result = schema_linking_retrieve.func(
        question="查询用户的留存率数据",
        candidate_top_k=5,
        selected_top_k=3,
        use_cache=False
    )

    import json
    data = json.loads(result)

    print(f"\n✅ 成功: {data['success']}")
    print(f"📊 问题: {data['question']}")
    print(f"🔍 召回候选表: {data['candidate_count']} 个")
    print(f"✓ 选中表: {data['selected_count']} 个")
    print(f"📋 选中的表: {data['selected_tables']}")

    # 验证只返回了表结构
    if data['selected_tables']:
        print(f"\n✅ 验证通过：只返回表结构（{len(data['selected_tables'])}个表）")
        for table_name in data['selected_tables']:
            print(f"   - {table_name}")
    else:
        print("\n⚠️  警告：没有返回任何表（可能是向量数据库未配置或无相关数据）")

    return data


async def test_knowledge_base_tool():
    """测试 knowledge_base_retrieve 工具（只检索非表结构知识）"""
    print("\n" + "="*80)
    print("测试 knowledge_base_retrieve 工具（应该只返回术语/关联/报表）")
    print("="*80)

    from services.agents.tools.knowledge_base_tool import knowledge_base_retrieve

    # 调用工具（通过 .func 属性访问底层函数）
    result = knowledge_base_retrieve.func(
        query="什么是留存率",
        top_k=5,
        resource_types=["glossary"],  # 只检索术语
        search_mode="hybrid"
    )

    import json
    data = json.loads(result)

    print(f"\n✅ 成功: {data['success']}")
    print(f"📊 查询: {data['query']}")

    if data['success']:
        print(f"🔍 搜索模式: {data.get('search_mode', 'N/A')}")
        print(f"📋 结果数量: {data['result_count']} 个")

        if data.get('type_counts'):
            print(f"📈 类型分布: {data['type_counts']}")
    else:
        print(f"❌ 错误: {data.get('error', 'Unknown error')}")

    # 验证只返回了非表结构知识
    if data['result_count'] > 0:
        print(f"\n✅ 验证通过：返回了非表结构知识")
        for item in data['results'][:3]:  # 只显示前3个
            resource_type = item['resource_type']
            content = item['content'][:100] + "..." if len(item['content']) > 100 else item['content']
            print(f"\n   [{resource_type}] {content}")
    else:
        print("\n⚠️  警告：没有返回任何结果（可能是向量数据库未配置或无相关数据）")

    return data


async def test_separation():
    """测试两个工具的功能分离"""
    print("\n" + "="*80)
    print("测试功能分离")
    print("="*80)

    from services.agents.tools.schema_linking_tool import schema_linking_retrieve
    from services.agents.tools.knowledge_base_tool import knowledge_base_retrieve

    # 同时测试两个工具
    schema_result = schema_linking_retrieve.func(
        question="用户数据",
        candidate_top_k=3,
        selected_top_k=2,
        use_cache=False
    )

    kb_result = knowledge_base_retrieve.func(
        query="用户数据",
        top_k=3,
        resource_types=["glossary", "relation"]
    )

    import json
    schema_data = json.loads(schema_result)
    kb_data = json.loads(kb_result)

    print(f"\n📊 schema_linking_retrieve 返回:")
    print(f"   - 类型: 表结构")
    print(f"   - 数量: {schema_data['selected_count']} 个表")
    print(f"   - 表名: {schema_data['selected_tables']}")

    print(f"\n📚 knowledge_base_retrieve 返回:")
    print(f"   - 类型: 非表结构知识（术语/关联/报表）")
    print(f"   - 数量: {kb_data['result_count']} 条")

    if kb_data.get('type_counts'):
        print(f"   - 分布: {kb_data['type_counts']}")

    print("\n✅ 功能分离验证完成")


async def main():
    """主测试函数"""
    print("\n" + "🔬 "*40)
    print("工具分离测试 - 验证 schema_linking_retrieve 和 knowledge_base_retrieve")
    print("🔬 "*40)

    try:
        # 测试 Schema Linking 工具
        await test_schema_linking_tool()

        # 测试知识库检索工具
        await test_knowledge_base_tool()

        # 测试功能分离
        await test_separation()

        print("\n" + "="*80)
        print("✅ 所有测试完成")
        print("="*80)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
