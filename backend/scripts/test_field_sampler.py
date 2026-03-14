"""
字段值采样服务测试脚本

测试字段值采样功能，包括：
1. 不同类型字段的采样策略
2. 日期分区条件的自动添加
3. 缓存机制
4. 向量训练服务的集成
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.db_base import SessionLocal
from services.vector_store.field_value_sampler import FieldValueSampler
from services.vector_store.vector_training_service import VectorTrainingService
from repositories.metadata_repository import MetadataTableRepository
from utils.logger import logger


def test_field_sampler():
    """测试字段值采样器"""
    logger.info("=" * 60)
    logger.info("开始测试字段值采样服务")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # 初始化采样器
        sampler = FieldValueSampler(db)

        # 获取一个测试表
        table_repo = MetadataTableRepository(db)
        tables = table_repo.get_all()

        if not tables:
            logger.warning("没有找到可用的表")
            return

        # 使用第一个可用的表进行测试
        test_table = tables[0]
        logger.info(f"测试表: {test_table.name} (ID: {test_table.id})")

        # 采样表的所有字段
        logger.info("\n开始采样字段值...")
        field_samples = sampler.sample_table_fields(test_table.id, limit=10)

        # 显示采样结果
        logger.info(f"\n采样结果统计:")
        logger.info(f"总字段数: {len(field_samples)}")

        for field_name, sample_data in field_samples.items():
            logger.info(f"\n字段: {field_name}")
            logger.info(f"  采样类型: {sample_data.get('sample_type', 'unknown')}")
            logger.info(f" 去重值数量: {sample_data.get('count', 0)}")

            if sample_data.get('values'):
                logger.info(f"  样例值: {sample_data['values'][:5]}")

            if sample_data.get('stats'):
                logger.info(f"  统计信息: {sample_data['stats']}")

        # 测试缓存功能
        logger.info("\n" + "=" * 60)
        logger.info("测试缓存功能")
        logger.info("=" * 60)

        cache_stats_before = sampler.get_cache_stats()
        logger.info(f"缓存字段数: {cache_stats_before['cached_fields']}")

        # 再次采样（应该使用缓存）
        logger.info("\n再次采样（应该使用缓存）...")
        field_samples_cached = sampler.sample_table_fields(test_table.id, limit=10)

        cache_stats_after = sampler.get_cache_stats()
        logger.info(f"缓存字段数: {cache_stats_after['cached_fields']}")

        # 清空缓存
        logger.info("\n清空缓存...")
        sampler.clear_cache()
        cache_stats_cleared = sampler.get_cache_stats()
        logger.info(f"清空后缓存字段数: {cache_stats_cleared['cached_fields']}")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


def test_vector_training_integration():
    """测试向量训练服务集成"""
    logger.info("\n" + "=" * 60)
    logger.info("测试向量训练服务集成")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # 初始化向量训练服务
        vector_training_service = VectorTrainingService(db)

        # 获取一个测试表
        table_repo = MetadataTableRepository(db)
        tables = table_repo.get_all()

        if not tables:
            logger.warning("没有找到可用的表")
            return

        # 使用第一个可用的表进行测试
        test_table = tables[0]
        logger.info(f"测试表: {test_table.name} (ID: {test_table.id})")

        # 生成表文档（包含字段值样例）
        logger.info("\n生成表文档...")
        document, metadata = vector_training_service._generate_table_document(test_table.id)

        logger.info(f"\n生成的文档:\n{document}")
        logger.info(f"\n元数据: {json.dumps(metadata, indent=2, ensure_ascii=False)}")

        # 检查是否包含字段值样例
        has_samples = metadata.get('has_field_samples', False)
        if has_samples:
            logger.info("\n✓ 向量训练服务已成功集成字段值采样功能")
        else:
            logger.warning("\n✗ 向量训练服务未包含字段值样例")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


def test_date_partition_detection():
    """测试日期分区字段检测"""
    logger.info("\n" + "=" * 60)
    logger.info("测试日期分区字段检测")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        sampler = FieldValueSampler(db)

        # 测试常见的日期分区字段名
        test_fields = ['etl_date', 'cdate', 'etl_dt', 'c_date', 'data_date', 'biz_date', 'create_time']

        logger.info(f"已配置的日期分区字段: {sampler.DATE_PARTITION_FIELDS}")

        # 获取一个表来测试
        table_repo = MetadataTableRepository(db)
        tables = table_repo.get_all()

        if tables:
            test_table = tables[0]
            logger.info(f"\n检测表 {test_table.name} 的日期分区字段...")

            date_partition_col = sampler._detect_date_partition_column(test_table.name)

            if date_partition_col:
                logger.info(f"✓ 检测到日期分区字段: {date_partition_col}")
            else:
                logger.info("✗ 未检测到日期分区字段")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


def main():
    """主测试函数"""
    logger.info("开始字段值采样服务测试\n")

    # 测试1：日期分区字段检测
    test_date_partition_detection()

    # 测试2：字段值采样器
    test_field_sampler()

    # 测试3：向量训练服务集成
    test_vector_training_integration()

    logger.info("\n" + "=" * 60)
    logger.info("测试完成！")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
