# FraudHunter 离线宽表双存储开发计划

> 状态：一期代码实施完成（2026-08-19）；二期（灰度可测性 + DS 部署适配）代码实施完成（2026-10-11），见 **第七章**，待内网联调后按 7.8 灰度
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
> 上线前置动作（一期原版，**已被第七章 7.8 灰度步骤取代**，保留备查）：
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

---

## 七、二期：灰度可测性与 DS 部署适配（2026-10-11 计划）

### 7.1 背景与诉求

一期代码完成后，评审上线方式时发现以下问题：

1. **零影响未被证明**：PG 路径经阶段 2 重构、阶段 4 路由改造，目前只是"逻辑等价"，缺少能证明"不切 DuckDB 时 PG 行为与 main 完全一致"的测试。
2. **`both` 不是纯影子写**：`query_router.preferred_snapshot_backend()` 在 `offline_store=both` 时优先读 duckdb 快照。直接切到 `both`，线上实时预警、模型执行、回测会**立刻全量改读 DuckDB**，与"写 both、读 PG、单独验证 DuckDB"的灰度意图相反。
3. **缺少 DuckDB 读路径的旁路验证手段**：没有办法在不影响线上告警的前提下，单独跑一次"DuckDB 版实时预警"并查看结果。
4. **离线同步实际在 DS（Hadoop 集群）执行**（`2bdc94d` 起，`main.py` 已注释掉 `offline_wide_table_sync`）：
   - DuckDB 路径中，"PG staging → Parquet"及落盘必须发生在淘沙机器上，DS worker 无法写淘沙磁盘；
   - DS worker 到淘沙机器 duckdb 容器（9494/9495）**网络不通**，只能访问淘沙后端端口；
   - 当前 remote 模式下，同步路径仍有 3 处直接访问本地文件系统（见 7.4.1），在 DS 上会出错或静默退化。
5. **`both` 模式 Spark 跑两遍**：PG 后端和 DuckDB 后端各自执行一次 Spark PIVOT（DuckDB 侧写 staging），灰度期间 Spark/JDBC 负载翻倍。
6. **后端机器 glibc 低**：只能装低版本 duckdb 包（或者不装），DuckDB 2.0（quack）只在容器中运行。

二期目标：

| # | 目标 | 对应阶段 |
|---|---|---|
| G1 | 不切换时 PG 行为与 main 一致，并有测试证明 | 阶段 8 |
| G2 | 读、写分别配置，全局生效（实时、离线、账户、客户） | 阶段 9 |
| G3 | DS 上执行离线同步，Parquet 相关操作全部委托给淘沙后端接口 | 阶段 10 |
| G4 | `both` 模式只跑一次 Spark | 阶段 11 |
| G5 | 提供"只算不落库"的预警试跑工具（CLI + API），可对比 PG 与 DuckDB 结果 | 阶段 12 |

**不在本期范围**：
- `services/query_engine` 顶层 `import duckdb` 的处理（平台通用查询引擎，由负责人单独处理）；
- 实时指标加工（step1）在 DuckDB 上的计算对比（可选扩展，见阶段 12 末尾）；
- `scripts/pg_partition_export.py` 走网关（仍需在装有 duckdb 的机器上运行）；
- 按宽表粒度的读写覆盖（评审结论：全局开关即可）。

### 7.2 目标部署架构

```
DS worker（Hadoop 集群，无 duckdb）               淘沙机器
┌──────────────────────────────┐               ┌───────────────────────────────────────┐
│ offline_wide_table_job.py    │               │ 淘沙后端 :50011（以生产实际端口为准） │
│  ① Spark PIVOT → PG          │               │  /fraudhunter/internal/wide-table-store│
│     （正式分区 / staging）   │──HTTP+token──▶│    probe / pull / merge / cleanup      │
│  ② 调淘沙内部接口            │               │    └ 复用 DuckdbParquetStore 现有实现  │
│  ③ 写快照元数据（MySQL）     │               │       duck_compute.mode = remote|local │
│  duck_compute.mode=delegate  │               │            │ 仅本机 127.0.0.1:9495     │
└──────────────────────────────┘               │  duckdb 容器（2.0 + quack + 网关）     │
          │ JDBC                               │  Parquet 目录（bind mount，路径一致）  │
          ▼                                    └───────────────────────────────────────┘
        PG ◀──────────── ATTACH pg_rt / pg_src（只读）─────────────┘
```

