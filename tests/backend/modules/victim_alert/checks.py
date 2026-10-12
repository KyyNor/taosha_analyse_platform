"""
受害人预警检查（子进程运行，避免改写 sys.modules 污染 pytest 进程）

替身：utils.config / utils.logger / models.db_base（SQLite 内存库）、requests.post；
被测：真实 ORM 模型、victim_alert_service、victim_alert_send_job。
输出：每项检查一行 JSON {"name", "ok", "detail"}。
"""

import importlib.util
import json
import sys
import traceback
import types
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[4] / 'backend'
sys.path.insert(0, str(BACKEND))


def _install_stubs():
    from loguru import logger
    from sqlalchemy import BigInteger, create_engine
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.orm import declarative_base, sessionmaker

    @compiles(BigInteger, 'sqlite')
    def _bigint_sqlite(type_, compiler, **kw):  # SQLite 仅 INTEGER PRIMARY KEY 自增
        return 'INTEGER'

    settings = types.SimpleNamespace(
        fraudhunter_victim_alert_enabled=True,
        fraudhunter_victim_alert_model_name_keyword='受害人',
        fraudhunter_victim_alert_trigger_api_url='http://ds/trigger',
        fraudhunter_victim_alert_send_api_url='http://downstream/send',
        fraudhunter_victim_alert_timeout_seconds=3,
    )
    config_mod = types.ModuleType('utils.config')
    config_mod.settings = settings
    logger_mod = types.ModuleType('utils.logger')
    logger_mod.logger = logger
    logger.remove()

    engine = create_engine('sqlite://')
    Session = sessionmaker(bind=engine)
    db_mod = types.ModuleType('models.db_base')
    db_mod.Base = declarative_base()
    db_mod.engine = engine
    db_mod.SessionLocal = Session

    @contextmanager
    def get_db_session():
        db = Session()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    db_mod.get_db_session = get_db_session
    models_pkg = types.ModuleType('models')  # 跳过 models/__init__（会导入全部模型与真实 db_base）
    models_pkg.__path__ = [str(BACKEND / 'models')]
    import utils  # noqa: F401  真实包（__init__ 为空）
    sys.modules.update({'utils.config': config_mod, 'utils.logger': logger_mod,
                        'models': models_pkg, 'models.db_base': db_mod})

    for name in ('services', 'services.fraudhunter', 'services.fraudhunter.model_service',
                 'services.scheduler', 'services.scheduler.jobs'):
        sys.modules[name] = types.ModuleType(name)
    return settings, db_mod


def _load(dotted, rel):
    spec = importlib.util.spec_from_file_location(dotted, BACKEND / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = module
    spec.loader.exec_module(module)
    return module


SETTINGS, DB = _install_stubs()
import models.fraudhunter  # noqa: E402,F401  注册全部真实模型
from models.fraudhunter.model_execution_tracking import (  # noqa: E402
    FraudHunterModelAlertControlRecord as Control,
    FraudHunterModelExecution,
    FraudHunterModelHitRecord,
)
from models.fraudhunter.victim_alert_record import FraudHunterVictimAlertRecord as Victim  # noqa: E402
from domain.victim_alert import compute_alert_id  # noqa: E402

svc = _load('services.fraudhunter.model_service.victim_alert_service',
            'services/fraudhunter/model_service/victim_alert_service.py')
job = _load('services.scheduler.jobs.victim_alert_send_job', 'services/scheduler/jobs/victim_alert_send_job.py')

TODAY = date(2026, 10, 11)
ALERT_TIME = datetime(2026, 10, 11, 9, 30, 15, 123456)


class FakeResponse:
    def __init__(self, status=200, body=None, text=None):
        self.status_code = status
        self.ok = 200 <= status < 300
        self._body = body
        self.text = text if text is not None else json.dumps(body, ensure_ascii=False)

    def json(self):
        if self._body is None:
            raise ValueError('no json')
        return self._body

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f'HTTP {self.status_code}')


class FakeHttp:
    def __init__(self):
        self.calls = []
        self.responses = {}  # url -> FakeResponse | Exception

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, json, timeout))
        resp = self.responses.get(url, FakeResponse(200, {'code': '00000'}))
        if isinstance(resp, Exception):
            raise resp
        return resp


def _reset():
    DB.Base.metadata.drop_all(DB.engine)
    DB.Base.metadata.create_all(DB.engine)
    http = FakeHttp()
    svc.requests.post = http.post
    SETTINGS.fraudhunter_victim_alert_enabled = True
    return DB.SessionLocal(), http


def _execution(db):
    ex = FraudHunterModelExecution(
        realtime_dep_acct_wide_table_path='rt', offline_dep_acct_wide_table_path='off',
        online_models_info=[], generated_sql='select 1', execution_start_time=datetime.now(),
    )
    db.add(ex)
    db.flush()
    return ex.id


