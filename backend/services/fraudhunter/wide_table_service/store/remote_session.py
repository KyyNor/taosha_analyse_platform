"""RemoteDuckSession: 经 HTTP 网关 (duckdb 容器) 执行 DuckDB SQL.

背景 (docs/duckdb_remote_compute_plan.md): 部分后端机器 glibc 为 2.17,
无法安装 pip 的 duckdb wheel (要求 glibc >= 2.27)。remote 模式下计算全部
收进 duckdb 容器 (build_scripts/duckdb), 后端只发 HTTP, 本模块是
DuckQuerySession 的同构替身:

    with get_query_session(attach_pg=False) as session:
        df = session.execute_df(sql)      # -> pandas DataFrame

差异与语义:
- SQL 在服务端容器执行; 表引用中的本地路径按 duck_compute.path_map 重写为容器路径
- attach_pg 参数保留但忽略: PG 由服务端容器启动时 ATTACH 为 pg_rt (只读),
  SQL 中 pg_rt.public.* 引用方式与本地模式完全一致
- 响应为列式 JSON (format=columns), 按 types 还原 dtype;
  与本地 fetchdf 的已知差异: DATE/TIMESTAMP 以 ISO 字符串返回 (上层 JSON 序列化本就要转字符串)
- DDL/DML 返回空 DataFrame (本地路径 DDL 不返回 DataFrame, 调用方不用于读)
"""

from typing import Optional

import pandas as pd
import requests

from utils.config import settings
from utils.logger import logger

# 网关单条 SQL 默认行数上限 (服务端 MAX_ROWS, 默认 100000); 超出会被截断
_MAX_ROWS_LIMIT = 100_000_000  # 请求侧不额外设限, 以服务端配置为准


def _cfg():
    return {
        'endpoint': settings.fraudhunter_duck_compute_endpoint,
        'token': settings.fraudhunter_duck_compute_token,
        'path_map': settings.fraudhunter_duck_compute_path_map or {},
        'timeout': settings.fraudhunter_duck_compute_timeout_seconds,
    }


def rewrite_path_in_sql(sql: str, path_map: dict) -> str:
    """按 path_map 把 SQL 中的本地路径前缀重写为容器内路径前缀.

    仅做字面量前缀替换 (read_parquet('...') 引用由 offline_table_ref 生成为绝对路径,
    不含变量); 同机容器挂载相同路径时 path_map 为空, 本函数为空操作。
    """
    for local_prefix, container_prefix in (path_map or {}).items():
        if local_prefix and local_prefix != container_prefix and local_prefix in sql:
            sql = sql.replace(local_prefix, container_prefix)
    return sql


class RemoteDuckSession:
    """DuckDB 远程查询会话（上下文管理器, 与 DuckQuerySession 同构）"""

    def __init__(self, attach_pg: bool = True):
        # attach_pg 仅保持接口兼容: PG 由服务端容器常驻 ATTACH (pg_rt)
        self._attach_pg = attach_pg
        self._session: Optional[requests.Session] = None

    def __enter__(self):
        self._session = requests.Session()
        return self

    def execute_df(self, sql: str):
        """执行查询并返回 pandas DataFrame（失败抛 RuntimeError, 与本地路径异常向上传播一致）"""
        cfg = _cfg()
        sql = rewrite_path_in_sql(sql, cfg['path_map'])
        logger.debug(f"[duckdb远程查询] {sql[:500]}")
        try:
            resp = self._session.post(
                f"{cfg['endpoint']}/query",
                json={'sql': sql, 'format': 'columns',
                      'timeout': cfg['timeout']},
                headers={'Authorization': f"Bearer {cfg['token']}"},
                timeout=cfg['timeout'] + 30,
            )
        except requests.RequestException as e:
            raise RuntimeError(f"[duckdb远程查询] 网关不可达 {cfg['endpoint']}: {e}") from e
        if resp.status_code == 401:
            raise RuntimeError("[duckdb远程查询] 网关鉴权失败: 检查 duck_compute.token")
        if resp.status_code != 200:
            detail = resp.json().get('detail') or resp.text
            if isinstance(detail, dict):
                detail = f"{detail.get('error_type')}: {detail.get('message')}"
            raise RuntimeError(f"[duckdb远程查询] {detail}")
        return self._to_dataframe(resp.json())

    @staticmethod
    def _to_dataframe(payload: dict) -> pd.DataFrame:
        columns = payload.get('columns') or []
        data = payload.get('data') or {}
        if not columns or payload.get('row_count', 0) == 0:
            return pd.DataFrame(columns=columns)
        types = payload.get('types') or [''] * len(columns)
        series = {}
        for col, typ in zip(columns, types):
            values = data.get(col, [])
            t = typ.upper()
            if t.startswith(('BIGINT', 'INTEGER', 'SMALLINT', 'TINYINT', 'HUGEINT', 'INT')):
                series[col] = pd.Series(values, dtype='int64')
            elif t.startswith(('DOUBLE', 'FLOAT', 'DECIMAL')):
                series[col] = pd.Series(values, dtype='float64')
            elif t.startswith('BOOLEAN'):
                series[col] = pd.Series(values, dtype='bool')
            else:  # VARCHAR / DATE / TIMESTAMP / LIST / STRUCT ...: 保持对象
                series[col] = pd.Series(values, dtype=object)
        df = pd.DataFrame(series, columns=columns)
        if payload.get('truncated'):
            logger.warning(
                f"[duckdb远程查询] 结果被服务端截断至 {len(df)} 行 "
                f"(调整网关 MAX_ROWS 或收窄查询)"
            )
        return df

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._session is not None:
            self._session.close()
            self._session = None
        return False