要点：
- DS 侧只做 PG 同步本来就在做的事（Spark、写 PG、写 MySQL），**不装 duckdb，不访问淘沙磁盘**；
- duckdb 容器的 9494/9495 只对淘沙本机开放；
- 容器 compose 必须打开 Parquet 目录挂载（`build_scripts/duckdb/docker-compose.yml` 第 38 行目前是注释状态），宿主机与容器内路径保持一致，等于 `fraudhunter.wide_table.duckdb.storage_path`，这样就不需要配置 `path_map`。

### 7.3 配置变更

```yaml
fraudhunter:
  wide_table:
    offline_store: both              # 写：postgresql | duckdb | both（含义不变）
    read_backend: postgresql         # 读：postgresql | duckdb（新增）
    duckdb:
      storage_path: /data/taosha/indicator_data/wide_tables_parquet

  duck_compute:
    mode: remote                     # local | remote | delegate（新增，DS 侧使用）
    endpoint: http://127.0.0.1:9495  # local/remote 使用：淘沙本机容器网关
    token: <GATEWAY_TOKEN>
    delegate:                        # mode=delegate 时使用（DS 侧）
      endpoint: http://<淘沙IP>:50011
      timeout_seconds: 1800          # 大表 COPY 可能持续数分钟

  internal_api:
    token: <共享TOKEN>               # 淘沙校验、DS 携带，两侧取值一致
```

`read_backend` 的默认值规则（保证存量配置行为不变）：
- 未配置时：`offline_store=duckdb` 读 duckdb，其余情况读 postgresql；
- 注意：这会改变现有 `both` 的读语义（原先 `both` 读 duckdb），属于有意修正，`both` 至今未在生产启用。

启动校验（`main.py` 启动阶段，以及 DS 脚本入口）：

| 组合 | 处理 |
|---|---|
| 写 postgresql + 读 duckdb | **启动失败**：不会产生 duckdb 快照 |
| 写 duckdb + 读 postgresql | 告警：PG 离线数据停止更新 |
| 淘沙后端配置 `mode=delegate` | **启动失败**：delegate 只能用于 DS 侧 |
| `internal_api.token` 为空 | 内部接口一律返回 503（默认拒绝），启动时打印告警 |

两侧的配置组合：

| | `offline_store` | `read_backend` | `duck_compute.mode` |
|---|---|---|---|
| 淘沙后端 | 与 DS 一致 | 按灰度阶段设置 | `remote`（低 glibc）或 `local` |
| DS 同步脚本 | 按灰度阶段设置 | 不涉及 | `delegate` |

---

### 阶段 8：零影响守护（G1）

**做什么**：用测试证明 `offline_store=postgresql`（默认）时，所有 SQL 与 main 分支逐字一致；并且部署时缺少迁移会立即报出明确错误，而不是在运行中零散报错。

**怎么做**：

1. **基准 SQL 采集**：新增 `tests/backend/modules/pg_golden/`。
   - 采集脚本 `capture_golden.py`：在 main 分支的 git worktree 中运行，用固定的输入（模型/规则定义、指标元数据、版本差异、日期，固定时间戳）生成 SQL，写入 `golden/*.sql`；
   - 覆盖范围：
     | 场景 | 入口 |
     |---|---|
     | 实时模型匹配 | `_build_model_matching_sql` |
     | 实时指标加工 | `_process_single_object_type` 内的 SQL 构建 |
     | 规则引擎 | `rule_engine` 条件/嵌套组编译 |
     | 回测/模型执行 | `model_executor` SQL 构建 |
     | 指标查询 | `_build_query_sql` / `_build_count_sql` |
     | 离线同步 | 全量 PIVOT、增量 PIVOT、`insert_select_from_base_delta`、建表/建分区 DDL |
   - 离线同步通过打桩 `AnalyzeDBConnector` / `AnalyzeDBPartitionManager` / Spark 执行器，按执行顺序捕获 SQL 序列；
   - 测试断言：本分支在 PG 模式下生成的 SQL 与 `golden/*.sql` **逐字相等**（只规整注释中的生成时间戳这一处）。
