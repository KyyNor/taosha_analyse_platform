"""
Schema摘要服务测试脚本

测试Schema摘要生成功能，包括：
1. 单摘要格式（小表）
2. 分离摘要格式（大表）
3. 字段值样例集成
4. 向量训练服务集成
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.db_base import SessionLocal
from services.vector_store.schema_summary_service import SchemaSummaryService
# from services.vector_store.vector_training_service import VectorTrainingService  # 需要Qdrant配置
from repositories.metadata_repository import MetadataTableRepository
from utils.logger import logger


def test_schema_summary_service():
    """测试Schema摘要服务"""
    logger.info("=" * 80)
    logger.info("开始测试Schema摘要服务")
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

        # 测试1：小表（单摘要格式）
        logger.info("\n" + "=" * 80)
        logger.info("测试1：小表单摘要格式")
        logger.info("=" * 80)

        # 找一个字段较少的表
        small_tables = [t for t in tables if len([c for c in t.columns if c.is_available == 0]) < 20]

        if small_tables:
            test_table = small_tables[0]
            logger.info(f"\n测试表: {test_table.name} (字段数: {len([c for c in test_table.columns if c.is_available == 0])})")

            # 生成Schema摘要
            summary, metadata = schema_service.generate_table_summary(
                table_id=test_table.id,
                include_field_samples=True,
                include_table_stats=True
            )

            if summary:
                logger.info(f"\n生成的Schema摘要:\n{summary}")
                logger.info(f"\n元数据: {json.dumps(metadata, indent=2, ensure_ascii=False)}")
            else:
                logger.error("生成Schema摘要失败")

        # 测试2：大表（分离摘要格式）
        logger.info("\n" + "=" * 80)
        logger.info("测试2：大表分离摘要格式")
        logger.info("=" * 80)

        # 找一个字段较多的表
        large_tables = [t for t in tables if len([c for c in t.columns if c.is_available == 0]) >= 20]

        if large_tables:
            test_table = large_tables[0]
            logger.info(f"\n测试表: {test_table.name} (字段数: {len([c for c in test_table.columns if c.is_available == 0])})")

            # 生成Schema摘要
            summary, metadata = schema_service.generate_table_summary(
                table_id=test_table.id,
                include_field_samples=True,
                include_table_stats=True
            )

            if summary:
                logger.info(f"\n生成的Schema摘要（前500字符）:\n{summary[:500]}...")
                logger.info(f"\n元数据: {json.dumps(metadata, indent=2, ensure_ascii=False)}")
            else:
                logger.error("生成Schema摘要失败")

        # 测试3：无字段值样例
        logger.info("\n" + "=" * 80)
        logger.info("测试3：无字段值样例")
        logger.info("=" * 80)

        if tables:
            test_table = tables[0]
            logger.info(f"\n测试表: {test_table.name}")

            # 生成不包含字段值样例的Schema摘要
            summary, metadata = schema_service.generate_table_summary(
                table_id=test_table.id,
                include_field_samples=False,
                include_table_stats=True
            )

            if summary:
                logger.info(f"\n生成的Schema摘要:\n{summary[:300]}...")
                logger.info(f"\n元数据: {json.dumps(metadata, indent=2, ensure_ascii=False)}")
            else:
                logger.error("生成Schema摘要失败")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


def test_vector_training_integration():
    """测试向量训练服务集成"""
    logger.info("\n" + "=" * 80)
    logger.info("测试向量训练服务集成")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 初始化Schema摘要服务
        schema_service = SchemaSummaryService(db)

        # 获取一个测试表
        table_repo = MetadataTableRepository(db)
        tables = table_repo.get_all()

        if not tables:
            logger.warning("没有找到可用的表")
            return

        # 使用第一个可用的表进行测试
        test_table = tables[0]
        logger.info(f"\n测试表: {test_table.name} (ID: {test_table.id})")

        # 生成表文档（模拟向量训练服务的调用）
        logger.info("\n生成表文档...")
        document, metadata = schema_service.generate_table_summary(
            table_id=test_table.id,
            include_field_samples=True,
            include_table_stats=True
        )

        if document:
            logger.info(f"\n生成的文档（前500字符）:\n{document[:500]}...")
            logger.info(f"\n元数据: {json.dumps(metadata, indent=2, ensure_ascii=False)}")

            # 检查是否使用了新的Schema摘要服务
            summary_type = metadata.get('summary_type', 'unknown')
            has_field_samples = metadata.get('has_field_samples', False)

            logger.info("\n" + "=" * 80)
            logger.info("集成测试结果:")
            logger.info(f"  - 摘要类型: {summary_type}")
            logger.info(f"  - 包含字段值样例: {has_field_samples}")

            if has_field_samples:
                logger.info("\n✓ Schema摘要服务已成功生成（包含字段值样例）")
            else:
                logger.warning("\n✗ Schema摘要服务未包含字段值样例")
        else:
            logger.error("生成表文档失败")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


def test_large_table_handling():
    """测试大表处理"""
    logger.info("\n" + "=" * 80)
    logger.info("测试大表处理（字段分离）")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        schema_service = SchemaSummaryService(db)

        # 获取表统计信息
        table_repo = MetadataTableRepository(db)
        tables = table_repo.get_all()

        large_table_count = 0
        small_table_count = 0

        for table in tables:
            available_columns = [col for col in table.columns if col.is_available == 0]
            column_count = len(available_columns)

            if column_count >= schema_service.LARGE_TABLE_COLUMN_THRESHOLD:
                large_table_count += 1
                logger.info(f"大表: {table.name} (字段数: {column_count})")
            else:
                small_table_count += 1

        logger.info("\n" + "=" * 80)
        logger.info("表统计:")
        logger.info(f"  - 总表数: {len(tables)}")
        logger.info(f"  - 大表数（字段数>={schema_service.LARGE_TABLE_COLUMN_THRESHOLD}）: {large_table_count}")
        logger.info(f"  - 小表数: {small_table_count}")

        if large_table_count > 0:
            logger.info("\n✓ 检测到大表，将使用分离摘要格式")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


def main():
    """主测试函数"""
    logger.info("开始Schema摘要服务测试\n")

    # 测试1：Schema摘要服务基础功能
    test_schema_summary_service()

    # 测试2：Schema摘要服务集成测试
    test_vector_training_integration()

    # 测试3：大表处理
    test_large_table_handling()

    logger.info("\n" + "=" * 80)
    logger.info("测试完成！")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
