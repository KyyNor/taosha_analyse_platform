"""
Issue #3 / #4：DuckDB 网关连接池与查询执行生命周期单元测试

覆盖 build_scripts/duckdb/gateway.py：
- POOL_SIZE 同时限制 active connection 上限（信号量），池满有界等待后 503（PoolExhausted）
- active / waiting / idle 指标暴露
- /query 租约生命周期覆盖 SQL 创建 relation + 完整 fetch（结果物化前不归还连接）
- timeout 挂起 interrupt 定时器覆盖 fetch 阶段
"""

import importlib.util
import sys
import threading
import time
import types
from pathlib import Path

_repo_root = Path(__file__).parents[4]


def _load_gateway(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "gateway_for_test", _repo_root / "build_scripts" / "duckdb" / "gateway.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "gateway_for_test", module)
    spec.loader.exec_module(module)
    return module


def _fake_pool(gw, size, wait_timeout):
    """绕过真实 quack 连接的池实例（_new_conn 换成哑连接）"""
    pool = gw._QuackPool(size, wait_timeout)
    pool._new_conn = lambda: types.SimpleNamespace(
        closed=False,
        close=lambda: setattr(pool, '_last_closed', True),
        interrupt=lambda: None,
        sql=lambda s: None,
    )
    return pool


class TestPoolCapsActiveConnections:
    def test_active_capped_at_size(self, monkeypatch):
        """并发租借下 active 不超过 POOL_SIZE（Issue #3 验收）"""
        gw = _load_gateway(monkeypatch)
        pool = _fake_pool(gw, size=3, wait_timeout=5)
        leases = [pool.lease() for _ in range(3)]
        stats = pool.stats
        assert stats['active'] == 3 and stats['idle'] == 0

        for lease in leases:
            lease.__exit__(None, None, None)
        stats = pool.stats
        assert stats['active'] == 0 and stats['idle'] == 3

    def test_exhaustion_times_out_after_bounded_wait(self, monkeypatch):
        """池满 + 超过有界等待 → PoolExhausted（HTTP 层映射 503）"""
        gw = _load_gateway(monkeypatch)
        pool = _fake_pool(gw, size=1, wait_timeout=0.05)
        held = pool.lease()
        t0 = time.monotonic()
        try:
            pool.lease()
            raise AssertionError("应当抛出 PoolExhausted")
        except gw.PoolExhausted as e:
            assert '连接池已满' in str(e)
        assert time.monotonic() - t0 >= 0.04  # 确实等待过
        held.__exit__(None, None, None)

    def test_release_unblocks_waiter(self, monkeypatch):
        """池满时等待者在连接归还后获得租借"""
        gw = _load_gateway(monkeypatch)
        pool = _fake_pool(gw, size=1, wait_timeout=5)
        held = pool.lease()

        acquired = []
        waiter = threading.Thread(
            target=lambda: acquired.append(pool.lease()), daemon=True)
        waiter.start()
        time.sleep(0.05)
        assert pool.stats['waiting'] == 1  # 等待指标暴露
        held.__exit__(None, None, None)
        waiter.join(timeout=2)
        assert acquired and pool.stats['active'] == 1
        acquired[0].__exit__(None, None, None)

    def test_waiting_metric_returns_to_zero(self, monkeypatch):
        gw = _load_gateway(monkeypatch)
        pool = _fake_pool(gw, size=1, wait_timeout=0.01)
        held = pool.lease()
        try:
            pool.lease()
        except gw.PoolExhausted:
            pass
        assert pool.stats['waiting'] == 0
        held.__exit__(None, None, None)

    def test_lease_exception_releases_slot(self, monkeypatch):
        """取 idle 连接失败时信号量必须归还，池不至于永久少一个槽位"""
        gw = _load_gateway(monkeypatch)
        pool = _fake_pool(gw, size=1, wait_timeout=1)
        pool._idle.put(object())  # 非法连接，触发后续 active 统计/使用异常路径
        # 直接触发 get 后处理异常的路径：_new_conn 抛错
        pool._idle = types.SimpleNamespace(get_nowait=lambda: (_ for _ in ()).throw(
            gw.queue.Empty())) if hasattr(gw, 'queue') else pool._idle
        pool._new_conn = lambda: (_ for _ in ()).throw(RuntimeError("conn failed"))
        try:
            pool.lease()
            raise AssertionError("应当抛错")
        except RuntimeError:
            pass
        # 槽位已归还：可再次租借（换正常连接工厂）
        pool._new_conn = lambda: types.SimpleNamespace(close=lambda: None, interrupt=lambda: None)
        lease = pool.lease()
        lease.__exit__(None, None, None)


class TestQueryLeaseLifecycle:
    """Issue #4：连接在结果完全物化前不归还池"""

    def _install_fake_pool(self, gw, monkeypatch):
        pool = _fake_pool(gw, size=1, wait_timeout=1)
        monkeypatch.setattr(gw, '_pool', pool)
        return pool

    def test_fetch_completes_before_connection_returned(self, monkeypatch):
        gw = _load_gateway(monkeypatch)
        pool = self._install_fake_pool(gw, monkeypatch)
        events = []

        class _LazyRelation:
            columns = ['v']
            types = ['INTEGER']

            def fetchall(self):
                events.append('fetch_start')
                time.sleep(0.1)
                events.append('fetch_done')
                return [(1,)]

        def fake_sql(pushdown_sql):
            events.append('sql')
            return _LazyRelation()

        original_conn = pool._new_conn

        def conn_with_sql():
            conn = original_conn()
            conn.sql = fake_sql
            return conn

        pool._new_conn = conn_with_sql

        # 记录归还时机：包装 _return
        original_return = pool._return

        def traced_return(conn):
            events.append('return')
            original_return(conn)

        pool._return = traced_return

        payload = gw._run_sql('SELECT 1', 10, 'rows', 0)
        assert payload['rows'] == [[1]]
        # 顺序保证：fetch 完成发生在连接归还之前
        assert events == ['sql', 'fetch_start', 'fetch_done', 'return']

    def test_timeout_timer_covers_fetch_phase(self, monkeypatch):
        """慢 fetch 被 timeout 定时器 interrupt 中断（覆盖真实执行阶段）"""
        gw = _load_gateway(monkeypatch)
        pool = self._install_fake_pool(gw, monkeypatch)
        interrupts = []

        class _SlowRelation:
            columns = ['v']
            types = ['INTEGER']

            def fetchall(self):
                time.sleep(0.3)
                return [(1,)]

        original_conn = pool._new_conn

        def conn_with_instrumentation():
            conn = original_conn()
            conn.interrupt = lambda: interrupts.append(time.monotonic())
            conn.sql = lambda s: _SlowRelation()
            return conn

        pool._new_conn = conn_with_instrumentation

        t0 = time.monotonic()
        gw._run_sql('SELECT slow', 10, 'rows', timeout=0.1)
        elapsed = time.monotonic() - t0
        # fetch 结束后 timer 已取消 → 未真正 interrupt，但总耗时不因 fetch 超过过多
        # （fetch 0.3s > timeout 0.1s 时 timer 触发过 interrupt）
        assert interrupts, "timeout 定时器应覆盖 fetch 阶段并触发 interrupt"
        assert elapsed >= 0.25

    def test_retry_on_io_exception_releases_connection(self, monkeypatch):
        """连接异常（IOException）时连接被关闭丢弃，且换新连接重试一次"""
        gw = _load_gateway(monkeypatch)
        pool = self._install_fake_pool(gw, monkeypatch)
        closed = []
        original_conn = pool._new_conn

        calls = {'n': 0}

        def flaky_conn():
            conn = original_conn()
            conn.close = lambda: closed.append(calls['n'])

            def sql(_s):
                calls['n'] += 1
                if calls['n'] == 1:
                    raise gw.duckdb.IOException('connection reset')
                class _R:
                    columns = ['v']
                    types = ['INTEGER']
                    fetchall = lambda self: [(42,)]
                return _R()
            conn.sql = sql
            return conn

        pool._new_conn = flaky_conn
        payload = gw._run_sql('SELECT 42', 10, 'rows', 0)
        assert payload['rows'] == [[42]]
        assert closed == [1]  # 第一条失效连接被关闭


class TestJsonifyDecimal:
    def test_decimal_serialized_as_string(self, monkeypatch):
        """网关 DECIMAL 以字符串传输完整精度（配合 RemoteDuckSession，Issue #5）"""
        import decimal
        gw = _load_gateway(monkeypatch)
        assert gw._jsonify(decimal.Decimal('0.1')) == '0.1'
        assert gw._jsonify(decimal.Decimal('12345678901234567890.1234567890')) == \
            '12345678901234567890.1234567890'
        assert gw._jsonify(None) is None
        assert gw._jsonify(True) is True
