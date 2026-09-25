# FraudHunter 离线宽表双存储开发计划

> 状态：代码实施完成（2026-08-19），待内网环境 E2E 验收与灰度切换
> 前置文档：`docs/fraudhunter_pg_migration.md`（DuckDB/Parquet → PostgreSQL 迁移）、`docs/polished-jumping-gosling.md`（已废弃的 HDFS 中转方案）
>
> 实施提交索引：
> | 阶段 | 提交 | 内容 |
> |---|---|---|
> | 1 | dd95869 | storage_backend 元数据/迁移SQL/配置项 |
> | 2 | 1119633 | WideTableStore 存储抽象层（纯重构） |
> | 3 | 742c27e | DuckdbParquetStore staging 中转全量路径 |
> | 4 | 38778a0 | 查询路由 + SQL 方言（预览/回测/实时任务） |
> | 5 | 8cbb94d | PG↔Parquet 互转工具（CLI + API） |
> | 6 | 4ead7e3 | DuckDB 增量列改写 + Parquet 引用计数清理 |
> | 7 | 2e4f823 | 双写对账任务 + 前端存储标记 |
>
> 上线前置动作（按序）：
> 1. 开发库执行 `backend/migrations/add_snapshot_storage_backend.sql` 与 `update_snapshot_unique_with_backend.sql`；
> 2. 配置保持 `offline_store: postgresql` 上线（行为零变化），观察一个同步周期；
> 3. 切 `both` 灰度双写 ≥1 周期（含版本变化），`[双写对账]` 日志 0 失败；
> 4. 用 `scripts/wide_table_transfer.py` 按需迁移存量日期，再切 `duckdb`；
> 5. PG 旧表退役走现有 `get_old_version_tables` 清理（保留30天回退窗口）。

## 一、背景与目标

实时链路（Flink → PG）不动。本计划解决离线宽表的双存储问题：

1. **离线同步支持两条路径**：PG 离线（现状，保底）+ DuckDB 离线（Parquet 存储），配置切换，可灰度双写；
2. **互转工具**：PG 离线表 ↔ Parquet 按日期互转，切换存储不需要从源头（Spark/Hive）重新同步；
3. **DuckDB 路径支持增量**：与 PG 增量同构——只同步版本间变化列，减少网络传输；
4. **查询按快照路由**：指标查询、回测、规则引擎按快照实际存储位置选择执行引擎（PG 或 DuckDB）。

### 历史结论（不重蹈覆辙）

| 路线 | 结论 |
|---|---|
| PySpark `toPandas()` 拉内存落地 | 内存峰值 ≈ 3 倍数据量，500MB-5GB/日曾炸内存，废弃 |
| Spark 写 HDFS → WebHDFS 下载合并 | 存活 4 天，运维负担重（两阶段事务、双侧清理），永久归档 |
| JDBC `fetchall()` | 同样有内存问题，仅保留为降级路径且必须改 `fetchmany` 分批 |
| **PG 临时表（UNLOGGED）中转 → DuckDB 落 Parquet** | **本次采用的同步路径**，两段均复用已验证代码 |

## 二、核心设计

### 2.1 数据流

```
① 离线同步（切换点）
   Spark/Hive 明细长表 ──PIVOT──┬─ offline_store=postgresql → executor JDBC 直写 PG 正式分区表（现状，零改动）
                               └─ offline_store=duckdb     → executor JDBC 写 PG staging 表(UNLOGGED)
                                                            → DuckDB COPY 拉成 Parquet（列式直转）
                                                            → 对账 → 原子 rename → DROP staging

② 实时流（不动）
   Flink → PG 实时宽表

③ 查询/回测/规则（按快照路由）
   snapshot.storage_backend = postgresql → PG 执行（现状路径）
   snapshot.storage_backend = duckdb     → DuckDB 执行：read_parquet(离线) + ATTACH PG(实时表)
```

### 2.2 同一 PG 实例中的两种目的地（严格区分，不得混淆）

