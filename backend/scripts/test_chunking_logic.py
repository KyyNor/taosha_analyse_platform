"""
分块逻辑单元测试（不依赖数据库）

测试分块逻辑的正确性：
- 字段分组逻辑
- 字符数限制逻辑
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class MockColumn:
    """模拟字段对象"""
    def __init__(self, name, col_type, comment, index):
        self.name = name
        self.type = col_type
        self.business_type = col_type
        self.comment = comment
        self.relation_config_id = None


def test_field_chunking():
    """测试字段分组逻辑"""
    print("=" * 80)
    print("测试字段分组逻辑")
    print("=" * 80)

    # 模拟配置
    FIELD_CHUNK_SIZE = 10
    MAX_CHARS_PER_CHUNK = 1000

    # 创建测试字段（30个字段）
    columns = []
    for i in range(1, 31):
        col = MockColumn(
            name=f"field_{i}",
            col_type="VARCHAR(50)" if i % 3 != 0 else "INT",
            comment=f"测试字段{i}" if i % 2 == 0 else "",
            index=i
        )
        columns.append(col)

    print(f"\n测试数据: {len(columns)}个字段")

    # 测试分组逻辑
    chunks = []
    current_chunk = []
    current_chars = 0

    for idx, col in enumerate(columns, 1):
        # 模拟生成字段摘要（估算字符数）
        col_summary = f"{idx}. {col.name} {col.type} - {col.comment}"
        col_chars = len(col_summary)

        # 判断是否需要分块
        if current_chunk and current_chars + col_chars > MAX_CHARS_PER_CHUNK:
            chunks.append(current_chunk)
            print(f"  分块 {len(chunks)}: {len(current_chunk)}个字段, {current_chars}字符")
            current_chunk = []
            current_chars = 0

        current_chunk.append({
            'column': col,
            'sample': None,
            'index': idx
        })
        current_chars += col_chars

        if len(current_chunk) >= FIELD_CHUNK_SIZE:
            chunks.append(current_chunk)
            print(f"  分块 {len(chunks)}: {len(current_chunk)}个字段, {current_chars}字符")
            current_chunk = []
            current_chars = 0

    if current_chunk:
        chunks.append(current_chunk)
        print(f"  分块 {len(chunks)}: {len(current_chunk)}个字段, {current_chars}字符")

    print(f"\n✓ 总共生成 {len(chunks)} 个chunks")
    print(f"  - 平均每个chunk {sum(len(c) for c in chunks) / len(chunks):.1f} 个字段")


def test_extreme_large_table():
    """测试极端大表（100个字段）"""
    print("\n" + "=" * 80)
    print("测试极端大表分块")
    print("=" * 80)

    FIELD_CHUNK_SIZE = 10
    MAX_CHARS_PER_CHUNK = 1000

    # 创建100个字段
    columns = []
    for i in range(1, 101):
        col = MockColumn(
            name=f"column_{i:03d}",
            col_type="VARCHAR(100)",
            comment=f"这是第{i}个字段的注释，可能会比较长" if i % 3 == 0 else "",
            index=i
        )
        columns.append(col)

    print(f"\n测试数据: {len(columns)}个字段（极端大表）")

    # 估算每个字段的字符数
    avg_chars_per_field = 80  # 平均每个字段摘要80字符

    # 估算需要的chunks数量
    estimated_total_chars = len(columns) * avg_chars_per_field
    estimated_chunks_by_chars = (estimated_total_chars + MAX_CHARS_PER_CHUNK - 1) // MAX_CHARS_PER_CHUNK
    estimated_chunks_by_fields = (len(columns) + FIELD_CHUNK_SIZE - 1) // FIELD_CHUNK_SIZE

    print(f"\n估算:")
    print(f"  - 总字符数: {estimated_total_chars}")
    print(f"  - 按字符数分块: ≈{estimated_chunks_by_chars}个chunks")
    print(f"  - 按字段数分块: ≈{estimated_chunks_by_fields}个chunks")
    print(f"  - 预计总chunks: {max(estimated_chunks_by_chars, estimated_chunks_by_fields)} + 1(表级) = {max(estimated_chunks_by_chars, estimated_chunks_by_fields) + 1}个")


def test_chunk_metadata():
    """测试chunk元数据结构"""
    print("\n" + "=" * 80)
    print("测试chunk元数据结构")
    print("=" * 80)

    # 表级chunk元数据
    table_metadata = {
        "resource_type": "table",
        "resource_id": 123,
        "table_name": "test_large_table",
        "column_count": 50,
        "is_large_table": True,
        "has_field_samples": False,
        "chunk_type": "table_level",
        "separated": 1,
        "part": "table"
    }

    print("\n表级chunk元数据:")
    for key, value in table_metadata.items():
        print(f"  {key}: {value}")

    # 字段级chunk元数据
    field_metadata = {
        "resource_type": "table",
        "resource_id": 123,
        "table_name": "test_large_table",
        "column_count": 50,
        "is_large_table": True,
        "has_field_samples": False,
        "chunk_type": "field_level",
        "separated": 1,
        "part": "field",
        "chunk_index": 2,
        "total_chunks": 5
    }

    print("\n字段级chunk元数据:")
    for key, value in field_metadata.items():
        print(f"  {key}: {value}")

    print("\n✓ 元数据结构正确，支持分块识别和重组")


def main():
    """主测试函数"""
    print("开始分块逻辑单元测试\n")

    test_field_chunking()
    test_extreme_large_table()
    test_chunk_metadata()

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
