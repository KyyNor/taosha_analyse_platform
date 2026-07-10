# 离线宽表 Delta + INSERT SELECT 物理化设计

## 背景

当前离线宽表同步在指标变更后会对历史日期重新生成完整宽表。即使只更新一个指标，也会触发 Spark 对全部指标做 PIVOT，并通过 JDBC 将完整宽表写入 PG。单日同步耗时几分钟到十几分钟，历史日期回补时整体链路过慢。

已有增量方案采用“复制旧表静态列 + 辅助表写变更列 + UPDATE FROM 合并”的方式，但大规模 UPDATE 容易带来表膨胀、锁、索引维护和调试复杂度，实际收益不稳定。

## 设计目标

- 指标变更时，Spark 只计算变更指标和新增指标。
- PG 侧通过顺序 `INSERT SELECT` 生成新版本物理宽表分区，避免大规模 UPDATE。
- 保留现有宽表版本、快照、ready 检查、版本提升机制。
- 无可复用旧分区时自动降级到现有全量同步。
- 第一版只处理清晰主路径，不引入 view 链、compact 或跨日期并行优化。

## 业务约束

同一 `object_type`、同一 `etl_date` 下，`target_id` 集合稳定。`target_id` 是存款账号、客户号或贷款账号；增减指标不会改变当天账号或客户全集。

因此增量物理化使用旧宽表分区作为基准：

- 从 base 分区出发做 `LEFT JOIN delta`。
- `target_id` 和 `etl_date` 直接取 base 表，不使用 `COALESCE`。
- 如果 delta 中出现 base 不存在的 `target_id`，视为异常数据，不进入新宽表；后续可加日志或校验。

## 可复用内容

- `WideTableComparator.diff()`：继续用于比较 current/base metadata 与 target metadata。
- `_find_copy_source()`：继续用于找到可复用的旧版本分区和旧 metadata。
- `_build_pivot_sql_inc()`：继续用于只生成变更指标的 Spark PIVOT SQL。
- `_execute_with_pyspark_to_pg()` / `_execute_with_jdbc_to_pg()`：继续用于把 delta 窄表写入 PG。
- 现有 snapshot 状态流转、版本 ready 检查、版本 promote 逻辑保持不变。

## 需要替换内容

废弃当前 `_copy_static_and_merge_incr()` 主路径，不再执行：

- `copy_static_columns()`
- `merge_aux_into_main()`
- 对新宽表的大规模 `UPDATE FROM`

改为：

1. Spark 只 PIVOT `changed_cols + new_cols`。
2. 写入临时 delta 表。
3. PG 用 `INSERT SELECT base LEFT JOIN delta` 一次性写入新版本宽表分区。
4. 删除 delta 表。

## 数据流

```text
target version ready
  -> 找旧版本可用分区
  -> diff(base_metadata, target_metadata)
  -> inc_cols = changed_cols + new_cols
  -> Spark PIVOT inc_cols
  -> 写 PG delta 窄表
  -> PG INSERT SELECT base LEFT JOIN delta 生成新宽表分区
  -> snapshot ready
  -> 检查 target -> current
```

无旧分区、无旧 metadata 或无法 diff 时，走现有全量路径。

## SQL 形态

目标主表和日期分区沿用现有命名：

```text
{wide_table_name}_{target_hash[:8]}
{wide_table_name}_{target_hash[:8]}_{yyyymmdd}
```

delta 临时表命名：

```text
_delta_{wide_table_name}_{target_hash[:8]}_{yyyymmdd}
```

delta 表只包含：

```text
target_id
etl_date
changed_col_1
new_col_1
...
```

新宽表分区生成 SQL：

```sql
INSERT INTO target_table (
    target_id,
    static_col_1,
    changed_col_1,
    new_col_1,
    etl_date
)
SELECT
    b.target_id,
    b.static_col_1,
    d.changed_col_1,
    d.new_col_1,
    b.etl_date
FROM old_partition b
LEFT JOIN delta_table d
  ON b.target_id = d.target_id
 AND b.etl_date = d.etl_date
WHERE b.etl_date = :etl_date
```

变更列和新增列必须直接取 delta 值，不能 `COALESCE(d.col, b.col)`。如果新指标结果为空，应该写入空值，而不是回退旧版本值。

## 指标分类

现有 `VersionDelta` 保留：

- `static_cols`：base 和 target 都存在且版本相同。
- `changed_cols`：base 和 target 都存在但版本不同。
- `new_cols`：target 中新增。

建议增加：

- `removed_cols`：base 中存在、target 中不存在。

`removed_cols` 不写入新宽表，也不参与 INSERT 字段列表。这样指标下线时不会把旧列带到新版本。

## 同步路径选择

- `current/target` 无差异：跳过，不生成新 snapshot。
- 有旧分区且 `inc_cols` 非空：走 delta insert-select 路径。
- 有旧分区但只有 removed_cols：走纯 base 投影路径，不需要 Spark delta。
- 没有旧分区：走现有全量 Spark PIVOT 路径。
- delta 写入或 insert-select 失败：snapshot 标记为 `failed`，保留错误信息，尽力清理 delta 表。

## 实现边界

第一版只修改离线宽表同步路径，不修改：

- DS 指标任务生成逻辑。
- 指标明细表结构。
- 实时宽表生成链路。
- 模型规则 SQL 生成逻辑。
- 宽表版本 promote 阈值。

## 测试计划

单元测试：

- `VersionDelta` 覆盖 static、changed、new、removed 四类组合。
- delta 表 DDL 只包含 `target_id`、`etl_date` 和 inc 指标。
- insert-select SQL 字段顺序与 target metadata 一致。
- changed/new 列取 delta，static 列取 base，key 字段取 base。
- 只有 removed_cols 时不生成 delta PIVOT SQL。

集成测试：

- 准备一份 base 分区和一份 delta 表，验证新分区数据正确。
- 验证 changed 指标为空值时不会回退 base 旧值。
- 验证无 base 分区时降级全量同步。
- 验证失败时 snapshot 标记为 `failed` 且 delta 表被清理。

## 风险与缓解

- PG `INSERT SELECT` 仍需读写完整分区：这是物理新宽表的必要成本，但比全量 Spark PIVOT 和全量 JDBC 传输更轻。
- delta 中出现 base 不存在的 target_id：按业务约束忽略，后续可增加异常计数日志。
- 指标下线场景：通过 `removed_cols` 明确处理，避免旧列残留。
- 字段顺序和类型：复用现有 PG 宽表 DDL 和 numeric 类型工具，SQL 生成统一走 metadata 顺序。