def _control(db, execution_id, account, names, ids=None, alert='sent', control='not_configured',
             record_date=TODAY, alert_time=ALERT_TIME):
    ids = ids or list(range(1, len(names) + 1))
    hit = FraudHunterModelHitRecord(execution_id=execution_id, account_id=account, hit_time=alert_time,
                                    hit_model_ids=ids, hit_model_names=names, indicator_data={})
    db.add(hit)
    db.flush()
    rec = Control(execution_id=execution_id, hit_record_id=hit.id, account_id=account, record_date=record_date,
                  hit_model_ids=ids, hit_model_names=names, alert_status=alert, control_status=control,
                  alert_time=alert_time)
    db.add(rec)
    db.flush()
    return rec


CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


@check
def filters_by_keyword_alert_and_control():
    db, http = _reset()
    ex = _execution(db)
    _control(db, ex, 'A1', ['受害人模型A', '普通模型'])                     # 命中
    _control(db, ex, 'A2', ['普通模型'])                                    # 名称不含关键字
    _control(db, ex, 'A3', ['受害人模型A'], alert='duplicate')              # 告警未发送
    _control(db, ex, 'A4', ['受害人模型A'], control='executed')             # 已管控
    _control(db, ex, 'A5', ['疑似受害人'], control='duplicate')             # 管控重复 != executed → 命中
    db.commit()
    svc.process_victim_alerts(db, ex, TODAY)
    accounts = sorted(v.account_id for v in db.query(Victim).all())
    assert accounts == ['A1', 'A5'], accounts
    return accounts


@check
def record_fields_and_alert_id():
    db, http = _reset()
    ex = _execution(db)
    _control(db, ex, 'A1', ['受害人模型A', '普通模型'], ids=[7, 9])
    db.commit()
    svc.process_victim_alerts(db, ex, TODAY)
    v = db.query(Victim).one()
    expected_id = compute_alert_id('A1', [7, 9], ALERT_TIME.replace(microsecond=0))
    assert v.alert_id == expected_id and len(v.alert_id) == 32
    import hashlib
    assert v.alert_id == hashlib.md5('A17,92026-10-11 09:30:15'.encode()).hexdigest()
    assert v.hit_model_ids == [7, 9] and v.hit_model_names == ['受害人模型A', '普通模型']
    assert v.hit_time == ALERT_TIME.replace(microsecond=0) and v.record_date == TODAY
    assert v.status == 'new' and v.message is None
    return v.alert_id


@check
def same_account_same_day_inserted_once():
    db, http = _reset()
    ex1 = _execution(db)
    _control(db, ex1, 'A1', ['受害人模型A'])
    db.commit()
    svc.process_victim_alerts(db, ex1, TODAY)
    ex2 = _execution(db)
    _control(db, ex2, 'A1', ['受害人模型B'], alert_time=datetime(2026, 10, 11, 11, 0, 0))
    db.commit()
    svc.process_victim_alerts(db, ex2, TODAY)
    assert db.query(Victim).count() == 1
    assert len([c for c in http.calls if c[0] == 'http://ds/trigger']) == 1
    return 'ok'


@check
def other_day_record_does_not_block():
    db, http = _reset()
    db.add(Victim(alert_id='x' * 32, account_id='A1', hit_model_ids=[1], hit_model_names=['受害人'],
                  hit_time=datetime(2026, 10, 10, 9), record_date=date(2026, 10, 10), status='sent'))
    ex = _execution(db)
    _control(db, ex, 'A1', ['受害人模型A'])
    db.commit()
    svc.process_victim_alerts(db, ex, TODAY)
    assert db.query(Victim).filter(Victim.record_date == TODAY).count() == 1
    return 'ok'


@check
def only_current_execution_considered():
    db, http = _reset()
    old = _execution(db)
    _control(db, old, 'OLD', ['受害人模型A'])
    ex = _execution(db)
    _control(db, ex, 'NEW', ['受害人模型A'])
    db.commit()
    svc.process_victim_alerts(db, ex, TODAY)
    assert [v.account_id for v in db.query(Victim).all()] == ['NEW']
    return 'ok'


@check
def trigger_called_with_alert_id_after_commit():
    db, http = _reset()
    ex = _execution(db)
    _control(db, ex, 'A1', ['受害人模型A'])
    db.commit()

    seen_committed = []

    def post(url, json=None, timeout=None):
        other = DB.SessionLocal()  # 独立会话：DS 任务读库时记录必须已提交
        seen_committed.append(other.query(Victim).filter(Victim.alert_id == json['alert_id']).count())
        other.close()
        return FakeResponse(200, {})

    svc.requests.post = post
    svc.process_victim_alerts(db, ex, TODAY)
    v = db.query(Victim).one()
    assert seen_committed == [1], seen_committed
    assert v.status == 'new'
    return 'ok'