| | PG 正式离线表 | staging 中转表 |
|---|---|---|
| 用途 | 最终存储（PG 模式的数据落点） | 传输管道（DuckDB 模式的临时落点） |
| 表类型 | LOGGED 分区表 | **UNLOGGED 堆表**（跳过 WAL，崩溃自动清空） |
| 生命周期 | 随快照保留期 | 成功即 DROP；失败保留排障；TTL 兜底清理 |
| 命名 | `{wide_table}_{version_hash[:8]}` | `_staging_{wide_table}_{vh8}_{yyyymmdd}` |
| 现有 `_delta_`/`_incr_` 辅助表 | PG 模式内部增量合并用，**维持现状不动** | 不使用 |

注意：实时表、正式离线表、PG 模式辅助表一律保持 LOGGED；UNLOGGED 只用于新增的 staging 表。

### 2.3 Parquet 目录规范

```
{fraudhunter.wide_table.duckdb.storage_path}/{wide_table_name}_{version_hash[:8]}/etl_date=YYYY-MM-DD/part-*.parquet
```

- 版本 + 日期双隔离，文件不可变，写入一律"临时目录 + 原子 rename"；
- DuckDB 查询用 `read_parquet('.../etl_date=D/*.parquet')`，多文件原生扫描，**不做单文件合并**（历史方案中 merge_parquet 环节永久去除）。

### 2.4 元数据扩展

`fraudhunter_wide_table_snapshot` 表：

- 新增 `storage_backend VARCHAR(16) NOT NULL DEFAULT 'postgresql'`（`postgresql` / `duckdb`）；
- `parquet_file_path` 字段复用：PG 快照存 PG 表名（现状语义不变），duckdb 快照存 Parquet 目录绝对路径；
- 版本表（`fraudhunter_wide_table_version`）不动——版本/哈希逻辑与存储无关。

### 2.5 配置

```yaml
fraudhunter:
  wide_table:
    offline_store: duckdb        # postgresql | duckdb | both（灰度双写）
    duckdb:
      storage_path: /data/taosha/wide_tables_parquet
      compression: zstd
      staging_ttl_hours: 24      # staging 孤儿表兜底清理阈值
```

## 三、阶段计划

> 依赖顺序：阶段1 → 阶段2 → 阶段3 →（阶段4、5 可并行）→ 阶段6 → 阶段7。
> 每阶段独立提交、独立可回退。

---

### 阶段 1：元数据与配置基础

**做什么**：snapshot 表加 `storage_backend` 字段；配置项落地；MySQL 模型同步。

**怎么做**：
1. `backend/migrations/add_snapshot_storage_backend.sql`：
   ```sql
   ALTER TABLE fraudhunter_wide_table_snapshot
     ADD COLUMN storage_backend VARCHAR(16) NOT NULL DEFAULT 'postgresql'
     COMMENT '存储后端: postgresql/duckdb';
   ```
2. `backend/models/fraudhunter/wide_table.py`：Snapshot 模型加 `storage_backend` 字段（默认 `postgresql`）；
3. `backend/utils/config.py` + `backend/config/config.yaml.example`：新增 `offline_store`、`duckdb.*` 配置项，默认 `postgresql`（本阶段不改变任何行为）。

**测试**：
- 单测：`tests/backend/modules/wide_table_sync/test_storage_backend_field.py`——模型字段存在、默认值正确、序列化往返。

**验收标准**：
- 迁移 SQL 在开发库执行成功，存量行全部为 `postgresql`；
- 后端启动、现有同步任务、查询接口行为与改动前完全一致（默认值兜底）。

---

### 阶段 2：存储抽象层（纯重构，行为不变）

**做什么**：把 sync_service 中"写 PG"的逻辑收敛到 `WideTableStore` 接口后面，PG 实现包住现有代码。

**怎么做**：
```
backend/services/fraudhunter/wide_table_service/store/
├── __init__.py          # get_store(config) 工厂
├── base.py              # WideTableStore 抽象接口
└── pg_store.py          # PgWideTableStore：收编现有 AnalyzeDBPartitionManager 调用
```

