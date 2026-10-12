# 离线宽表双存储 操作手册

> 适用分支：`feature/offline-dual-store`（二期，2026-10-11）
> 设计与实施细节见 `docs/fraudhunter_offline_dual_store_plan.md` 第七章；本文只讲怎么部署、怎么切、怎么验、怎么退。

## 一、角色与端口

| 角色 | 跑在哪 | 做什么 | 需要访问 |
|---|---|---|---|
| 淘沙后端 | 淘沙机器 | 实时预警、回测、指标查询；提供内部存储接口 | PG、MySQL、本机 duckdb 容器 `127.0.0.1:9495` |
| duckdb 容器 | 淘沙机器 | 执行 DuckDB SQL、读写 Parquet | PG（只读 ATTACH） |
| 离线同步脚本 | DS（Hadoop 集群） | Spark → PG、写快照元数据；Parquet 操作调淘沙接口 | PG、MySQL、Spark、**淘沙后端端口** |

- DS 只需要能访问淘沙后端端口（以生产实际监听端口为准，`sbackend.sh` 中为 50011）；
- duckdb 容器的 9494/9495 只对淘沙本机开放，不需要对外。

## 二、配置

### 2.1 淘沙后端 `backend/config/config.yaml`

```yaml
fraudhunter:
  wide_table:
    offline_store: postgresql        # 写：postgresql | duckdb | both（按灰度阶段改）
    # read_backend: postgresql       # 读：postgresql | duckdb；不配时 offline_store=duckdb 读 duckdb，其余读 PG
    duckdb:
      storage_path: /data/taosha/indicator_data/wide_tables_parquet

  duck_compute:                      # 注意：与 wide_table 同级，不要缩进到 wide_table 下面
    mode: remote                     # 低 glibc 机器用 remote；能装 duckdb 的机器可用 local
    endpoint: http://127.0.0.1:9495
    token: <GATEWAY_TOKEN>           # 与容器 GATEWAY_TOKEN 一致

  internal_api:
    token: <共享TOKEN>               # 与 DS 一致；为空时内部接口全部拒绝
```

### 2.2 DS 离线同步 `backend/config/config.yaml`

```yaml
fraudhunter:
  wide_table:
    offline_store: postgresql        # 与淘沙后端保持一致
    duckdb:
      storage_path: /data/taosha/indicator_data/wide_tables_parquet   # 仅占位，实际以淘沙返回的路径为准

  duck_compute:
    mode: delegate                   # DS 专用：Parquet 操作委托淘沙后端
    delegate:
      endpoint: http://<淘沙IP>:50011
      timeout_seconds: 1800

  internal_api:
    token: <共享TOKEN>               # 与淘沙后端一致
```

> 淘沙后端不能配 `delegate`；`offline_store=postgresql` 时不能配 `read_backend: duckdb`。配置不合法时启动直接失败，日志会说明原因。

### 2.3 duckdb 容器（`build_scripts/duckdb/docker-compose.yml`）

- 设置 `GATEWAY_TOKEN`、`DUCKDB_PG_ATTACH_DSN`（PG 连接串，容器内以只读方式 ATTACH）；
- **打开 Parquet 目录挂载**（默认是注释的），宿主机与容器内路径一致：
  ```yaml
  volumes:
    - /data/taosha/indicator_data/wide_tables_parquet:/data/taosha/indicator_data/wide_tables_parquet
  ```
- 端口映射建议只绑本机：`127.0.0.1:9495:9495`。

## 三、部署步骤

1. **执行唯一索引迁移**（`storage_backend` 列淘沙后端启动时会自动补，索引需手工执行）：
   ```sql
   -- backend/migrations/update_snapshot_unique_with_backend.sql
   ```
   不执行也能以纯 PG 模式运行，但切 `both`/`duckdb` 时启动会失败并提示该文件名。
2. **先升级淘沙后端**（配置保持 `offline_store: postgresql`），启动日志应出现：
   ```
   [存储配置] 写=postgresql 读=postgresql duck_compute=remote
   ```
3. **再升级 DS 同步脚本**（同一版本代码）。DS 入口会校验快照表结构，淘沙后端未先升级时直接报错退出。
4. 启动 duckdb 容器，在淘沙机器上自检：
   ```bash
   curl -s http://127.0.0.1:9495/health
   ```
5. 在 DS 机器上自检内部接口（token 正确应返回 JSON，错误返回 401）：
   ```bash
   curl -s -X POST http://<淘沙IP>:50011/api/taosha/v1/fraudhunter/internal/wide-table-store/parquet/probe \
     -H 'Content-Type: application/json' -H 'X-Internal-Token: <共享TOKEN>' \
     -d '{"version_dir_name":"dep_acct_wide_table_00000000","etl_date":"2026-10-09"}'
   ```

## 四、灰度切换

每一步改的是两侧配置中的 `offline_store` / `read_backend`，改完重启对应进程。

