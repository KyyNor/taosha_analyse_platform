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
- 类型恢复策略 (Issue #5):
  * 整数列含 NULL → pandas nullable Int64 (无 NULL 保持 int64, 与本地非空行为一致);
    HUGEINT 可能超 int64 → 直接对象列
  * 布尔列含 NULL → pandas nullable boolean (无 NULL 保持 bool)
  * DECIMAL → decimal.Decimal 对象列 (网关以字符串传输完整精度, 不静默降 float)
  * DATE/TIMESTAMP → ISO 字符串对象列 (上层序列化本就要转字符串)
- DDL/DML 返回空 DataFrame (本地路径 DDL 不返回 DataFrame, 调用方不用于读)
- 截断保护 (PR#12 评论#1): 服务端返回 truncated=true 时默认抛 RuntimeError
  禁止静默使用不完整结果（模型匹配/回测超限会导致业务结果缺失）;
  确需容忍截断的调用方显式传 allow_truncated=True;
  max_rows 可由调用方按需指定（服务端会 clamp 到其 MAX_ROWS 配置）
"""

import decimal
from typing import Optional

import pandas as pd
import requests

from utils.config import settings
from utils.logger import logger


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

    def execute_df(self, sql: str, *, max_rows: Optional[int] = None,
                   allow_truncated: bool = False):
        """执行查询并返回 pandas DataFrame（失败抛 RuntimeError, 与本地路径异常向上传播一致）

        Args:
            sql: 查询 SQL
            max_rows: 单条 SQL 行数上限; None=不指定（以服务端 MAX_ROWS 配置为准）,
                服务端会 clamp 到其上限后超出部分截断并标记 truncated
            allow_truncated: 默认 False, 服务端标记 truncated=true 时抛错,
                防止不完整 DataFrame 静默流入模型匹配/回测等业务链路
        """
        cfg = _cfg()
        sql = rewrite_path_in_sql(sql, cfg['path_map'])
        logger.debug(f"[duckdb远程查询] {sql[:500]}")
        payload = {'sql': sql, 'format': 'columns', 'timeout': cfg['timeout']}
        if max_rows is not None:
            payload['max_rows'] = int(max_rows)
        try:
            resp = self._session.post(
                f"{cfg['endpoint']}/query",
                json=payload,
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
        return self._to_dataframe(resp.json(), allow_truncated=allow_truncated)

    @staticmethod
    def _column_series(col: str, values: list, typ: str) -> 'pd.Series':
        """按服务端返回的 DuckDB 类型恢复单列（含 NULL 安全处理，Issue #5）"""
        t = typ.upper()
        has_null = any(v is None for v in values)

        if t.startswith('DECIMAL'):
            # 高精度 Decimal 保留为对象列（网关传字符串原值），不静默降 float
            return pd.Series(
                [None if v is None else decimal.Decimal(str(v)) for v in values],
                dtype=object,
            )
        if t.startswith('BOOLEAN'):
            if has_null:
                return pd.Series(
                    [None if v is None else v for v in values], dtype='boolean',
                )
            return pd.Series(values, dtype='bool')
        if t.startswith('HUGEINT'):
            # HUGEINT 可能超出 int64 表达范围，保持对象列
            return pd.Series(values, dtype=object)
        if t.startswith(('BIGINT', 'INTEGER', 'SMALLINT', 'TINYINT', 'INT')):
            if has_null:
                return pd.Series(
                    [None if v is None else v for v in values], dtype='Int64',
                )
            return pd.Series(values, dtype='int64')
        # DOUBLE/FLOAT: None 由 float64 的 NaN 表达（与本地 fetchdf 行为一致）
        # VARCHAR/DATE/TIMESTAMP/LIST/STRUCT ...: 保持对象
        return pd.Series(values, dtype='float64' if t.startswith(('DOUBLE', 'FLOAT'))
                         else object)

    @classmethod
    def _to_dataframe(cls, payload: dict, allow_truncated: bool = False) -> pd.DataFrame:
        columns = payload.get('columns') or []
        data = payload.get('data') or {}
        if not columns or payload.get('row_count', 0) == 0:
            return pd.DataFrame(columns=columns)
        types = payload.get('types') or [''] * len(columns)
        series = {
            col: cls._column_series(col, data.get(col, []), typ)
            for col, typ in zip(columns, types)
        }
        df = pd.DataFrame(series, columns=columns)
        if payload.get('truncated'):
            if not allow_truncated:
                # 静默返回不完整 DataFrame 会造成业务结果缺失, 默认直接失败
                raise RuntimeError(
                    f"[duckdb远程查询] 结果被服务端截断至 {len(df)} 行, 拒绝返回不完整结果: "
                    f"收窄查询范围, 或调大网关 MAX_ROWS / 指定 max_rows "
                    f"(确需容忍截断时显式传 allow_truncated=True)"
                )
            logger.warning(
                f"[duckdb远程查询] 结果被服务端截断至 {len(df)} 行 (allow_truncated=True)"
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