接口（以现有调用面为准，不发明新概念）：
```python
class WideTableStore(ABC):
    def ensure_table(...) -> None                    # create_wide_table + ensure_partition
    def write_full(sql, table, refresh_sql) -> (rows, cols)      # _execute_with_pyspark_to_pg / jdbc
    def table_ref(snapshot) -> str                    # 返回 SQL 中可用的表引用（PG 表名）
    def drop_table(name) / cleanup(...)
```

- `sync_service.py` 中对 `AnalyzeDBPartitionManager`、`_execute_with_*_to_pg` 的直接调用改为经 store；方法本身逻辑一行不改，只挪位置；
- `offline_store=postgresql` 时工厂返回 PgStore，行为与现状完全等价。

**测试**：
- 单测：工厂按配置返回正确实现；PgStore 方法到 AnalyzeDBPartitionManager 的调用映射（mock 验证参数透传）；
- 回归：内网测试环境手动触发一次 `offline_wide_table_sync`。

**验收标准**：
- 回归同步成功：快照 ready、行数/列数与重构前一致，`[阶段耗时]` 日志各阶段齐全；
- 代码中 `sync_service.py` 不再直接 import `AnalyzeDBPartitionManager` 的写路径。

**回退**：revert 单个提交即可，无数据影响。

---

### 阶段 3：DuckdbParquetStore 全量路径（staging 中转）

**做什么**：新增 DuckDB 存储 backend，实现"executor 写 staging → DuckDB 拉 Parquet → 对账 → 落盘"全量链路。

**怎么做**：
```
backend/services/fraudhunter/wide_table_service/store/duckdb_parquet_store.py
```

核心流程（`write_full`）：
1. `CREATE UNLOGGED TABLE _staging_{wide_table}_{vh8}_{yyyymmdd} (...)`（复用 `create_heap_table` 的类型映射，加 `unlogged=True` 参数）；
2. **原样复用** `_execute_with_pyspark_to_pg(pivot_sql, staging_table)`——executor 并行 JDBC 写，数据不过应用服务器；
3. DuckDB 执行（独立连接，复用/扩展 `duckdb_analyze_pool`）：
   ```sql
   INSTALL postgres; LOAD postgres;
   ATTACH 'dbname=... host=...' AS pg_src (TYPE POSTGRES, READ_ONLY);
   COPY (SELECT * FROM pg_src.public._staging_xxx)
   TO '{dir}.tmp/' (FORMAT PARQUET, COMPRESSION ZSTD);
   ```
4. 对账：三方行数（`df.count()` vs staging `count(*)` vs parquet 行数）+ 指标列抽样 checksum（DuckDB `md5` 聚合比对）；
5. 原子 rename `{dir}.tmp → etl_date=D`；
6. `DROP TABLE _staging_xxx`；
7. 快照落库：`storage_backend='duckdb'`，`parquet_file_path=目录`。

配套：
- staging TTL 清理任务（扫 `_staging_%` 前缀、超过 `staging_ttl_hours` 的孤儿表 DROP），挂入统一调度；
- 同步入口按 `offline_store` 路由到对应 store；`both` 模式串行执行两 store，PG 先、Parquet 后，各自独立快照记录。

**测试**：
- 单测（本地 DuckDB + mock PG）：parquet 写入/对账/rename/DROP 的 SQL 生成与状态机；
- 集成（本地 docker PG + DuckDB，小数据量手工灌 staging）：全流程跑通，故意制造对账不一致（改一行数据）验证失败路径：不 rename、不 DROP、快照 failed、staging 保留；
- E2E（内网，真实 Spark/Hive）：`offline_store=duckdb` 跑一个宽表一个日期。

**验收标准**：
- E2E 同步成功：快照 ready、三方对账通过；
- `read_parquet` 查询结果与同日期 PG 正式表 SELECT 行数一致、抽样值一致；
- staging 表已删除，Parquet 目录结构与规范一致；
- 同步中途 kill 进程重跑：staging 被复用或清理，最终状态正确（幂等）。