@check
def trigger_failure_marks_error():
    db, http = _reset()
    ex = _execution(db)
    _control(db, ex, 'A1', ['受害人模型A'])
    _control(db, ex, 'A2', ['受害人模型B'])
    db.commit()
    calls = []

    def post(url, json=None, timeout=None):
        calls.append(json['alert_id'])
        if len(calls) == 1:
            raise ConnectionError('ds down')
        return FakeResponse(200, {})

    svc.requests.post = post
    svc.process_victim_alerts(db, ex, TODAY)
    fresh = DB.SessionLocal()
    statuses = {v.account_id: (v.status, v.message) for v in fresh.query(Victim).all()}
    assert statuses['A1'][0] == 'error' and 'ds down' in statuses['A1'][1], statuses
    assert statuses['A2'] == ('new', None), statuses
    return statuses


@check
def disabled_does_nothing():
    db, http = _reset()
    SETTINGS.fraudhunter_victim_alert_enabled = False
    ex = _execution(db)
    _control(db, ex, 'A1', ['受害人模型A'])
    db.commit()
    svc.process_victim_alerts(db, ex, TODAY)
    assert db.query(Victim).count() == 0 and http.calls == []
    return 'ok'


@check
def collect_failure_is_swallowed():
    db, http = _reset()
    ex = _execution(db)
    db.commit()
    original = svc.collect_victim_alerts
    svc.collect_victim_alerts = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('boom'))
    try:
        svc.process_victim_alerts(db, ex, TODAY)  # 不抛异常
    finally:
        svc.collect_victim_alerts = original
    return 'ok'


def _seed_victim(db, status='new'):
    v = Victim(alert_id='a' * 32, account_id='A1', hit_model_ids=[7], hit_model_names=['受害人模型A'],
               hit_time=datetime(2026, 10, 11, 9, 30, 15), record_date=TODAY, status=status)
    db.add(v)
    db.commit()
    return v.alert_id


@check
def job_send_success():
    db, http = _reset()
    alert_id = _seed_victim(db)
    code = job.main(['--alert-id', alert_id])
    url, payload, timeout = http.calls[0]
    assert code == 0 and url == 'http://downstream/send' and timeout == 3
    assert payload == {
        'alert_id': alert_id, 'account_id': 'A1', 'hit_model_ids': [7], 'hit_model_names': ['受害人模型A'],
        'hit_time': '2026-10-11 09:30:15', 'record_date': '2026-10-11', 'status': 'new', 'message': None,
    }, payload
    v = DB.SessionLocal().query(Victim).one()
    assert v.status == 'sent' and v.message is None
    return payload


@check
def job_send_business_failure():
    db, http = _reset()
    alert_id = _seed_victim(db)
    http.responses['http://downstream/send'] = FakeResponse(200, {'code': '50001', 'message': '账号不存在'})
    assert job.main(['--alert-id', alert_id]) == 1
    v = DB.SessionLocal().query(Victim).one()
    assert v.status == 'error' and '50001' in v.message, v.message
    return v.message


@check
def job_send_http_failure_and_exception():
    db, http = _reset()
    alert_id = _seed_victim(db)
    http.responses['http://downstream/send'] = FakeResponse(502, None, text='bad gateway')
    assert job.main(['--alert-id', alert_id]) == 1
    v = DB.SessionLocal().query(Victim).one()
    assert v.status == 'error' and 'HTTP 502' in v.message
    http.responses['http://downstream/send'] = TimeoutError('read timeout')
    assert job.main(['--alert-id', alert_id]) == 1
    v = DB.SessionLocal().query(Victim).one()
    assert v.status == 'error' and 'read timeout' in v.message
    return v.message


@check
def job_retry_after_error_then_success():
    db, http = _reset()
    alert_id = _seed_victim(db, status='error')
    assert job.main(['--alert-id', alert_id]) == 0
    v = DB.SessionLocal().query(Victim).one()
    assert v.status == 'sent' and v.message is None
    return 'ok'


@check
def job_skips_already_sent():
    db, http = _reset()
    alert_id = _seed_victim(db, status='sent')
    assert job.main(['--alert-id', alert_id]) == 0 and http.calls == []
    return 'ok'


@check
def job_unknown_alert_id():
    db, http = _reset()
    assert job.main(['--alert-id', 'nope']) == 2 and http.calls == []
    return 'ok'


@check
def job_missing_send_url_marks_error():
    db, http = _reset()
    alert_id = _seed_victim(db)
    SETTINGS.fraudhunter_victim_alert_send_api_url = ''
    try:
        assert job.main(['--alert-id', alert_id]) == 1
    finally:
        SETTINGS.fraudhunter_victim_alert_send_api_url = 'http://downstream/send'
    v = DB.SessionLocal().query(Victim).one()
    assert v.status == 'error' and 'send_api_url' in v.message
    return v.message


def main():
    for fn in CHECKS:
        try:
            detail = fn()
            print(json.dumps({'name': fn.__name__, 'ok': True, 'detail': detail}, ensure_ascii=False, default=str))
        except Exception:
            print(json.dumps({'name': fn.__name__, 'ok': False, 'detail': traceback.format_exc()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
