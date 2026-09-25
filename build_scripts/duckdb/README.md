# DuckDB 2.0 Alpha — Quack 远程查询服务端 (Docker)

> 调研 + 镜像构建日期: 2026-09-09。alpha 版本迭代很快, 本文的版本号以当天官方渠道为准。
> 位置: `taosha_analyse_platform/build_scripts/duckdb/`

## 一、DuckDB 2.0 最近情况 (来自 duckdb.org/news)

- **2026-08-17** [A Preview of DuckDB v2.0](https://duckdb.org/2026/08/17/duckdb-20-highlights.html) — 2.0 特性预览
- **2026-08-20** [DuckDB v2.0: Your Database Deserves a Better Parser](https://duckdb.org/2026/08/20/duckdb-20-peg-parser.html) — 新 PEG 解析器
- **2026-09-02** [Try DuckDB v2.0-alpha](https://duckdb.org/2026/09/02/try-duckdb-20-alpha.html) — **v2.0 feature freeze**, 代号 **Cyanoptera**, 已从 main 分出 `v2.0-cyanoptera` 分支, 正式版目标 **2026 年 10 月下旬**
- 远程查询能力来自 **Quack 客户端/服务端协议** (2026-05-12 [公告](https://duckdb.org/2026/05/12/quack-remote-protocol.html)): HTTP 传输、端口 9494、MIME `application/duckdb`、token 认证, 官方基准中 6000 万行传输比 Arrow Flight 快 3 倍+

### 版本现状 (踩坑记录)

| 渠道 | 版本 | quack 扩展 | 可用性 |
|---|---|---|---|
| `curl https://install.duckdb.org \| DUCKDB_VERSION=alpha bash` (官方 alpha 频道, main 分支) | v2.1.0-alpha40775 | ✅ | **osx 服务端正常; linux 服务端有认证 bug (见下)** |
| `pip install duckdb --pre` (1.6.0.dev379) | 库 v2.0.0-alpha39998 | ✅ | **全平台正常 (本方案采用)** |
| artifacts.duckdb.org 的 `v2.0-cyanoptera` 分支 CLI | v2.0.0-alpha41047 | ❌ (扩展仓库未发布该版本任何扩展, 连 httpfs 都 404) | 不可用 |

⚠️ **linux CLI 的 quack 认证 bug**: 官方 alpha CLI 的 linux 版 quack 扩展 (f4328c5333) 做服务端时,
token 完全正确也一律 `Authentication failed` (容器内 127.0.0.1 loopback 也复现; 同版本 osx 二进制正常;
客户端侧无问题)。因此本项目的服务端镜像改用 **Python 库** (`pip duckdb --pre`), 其 linux quack 扩展工作正常。
客户端不受影响, 用 CLI / Python / Wasm 都能连。

## 二、架构与目录结构

**单容器双端口**: 一个容器里跑两个进程, 任一退出容器即重启。

```
客户端机器
  ├─ glibc >= 2.27 ────── quack 协议直连 ──▶ 9494 ┐
  │                                                │  同一容器
  └─ glibc < 2.27 (curl) ── JSON/HTTP ──────▶ 9495 ┤  ├─ duckdb 服务端 (server.py, 数据在 /data/duck.db)
                                                   └─┴─ HTTP 网关 (gateway.py, 经容器内 127.0.0.1:9494 转发)
```

```
build_scripts/duckdb/
├── Dockerfile            # 单容器镜像: duckdb 服务端 (9494) + HTTP 网关 (9495)
├── server.py             # duckdb 服务端: 打开持久库 + quack_serve + 常驻
├── gateway.py            # HTTP 网关: POST /query (SQL 永远推到 duckdb 服务端执行)
├── entrypoint.sh         # 容器入口: 双进程拉起与信号处理
├── build-portable-client.sh  # 生成 glibc 2.17 可用的 musl 便携客户端包 (直连 9494)
├── docker-compose.yml    # 服务 + 一次性测试客户端 (tools profile)
└── test/test_remote_query.py  # 远程查询测试脚本
```

## 三、启动

```bash
cd build_scripts/duckdb

# 设置 token (客户端连接时必须携带, >= 4 字符)
export QUACK_TOKEN=your-secret-token

docker compose up -d --build     # 构建并启动单容器: 9494 (quack) + 9495 (HTTP 网关)
docker compose ps                # 等待 healthy
docker compose logs -f duckdb-quack

# 常用操作
docker compose run --rm quack-client   # 跑一次容器间远程查询测试
docker compose down -v                 # 停止并清空数据
docker compose exec duckdb-quack python -c "import duckdb"  # 进容器
```

数据持久化在 named volume `duckdb_data` (数据库文件 `/data/duck.db`), 重启不丢。

## 四、远程连接方式

### 1. Python 客户端 (需要 glibc >= 2.27 的 Linux, 详见第七节)

```bash
pip install --pre duckdb        # 当前 = 1.6.0.dev379 (库 v2.0.0-alpha39998), 要求 Python >= 3.11
```

```python
import duckdb

con = duckdb.connect()
con.sql("INSTALL quack")   # 首次需要, 之后幂等
con.sql("LOAD quack")

HOST, PORT, TOKEN = "192.168.0.108", "9494", "your-secret-token"

# 方式 A: 无状态单次查询
rows = con.sql(f"""
    SELECT * FROM quack_query('quack:{HOST}:{PORT}', 'SELECT 42 AS answer',
                              token => '{TOKEN}', disable_ssl => true)
""").fetchall()

# 方式 B: ATTACH 成远程库 (DDL/写入/事务/过滤下推都支持)
con.sql(f"ATTACH 'quack:{HOST}:{PORT}' AS remote (TYPE quack, TOKEN '{TOKEN}', DISABLE_SSL true)")
con.sql("CREATE TABLE remote.t AS SELECT range AS i FROM range(10)")
print(con.sql("SELECT sum(i) FROM remote.t").fetchone())
```

> **`DISABLE_SSL true` 是必须的**: 客户端对非 localhost 地址默认走 HTTPS, 而本服务端未配 TLS。
> 公网部署请按官方文档用 nginx 做 TLS 终结反向代理。

### 2. CLI 客户端 (glibc >= 2.27 的机器; glibc 2.17 机器用第七节的便携包)

```bash
curl https://install.duckdb.org | DUCKDB_VERSION=alpha bash   # v2.1.0-alpha40775
```

```sql
ATTACH 'quack:192.168.0.108:9494' AS remote (TYPE quack, TOKEN 'your-secret-token', DISABLE_SSL true);
SELECT * FROM remote.t;
```

### 3. HTTP 网关 (✅ 老机器专用: 只需 curl, 零依赖; 也是 taosha 后端 remote 计算模式的入口)

quack 本身是二进制协议, 官方没有 JSON REST API。容器内置了一个**网关** (端口 9495),
SQL **永远推到 duckdb 服务端执行**, 网关只做协议转换 (连接池并发、列式 JSON、超时中断):

| 端点 | 用途 |
|---|---|
| `GET /health` | 健康 (含 quack 上游探测 + 连接池状态) |
| `POST /query` | `{"sql": "...", "format": "rows\|columns"}` 单条查询 |
| `POST /batch` | `{"sqls": [...]}` 顺序执行多条, 失败即停 |
| `POST /write` | 写路径分段协议 (见 gateway.py docstring): COPY/对账 SQL + `prepare`/`land` 开关 |
| `POST /write-land` | 分段写收尾: tmp → final 原子落盘 |
| `POST /write-cleanup` | 分段写失败清理 |

```bash
# 健康
curl http://<host>:9495/health

# 查询 (等价于直连 9494, 表名就是服务端上的表名)
curl -X POST http://<host>:9495/query \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <GATEWAY_TOKEN>' \
  -d '{"sql": "SELECT count(*) AS rows, sum(i) AS total FROM quack_test_rows"}'
# -> {"columns":["rows","total"],"types":["BIGINT","HUGEINT"],"rows":[[100,4950]],"row_count":1,"truncated":false}
```

鉴权: `Authorization: Bearer $GATEWAY_TOKEN` (默认复用 `QUACK_TOKEN`, 可用环境变量单独设置)。
`format=columns` 返回列式数据 (`{"data": {列名: [值...]}}`), 供后端 RemoteDuckSession 零损重建 DataFrame。
返回行数上限 `MAX_ROWS` (默认 100000, 超出截断并标记 `"truncated": true`);
连接池 `POOL_SIZE` (默认 4, 同时限制 active 总数, 池满排队 `POOL_WAIT_TIMEOUT` 秒后 503, 默认 60;
`/health` 的 `pool` 字段暴露 size/created/closed/active/waiting/idle 指标);
`DEFAULT_TIMEOUT` 覆盖 SQL 执行+fetch 全程 (超时经 interrupt 中断)。
可选 `PG_ATTACH_DSN` (libpq 连接串): 服务端启动时 ATTACH 为 `pg_rt` (只读), SQL 以 `pg_rt.public.*` 引用 PG 表。

taosha 后端接入方式见 `docs/duckdb_remote_compute_plan.md` 与
`backend/services/fraudhunter/wide_table_service/store/remote_session.py`
(配置 `fraudhunter.duck_compute.mode: remote` 即切换)。

### 4. quack 原生 HTTP 面

Quack 的 HTTP 面只有两个端点 (源码 `quack_http_server.cpp`):

| 端点 | 用途 |
|---|---|
| `GET /` | 健康检查, 返回 `This is a DuckDB Quack RPC endpoint...` |
| `POST /quack` | quack RPC 本体 (HTTP/2 + `application/duckdb` 二进制序列化, 供 DuckDB 客户端使用) |

**没有** JSON/REST 风格的 SQL 端点; "HTTP API" 就是 quack 二进制协议本身, 由 Python/CLI/Wasm 客户端原生使用。
健康检查: `curl http://<host>:9494/`

## 五、测试结果 (2026-09-10, macOS arm64 + OrbStack/Docker 29.4)

| 测试 | 结果 |
|---|---|
| HTTP 健康检查 (`GET /`) | ✅ |
| Python 客户端 @ 127.0.0.1 (无状态查询 / ATTACH 建表写入 / 聚合 / 过滤) | ✅ |
| Python 客户端 @ 局域网 IP (真远程, 非本机地址) | ✅ |
| 容器间 (quack-client 容器 → 服务端容器) | ✅ |
| CLI 客户端 (v2.1.0-alpha40775) → 服务端 | ✅ |
| 重启持久化 (建表 → restart → 数据完整) | ✅ |
| HTTP 网关: 健康/鉴权 401/查询/错误处理 400 | ✅ |
| **CentOS 7 (glibc 2.17) 仅用 curl 经网关查询** | ✅ |
| **CentOS 7 (glibc 2.17) 用 musl 便携客户端包直连 9494** | ✅ |
| 对照组: CLI 版镜像 (linux) 作服务端 | ❌ Authentication failed (上述 bug) |
| 对照组: glibc 2.17 装 pip wheel | ❌ manylinux_2_27 标签拒装 (无匹配 wheel) |

一键回归:

```bash
QUACK_TOKEN=testtoken123 docker compose up -d --build
QUACK_TOKEN=testtoken123 docker compose run --rm quack-client   # 容器间
QUACK_URI=quack:127.0.0.1:9494 QUACK_TOKEN=testtoken123 \
  python test/test_remote_query.py                              # 宿主机 (需 pip install --pre duckdb)
# 网关 (GATEWAY_TOKEN 默认取 QUACK_TOKEN)
curl -X POST http://127.0.0.1:9495/query -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer testtoken123' -d '{"sql":"SELECT 42"}'
```

## 六、Python 客户端安装与 glibc 要求

**安装方式**: 纯 wheel 安装, 无需编译 (官方不发布 sdist 之外的源码包给 pip):

```bash
pip install --pre duckdb     # 1.6.0.dev379, 底层库 v2.0.0-alpha39998
```

**Python 版本**: `>= 3.11` (发布 cp311 ~ cp314 的 wheel; macOS 10.15+/11.0 arm64、Windows 均有)。

**Linux 平台标签与 glibc 要求** (来自 PyPI wheel 文件名 + `.so` 符号分析):

| 项 | x86_64 | aarch64 |
|---|---|---|
| wheel 标签 (pip 安装门槛) | `manylinux_2_27_x86_64.manylinux_2_28_x86_64` → **glibc >= 2.27** | `manylinux_2_26_aarch64.manylinux_2_28_aarch64` → **glibc >= 2.26** |
| `.so` 实际引用的最高符号 | `GLIBC_2.25` | `GLIBC_2.25` |
| 外部动态库依赖 | 无 libstdc++ (静态链入), 仅 glibc 自带组件 | 同左 |

- 也就是说 **pip 能装并运行的底线是 glibc 2.27 (x86_64)**; 实测 Debian 10 (2.28) ✅、Debian 11 (2.31) ✅。
- **glibc 2.17 (CentOS 7) 不行**: pip 直接找不到匹配 wheel; 且 `.so` 引用 `GLIBC_2.25` 符号, 强行解开装上也会在加载时报错。
- **Alpine (musl) 不行**: 官方没有 `musllinux` wheel, pip 会尝试源码编译 (需要巨大 C++ 工具链, 实测失败)。
- 对应发行版: Ubuntu >= 18.04、Debian >= 10、RHEL/Rocky/Alma >= 8 可用; CentOS 7、Ubuntu 16.04、Debian 9、Alpine 不可用。

> 顺带: 官方 CLI 的 glibc 版二进制符号底线同样是 `GLIBC_2.25` (依赖仅 libc/libm/libdl/libgcc_s/libpthread),
> 也不支持 CentOS 7 原生运行; 但官方发布 **musl 静态版 CLI**, 见下一节方案 A。

## 七、glibc 2.17 老机器的零依赖方案 (已实测 CentOS 7)

### 方案 A: musl 便携客户端包 (不装任何东西, 解压即用)

官方 musl 版 CLI 不链接系统 glibc, 配上 musl loader 和 musl 版 libstdc++/libgcc 共 4 个文件,
可在任意 x86_64 Linux 上直跑 (实测 CentOS 7.9 / glibc 2.17 ✅):

```bash
# 在有 docker 的机器上生成 (产物 ~85MB, 不入库, .gitignore 已配置)
cd build_scripts/duckdb && ./build-portable-client.sh

# 拷贝 portable-client-amd64/ 到目标机器后:
./portable-client-amd64/quack-remote.sh <host>:9494 <token> \
  "SELECT count(*) FROM remote.quack_test_rows;"
# 或手动:
export LD_LIBRARY_PATH=/path/to/portable-client-amd64
/path/to/portable-client-amd64/ld-musl-x86_64.so.1 \
  /path/to/portable-client-amd64/duckdb -unsigned -c "<SQL>"
```

⚠️ `-unsigned` 说明: 官方扩展仓库**没有发布 musl 平台的 quack 扩展签名** (`.signature` 404),
签名校验必然失败, 只能跳过; 扩展文件本身仍从官方 `extensions.duckdb.org` 下载。
内网使用可接受, 用前请自行评估。

### 方案 B: HTTP 网关 (✅ 推荐, 真正的"纯服务"查询)

见第四节第 3 小节。客户端机器**只需要 curl** (或任意语言标准库 HTTP), 与本机 glibc/python 版本完全无关。
网关跑在容器里随 compose 一起部署 (端口 9495), 已在 CentOS 7 上实测通过。

选型建议: 机器上要跑复杂分析脚本 → 方案 A (完整 SQL/CLI 能力);
只是取数、出报表、接脚本 → 方案 B (curl 一行搞定, 维护成本最低)。

## 八、升级 / 正式版

正式版 (2026 年 10 月下旬) 发布后: 把 `Dockerfile` 里的 `duckdb==1.6.0.dev379` 改成正式版本,
或切回 `Dockerfile` (CLI 版, 镜像更小), 并验证 linux CLI 认证 bug 是否已修复
(`docker build -f Dockerfile .` 后跑同一套测试即可)。

## 九、PG Connector 镜像 (duckdb-quack:2.0-alpha-pg, 2026-09-23)

在现有生产镜像 `duckdb-quack:2.0-alpha` 之外新增的 **Alpha 实验镜像**，不替换生产镜像：
**构建期预装 PostgreSQL Connector（postgres 扩展）**，启动后无需联网即可 `LOAD postgres`
并 ATTACH PostgreSQL。

### 为什么需要独立镜像（dev379 无法预装 postgres）

2026-09-23 探测发现：pip `1.6.0.dev379`（库 v2.0.0-alpha39998）的 **postgres 扩展二进制
已从 alpha 扩展频道下架**（`INSTALL postgres` 后为空；quack 仍在），基于 dev379 的镜像
已无法在运行时下载/预装 postgres 扩展——`server.py` 的 `LOAD postgres`（设置
`PG_ATTACH_DSN` 时）在新构建的旧镜像上会失败。新镜像改用当前 alpha 频道仍完整的版本：

| 项 | 值（固定，不浮动） |
|---|---|
| pip 包 | `duckdb==2.0.0.dev2609222040` |
| 库版本 | `v2.0.0-alpha43089` |
| 预装扩展 | `postgres`（2.0 中注册名 `postgres_scanner`, `LOAD postgres` 为兼容别名）+ `quack` |

版本固定在 `Dockerfile.alpha-pg` 的 `ARG` 与 `build-alpha-pg.sh` 两处，升级时同步修改。

### 文件

| 文件 | 说明 |
|---|---|
| `Dockerfile.alpha-pg` | 镜像定义（构建期 `INSTALL postgres/quack` 进镜像内扩展缓存，并断言离线 LOAD 成功） |
| `docker-compose.alpha-pg.yml` | 服务编排；宿主端口 **9496/9497**（避开生产 9494/9495）；`verify` profile 附 PostgreSQL 16 验证库 |
| `build-alpha-pg.sh` | 构建 + 版本自检；`--verify` 一键跑最小验证测试 |
| `test/test_postgres_connector.py` | 最小验证：版本固定 / 离线 LOAD postgres / PG attach 读写往返 / quack 远程查询 + pg_rt 引用 |

### 构建与验证

```bash
cd build_scripts/duckdb
./build-alpha-pg.sh              # 仅构建
./build-alpha-pg.sh --verify     # 构建 + 起 compose 跑最小验证测试（含独立 PostgreSQL 16）
```

`PG_ATTACH_DSN` 默认为空（普通启动不 ATTACH，避免指向不存在的验证库白等重试）；
`--verify` 会显式注入 compose 内 `pg-verify-db` 的测试 DSN，脚本以 trap 保证
verify 失败/中断也能 `down -v` 清理验证环境。

### 验证结果（2026-09-23, macOS arm64 + Docker 29.4）

| 检查 | 结果 |
|---|---|
| 版本固定（pip=2.0.0.dev2609222040 / library=v2.0.0-alpha43089） | ✅ |
| postgres 扩展离线加载（`autoinstall_known_extensions=false` 后 `LOAD postgres`） | ✅ postgres_scanner bc6aab54de |
| PostgreSQL attach/connect 读写往返（建表/100 行写入/聚合/过滤） | ✅ |
| 服务端常驻 `pg_rt`（READ_ONLY）+ ATTACH 失败自动重试（`PG_ATTACH_RETRY_SECONDS`, 默认 60s） | ✅ |
| quack 远程查询透传 + 经 pg_rt 引用 PG 表 | ✅ |
| 网关连接池上限/排队（POOL_SIZE 语义见网关文档）、分段写协议、失败清理 | ✅ |

### 已知限制

- **quack 路径的服务端 DDL 会重复执行**：alpha43089 上经 `quack_query` 执行
  `CREATE TABLE ...` 会出现"执行两次"（第一次建表成功、第二次报 already exists）。
  生产写路径（COPY / DESCRIBE / checksum SELECT）不含服务端 DDL，不受影响；
  临时数据请用 `COPY (SELECT ...) TO '...parquet'` 直出。正式版发布后需复验。
- duckdb Python 连接**不可并发共享**（同连接并发执行报 Invalid Input Error），
  网关已按"每请求独占租约"隔离并实测 8 路并发稳定。
- alpha 版本明确不建议生产使用；`duckdb-quack:2.0-alpha`（dev379, quack only）
  仍是当前生产镜像，两者独立 tag、互不影响。
- 旧镜像（dev379）因 postgres 扩展下架，**新构建后无法使用 PG_ATTACH_DSN**；
  需要 PG 连接能力请使用本镜像（alpha-pg）。