**回退**：`offline_store` 改回 `postgresql`；已生成 Parquet 目录无副作用。

---

### 阶段 4：查询路由与方言适配

**做什么**：指标查询、回测、规则执行按 `snapshot.storage_backend` 路由执行引擎；SQL 生成支持 duckdb 方言。

**怎么做**：
1. 新增 `backend/services/fraudhunter/wide_table_service/store/query_router.py`：
   - 入参：快照集 + SQL 模板；出参：可执行 SQL + 目标执行器；
   - postgresql 快照 → 现状路径（`AnalyzeDBConnector.execute_sql`），表引用为 PG 表名；
   - duckdb 快照 → DuckDB 执行，离线表引用替换为 `read_parquet('{snapshot.parquet_file_path}/etl_date=D/*.parquet')`，实时表引用替换为 ATTACH 别名（`pg_rt.schema.table`）；
   - DuckDB 连接初始化时统一 `ATTACH ... (TYPE POSTGRES, READ_ONLY)`，对实时表查询必须携带日期过滤（谓词下推前提，回测 SQL 天然满足）；
2. `rule_engine.py` 的 SQL 生成加 `dialect` 参数，差异收敛到新文件 `backend/services/fraudhunter/model_service/sql_dialect.py`：
   ```python
   class SqlDialect:            # postgresql / duckdb
       def regex_match(expr, pattern) -> str    # PG: expr ~ pattern；DuckDB: regexp_full_match(expr, pattern)
       def cast_expr(expr, type) -> str
       def quote_ident(name) -> str
   ```
   只允许这三类原语出现 if-dialect，其余表达式保持 ANSI；
3. 改造调用点：`indicator_query_service.py`（数据预览）、`model_executor.py`（回测/干跑 SQL 构建与执行）、`realtime_indicator_job.py`（实时任务中 LEFT JOIN 离线宽表的段落，按离线快照 backend 分支）。

**测试**：
- 单测：SqlDialect 三原语双方言输出正确性；query_router 的表引用替换（含混合快照集报错提示）；
- 集成：同一指标查询在双后端执行，`pandas.testing.assert_frame_equal` 核对结果（含类型注记差异清单）；
- E2E：`offline_store=duckdb` 下跑一次完整回测（含实时表 JOIN 离线 Parquet），与 PG 模式回测结果 diff。

**验收标准**：
- 双后端同一回测：命中行集合一致（排序后逐行比对，允许浮点/类型展示差异，需在结果中注记）；
- PG 模式所有现有查询路径回归通过（默认 dialect 不变）；
- duckdb 模式查询日志中可见实时表过滤条件（谓词下推生效，可 EXPLAIN 验证）。

**回退**：路由层 fallback——任何 duckdb 路径异常自动回退 PG 路径并告警日志（仅当该快照在 PG 侧仍存在时）。

---

### 阶段 5：互转工具

**做什么**：PG 离线表 ↔ Parquet 按日期互转的 CLI 与管理 API，用于存量迁移与应急反向回退。

**怎么做**：
1. `backend/scripts/wide_table_transfer.py`（CLI）：
   ```
   --wide-table cust_wide_table --version-hash xxx \
   --dates 2026-08-01 2026-08-02 | --backfill 30 \
   --direction pg2duckdb | duckdb2pg \
   [--keep-source] [--overwrite]
   ```
2. `wide_table_routes.py` 加 `POST /wide-tables/transfer` 端点（单表单日粒度，前端可后补）；
3. pg2duckdb 核心与阶段 3 的第 3-6 步同源（抽取公共函数 `pull_pg_to_parquet(table, etl_date, dest_dir)`）：
   ```sql
   COPY (SELECT * FROM pg_src.public.{wide_table}_{vh8}
         WHERE etl_date = DATE '2026-08-01')
   TO '{dir}.tmp/' (FORMAT PARQUET, COMPRESSION ZSTD);
   ```
