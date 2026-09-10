# DuckDB 计算容器化迁移规划 (HTTP + DuckDB 容器)

> 背景: `feature/offline-dual-store` 分支已把离线宽表计算从 PG 迁到进程内 DuckDB
> (`import duckdb` + 本地 Parquet + ATTACH PG)。但部分后端机器 glibc 为 2.17,
> pip 的 duckdb wheel 要求 glibc >= 2.27 (符号底线 GLIBC_2.25), 无法安装。
> 方案: 计算挪进已验证的 DuckDB 容器 (`build_scripts/duckdb`, 单容器双端口),
> 后端机器零 duckdb 依赖, 只发 HTTP。
>
> 前置验证 (2026-09-10 已完成): 容器内 duckdb 2.0-alpha 服务端 + HTTP 网关,
> CentOS 7 (glibc 2.17) 仅用 curl 远程查询实测通过, 详见 `build_scripts/duckdb/README.md`。

## 一、目标架构

```
后端机器 (glibc 2.17, 只有 FastAPI/requests)          计算容器 (docker, glibc 2.36)
┌─────────────────────────────┐                 ┌────────────────────────────────┐
│ indicator_query_service     │                 │ duckdb 服务端 (server.py)        │
│ model_executor        ──────┼──HTTP JSON────▶ │ 网关 :9495 (gateway.py, /query) │
│ sync_service (诊断)         │                 │   │ 容器内 loopback quack       │
│ RemoteDuckSession (新增)    │                 │   ▼                            │
└─────────────────────────────┘                 │ duckdb :9494 + /data/duck.db    │
                                                │   ├─ read_parquet(宽表快照卷)   │
        PG (staging/实时表) ◀───────────────────┼───┤ ATTACH pg_rt (READ_ONLY)    │
                                                └────────────────────────────────┘
```

部署形态二选一:

| 形态 | 说明 | 适用 |
|---|---|---|
| **A. 同机容器 (推荐起步)** | 每台后端机器本地跑一个 duckdb 容器, 后端连 `127.0.0.1:9495`; 宽表 Parquet 目录直接 bind mount 进容器 | 改动最小, 无网络/数据搬迁, 单机吞吐即原进程内水平 |
| B. 集中计算服务器 | 独立机器跑容器, 所有后端共享 | 宽表数据需集中 (NFS/对象存储/同步), 后续按需演进 |

## 二、现状盘点 (分支上全部 duckdb 使用点 → 迁移矩阵)

| # | 位置 | 用法 | 数据访问 | 迁移动作 |
|---|---|---|---|---|
| 1 | `wide_table_service/store/query_router.py` `DuckQuerySession` | 每次查询新建 `duckdb.connect()`, `execute_df()` → DataFrame | 读本地 Parquet; `ATTACH pg_rt` 只读 PG | 换 `RemoteDuckSession` (同接口, 走 HTTP) |
| 2 | `indicator_service/indicator_query_service.py:299` | `DuckQuerySession(attach_pg=False)`: count + 分页查询 | `read_parquet(glob)` | 只换 session, SQL 不动 |
| 3 | `model_service/model_executor.py:553` | `DuckQuerySession(attach_pg=True)`: 模型/回测执行, 结果可能大 | Parquet JOIN `pg_rt.*` 实时表 | 换 session; 大结果集传输见 §4 |
| 4 | `wide_table_service/store/duckdb_parquet_store.py` | 写路径: `_attach_pg()` + `COPY staging→Parquet` + 三方对账 (多语句, 需在同一连接上执行) | PG staging → Parquet | 整体挪进容器: 网关加批量/事务端点, 或封装为专用端点 |
| 5 | `wide_table_service/sync_service.py:231` | `duckdb.connect()` 单条 count 诊断 | read_parquet | 换 RemoteDuckSession |

范围说明: `services/query_engine/duckdb_service.py` (平台通用查询引擎, 供 Agent SQL 工具)
不在本分支 fraudhunter 链路内, 暂不迁移, 后续可复用同一容器。

## 三、关键设计

### 3.1 表引用与路径映射 (最大的坑)

`query_router.offline_table_ref()` 生成的引用内嵌了**后端机器的绝对路径**:

```sql
read_parquet('/data/wide_table/xxx/etl_date=2026-09-10/*.parquet', hive_partitioning=false)
```

挪容器后, 路径必须是**容器内**路径。SQL 生成逻辑不动, 增加配置化前缀重写:

```yaml
# backend/config/config.yaml
fraudhunter:
  duck_compute:
    mode: remote                      # local(现状进程内) | remote(HTTP容器)
    endpoint: http://127.0.0.1:9495   # 形态A=本机; 形态B=计算服务器
    token: ${DUCKDB_GATEWAY_TOKEN}
    path_map:                         # 后端路径前缀 → 容器内路径前缀
      /data/wide_table: /data/wide_table
    request_timeout_seconds: 300
```

`RemoteDuckSession.execute_df()` 发送前做前缀替换; 容器 compose 里 bind mount 同一目录,
`path_map` 大多为一一对应 (同机形态可直接挂相同路径, 重写为空操作)。

### 3.2 RemoteDuckSession (后端唯一新增代码面)

对齐 `DuckQuerySession` 接口, 调用方一行不改 (工厂切换):

```python
# backend/services/fraudhunter/wide_table_service/store/remote_session.py
class RemoteDuckSession:
    """与 DuckQuerySession 同构: execute_df(sql) -> pandas DataFrame | None"""
    def __enter__(self): ...          # 无状态, HTTP 就绪检查
    def execute_df(self, sql): ...    # POST /query → 列式JSON → pandas.DataFrame
    def __exit__(self, *a): ...
```

