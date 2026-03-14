"""
Schema摘要生成服务

生成包含字段值样例、统计信息的丰富schema描述，用于向量化。
支持大表字段分离，生成表级和字段级两个层次的摘要。
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from utils.logger import LoggerMixin
from utils.config import settings
from repositories.metadata_repository import (
    MetadataTableRepository,
    MetadataColumnRepository
)
from repositories.relation_repository import RelationFieldConfigRepository
from services.vector_store.field_value_sampler import FieldValueSampler


class SchemaSummaryService(LoggerMixin):
    """Schema摘要生成服务

    生成包含以下信息的丰富schema描述：
    1. 表基本信息：表名、表注释、业务描述
    2. 字段详细信息：字段名、类型、注释
    3. 字段值样例：实际值、值范围、去重值数量
    4. 表统计信息：总行数、ETL_DATE范围
    5. 业务关系：关联表、外键关系（如果有）

    支持大表字段分离：对于字段过多的表，分离表级和字段级摘要
    """

    # 分块配置
    LARGE_TABLE_COLUMN_THRESHOLD = 20  # 大表字段数量阈值
    FIELD_CHUNK_SIZE = 10  # 每个字段chunk包含的字段数量
    MAX_CHARS_PER_CHUNK = 1000  # 每个chunk的最大字符数（参考DB-GPT的512，适当放大）

    def __init__(self, db: Session):
        """初始化Schema摘要服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.table_repo = MetadataTableRepository(db)
        self.column_repo = MetadataColumnRepository(db)
        self.relation_repo = RelationFieldConfigRepository(db)

        # 初始化字段值采样器
        try:
            self.field_sampler = FieldValueSampler(db)
            self.logger.info("字段值采样器初始化成功")
        except Exception as e:
            self.logger.warning(f"字段值采样器初始化失败: {e}")
            self.field_sampler = None

    def generate_table_summary(
        self,
        table_id: int,
        include_field_samples: bool = True,
        include_table_stats: bool = True
    ) -> List[Tuple[str, Dict]]:
        """生成表的Schema摘要（支持分块）

        对于小表：返回单个chunk
        对于大表：返回多个chunks（1个表级 + N个字段级）

        Args:
            table_id: 表ID
            include_field_samples: 是否包含字段值样例
            include_table_stats: 是否包含表统计信息

        Returns:
            [(摘要文本, 元数据字典), ...] 列表
        """
        try:
            # 获取表信息
            table = self.table_repo.get_by_id(table_id)
            if not table:
                self.logger.warning(f"表ID {table_id} 不存在")
                return "", {}

            # 获取字段信息
            columns = self.column_repo.get_by_table_id(table_id)
            available_columns = [col for col in columns if col.is_available == 0]

            if not available_columns:
                self.logger.warning(f"表 {table.name} 没有可用字段")
                return "", {}

            # 采样字段值
            field_samples = {}
            if include_field_samples and self.field_sampler:
                try:
                    field_samples = self.field_sampler.sample_table_fields(
                        table_id,
                        limit=10
                    )
                    self.logger.debug(
                        f"成功采样表 {table.name} 的字段值，"
                        f"共 {len(field_samples)} 个字段"
                    )
                except Exception as e:
                    self.logger.warning(f"字段值采样失败: {e}")

            # 获取表统计信息
            table_stats = {}
            if include_table_stats:
                try:
                    table_stats = self._get_table_statistics(table, available_columns)
                except Exception as e:
                    self.logger.warning(f"获取表统计信息失败: {e}")

            # 判断是否为大表
            is_large_table = len(available_columns) > self.LARGE_TABLE_COLUMN_THRESHOLD

            # 生成摘要
            if is_large_table:
                # 大表：生成多个chunks（表级 + 字段级）
                chunks = self._generate_large_table_chunks(
                    table,
                    available_columns,
                    field_samples,
                    table_stats,
                    table_id
                )
            else:
                # 小表：生成单个chunk
                summary_text = self._generate_single_table_summary(
                    table,
                    available_columns,
                    field_samples,
                    table_stats
                )
                metadata = {
                    "resource_type": "table",
                    "resource_id": table_id,
                    "table_name": table.name,
                    "column_count": len(available_columns),
                    "is_large_table": False,
                    "has_field_samples": len(field_samples) > 0,
                    "has_table_stats": len(table_stats) > 0,
                    "chunk_type": "single",
                    "separated": 0
                }
                chunks = [(summary_text, metadata)]

            return chunks

        except Exception as e:
            self.logger.error(f"生成表摘要失败 table_id={table_id}: {e}")
            return "", {}

    def _generate_single_table_summary(
        self,
        table,
        columns: List,
        field_samples: Dict[str, Dict],
        table_stats: Dict
    ) -> str:
        """生成单摘要格式（适用于字段较少的表）

        Args:
            table: 表对象
            columns: 字段列表
            field_samples: 字段值采样结果
            table_stats: 表统计信息

        Returns:
            摘要文本
        """
        lines = []

        # 1. 表基本信息
        lines.append(f"表名：{table.name}")

        if table.comment:
            lines.append(f"表注释：{table.comment}")

        # 2. 表统计信息
        if table_stats:
            lines.append("\n表统计：")
            if table_stats.get("row_count"):
                lines.append(f"- 总行数：{table_stats['row_count']}")
            if table_stats.get("etl_date_range"):
                lines.append(f"- ETL_DATE范围：{table_stats['etl_date_range']}")

        # 3. 字段详细信息
        lines.append("\n字段列表：")
        for idx, col in enumerate(columns, 1):
            col_summary = self._generate_column_summary(
                col,
                field_samples.get(col.name),
                idx
            )
            lines.append(col_summary)

        # 4. 业务关系（如果有）
        relations = self._get_table_relations(columns)
        if relations:
            lines.append("\n业务关系：")
            lines.extend(relations)

        return "\n".join(lines)

    def _generate_large_table_chunks(
        self,
        table,
        columns: List,
        field_samples: Dict[str, Dict],
        table_stats: Dict,
        table_id: int
    ) -> List[Tuple[str, Dict]]:
        """生成分离摘要格式（适用于字段较多的表）

        将表级信息和字段级信息分离为多个chunks，便于向量检索时分别匹配

        Args:
            table: 表对象
            columns: 字段列表
            field_samples: 字段值采样结果
            table_stats: 表统计信息
            table_id: 表ID

        Returns:
            [(摘要文本, 元数据字典), ...] 列表
            - Chunk 0: 表级信息
            - Chunk 1-N: 字段级信息（按FIELD_CHUNK_SIZE分组）
        """
        chunks = []

        # ===== Chunk 0: 表级信息 =====
        table_lines = []
        table_lines.append("【表级信息】")
        table_lines.append(f"表名：{table.name}")

        if table.comment:
            table_lines.append(f"表注释：{table.comment}")

        # 表统计信息
        if table_stats:
            table_lines.append("\n表统计：")
            if table_stats.get("row_count"):
                table_lines.append(f"- 总行数：{table_stats['row_count']}")
            if table_stats.get("etl_date_range"):
                table_lines.append(f"- ETL_DATE范围：{table_stats['etl_date_range']}")

        # 字段概览
        table_lines.append(f"\n字段概览：共 {len(columns)} 个字段")

        # 按类型分组统计
        type_stats = self._group_columns_by_type(columns)
        table_lines.append("字段类型分布：")
        for col_type, count in sorted(type_stats.items()):
            table_lines.append(f"  - {col_type}: {count} 个")

        # 关键字段（有值样例且基数较低的字段）
        key_columns = self._identify_key_columns(columns, field_samples)
        if key_columns:
            table_lines.append("\n关键字段（重要业务字段）：")
            for col_name in key_columns[:5]:  # 最多显示5个
                col = next(c for c in columns if c.name == col_name)
                table_lines.append(f"  - {col.name} ({col.business_type or col.type}): {col.comment}")

        # 业务关系（如果有）
        relations = self._get_table_relations(columns)
        if relations:
            table_lines.append("\n业务关系：")
            table_lines.extend(relations)

        table_summary = "\n".join(table_lines)

        # 表级chunk的元数据
        table_metadata = {
            "resource_type": "table",
            "resource_id": table_id,
            "table_name": table.name,
            "column_count": len(columns),
            "is_large_table": True,
            "has_field_samples": len(field_samples) > 0,
            "has_table_stats": len(table_stats) > 0,
            "chunk_type": "table_level",
            "separated": 1,  # 标记为分块
            "part": "table"
        }

        chunks.append((table_summary, table_metadata))

        # ===== Chunk 1-N: 字段级信息 =====
        # 按FIELD_CHUNK_SIZE将字段分组
        field_chunks = self._split_columns_into_chunks(
            columns,
            field_samples,
            chunk_size=self.FIELD_CHUNK_SIZE
        )

        for chunk_idx, field_chunk in enumerate(field_chunks):
            field_lines = [f"【字段详细信息 Part {chunk_idx + 1}】"]

            for col_info in field_chunk:
                col = col_info['column']
                col_sample = col_info['sample']
                col_idx = col_info['index']

                col_summary = self._generate_column_summary(
                    col,
                    col_sample,
                    col_idx
                )
                field_lines.append(col_summary)

            field_summary = "\n".join(field_lines)

            # 字段级chunk的元数据
            field_metadata = {
                "resource_type": "table",
                "resource_id": table_id,
                "table_name": table.name,
                "column_count": len(columns),
                "is_large_table": True,
                "has_field_samples": len(field_samples) > 0,
                "chunk_type": "field_level",
                "separated": 1,  # 标记为分块
                "part": "field",
                "chunk_index": chunk_idx,
                "total_chunks": len(field_chunks)
            }

            chunks.append((field_summary, field_metadata))

        return chunks

    def _generate_column_summary(
        self,
        col,
        sample_data: Optional[Dict],
        index: int
    ) -> str:
        """生成单个字段的摘要

        Args:
            col: 字段对象
            sample_data: 字段值采样数据
            index: 字段序号

        Returns:
            字段摘要文本
        """
        col_name = col.name
        col_type = col.business_type or col.type
        col_comment = col.comment or ""

        # 基础字段信息
        lines = [f"{index}. {col_name} {col_type} - {col_comment}"]

        # 关联信息
        if col.relation_config_id:
            relation = self.relation_repo.get_by_id(col.relation_config_id)
            if relation:
                lines.append(f"   关联：{relation.relation_family}|{relation.relation_subfamily}")

        # 字段值样例
        if sample_data and sample_data.get('values'):
            sample_values = sample_data['values'][:5]
            valid_samples = [str(v) for v in sample_values if v is not None]

            if valid_samples:
                samples_str = ', '.join(valid_samples)
                lines.append(f"   值样例：[{samples_str}]")

            # 去重值数量
            count = sample_data.get('count', 0)
            if count > 0:
                if count <= 50:
                    lines.append(f"   去重值数量：{count}（枚举型字段）")
                else:
                    lines.append(f"   去重值数量：{count}")

            # 数值统计信息
            stats = sample_data.get('stats', {})
            if stats.get('min') is not None and stats.get('max') is not None:
                lines.append(f"   值范围：{stats['min']} ~ {stats['max']}")
                if stats.get('avg') is not None:
                    lines.append(f"   平均值：{stats['avg']:.2f}")

            # 日期范围信息
            if stats.get('min_date') and stats.get('max_date'):
                lines.append(f"   日期范围：{stats['min_date']} ~ {stats['max_date']}")

        return "\n".join(lines)

    def _get_table_statistics(
        self,
        table,
        columns: List
    ) -> Dict[str, Optional[str]]:
        """获取表统计信息

        Args:
            table: 表对象
            columns: 字段列表

        Returns:
            统计信息字典
        """
        stats = {}

        # 检查是否有etl_date字段
        etl_date_col = next(
            (c for c in columns if c.name.lower() in ['etl_date', 'cdate']),
            None
        )

        if etl_date_col and self.field_sampler:
            try:
                # 采样etl_date字段的值范围
                sample_result = self.field_sampler.sample_field_values(
                    table_name=table.name,
                    column_name=etl_date_col.name,
                    column_type=etl_date_col.type,
                    limit=1
                )

                if sample_result.get('stats'):
                    date_range = sample_result['stats']
                    min_date = date_range.get('min_date')
                    max_date = date_range.get('max_date')
                    if min_date and max_date:
                        stats['etl_date_range'] = f"{min_date} ~ {max_date}"
            except Exception as e:
                self.logger.debug(f"获取ETL_DATE范围失败: {e}")

        # TODO: 获取总行数（需要查询引擎支持）
        # 当前先返回估算值或None
        stats['row_count'] = None

        return stats

    def _group_columns_by_type(self, columns: List) -> Dict[str, int]:
        """按类型分组统计字段

        Args:
            columns: 字段列表

        Returns:
            类型到数量的映射
        """
        type_stats = {}
        for col in columns:
            col_type = col.business_type or col.type
            # 简化类型名称
            if 'varchar' in col_type.lower() or 'char' in col_type.lower():
                col_type = 'VARCHAR'
            elif 'int' in col_type.lower():
                col_type = 'INT'
            elif 'decimal' in col_type.lower() or 'double' in col_type.lower():
                col_type = 'DECIMAL'
            elif 'date' in col_type.lower():
                col_type = 'DATE'
            elif 'text' in col_type.lower():
                col_type = 'TEXT'

            type_stats[col_type] = type_stats.get(col_type, 0) + 1

        return type_stats

    def _identify_key_columns(
        self,
        columns: List,
        field_samples: Dict[str, Dict]
    ) -> List[str]:
        """识别关键字段（有值样例且基数较低的字段）

        这些字段通常是重要的业务字段（如状态、类型等）

        Args:
            columns: 字段列表
            field_samples: 字段值采样结果

        Returns:
            关键字段名列表
        """
        key_columns = []

        for col in columns:
            sample_data = field_samples.get(col.name)
            if not sample_data:
                continue

            # 判断是否为关键字段：
            # 1. 有值样例
            # 2. 基数较小（去重值数量 <= 100）
            # 3. 有注释
            count = sample_data.get('count', 0)
            if count > 0 and count <= 100 and col.comment:
                key_columns.append(col.name)

        return key_columns

    def _split_columns_into_chunks(
        self,
        columns: List,
        field_samples: Dict[str, Dict],
        chunk_size: int = 10
    ) -> List[List[Dict]]:
        """将字段分组为多个chunks

        Args:
            columns: 字段列表
            field_samples: 字段值采样结果
            chunk_size: 每个chunk的字段数量

        Returns:
            分组后的字段列表，每个元素包含:
            [{'column': col, 'sample': sample_data, 'index': idx}, ...]
        """
        chunks = []
        current_chunk = []
        current_chars = 0

        for idx, col in enumerate(columns, 1):
            # 生成字段摘要（预估字符数）
            col_sample = field_samples.get(col.name)
            col_summary = self._generate_column_summary(col, col_sample, idx)
            col_chars = len(col_summary)

            # 如果添加当前字段会超过字符限制，先保存当前chunk
            if current_chunk and current_chars + col_chars > self.MAX_CHARS_PER_CHUNK:
                chunks.append(current_chunk)
                current_chunk = []
                current_chars = 0

            # 添加到当前chunk
            current_chunk.append({
                'column': col,
                'sample': col_sample,
                'index': idx
            })
            current_chars += col_chars

            # 如果达到字段数量限制，也保存当前chunk
            if len(current_chunk) >= chunk_size:
                chunks.append(current_chunk)
                current_chunk = []
                current_chars = 0

        # 保存最后一个chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

        return key_columns

    def _get_table_relations(self, columns: List) -> List[str]:
        """获取表的业务关系

        Args:
            columns: 字段列表

        Returns:
            业务关系描述列表
        """
        relations = []

        for col in columns:
            if col.relation_config_id:
                relation = self.relation_repo.get_by_id(col.relation_config_id)
                if relation:
                    rel_desc = (
                        f"- {col.name} 关联到 "
                        f"{relation.relation_family}|{relation.relation_subfamily}"
                    )
                    relations.append(rel_desc)

        return relations