2. **PG 模式下不触碰 duckdb**：在子进程中将 `sys.modules['duckdb'] = None`，`offline_store=postgresql` 时跑完上述各入口，断言不出现 ImportError，也不调用 `get_query_session()`。
3. **启动时检查迁移**：`main.py` 初始化数据库阶段检查 `fraudhunter_wide_table_snapshot.storage_backend` 列是否存在；缺失时直接退出，并提示需要执行的迁移 SQL 文件名。DS 脚本入口做同样的检查。

**验收**：golden 测试全部通过；人为改动 PG 路径任意一处 SQL，测试必须失败。

**实施记录（2026-10-11）**：
- 基准与守卫：`tests/backend/modules/pg_golden/`（`harness.py` 场景执行器 + `golden/*.json` main 基准 + `test_pg_golden.py`）。7 个场景：实时 step1+step2、模型回测、指标查询、离线同步（全量 JDBC / 全量 PySpark / 增量 / 无变化跳过）。MySQL 用 SQLite 内存库（真实 ORM），PG 用 FakePG 记录 SQL，Spark 用替身；当前分支额外启用 `--forbid-duckdb`。
- 基准采集过程中发现并修正了 2 处与 main 的偏差：
  1. 指标查询 PG 快照的表引用被改成了日期分区表名，改回 `parquet_file_path` 原值（主表 + etl_date 过滤）；
  2. 离线同步对"已有 ready 快照"的日期多做了一次 PG 复制源探测（存在性 + 行数查询），已调整为先检查已存在快照、再探测复制源，与 main 顺序一致。
- 配置加载新增 `TAOSHA_CONFIG_FILE` 环境变量（未设置时行为不变），供测试指定配置文件。
- 迁移检查与计划略有不同：沿用项目已有的 `_apply_lightweight_migrations` 惯例，**启动时自动补 `storage_backend` 列**（只加列，存量回填 postgresql）；唯一索引扩展涉及删除重建，不自动执行。`verify_wide_table_snapshot_schema()` 在 `main.py` 启动与 DS 入口调用：列缺失任何模式都拒绝；唯一索引未扩展时仅允许 `offline_store=postgresql`。因此部署顺序是先升级淘沙后端，再升级 DS。

---

### 阶段 9：读写分离（G2）

**做什么**：新增 `read_backend` 配置，快照选择只看读配置；DuckDB 维护任务仍按写配置启用。

**怎么做**：
1. `utils/config.py`：新增 `fraudhunter_wide_table_read_backend`（默认 `None`，按 7.3 的规则推导）；
2. `query_router.preferred_snapshot_backend()` 改为返回推导后的读后端。所有读路径已经统一经过 `select_snapshot_by_preferred_backend()`：
   - `realtime_indicator_job._get_latest_offline_snapshot`（实时指标加工 + 实时模型匹配）
   - `model_executor`（模型执行 / 回测）
3. `offline_store_uses_duckdb()`、`main.py` 中的 `duck_maintenance_enabled` / `dual_write_enabled` 保持按**写**配置判断，不改；
4. 7.3 中的启动校验；
5. 读后端没有快照时的现有回退（回退到最新一条快照并告警）保留，日志中同时打印读配置与实际选中的后端。

**测试**：`test_snapshot_backend_selection.py` 补充写/读组合矩阵（3×2），以及读配置未设置时的默认推导、启动校验失败用例。

**验收**：`offline_store=both` 且 `read_backend=postgresql` 时，实时任务、回测选中的都是 PG 快照，生成的 SQL 与阶段 8 的 golden 一致。

**实施记录（2026-10-11）**：
- `query_router.resolve_read_backend()` / `validate_store_config()` 为纯函数；`preferred_snapshot_backend()` 改为返回读后端；`main.py` 启动与 DS 入口调用校验并打印 `[存储配置] 写=… 读=… duck_compute=…`；
- `config.yaml.example` 增加 `read_backend` 注释示例；
- 验收由 `test_pg_golden.py::test_shadow_write_keeps_pg_read_path` 覆盖：`both` 写、不配置读后端、库内存在生成时间更晚的 duckdb 快照时，实时任务、回测、指标查询的 SQL 与 main 基准一致，且全程未进入 DuckDB 路径。