4. duckdb2pg：`read_parquet` → 经 postgres 扩展写回 PG 正式表（先 ensure_table + partition）；
5. 元数据规则：对账通过后才把快照 `storage_backend` 改写、`parquet_file_path` 回填；`--keep-source`（默认）保留 PG 表，清理交给现有 `get_old_version_tables`/分区清理延迟处理；
6. 幂等：目标日期目录已存在则跳过（`--overwrite` 除外）。

**测试**：
- 集成：本地 PG 灌样本数据 → pg2duckdb → 读 parquet 校验；再 duckdb2pg 往返 → 双侧 checksum 一致；
- 幂等：连续执行两次，第二次全部 skip；中断重跑（手动删半个 tmp 目录）无残留。

**验收标准**：
- 真实环境抽 3 个日期完成 PG→Parquet 迁移：行数、checksum、查询结果三项一致；
- 切 `offline_store=duckdb` 后，指标查询/回测直接可用迁移后的快照，无需重新同步；
- 反向（duckdb2pg）演练一次成功（应急回退通道可用）。

---

### 阶段 6：DuckDB 增量路径

**做什么**：DuckDB 模式下版本变化时只同步变化列（对齐 PG 的 `insert_select_from_base_delta` 语义）。

**怎么做**：
1. 复用现有 `VersionDelta`（`domain/wide_table/version_delta.py`）差异计算，不重写；
2. 增量流程：
   - PIVOT 只含 `inc_cols`（changed + new）→ 写 staging delta 表（UNLOGGED，仅含变化列 + target_id + etl_date，体积小）；
   - DuckDB 本地合并（`write_delta` 核心）：
     ```sql
     COPY (
       SELECT s.target_id, s.etl_date,
              s.{static_cols...},          -- 旧 Parquet 列式读取，只读这些列
              d.{inc_cols...}
       FROM read_parquet('{旧版本目录}/etl_date=D/*.parquet') s
       JOIN read_parquet('{delta.parquet}') d
         ON s.target_id = d.target_id AND s.etl_date = d.etl_date
     ) TO '{新版本目录}/etl_date=D.tmp/' (FORMAT PARQUET, COMPRESSION ZSTD);
     ```
   - 对账（新目录行数 = 旧目录行数）→ rename → DROP staging；
   - removed 列：不 SELECT 即消失；无变化 + 有可复用旧表：新快照直接指向旧 Parquet 目录（Parquet 不可变，复用零拷贝、绝对安全）；
3. 版本目录引用计数：多个快照指向同一目录时，清理任务按引用数判断，防止误删。

**target_id universe 不变量（Issue #7，硬约束）**：
增量列改写以旧版本 Parquet 为 LEFT JOIN 左表（`old s LEFT JOIN delta d`），隐含前提是
**同一 etl_date 下，不同指标版本之间的 target_id 集合保持不变**。旧版本快照生成后源数据
补入新 target_id 时，该对象在 LEFT JOIN 中会被静默丢弃，且"新旧行数相等"无法发现。
因此增量执行前先做反连接计数校验（delta 中旧版本不存在的 target_id 数量）：
- 计数 > 0 → 抛 `TargetUniverseChangedError`，`sync_service` 捕获后**自动回退全量路径**重算；
- 纯列裁剪（无 delta 表）无新增对象风险，跳过校验。

**失败语义（Issue #6，local/remote 一致）**：
- 对账失败（行数/列集/checksum/universe 校验）：保留 tmp 目录与 staging 现场，
  路径落日志供人工复核，由 Parquet 清理任务 TTL 兜底删除；
- SQL/COPY 执行失败：清理不完整 tmp（remote 模式立即清理；local 模式由下次
  同步的 `_prepare_tmp_dir` 幂等清理），staging 保留、TTL 兜底。

**测试**：
- 单测：增量 SQL 生成（增/删/改列组合矩阵）；
- 集成：构造 v1 → 加 2 个指标 + 删 1 个 + 改 1 个 → v2，验证：staging 只含变化列（日志断言列数）、新版本目录行数与 v1 相同、static 列值逐行一致、inc 列为新值；
- E2E：真实环境制造一次版本演进，比较增量路径与全量回退路径产出的 parquet checksum 一致（正确性等价证明）。

