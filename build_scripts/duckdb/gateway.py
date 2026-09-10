"""DuckDB Quack HTTP 网关: 把 quack 二进制协议包成普通 JSON REST API.

与 duckdb 服务端跑在同一个容器里 (见 entrypoint.sh), 只连容器内 127.0.0.1:9494。
面向无法安装 duckdb 客户端的老旧机器 (例如 glibc 2.17 的 CentOS 7):
客户端只需要 curl / requests, 与本机 glibc / python 版本无关。

端点:
    GET  /health   健康检查 (顺带 ping 一次 quack 服务端, 报告连接池状态)
    POST /query    {"sql": "...", "format": "rows|columns"}    单条查询, 服务端执行
    POST /batch    {"sqls": ["...", ...], "format": ...}       顺序执行多条, 失败即停
    POST /write    {"sqls": [...], "tmp_dir": ..., "final_dir": ...}
                   写路径专用: 顺序执行 SQL + 临时目录原子落盘 (tmp→final),
                   任一 SQL 失败则清理 tmp 并中止, 不触碰 final_dir

响应格式 (向后兼容):
    format=rows (默认):    {"columns": [...], "types": [...], "rows": [[...], ...]}
    format=columns:        {"columns": [...], "types": [...],
                            "data": {列名: [值, ...]}}   # RemoteDuckSession 用, 重建 DataFrame 零损
    /batch、/write 返回 {"results": [单个结果, ...]} (+ /write 附带 "files"/"size_bytes")

鉴权: Authorization: Bearer $GATEWAY_TOKEN

错误: HTTP 400, body {"detail": {"error_type": "...", "message": "..."}}

环境变量:
    QUACK_URI          服务端地址, 默认 quack:127.0.0.1:9494
    QUACK_TOKEN        服务端认证 token
    GATEWAY_TOKEN      网关 Bearer token, 默认复用 QUACK_TOKEN
    MAX_ROWS           单条 SQL 返回行数上限, 默认 100000 (超出截断并标记 truncated)
    POOL_SIZE          quack 客户端连接池大小, 默认 4
    DEFAULT_TIMEOUT    单条 SQL 超时秒数, 0=不限制; 请求可用 timeout 参数覆盖
"""
import datetime
import decimal
import os
import queue
import threading

import duckdb
from fastapi import FastAPI, HTTPException, Request

QUACK_URI = os.environ.get("QUACK_URI", "quack:127.0.0.1:9494")
QUACK_TOKEN = os.environ.get("QUACK_TOKEN", "")
GATEWAY_TOKEN = os.environ.get("GATEWAY_TOKEN") or QUACK_TOKEN
MAX_ROWS = int(os.environ.get("MAX_ROWS", "100000"))
POOL_SIZE = int(os.environ.get("POOL_SIZE", "4"))
DEFAULT_TIMEOUT = float(os.environ.get("DEFAULT_TIMEOUT", "0"))

app = FastAPI(title="duckdb-quack-gateway", version="2.0-alpha")


# ---------------------------------------------------------------------------
# quack 客户端连接池: quack_query 无状态, 多连接并发执行
# ---------------------------------------------------------------------------
class _QuackPool:
    def __init__(self, size: int):
        self._size = size
        self._idle: queue.Queue = queue.Queue()
        self._created = 0
        self._lock = threading.Lock()

    def _new_conn(self) -> duckdb.DuckDBPyConnection:
        con = duckdb.connect()
        con.sql("INSTALL quack")  # 已安装时幂等
        con.sql("LOAD quack")
        return con

    @property
    def stats(self) -> dict:
        return {"size": self._size, "created": self._created,
                "idle": self._idle.qsize()}

    def _return(self, conn) -> None:
        if self._idle.qsize() < self._size:
            self._idle.put(conn)
        else:
            try:
                conn.close()
            except Exception:
                pass

    class _Lease:
        """借出的连接: 正常归还入池; 出现任何异常则关闭 (不回池)."""

        def __init__(self, pool: "_QuackPool", conn):
            self._pool, self.conn = pool, conn

        def __enter__(self):
            return self.conn

        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                self._pool._return(self.conn)
            else:
                try:
                    self.conn.close()
                except Exception:
                    pass
            return False

    def lease(self) -> "_Lease":
        try:
            conn = self._idle.get_nowait()
        except queue.Empty:
            with self._lock:
                self._created += 1
            conn = self._new_conn()
        return self._Lease(self, conn)


_pool = _QuackPool(POOL_SIZE)


def _jsonify(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).decode("utf-8", errors="replace")
    return str(value)


def _pushdown_sql(sql: str) -> str:
    inner = sql.replace("'", "''")
    return (
        f"SELECT * FROM quack_query('{QUACK_URI}', '{inner}', "
        f"token => '{QUACK_TOKEN}', disable_ssl => true)"
    )