---

### 阶段 10：淘沙内部存储接口 + DS delegate 模式（G3）

#### 7.4.1 DS 上会出问题的本地文件访问点

| 位置 | 现状 | DS 上的后果 |
|---|---|---|
| `sync_service.py` `_find_duckdb_copy_source`（约 220 行） | 本地 `glob` 判断旧 Parquet 是否存在 | 永远找不到 → **每次都悄悄退化为全量同步** |
| `duckdb_parquet_store.py` `merge_delta_insert_select`（约 224 行） | `Path(base_table).is_dir()` | 直接抛异常 |
| `duckdb_parquet_store.py` `ensure_table`（约 114 行） | `storage_path.mkdir()` | 在 DS 本地建空目录，没有权限时直接失败 |
| local 模式的 `_prepare_tmp_dir` / `_atomic_landing` / 文件大小统计 | 本地文件操作 | delegate 模式下不会走到；需要守卫测试保证 |

#### 7.4.2 接口定义

路由前缀：`/api/taosha/v1/fraudhunter/internal/wide-table-store`，新文件 `backend/api/fraudhunter/internal_wide_table_store_routes.py`。

**鉴权**：请求头 `X-Internal-Token`，与 `fraudhunter.internal_api.token` 做常量时间比较（`hmac.compare_digest`）；配置为空时一律返回 503。不挂 `get_current_user`（非用户接口）。

**设计原则**：接口按业务动作设计，**不接受 SQL，也不接受路径**。
- 目录由服务端根据 `storage_path` + `version_dir_name` + `etl_date` 拼接；
- 所有名称类参数（`version_dir_name`、`source_pg_table`、`delta_table`、列名）必须匹配 `^[a-z0-9_]+$`，长度 ≤ 128；
- `etl_date` 按 `YYYY-MM-DD` 解析；
- 拼出的路径 `resolve()` 后必须位于 `storage_path` 之下。

| 接口 | 请求体 | 响应 | 服务端行为 |
|---|---|---|---|
| `POST /parquet/probe` | `version_dir_name, etl_date` | `{exists, rows, final_dir}` | 统计日期目录的行数；目录或文件不存在时 `exists=false` |
| `POST /parquet/pull` | `source_pg_table, version_dir_name, etl_date, expected_rows?` | `{rows, column_count, checksum, files, size_bytes, final_dir}` | COPY 源 PG 表 → 临时目录 → 对账（`expected_rows` 有值时比较 Spark 或源行数，并比较 PG 与 Parquet 的行数和校验和）→ 原子落盘 |
| `POST /parquet/merge` | `base_version_dir_name, dest_version_dir_name, etl_date, delta_table?, static_cols[], inc_cols[]` | `{rows, files, size_bytes, final_dir}` | 检查对象范围 → 合并 COPY → 行数对账 → 原子落盘 |
| `POST /parquet/cleanup` | `version_dir_name, etl_date` | `{removed}` | 幂等删除残留的临时目录 |

错误码（响应体 `{error_code, message}`）：

| HTTP | error_code | DS 侧处理 |
|---|---|---|
| 401 | `UNAUTHORIZED` | 失败，提示检查 token |
| 409 | `TARGET_UNIVERSE_CHANGED` | 抛 `TargetUniverseChangedError` → 现有逻辑回退全量 |
| 409 | `BUSY` | 同一目标正在被另一请求写入；按退避重试 |
| 422 | `RECONCILE_FAILED` | 失败，保留现场（与一期 Issue #6 语义一致） |
| 422 | `INVALID_ARGUMENT` | 失败 |
| 503 | `NOT_CONFIGURED` | token 未配置，或服务端 mode 非法 |