`query_router` 增加工厂: `get_query_session(attach_pg) -> DuckQuerySession | RemoteDuckSession`,
按 `mode` 配置返回。ATTACH 语义差异: remote 模式下 PG 由**服务端容器启动时** ATTACH,
后端不再传 attach_pg (参数保留, 忽略), `pg_rt.*` 引用不变 → **SQL 层零改动**。

### 3.3 服务端容器增强 (build_scripts/duckdb)

| 项 | 现状 (lab级) | 目标 |
|---|---|---|
| 执行并发 | 单连接+锁, 串行 | 连接池 (每请求独立连接, quack_query 本身无状态), uvicorn 多 worker |
| 结果格式 | JSON rows (逐行数组) | 默认列式 JSON (columns + 列数组, DataFrame 重建零损失且更省流量); 可选 `format: arrow` (Arrow IPC base64) 用于超大结果 |
| 行数上限 | 10000 | 可配, 默认放开到配置值 (回测命中记录可能远超 1 万) |
| 多语句/事务 | 无 | `POST /batch` (顺序执行 + 全成功才提交) 支撑写路径对账等 |
| 超时/取消 | 无 | per-request 超时, 透传 duckdb 错误 (code/message/position) |
| ATTACH PG | 无 | server.py 启动时 `ATTACH pg_rt (READ_ONLY)`, 失败仅告警可重试 |
| 观测 | stdout 日志 | 请求日志: sql指纹/耗时/行数/错误; /health 带 pool 状态 |

### 3.4 写路径迁移 (duckdb_parquet_store)

`pull_pg_partition_to_parquet` 的 PG→Parquet 拷贝+对账本质是**固定模板的多条 SQL**:
ATTACH、COPY、行数/校验和比对、原子落盘目录操作。两种迁法:

- **推荐**: 网关加语义化端点 `POST /ops/pull-parquet` {pg_conn_id, staging_table, target_dir},
  模板 SQL 在服务端拼装执行, 目录原子切换在容器内完成 → 后端只拿到结果摘要
  (rows/checksum/落地路径), 减少SQL暴露面;
- 备选: `POST /batch` 直接下发现有 SQL 序列 (模板继续留在后端, 服务端无业务感知)。

## 四、性能与风险

| 风险 | 评估 | 对策 |
|---|---|---|
| HTTP+JSON 序列化开销 | 分页查询 (~100行) 可忽略; 指标聚合小结果可忽略 | 大结果集走列式 JSON / Arrow; 超 10万行按批拉取 |
| 大结果集 (回测 rows_matched) | 原进程内零拷贝 → 现在过网 | 列式压缩 + Arrow 可选; 必要时服务端先落 Parquet 再传文件路径 |
| 网关单点 | 容器 restart 已有; quack 连接失效网关已做重试 | 同机形态故障域=单机, 与现状进程内故障域等价 |
| duckdb 2.0 alpha 稳定性 | 已避开 linux CLI 认证 bug; alpha 明确不保生产 | 10月下旬正式版发布后改 Dockerfile 版本号回归即可 (见 build_scripts/duckdb/README §八) |
| NaN/Inf 与 dtype 语义 | JSON 无 NaN; model_executor 已有 NaN 清洗 | 列式 JSON 保留 null; int 列强制按 types 还原 dtype, 补单测 |
| 并发上限 | 服务端 quack 写并发 ~数千tx/s (官方口径), 读并发更好 | 指标查询/回测频次远低; 连接池上限+排队指标先观测 |

## 五、实施阶段

| 阶段 | 内容 | 验收 |
|---|---|---|
| 0 ✅ | duckdb 容器 + quack + HTTP 网关验证 (build_scripts/duckdb, 已提交 master) | CentOS 7 curl 查询通过 |
| 1 ✅ | 网关增强 (§3.3): 连接池/列式JSON/batch/分段写/超时/ATTACH PG | 并发8路通过; 端点单测+集成验证通过 |
| 2 ✅ | 后端 RemoteDuckSession + 配置开关 + 工厂切换 (§3.1/3.2); 读路径 3 个调用点 (#2 #3 #5) 接入 | 既有 364 测试全过(local不变); 新增 15 个 remote 单测 + 真容器集成验证 |
| 3 ✅ | 写路径迁移 (网关分段写协议 /write+/write-land+/write-cleanup) + sync_service 诊断 | SQL builder 别名化共用, 对账断言 local/remote 同一实现; 分段协议真容器验证通过 |
| 4 | 灰度: 单后端机器 remote 模式试运行 → 全量; 移除后端 duckdb 依赖 | 生产观测一周 (错误率/耗时/内存) |
| 5 | (可选) 2.0 正式版升级; 形态B集中化演进 | 正式版回归 |

## 六、与现有代码的衔接

- 分支 `docs/fraudhunter_offline_dual_store_plan.md` 的"阶段4 查询路由"即本规划的接入点,
  `storage_backend` 路由逻辑完全复用, 本规划只替换其下层的"执行引擎"。
- 配置开关默认 `local`, 保证分支既有测试 (test_query_router.py 等) 不受影响;
  remote 模式新增对应用例 (mock HTTP 或起容器跑集成测试)。
- `build_scripts/duckdb` 容器随本仓库交付, 同机部署一条命令:
  `cd build_scripts/duckdb && QUACK_TOKEN=xxx docker compose up -d`。