def _exec_one(conn, sql: str, timeout: float):
    """在给定连接上推送执行一条 SQL, 返回 (relation|None).

    timeout > 0 时超时调用 conn.interrupt() 中断 (quack 客户端取消请求)。
    """
    if timeout and timeout > 0:
        timer = threading.Timer(timeout, conn.interrupt)
        timer.start()
        try:
            return conn.sql(_pushdown_sql(sql))
        finally:
            timer.cancel()
    return conn.sql(_pushdown_sql(sql))


def _result_payload(result, max_rows: int, fmt: str) -> dict:
    if result is None:  # DDL/DML 无结果集
        return {"columns": [], "types": [], "rows": [], "row_count": 0,
                "truncated": False}
    columns = result.columns
    types = [str(t) for t in result.types]
    fetched = result.fetchall()
    fetched = fetched[: max_rows + 1]
    truncated = len(fetched) > max_rows
    if truncated:
        fetched = fetched[:max_rows]
    if fmt == "columns":
        data = {
            col: [_jsonify(row[i]) for row in fetched]
            for i, col in enumerate(columns)
        }
        return {"columns": columns, "types": types, "data": data,
                "row_count": len(fetched), "truncated": truncated}
    rows = [[_jsonify(v) for v in row] for row in fetched]
    return {"columns": columns, "types": types, "rows": rows,
            "row_count": len(fetched), "truncated": truncated}


def _run_sql(sql: str, max_rows: int, fmt: str, timeout: float) -> dict:
    """从连接池取连接执行单条 SQL; 连接异常时换新连接重试一次."""
    last_err = None
    for attempt in (0, 1):
        lease = _pool.lease()
        try:
            with lease as conn:
                result = _exec_one(conn, sql, timeout)
            return _result_payload(result, max_rows, fmt)
        except duckdb.IOException as e:
            last_err = e
            if attempt == 0:
                continue  # 连接失效(服务端重启等): 换新连接重试
            raise
    raise last_err  # pragma: no cover


# ---------------------------------------------------------------------------
# 文件系统原语 (写路径 /write): 容器内路径, 与 duckdb 服务端共享挂载
# ---------------------------------------------------------------------------
import os as _os
import shutil


def _fs_prepare_tmp(tmp_dir: str) -> None:
    tmp = _os.path.abspath(tmp_dir)
    if _os.path.exists(tmp):
        shutil.rmtree(tmp)
    _os.makedirs(tmp)


def _fs_atomic_landing(tmp_dir: str, final_dir: str) -> None:
    """tmp → final 原子落盘 (与后端 _atomic_landing 同语义: trash 挪旧 + 失败回滚)."""
    tmp, final = _os.path.abspath(tmp_dir), _os.path.abspath(final_dir)
    if not _os.path.exists(tmp):
        raise RuntimeError(f"tmp 目录不存在: {tmp}")
    _os.makedirs(_os.path.dirname(final), exist_ok=True)
    trash = final + ".trash"
    if _os.path.exists(trash):
        shutil.rmtree(trash)
    if _os.path.exists(final):
        _os.rename(final, trash)
    try:
        _os.rename(tmp, final)
    except Exception:
        if _os.path.exists(trash) and not _os.path.exists(final):
            _os.rename(trash, final)
        raise
    if _os.path.exists(trash):
        shutil.rmtree(trash)


def _fs_dir_stats(final_dir: str) -> dict:
    files = sorted(
        _os.path.join(final_dir, f)
        for f in _os.listdir(final_dir) if f.endswith(".parquet")
    )
    return {"files": files, "size_bytes": sum(
        _os.path.getsize(f) for f in files)}


# ---------------------------------------------------------------------------
# HTTP 层
# ---------------------------------------------------------------------------
def _check_auth(request: Request) -> None:
    auth = request.headers.get("authorization", "")
    if auth != f"Bearer {GATEWAY_TOKEN}":
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")


async def _parse_body(request: Request) -> dict:
    body = await request.json()
    max_rows = min(int(body.get("max_rows", MAX_ROWS)), MAX_ROWS)
    fmt = body.get("format", "rows")
    if fmt not in ("rows", "columns"):
        raise HTTPException(status_code=400, detail=f"unknown format: {fmt}")
    timeout = float(body.get("timeout", DEFAULT_TIMEOUT))
    return body, max_rows, fmt, timeout


def _bad_request(e: Exception) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"error_type": type(e).__name__, "message": str(e)},
    )


@app.get("/health")
def health():
    try:
        _run_sql("SELECT 1", 1, "rows", 0)
        upstream = "ok"
    except Exception as e:  # noqa: BLE001
        upstream = f"error: {e}"
    return {"status": "ok", "upstream": upstream, "quack_uri": QUACK_URI,
            "pool": _pool.stats}


