"""
Schema分块存储测试脚本

测试真正的分块存储功能：
- 小表：单个chunk
- 大表：表级chunk + 多个字段级chunks
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.db_base import SessionLocal
from services.vector_store.schema_summary_service import SchemaSummaryService
from repositories.metadata_repository import MetadataTableRepository
from utils.logger import logger


def test_schema_chunking():
    """测试Schema分块功能"""
    logger.info("=" * 80)
    logger.info("测试Schema分块存储功能")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 初始化Schema摘要服务
        schema_service = SchemaSummaryService(db)
        logger.info("Schema摘要服务初始化成功\n")

        # 获取测试表
        table_repo = MetadataTableRepository(db)
        tables = table_repo.get_all()

        if not tables:
            logger.warning("没有找到可用的表")
            return

        # 测试1：小表（单chunk）
        logger.info("\n" + "=" * 80)
        logger.info("测试1：小表（应该返回单个chunk）")
        logger.info("=" * 80)

        small_tables = [t for t in tables if len([c for c in t.columns if c.is_available == 0]) < 20]

        if small_tables:
            test_table = small_tables[0]
            logger.info(f"\n测试表: {test_table.name} (字段数: {len([c for c in test_table.columns if c.is_available == 0])})")

            # 生成Schema摘要（不包含字段值样例，避免查询数据库）
            chunks = schema_service.generate_table_summary(
                table_id=test_table.id,
                include_field_samples=False,  # 不采样，避免数据库查询
                include_table_stats=False
            )

            logger.info(f"\n生成的chunk数量: {len(chunks)}")
            if len(chunks) == 1:
                logger.info("✓ 小表正确返回单个chunk")
            else:
                logger.warning(f"✗ 小表应该返回1个chunk，实际返回{len(chunks)}个")

            for idx, (doc, metadata) in enumerate(chunks):
                logger.info(f"\nChunk {idx} 元数据:")
                logger.info(f"  - chunk_type: {metadata.get('chunk_type')}")
                logger.info(f"  - separated: {metadata.get('separated')}")
                logger.info(f"  - table_name: {metadata.get('table_name')}")
                logger.info(f"  - column_count: {metadata.get('column_count')}")
                logger.info(f"\nChunk {idx} 内容（前200字符）:")
                logger.info(f"{doc[:200]}...")

        # 测试2：大表（多chunks）
        logger.info("\n" + "=" * 80)
        logger.info("测试2：大表（应该返回多个chunks）")
        logger.info("=" * 80)

        large_tables = [t for t in tables if len([c for c in t.columns if c.is_available == 0]) >= 20]

        if large_tables:
            test_table = large_tables[0]
            logger.info(f"\n测试表: {test_table.name} (字段数: {len([c for c in test_table.columns if c.is_available == 0])})")

            # 生成Schema摘要
            chunks = schema_service.generate_table_summary(
                table_id=test_table.id,
                include_field_samples=False,
                include_table_stats=False
            )

            logger.info(f"\n生成的chunk数量: {len(chunks)}")

            if len(chunks) > 1:
                logger.info(f"✓ 大表正确返回多个chunks（{len(chunks)}个）")
            else:
                logger.warning(f"✗ 大表应该返回多个chunks，实际只返回{len(chunks)}个")

            # 分析每个chunk
            table_level_chunks = [c for c in chunks if c[1].get('chunk_type') == 'table_level']
            field_level_chunks = [c for c in chunks if c[1].get('chunk_type') == 'field_level']

            logger.info(f"\nChunk分析:")
            logger.info(f"  - 表级chunks: {len(table_level_chunks)}")
            logger.info(f"  - 字段级chunks: {len(field_level_chunks)}")

            # 显示表级chunk
            if table_level_chunks:
                doc, metadata = table_level_chunks[0]
                logger.info(f"\n【表级Chunk】")
                logger.info(f"元数据: chunk_type={metadata.get('chunk_type')}, separated={metadata.get('separated')}")
                logger.info(f"内容（前300字符）:\n{doc[:300]}...")

            # 显示字段级chunks
            for idx, (doc, metadata) in enumerate(field_level_chunks[:2]):  # 只显示前2个
                logger.info(f"\n【字段级Chunk {idx + 1}】")
                logger.info(f"元数据: chunk_index={metadata.get('chunk_index')}, total_chunks={metadata.get('total_chunks')}")
                logger.info(f"内容（前200字符）:\n{doc[:200]}...")

        # 测试3：分块配置
        logger.info("\n" + "=" * 80)
        logger.info("测试3：分块配置")
        logger.info("=" * 80)

        logger.info(f"\n当前分块配置:")
        logger.info(f"  - LARGE_TABLE_COLUMN_THRESHOLD: {schema_service.LARGE_TABLE_COLUMN_THRESHOLD}")
        logger.info(f"  - FIELD_CHUNK_SIZE: {schema_service.FIELD_CHUNK_SIZE}")
        logger.info(f"  - MAX_CHARS_PER_CHUNK: {schema_service.MAX_CHARS_PER_CHUNK}")

        # 统计表分布
        small_count = len(small_tables)
        large_count = len(large_tables)
        logger.info(f"\n表分布统计:")
        logger.info(f"  - 小表（字段数 < {schema_service.LARGE_TABLE_COLUMN_THRESHOLD}）: {small_count}")
        logger.info(f"  - 大表（字段数 >= {schema_service.LARGE_TABLE_COLUMN_THRESHOLD}）: {large_count}")

        if large_count > 0:
            # 估算大表的chunk数量
            for table in large_tables[:3]:  # 只看前3个大表
                col_count = len([c for c in table.columns if c.is_available == 0])
                estimated_chunks = 1 + (col_count // schema_service.FIELD_CHUNK_SIZE)
                logger.info(f"  - 表 {table.name}: {col_count}个字段 ≈ {estimated_chunks}个chunks")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


def main():
    """主测试函数"""
    logger.info("开始Schema分块存储测试\n")
    test_schema_chunking()
    logger.info("\n" + "=" * 80)
    logger.info("测试完成！")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