**服务端实现要点**：
- 路由函数写成同步 `def`（FastAPI 会放进线程池执行），**不能写成 `async def`**，否则长时间 COPY 会阻塞所在 worker 的事件循环，实时预警任务也跑在这个事件循环上；
- 内部直接调用 `DuckdbParquetStore` 现有方法（按服务端 `duck_compute.mode` 走 local 或 remote），对账与落盘逻辑**不重写**；
- 并发与幂等：对 `final_dir` 加文件锁（`fcntl.flock`，跨 uvicorn worker 有效），抢不到锁时返回 `BUSY`；原子落盘本身是覆盖式的，DS 网络中断后重试是安全的；
- 每个请求打印 `[内部存储接口]` 日志：接口、目标、耗时、行数、结果。

#### 7.4.3 DS 侧 delegate 模式

- `DuckdbParquetStore` 增加 delegate 分支（与现有 local/remote 分支并列）：
  - `write_pivot`：Spark → PG staging（不变）→ `POST /parquet/pull`（`source_pg_table=staging`，`expected_rows=spark_rows`）→ 成功后由 DS DROP staging；失败时保留 staging，由 TTL 兜底清理；
  - `merge_delta_insert_select`：Spark → PG delta 表（不变）→ `POST /parquet/merge`；
  - `ensure_table`：delegate 模式下不执行 `mkdir`；
  - 快照的 `parquet_file_path` / `file_size_bytes` **使用接口返回的 `final_dir` / `size_bytes`**，不在 DS 侧用自身的 `storage_path` 拼接，避免两侧配置不一致；
- `sync_service._find_duckdb_copy_source`：本地 glob + 计数改为调用 `probe`（local/remote 模式也统一改为 probe 语义的内部函数，三种模式共用同一套判定逻辑）；
- 零拷贝路径（`_zero_copy_snapshot`）只写 MySQL 元数据，确认不访问文件系统；
- 新增 `delegate_client.py`（requests，带超时，`BUSY` 时退避重试 3 次）。

**测试**：
- 接口：token 正确/错误/未配置；非法名称（`../`、大写、超长）；路径越界；锁冲突返回 BUSY；各错误码到 DS 侧异常的映射；
- DS 侧守卫：delegate 模式下把 `Path.glob/is_dir/mkdir/exists`、`shutil.*`、`os.rename` 打桩成直接报错，并设置 `sys.modules['duckdb']=None`，跑通全量、增量、零拷贝、回退全量四条路径（接口用 mock server）；
- 集成：在本地启动后端，DS 侧以 delegate 模式调用真实接口，接口内部走 remote 模式访问 duckdb 容器，完成一次全量和一次增量同步。

**验收**：在内网 DS 上以 delegate 模式完成一次 `both` 同步；`[duckdb增量诊断]` 日志能正确选中旧 Parquet 目录（不再静默退化为全量）；DS worker 本地没有产生任何 Parquet 相关目录。

**实施记录（2026-10-11）**：
- 服务端：`store/parquet_ops.py`（`ParquetOpsService`，复用 `DuckdbParquetStore` 的 local/remote 实现）+ `api/fraudhunter/internal_wide_table_store_routes.py`（4 个同步 `def` 路由，`X-Internal-Token` 常量时间比较，token 为空时 503）；
- DS 侧：`store/delegate_client.py`；`DuckdbParquetStore` 增加 delegate 分支（`write_pivot` → `pull`，`merge_delta_insert_select` → `merge`，`ensure_table` 不建本地目录，`snapshot_ref` 取服务端返回路径）；新增公共方法 `land_staging_to_parquet()`、`probe_parquet()`，服务端与本地模式共用；`_find_duckdb_copy_source` 改为调用 `store.probe_parquet()`；
- `pull_pg_partition_to_parquet()` 增加可选 `expected_rows`（阶段 11 使用）；
- 配置：`fraudhunter.duck_compute.delegate.{endpoint,timeout_seconds}`、`fraudhunter.internal_api.token`；同时修正 `config.yaml.example` 中 `duck_compute` 误缩进在 `wide_table` 下的问题（代码读取的是 `fraudhunter.duck_compute`，原示例会被静默忽略）；
- 修复既有 bug：`sync_service._zero_copy_snapshot` 误加 `@staticmethod`，导致 DuckDB "版本无变化零拷贝"路径在任何模式下都会报参数缺失；
- 测试：`tests/backend/modules/delegate_store/`（20 项检查，独立子进程运行），包含 DS delegate 全链路同步在"禁止本地文件系统 + 禁止 duckdb"下的全量、增量、对象范围变化回退全量、零拷贝、路径不一致不复用。
- 已知未改（main 既有行为）：同一日期所有后端都失败时 `sync_wide_table` 返回 `None`，`_sync_dates` 会因 `None.get` 抛错，由外层按宽表捕获。