| 步骤 | 写 `offline_store` | 读 `read_backend` | 改哪里 | 进入下一步的条件 |
|---|---|---|---|---|
| S0 | postgresql | （不配） | — | 一个同步周期 + 实时任务正常 |
| S1 | **both** | （不配，即读 PG） | 淘沙 + DS | ≥1 个周期（含一次版本变化），对账 0 失败 |
| S2 | both | （不配） | — | 连续 3–5 天试跑对比无差异（或差异均已解释） |
| S3 | both | **duckdb** | 淘沙 | 3 个工作日实时告警、回测、查询正常 |
| S4 | **duckdb** | duckdb | 淘沙 + DS | 按需迁移存量日期 |
| S5 | duckdb | duckdb | — | PG 旧表按现有清理逻辑退役（保留 30 天） |

### S1 每天检查

在淘沙后端 / DS 日志中检索：

| 关键字 | 含义 | 期望 |
|---|---|---|
| `[双写复用]` | DuckDB 直接拉取 PG 数据（不跑 Spark） | 每个新同步日期出现一次 |
| `三方对账通过` | PG 与 Parquet 行数、校验和一致 | 与 `[双写复用]` 一一对应 |
| `[双写对账] PASS` / `FAIL` | 每日定时双写对账 | 无 FAIL |
| `[duckdb增量诊断]` | DuckDB 增量基准选择 | 版本变化后能"选中可复用旧Parquet目录" |
| `[duckdb-delegate]` | DS 调用淘沙接口的耗时与结果 | 无报错 |

DS worker 本地不应产生任何 Parquet 目录。

### S2 每天试跑对比（在淘沙机器上执行，不入库、不发消息、不管控）

```bash
cd /data/taosha/taosha_analyse_platform/backend
python scripts/realtime_alert_dry_run.py --backend both --output /tmp/dry_run_$(date +%Y%m%d).csv
```

- 退出码：`0` 两侧一致；`1` 有差异或某一侧出错；`2` 参数/前置数据问题；
- 输出中"仅 PG 命中 / 仅 DuckDB 命中 / 字段值不一致"均为 0 才算通过；差异明细在 `*_diff.json`；
- 出现"离线快照不一致"告警时，两侧用的不是同一天/同一版本的数据，结果不可比，先排查同步；
- 常用参数：`--models M001 M002`、`--etl-date 2026-10-09`、`--show-sql`、`--realtime-table dep_acct_no=<分区表名>`。

也可调用接口（需登录 token）：

```bash
curl -s -X POST http://<淘沙IP>:50011/api/taosha/v1/fraudhunter/backend-compare/realtime-match \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer <用户token>' \
  -d '{"backend":"both","limit":5}'
```

### S4 迁移存量日期（PG → Parquet）

```bash
python scripts/wide_table_transfer.py --wide-table dep_acct_wide_table \
  --version-hash <版本hash> --backfill 30 --direction pg2duckdb
```

## 五、回退

| 当前在 | 操作 | 影响 |
|---|---|---|
| S1 / S2 | 两侧 `offline_store` 改回 `postgresql`，重启 | 无业务影响；已生成的 DuckDB 快照保留但不再被读取 |
| S3 | 淘沙 `read_backend` 改回 `postgresql`（或删掉该行），重启淘沙后端 | 立即恢复读 PG；PG 一直在写，数据无缺口 |
| S4 及以后 | 两侧改回 `both`，`read_backend` 改回 `postgresql`；S4 期间缺失的 PG 日期用 `wide_table_transfer.py --direction duckdb2pg` 补齐（需在能装 duckdb 的机器以 local 模式执行） | 补数完成前，读 PG 会出现"回退使用最新快照"告警 |

## 六、常见问题

| 现象 | 原因 / 处理 |
|---|---|
| 启动失败：`缺少 storage_backend 列` | 淘沙后端未先升级（DS 先跑了），或数据库账号无 ALTER 权限；手工执行 `add_snapshot_storage_backend.sql` |
| 启动失败：`需要唯一索引 uk_fh_ws_table_date 包含 storage_backend` | 执行 `update_snapshot_unique_with_backend.sql` |
| 启动失败：`read_backend 不能为 duckdb` / `delegate 仅用于 DS` | 配置组合不合法，按 2.1/2.2 修正 |
| DS 报 `UNREACHABLE` | DS 到淘沙后端端口不通，或 `delegate.endpoint` 写错 |
| DS 报 `UNAUTHORIZED` | 两侧 `internal_api.token` 不一致 |
| DS 报 `NOT_CONFIGURED` | 淘沙后端 `internal_api.token` 为空，或淘沙后端被配成了 delegate |
| DS 报 `BUSY` | 同一宽表同一日期正被另一请求写入；客户端自动重试 3 次，仍失败说明有并发同步任务 |
| DS 报 `RECONCILE_FAILED` | PG 与 Parquet 对账不一致，DuckDB 快照标记失败、现场保留；查淘沙后端日志中的 tmp 路径排查，下个同步周期会重试 |
| 增量总是走全量（`[全量回退]`） | 检索 `[duckdb增量诊断]`：若提示"服务端版本目录与快照记录不一致"，说明两侧 `storage_path` 或挂载路径变过 |
| remote 配置不生效 | 检查 `duck_compute` 是否误缩进到 `wide_table` 下面 |