**验收标准**：
- 增量路径网络传输量 = 变化列（Spark → staging 行数、staging → parquet 列数可从日志量化对比全量）；
- 增量与全量产出等价（checksum 一致）；
- 版本不变场景零同步（快照秒级 ready，指向旧目录）。

---

### 阶段 7：灰度、切换与清理

**做什么**：`both` 双写验证 → 切纯 duckdb → PG 旧数据延迟退役。

**怎么做**：
1. `offline_store=both` 运行 ≥ 1 个完整同步周期（含至少一次版本变化），每日自动对账双侧行数 + checksum，结果落日志与快照；
2. 对账连续通过后切 `duckdb`；存量 PG 快照用阶段 5 工具按需迁移（近 N 个月常用日期优先）；
3. PG 旧表退役：`--keep-source` 解除，走现有 `get_old_version_tables` 清理，保留最近 30 天可回退窗口；
4. 前端宽表版本页展示 `storage_backend` 标记（`wide-table-versions` 页面小改）。

**验收标准**：
- 双写周期内对账 0 失败；
- 切换后 3 个工作日：同步、指标查询、回测、实时任务（JOIN 离线段）全部正常，无 PG 离线表回退发生；
- 清理任务释放 PG 空间，且被引用计数的 Parquet 目录未误删。

**回退**：任一环节不达标 → `offline_store` 切回 `postgresql`，duckdb 快照查询走阶段 4 的 fallback 或经互转工具反向回 PG。

## 四、测试策略总述

| 层级 | 环境 | 覆盖内容 | 位置 |
|---|---|---|---|
| 单元 | 本地（DuckDB + mock） | SQL 生成、对账函数、状态机、方言原语、工厂 | `tests/backend/modules/wide_table_sync/` 新增子模块 |
| 集成 | 本地 docker PG + DuckDB | staging 全流程、互转往返、失败路径、幂等 | 同上，标记 `@pytest.mark.integration` |
| E2E | 内网测试环境（真实 Spark/Hive/PG） | 真实同步任务、双写对账、回测 diff | 手动触发 + `[阶段耗时]` 日志核验 |

单日数据规模基准（沿用历史文档）：100 万-1000 万行 / 500MB-5GB，E2E 验收以此量级为准。

## 五、风险清单

| 风险 | 影响 | 缓解 |
|---|---|---|
| `parquet_file_path` 字段语义复用（PG 表名 ↔ Parquet 路径） | 老代码误读 | 阶段 4 全量梳理该字段读取点，一律经 `query_router`；字段语义由 `storage_backend` 决定 |
| DuckDB postgres 扩展类型边界（numeric 精度、timestamptz） | 数据失真 | 集成测试显式覆盖这些类型；`numeric_type_utils` 扩展双后端映射 |
| UNLOGGED 表在有流复制的 PG 上不同步 | 备库看不到 staging | staging 本就无需复制；确认 DBA 无依赖备库读 staging 的用法 |
| DuckDB COPY 内存 | OOM | `SET memory_limit`；COPY 流式本身友好，单测验证 5GB 级 |
| 双写期间 staging 与正式表并发写 PG | 连接/磁盘压力 | `both` 模式串行执行；staging 即用即删 |
| Parquet 目录被多快照复用后被清理误删 | 数据丢失 | 引用计数 + 清理任务只删引用为 0 的目录 |

## 六、里程碑

| 里程碑 | 内容 | 预估规模 |
|---|---|---|
| M1 | 阶段 1+2（基础 + 抽象重构） | 小，纯结构改动 |
| M2 | 阶段 3（staging 中转全量路径） | 中，核心新代码 |
| M3 | 阶段 4+5（查询路由 + 互转工具） | 中，改动面最宽 |
| M4 | 阶段 6（增量） | 中 |
| M5 | 阶段 7（灰度切换） | 运维节奏主导 |