---

### 阶段 11：`both` 模式复用 PG 正式分区，只跑一次 Spark（G4）

**做什么**：`both` 模式下 PG 后端先执行。只要本次 PG 已经成功产出该日期的正式分区（或者已存在同版本同日期的 ready PG 快照），DuckDB 后端就直接 `pull` 这个 PG 分区，不再跑 Spark，也不再写 staging。

**怎么做**：
1. `sync_service` 在 `both` 模式下把 PG 后端的结果（分区名、行数）传给 DuckDB 后端；
2. DuckDB 后端的全量路径和增量路径都改为：`pull(source_pg_table=PG正式分区, expected_rows=PG快照行数)`。PG 新分区已经是新版本的完整数据，所以 `both` 模式下不需要走 merge；
3. 指标完全未变化时的零拷贝逻辑保持不变；
4. PG 后端失败时，DuckDB 后端回退到自己跑 Spark（现有路径），并在日志中注明原因；
5. `pull` 的对账就是"PG 分区与 Parquet 的行数 + 校验和比对"，相当于每次同步都**内置了一次双写对账**；`dual_store_reconcile_job` 保留，作为兜底。

**测试**：`both` 模式下断言 Spark 执行器只被调用一次；PG 失败时 DuckDB 回退并自行调用 Spark；对账失败时 DuckDB 快照不写入。

**验收**：内网 `both` 同步时，Spark 任务数与纯 PG 模式相同；`[阶段耗时]` 日志中 DuckDB 后端没有 PIVOT 阶段。

**实施记录（2026-10-11）**：
- `sync_wide_table` 在 `both` 模式下根据 PG 结果确定 DuckDB 的数据源（`_pg_source_for_duckdb`）：
  - PG 本版本快照 ready（本次新同步或已存在）→ 拉取 PG 本版本表（按 etl_date 过滤），`expected_rows` = PG 快照行数；
  - PG 因"版本无变化且有可复用旧分区"跳过 → 拉取该旧分区（实施中补充的情形，计划未列出）；
  - 其他（PG 失败等）→ DuckDB 走自身原有路径（Spark → staging）。
- 优先级：DuckDB 版本无变化零拷贝 > 从 PG 拉取 > 自身增量/全量；
- 从 PG 拉取失败（如对账不一致）时 DuckDB 快照标记 failed，**不**静默改跑 Spark（对账失败意味着两侧数据真实不一致，应暴露）；
- 新增 `DuckdbParquetStore.write_from_pg_table()`（local/remote 复用 `pull_pg_partition_to_parquet`，delegate 走 `pull(source_kind=partition)`）；
- 日志关键字：`[双写复用]`；测试见 `delegate_store/checks.py` 的 `check_both_*`（6 项）。

---

### 阶段 12：实时预警试跑工具（G5）

**做什么**：按指定后端组装并执行一次"实时模型匹配"，**只输出命中结果**，不写执行记录、不生成命中/告警/管控记录、不发消息、不写任何表。

**CLI**：`backend/scripts/realtime_alert_dry_run.py`

```bash
# 用 DuckDB 快照跑一次在线模型匹配
python scripts/realtime_alert_dry_run.py --backend duckdb
# PG 与 DuckDB 各跑一次并对比差异
python scripts/realtime_alert_dry_run.py --backend both --models M001 M002 --output hits.csv
```

参数：`--backend postgresql|duckdb|both`（必填）、`--models`（模型编码，默认全部在线模型）、`--etl-date`（离线快照日期，默认取各后端最新的 ready 快照）、`--realtime-table`（覆盖实时表分区名，默认取最近一次实时快照）、`--limit`（打印样例行数，默认 20）、`--output`（导出 CSV，`both` 模式下额外输出差异文件）、`--show-sql`。