@app.post("/query")
async def query(request: Request):
    _check_auth(request)
    body, max_rows, fmt, timeout = await _parse_body(request)
    sql = body.get("sql")
    if not sql:
        raise HTTPException(status_code=400, detail="'sql' is required")
    try:
        return _run_sql(sql, max_rows, fmt, timeout)
    except Exception as e:  # noqa: BLE001
        raise _bad_request(e) from e


@app.post("/batch")
async def batch(request: Request):
    """顺序执行多条 SQL (各自独立, 无跨语句事务), 失败即停, 返回逐条结果."""
    _check_auth(request)
    body, max_rows, fmt, timeout = await _parse_body(request)
    sqls = body.get("sqls")
    if not isinstance(sqls, list) or not sqls:
        raise HTTPException(status_code=400, detail="'sqls' (非空数组) is required")
    results = []
    lease = _pool.lease()
    try:
        with lease as conn:
            for sql in sqls:
                result = _exec_one(conn, sql, timeout)
                results.append(_result_payload(result, max_rows, fmt))
    except Exception as e:  # noqa: BLE001
        raise _bad_request(e) from e
    return {"results": results, "executed": len(results)}


@app.post("/write")
async def write(request: Request):
    """写路径: (可选)准备 tmp 目录 → 顺序执行 SQL → (可选)原子落盘 tmp→final.

    body:
        sqls:      [SQL...] 顺序执行, 失败即停
        tmp_dir:   容器内临时目录
        final_dir: 落盘目标目录 (land=true 时必须)
        prepare:   默认 true; false=复用已存在的 tmp (分段执行场景, 见下)
        land:      默认 true; false=只执行 SQL 不落盘 (等待后续 /write-land)

    分段执行协议 (对账需要中间结果, 如 DESCRIBE 列后才能建 checksum SQL):
        1. POST /write {sqls:[COPY, DESCRIBE...], tmp_dir, land:false}
        2. 调用方根据返回结果构建对账 SQL
        3. POST /write {sqls:[对账SQL...], tmp_dir, prepare:false, land:false}
        4. 全部通过 → POST /write-land; 失败 → POST /write-cleanup

    SQL 失败: 清理 tmp, 返回 400 (final_dir 不受影响);
    land=true 全部成功: 返回 {"results": [...], "files": [...], "size_bytes": n}.
    """
    _check_auth(request)
    body, max_rows, fmt, timeout = await _parse_body(request)
    sqls = body.get("sqls")
    tmp_dir, final_dir = body.get("tmp_dir"), body.get("final_dir")
    prepare = bool(body.get("prepare", True))
    land = bool(body.get("land", True))
    if not (isinstance(sqls, list) and sqls and tmp_dir):
        raise HTTPException(
            status_code=400, detail="'sqls'(非空数组) 与 'tmp_dir' are required",
        )
    if land and not final_dir:
        raise HTTPException(status_code=400, detail="land=true 需要 final_dir")
    results = []
    if prepare:
        try:
            _fs_prepare_tmp(tmp_dir)
        except Exception as e:  # noqa: BLE001
            raise _bad_request(e) from e
    lease = _pool.lease()
    try:
        with lease as conn:
            for sql in sqls:
                result = _exec_one(conn, sql, timeout)
                results.append(_result_payload(result, max_rows, fmt))
    except Exception as e:  # noqa: BLE001
        shutil.rmtree(tmp_dir, ignore_errors=True)  # 失败清理, 不触碰 final
        raise _bad_request(e) from e
    if not land:
        return {"results": results, "executed": len(results)}
    try:
        _fs_atomic_landing(tmp_dir, final_dir)
        stats = _fs_dir_stats(final_dir)
    except Exception as e:  # noqa: BLE001
        raise _bad_request(e) from e
    return {"results": results, "executed": len(results), **stats}


@app.post("/write-land")
async def write_land(request: Request):
    """分段写路径收尾: tmp → final 原子落盘, 返回文件清单与大小."""
    _check_auth(request)
    body = await request.json()
    tmp_dir, final_dir = body.get("tmp_dir"), body.get("final_dir")
    if not (tmp_dir and final_dir):
        raise HTTPException(status_code=400, detail="'tmp_dir' 与 'final_dir' are required")
    try:
        _fs_atomic_landing(tmp_dir, final_dir)
        return _fs_dir_stats(final_dir)
    except Exception as e:  # noqa: BLE001
        raise _bad_request(e) from e


@app.post("/write-cleanup")
async def write_cleanup(request: Request):
    """分段写路径失败清理: 删除指定临时目录 (幂等)."""
    _check_auth(request)
    body = await request.json()
    dir_path = body.get("dir")
    if not dir_path:
        raise HTTPException(status_code=400, detail="'dir' is required")
    shutil.rmtree(dir_path, ignore_errors=True)
    return {"cleaned": True}