def _post(path: str, payload: dict, cfg: dict, timeout_pad: float = 60) -> dict:
    try:
        resp = requests.post(
            f"{cfg['endpoint']}{path}",
            json=payload,
            headers={'Authorization': f"Bearer {cfg['token']}"},
            timeout=cfg['timeout'] + timeout_pad,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"[duckdb远程] 网关不可达 {cfg['endpoint']}{path}: {e}") from e
    if resp.status_code != 200:
        detail = resp.json().get('detail') or resp.text
        if isinstance(detail, dict):
            detail = f"{detail.get('error_type')}: {detail.get('message')}"
        raise RuntimeError(f"[duckdb远程]{path} {detail}")
    return resp.json()


def _rewrite_payload(payload: dict, path_map: dict) -> dict:
    """对 payload 中的 SQL 字符串与目录路径做 path_map 重写"""
    out = dict(payload)
    if 'sqls' in out:
        out['sqls'] = [rewrite_path_in_sql(s, path_map) for s in out['sqls']]
    for key in ('tmp_dir', 'final_dir', 'dir'):
        if key in out and out[key]:
            out[key] = rewrite_path_in_sql(str(out[key]), path_map)
    return out


def remote_write_sqls(sqls: list, tmp_dir: str, *, prepare: bool = True,
                      land: bool = True, final_dir: str = '') -> dict:
    """网关 /write: (可选)准备 tmp → 顺序执行 SQL → (可选)原子落盘.

    对账需要中间结果时用分段协议:
        remote_write_sqls(copy+describe..., land=False)
        → 构建对账 SQL → remote_write_sqls(对账SQL, prepare=False, land=False)
        → remote_write_land() / remote_write_cleanup()
    """
    cfg = _cfg()
    payload = {'sqls': sqls, 'tmp_dir': tmp_dir, 'prepare': prepare, 'land': land}
    if final_dir:
        payload['final_dir'] = final_dir
    return _post('/write', _rewrite_payload(payload, cfg['path_map']), cfg)


def remote_write_land(tmp_dir: str, final_dir: str) -> dict:
    """网关 /write-land: tmp → final 原子落盘, 返回 {files, size_bytes}"""
    cfg = _cfg()
    return _post(
        '/write-land',
        _rewrite_payload({'tmp_dir': tmp_dir, 'final_dir': final_dir}, cfg['path_map']),
        cfg,
    )


def remote_write_cleanup(dir_path: str) -> dict:
    """网关 /write-cleanup: 删除临时目录 (幂等)"""
    cfg = _cfg()
    return _post(
        '/write-cleanup',
        _rewrite_payload({'dir': dir_path}, cfg['path_map']),
        cfg,
    )