**API**：`POST /api/taosha/v1/fraudhunter/backend-compare/realtime-match`，请求体与 CLI 参数一致，挂 `get_current_user` 普通用户鉴权；响应为各后端的命中统计、样例和差异，不返回全量明细，全量请用 CLI 导出。

**执行流程**：
1. 数据库会话只读，结束时统一 `rollback()`；
2. 实时表：读取实时快照记录（`version_hash IS NULL`，当天）中的 `parquet_file_path`，即线上实时任务最近一次产出的分区；**不重新加工实时指标**（step1 会写 PG）；`both` 模式下两个后端使用同一个实时分区；
3. 离线快照：`_get_latest_offline_snapshot(db, name, backend=<强制>)`，再经 `resolve_offline_table_refs()` 解析表引用；打印每张表的 etl_date、版本号、存储后端、快照 id；`both` 模式下两侧 etl_date 或版本不一致时**醒目告警**（结果没有可比性）；
4. 生成 SQL：复用生产的 `_build_model_matching_sql()`（与线上完全相同的 SQL 构建逻辑）；
5. 执行：PG 走 `AnalyzeDBConnector`；DuckDB 走 `get_query_session(attach_pg=True)`（remote 模式访问容器网关）；
6. 输出：每个模型的命中数、耗时、样例行；`both` 模式下按（模型编码、`target_id`）对比，输出只在 PG 命中、只在 DuckDB 命中、两边都命中但字段值不一致的行（浮点比较容差 1e-9，可配置）。

**需要的重构**（生产行为不变，由阶段 8 golden 测试守护）：
- `step2_online_model_executor` 拆出纯函数 `run_model_matching(db, models, offline_tables, realtime_tables, duckdb_mode) -> (sql, matched_df)`，生产路径改为调用它，执行记录的写入留在 step2；
- `_get_latest_offline_snapshot` 增加可选参数 `backend`（为 `None` 时走读配置，即现状）。

**测试**：试跑过程中断言没有任何 `db.add/commit/flush`、`ModelHitAlertManager` 未被调用、消息发送桩未被调用；`both` 差异计算的单测（三类差异、浮点容差）。

**可选扩展**（不在本期必做范围，约 1 天）：`--with-realtime-indicators`，用指定后端重新计算 step1 实时指标，得到 DataFrame 后与 PG 实时表同一分区对比，不写入。

**实施记录（2026-10-11）**：
- 服务层 `services/fraudhunter/model_service/realtime_dry_run.py`；CLI `backend/scripts/realtime_alert_dry_run.py`；接口 `api/fraudhunter/backend_compare_routes.py`（`POST /fraudhunter/backend-compare/realtime-match`，用户鉴权，同步 `def`，不返回全量明细，差异列表截断并附 `*_count`）；
- 生产代码重构：`step2_online_model_executor` 的执行部分抽为 `execute_model_matching_sql()`（SQL 构建本就是独立的 `_build_model_matching_sql`）；`_get_latest_offline_snapshot` 增加可选 `backend`（指定时只取该后端、不回退）。生产行为由阶段 8 golden 守护，未变化；
- CLI 退出码：两侧一致且无错误为 0，有差异或任一后端出错为 1，参数/前置数据问题为 2，便于脚本化每日对比；
- 测试 `tests/backend/modules/realtime_dry_run/`（11 项），其中 PG 试跑 SQL 直接与 golden 中线上 step2 的 SQL 逐字比对。

---

### 7.5 工作量与顺序

| 顺序 | 阶段 | 估时 | 说明 |
|---|---|---|---|
| 1 | 阶段 8 零影响守护 | 1–1.5 天 | 最先做，后续所有重构都依赖它守护 |
| 2 | 阶段 9 读写分离 | 0.5 天 | |
| 3 | 阶段 10 内部接口 + delegate | 2 天 | 接口 1 天，DS 侧 0.5–1 天，测试 0.5 天 |
| 4 | 阶段 11 `both` 只跑一次 Spark | 0.5 天 | 依赖阶段 10 的 `pull` 源表参数 |
| 5 | 阶段 12 试跑 CLI + API | 2 天 | CLI 1.5 天，API 0.5 天 |
| | **合计** | **约 6–6.5 天** | 不含内网联调 |

每个阶段独立提交、可以单独回退。

### 7.6 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 内部接口不走用户鉴权 | 被误调用或扫描 | 共享 token + 接口不接受 SQL 和路径 + 名称白名单 + 路径越界校验；token 未配置时默认拒绝 |
| 长时间 COPY 占用后端线程池 | 影响其他接口 | 同步 `def` 放进线程池；文件锁让同一目标串行；必要时为内部接口单独起一个 uvicorn 实例 |
| DS → 淘沙之间经过代理导致超时 | 同步失败 | DS 直连后端端口；客户端超时 1800s；落盘是幂等的，可以安全重试 |
| DS 与淘沙的 `storage_path` 不一致 | 快照路径错误 | DS 侧只使用接口返回的 `final_dir` |
| duckdb 2.0 alpha（容器内） | 稳定性 | 灰度期间问题不大；切换到读 duckdb 之前升级正式版并回归（`build_scripts/duckdb/README.md` §八） |
| `both` 读语义修正（原先读 duckdb，改为读 PG） | 预期不一致 | 生产从未启用 `both`；在 7.3 和发布说明中写明 |
| 试跑工具与线上实时任务同时运行 | 实时分区刚好切换，导致 PG 与 DuckDB 两次执行读到的数据不同 | `both` 模式两次执行固定使用同一个实时分区名 |

### 7.7 部署前置

1. 两个迁移 SQL 已执行（阶段 8 的启动检查会兜底）；
2. 淘沙机器：duckdb 容器打开 Parquet 目录挂载（路径一致），9494/9495 只对本机开放；淘沙后端配置 `duck_compute.mode=remote`、`internal_api.token`；
3. DS：部署包与淘沙同版本；配置 `duck_compute.mode=delegate`、`delegate.endpoint`（淘沙后端实际端口）、`internal_api.token`；
4. 网络：DS worker → 淘沙后端端口（已确认可通）。

### 7.8 灰度上线步骤（取代文档开头的"上线前置动作"）

| 步骤 | 写 | 读 | 操作与观察 | 退出条件 |
|---|---|---|---|---|
| S0 | postgresql | postgresql | 部署二期代码，配置不变 | 一个同步周期 + 实时任务正常，行为与上线前一致 |
| S1 | **both** | postgresql | 线上读写仍是 PG；DuckDB 只是影子写；每次同步都有 `pull` 内置对账，再加每日 `[双写对账]` | ≥1 周期（含一次版本变化），对账 0 失败；DS 本地没有残留文件 |
| S2 | both | postgresql | 每天用 `realtime_alert_dry_run.py --backend both` 对比命中；指标查询按 duckdb 快照 id 抽查；回测对比 | 连续 N 天（建议 3–5 天）命中差异为 0，或差异均已解释 |
| S3 | both | **duckdb** | 线上改读 DuckDB；PG 继续写，用于兜底 | 3 个工作日内实时告警、回测、查询全部正常 |
| S4 | **duckdb** | duckdb | 停止写 PG；用 `wide_table_transfer.py` 按需迁移存量日期 | — |
| S5 | duckdb | duckdb | PG 旧表按现有 `get_old_version_tables` 退役（保留 30 天回退窗口） | — |

### 7.9 回退矩阵

| 当前步骤 | 回退操作 | 影响 |
|---|---|---|
| S1 / S2 | 写改回 `postgresql`（淘沙与 DS 两侧都改），重启 | 无业务影响；已生成的 duckdb 快照保留，不会被读取 |
| S3 | 读改回 `postgresql`，重启淘沙后端 | 立即恢复 PG 读；PG 数据一直在写，没有缺口 |
| S4 及以后 | 写改回 `both` 或 `postgresql`，读改回 `postgresql`；S4 期间缺失的 PG 日期用 `wide_table_transfer.py --direction duckdb2pg` 补齐 | 补数完成前，PG 读会触发"回退到最新快照"的告警 |
