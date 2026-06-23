"""实时指标宽表定时生成任务"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
import time
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from models.db_base import get_db_session
from models.fraudhunter.indicator import FraudHunterIndicatorTask, FraudHunterIndicatorDefinition
from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot, FraudHunterWideTableVersion
from models.fraudhunter.risk_control_model import FraudHunterModelDefinition, FraudHunterModelHistory
from models.fraudhunter.model_execution_tracking import FraudHunterModelExecution
from services.fraudhunter.model_service.model_hit_alert_manager import ModelHitAlertManager, ModelHit
from services.fraudhunter.system_config_service import SystemConfigManager
from services.fraudhunter.model_service.model_executor import build_model_whitelist_dict
from services.fraudhunter.wide_table_service.numeric_type_utils import WideTableNumericTypeHelper
from utils.logger import logger
from utils.config import settings
from utils.analyze_db_utils import AnalyzeDBConnector, AnalyzeDBPartitionManager
from utils.common_decorator import timing_it

def _get_latest_offline_table_name(
    db: Session,
    wide_table_name: str
) -> Optional[str]:
    """获取最新的离线宽表快照

    Args:
        db: 数据库会话
        wide_table_name: 宽表名称

    Returns:
        最新的快照记录，如果不存在返回None
    """
    # 获取最新日期的快照
    snapshot = db.query(FraudHunterWideTableSnapshot).filter(
        and_(
            FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
            FraudHunterWideTableSnapshot.status == 'ready'
        )
    ).order_by(
        desc(FraudHunterWideTableSnapshot.etl_date),
        desc(FraudHunterWideTableSnapshot.generation_time)
    ).first()

    if not snapshot:
        logger.warning(f"未找到 {wide_table_name} 的任何ready状态快照")
        return None

    latest_table_name = f"{snapshot.wide_table_name}_{snapshot.version_hash}_{snapshot.etl_date.strftime('%Y%m%d')}"

    return latest_table_name


def _compute_half_hour_slot(full_ts: str) -> str:
    """将精确到分钟的时间戳归整到上一个半小时间隔。

    例如: "202604220944" -> "202604220930"
          "202604220955" -> "202604220930"
          "202604220015" -> "202604220000"（跨小时进位）

    Args:
        full_ts: 格式为 YYYYMMDDHHMM 的时间戳字符串

    Returns:
        半小时间隔的字符串，格式同样为 YYYYMMDDHHMM
    """
    base_dt = datetime.strptime(full_ts[:8] + full_ts[8:12], '%Y%m%d%H%M')
    floored_minute = (base_dt.minute // 30) * 30
    floored = base_dt.replace(minute=floored_minute, second=0, microsecond=0)
    return floored.strftime('%Y%m%d%H%M')


def _update_realtime_snapshot(
    db: Session,
    wide_table_name: str,
    etl_date: date,
    pg_table_name: str,
    row_count: int,
    column_count: int
):
    snapshot = db.query(FraudHunterWideTableSnapshot).filter(
        and_(
            FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
            FraudHunterWideTableSnapshot.etl_date == etl_date,
            FraudHunterWideTableSnapshot.version_hash.is_(None)
        )
    ).first()

    if snapshot:
        snapshot.parquet_file_path = pg_table_name
        snapshot.row_count = row_count
        snapshot.column_count = column_count
        snapshot.status = 'ready'
        snapshot.generation_time = datetime.now()
        snapshot.error_message = None
    else:
        snapshot = FraudHunterWideTableSnapshot(
            wide_table_name=wide_table_name,
            etl_date=etl_date,
            version_hash=None,
            parquet_file_path=pg_table_name,
            row_count=row_count,
            column_count=column_count,
            status='ready',
            generation_time=datetime.now()
        )
        db.add(snapshot)

    db.flush()
    logger.debug(f"更新实时宽表快照: {wide_table_name}, etl_date={etl_date}, rows={row_count}")


def _execute_single_task(
    task: "FraudHunterIndicatorTask",
    user_variable_config: dict,
    today_str: str,
    offline_table: str,
    cust_offline_table: Optional[str],
    object_type: str,
) -> Tuple["FraudHunterIndicatorTask", Optional[pd.DataFrame]]:
    """执行单个实时指标任务（供线程池调用）"""
    sql = task.realtime_logic_content
    for k, v in user_variable_config.items():
        sql = sql.replace("${" + k + "}", v)
    sql = sql.replace("${date}", today_str)

    if object_type == 'dep_acct_no':
        sql = sql.replace('offline_dep_acct_no_table', offline_table)
        if cust_offline_table:
            sql = sql.replace('offline_cust_no_table', cust_offline_table)
    elif object_type == 'cust_no':
        sql = sql.replace('offline_cust_no_table', offline_table)
    elif object_type == 'loan_acct_no':
        sql = sql.replace('offline_loan_acct_no_table', offline_table)

    try:
        result_df = AnalyzeDBConnector.execute_sql(sql, fetch_df=True)
        if result_df is not None and not result_df.empty:
            result_df = result_df.drop(columns=['etl_date'], errors='ignore')
            return (task, result_df)
    except Exception as e:
        logger.error(f"执行指标任务 {task.task_code} 失败: {e}")
    return (task, None)


@timing_it
def step1_generate_realtime_indicators(db, today, today_str, now_str):
    logger.debug("=" * 60)
    logger.debug("步骤1: 实时指标加工")
    logger.debug("=" * 60)

    # 计算半小时间隔的分区字符串，所有该时段内的任务执行共用同一张表
    half_hour_slot = _compute_half_hour_slot(now_str)
    logger.debug(f"本次执行归整到半小时间隔: {now_str} -> {half_hour_slot}")

    # 查询所有在线的实时指标任务
    realtime_tasks = db.query(FraudHunterIndicatorTask).join(
        FraudHunterIndicatorDefinition,
        FraudHunterIndicatorDefinition.indicator_task_id == FraudHunterIndicatorTask.id
    ).filter(
        and_(
            FraudHunterIndicatorDefinition.status == 'online',
            FraudHunterIndicatorDefinition.indicator_type == 'realtime'
        )
    ).all()

    if not realtime_tasks:
        logger.info("没有在线的实时指标任务，跳过生成")
        return None, None
    logger.debug(f"找到 {len(realtime_tasks)} 个在线的实时指标任务")

    # 按 object_type 分组任务
    tasks_by_object_type: Dict[str, List[FraudHunterIndicatorTask]] = {}
    for task in realtime_tasks:
        # 从关联的指标定义中获取 object_type
        for indicator in task.indicators:
            if indicator.indicator_type == 'realtime' and indicator.status == 'online':
                object_type = indicator.object_type
                if object_type not in tasks_by_object_type:
                    tasks_by_object_type[object_type] = []
                tasks_by_object_type[object_type].append(task)
                break

    if not tasks_by_object_type:
        logger.info("没有有效的实时指标任务分组，跳过生成")
        return None, None

    logger.debug(f"按 object_type 分组: {list(tasks_by_object_type.keys())}")

    # object_type 到宽表名称的映射
    object_type_to_wide_table = {
        'dep_acct_no': 'dep_acct_wide_table',
        'cust_no': 'cust_wide_table',
        'loan_acct_no': 'loan_acct_wide_table'
    }
    offline_dep_acct_table_name = _get_latest_offline_table_name(db, object_type_to_wide_table['dep_acct_no'])
    offline_cust_table_name = _get_latest_offline_table_name(db, object_type_to_wide_table['cust_no'])

    # 获取所有离线宽表
    offline_tables = {
        'dep_acct_no': offline_dep_acct_table_name,
        'cust_no': offline_cust_table_name,
    }

    # 处理每个 object_type 的实时指标
    user_variable_config = _build_all_user_variable_config(db)
    generated_realtime_tables: Dict[str, str] = {}

    for object_type, tasks in tasks_by_object_type.items():
        logger.debug(f"\n处理 object_type: {object_type}, 任务数: {len(tasks)}")

        wide_table_name = object_type_to_wide_table.get(object_type)
        if not wide_table_name:
            logger.warning(f"未定义 object_type '{object_type}' 的宽表映射，跳过")
            continue

        # 获取对应的离线宽表
        offline_table = offline_tables.get(object_type)
        if not offline_table:
            logger.warning(f"没有找到 {wide_table_name} 的当前版本，跳过")
            continue

        # 获取当前版本信息
        current_version = db.query(FraudHunterWideTableVersion).filter(
            and_(
                FraudHunterWideTableVersion.wide_table_name == wide_table_name,
                FraudHunterWideTableVersion.status.in_(['current', 'target'])
            )
        ).order_by(desc(FraudHunterWideTableVersion.created_at)).first()

        if not current_version:
            logger.warning(f"没有找到 {wide_table_name} 的current版本，跳过")
            continue

        realtime_table_name = f"{wide_table_name}_realtime_{current_version.version_hash[:8]}"
        

        # 创建实时表（如果不存在）
        table_exists_sql = """
            SELECT EXISTS (
                SELECT 1 FROM pg_tables
                WHERE schemaname = 'public' AND tablename = :table_name
            )
        """
        table_exists = AnalyzeDBConnector.execute_sql(
            table_exists_sql, params={"table_name": realtime_table_name}, fetch_df=True
        )

        if table_exists is not None and not table_exists.iloc[0]['exists']:
            AnalyzeDBPartitionManager.create_wide_table(
                realtime_table_name, current_version.indicator_metadata, partition_col='run_time'
            )
            logger.info(f"创建实时宽表: {realtime_table_name}")

        # 确保分区存在（使用半小时间隔作为分区标识）
        AnalyzeDBPartitionManager.ensure_partition(realtime_table_name, today, partition_str=half_hour_slot)

        # 执行该 object_type 的所有实时指标任务
        all_indicator_results = []

        logger.info(f"[{object_type}] 实时指标任务开始（并发）...")
        t_loop = time.perf_counter()

        # 并发执行所有任务，按完成顺序收集结果
        cust_offline_table = offline_tables.get('cust_no')
        with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
            futures = {
                pool.submit(
                    _execute_single_task, task, user_variable_config,
                    today_str, offline_table, cust_offline_table, object_type
                ): task
                for task in tasks
            }
            for future in as_completed(futures):
                task, result_df = future.result()
                if result_df is not None:
                    all_indicator_results.append(result_df)
                    logger.info(f" {task.task_name} -> 返回 {len(result_df)} 行，{len(result_df.columns)} 列")

        t_loop_elapsed = time.perf_counter() - t_loop
        logger.info(f"[{object_type}] 所有SQL执行完成，共 {len(tasks)} 个任务，耗时: {t_loop_elapsed:.2f}s")

        if not all_indicator_results:
            logger.warning(f"object_type '{object_type}' 没有成功执行的实时指标任务")
            continue

        # 合并所有指标结果
        t_merge = time.perf_counter()
        logger.info(f"[{object_type}] 合并所有指标结果开始...")
        final_result = all_indicator_results[0]
        for i in range(1, len(all_indicator_results)):
            final_result = final_result.merge(
                all_indicator_results[i], on='target_id', how='outer', suffixes=('', f'_dup_{i}')
            )
        final_result['etl_date'] = today
        final_result['run_time'] = half_hour_slot
        final_result, numeric_conversion_stats = (
            WideTableNumericTypeHelper.convert_numeric_dataframe_columns(
                final_result,
                current_version.indicator_metadata or {},
            )
        )
        for stats in numeric_conversion_stats:
            if stats.blank_count or stats.invalid_count:
                logger.debug(
                    f"[{object_type}] 实时数值指标转换: "
                    f"indicator_code={stats.indicator_code}, "
                    f"blank_count={stats.blank_count}, invalid_count={stats.invalid_count}"
                )
        merge_sec = time.perf_counter() - t_merge
        logger.info(f"[{object_type}] 合并完成: {merge_sec:.2f}s")

        # 写入实时表（使用 COPY 命令优化性能）
        t_copy = time.perf_counter()
        partition_table_name = f"{realtime_table_name}_{half_hour_slot}"
        AnalyzeDBConnector.truncate_table(partition_table_name)
        rows_inserted = AnalyzeDBConnector.batch_insert_copy(
            realtime_table_name, final_result
        )
        copy_sec = time.perf_counter() - t_copy
        logger.info(f"[{object_type}] COPY完成: {copy_sec:.2f}s")

        row_count = len(final_result)
        column_count = len(final_result.columns)
        logger.info(f"[{object_type}] 写入实时指标宽表完成: {realtime_table_name}, 行数: {row_count}, 列数: {column_count}")
        logger.info(f"=== {object_type} 三阶段汇总 => SQL:{t_loop_elapsed:.2f}s + 合并:{merge_sec:.2f}s + COPY:{copy_sec:.2f}s ===")

        realtime_table_name_with_partition = f'{realtime_table_name}_{half_hour_slot}'
        generated_realtime_tables[object_type] = realtime_table_name_with_partition

        # 更新快照
        _update_realtime_snapshot(
            db, f'{wide_table_name}_realtime', today, realtime_table_name_with_partition, row_count, column_count
        )

    db.commit()

    # 如果没有生成任何实时表，直接返回
    if not generated_realtime_tables:
        logger.warning("没有成功生成任何实时宽表")
        return None, None
    return offline_tables, generated_realtime_tables


@timing_it
def step2_online_model_executor(db, offline_tables, generated_realtime_tables):
    logger.debug("=" * 60)
    logger.debug("步骤2: 已上线模型执行")
    logger.debug("=" * 60)

    online_models = db.query(FraudHunterModelDefinition).filter(
        FraudHunterModelDefinition.status == 'online',
        FraudHunterModelDefinition.model_type == 'normal'
    ).all()

    if not online_models:
        logger.warning("没有在线的模型，跳过模型执行")
        return None, None
    logger.debug(f"找到 {len(online_models)} 个在线模型")

    # 模型只执行一次，需要关联的表：离线账户、离线客户、实时账户、实时客户
    dep_acct_realtime_table = generated_realtime_tables.get('dep_acct_no')
    cust_realtime_table = generated_realtime_tables.get('cust_no')
    dep_acct_offline_table = offline_tables.get('dep_acct_no')
    cust_offline_table = offline_tables.get('cust_no')

    # 至少需要有存款账户的实时表和离线表才能执行模型
    if not dep_acct_realtime_table or not dep_acct_offline_table:
        logger.warning("缺少存款账户的实时表或离线表，无法执行模型匹配")
        return None, None

    online_models_info = [
        {'id': m.id, 'name': m.model_name, 'code': m.model_code, 'version': m.current_version}
        for m in online_models
    ]

    execution_start_time = datetime.now()
    execution_record = FraudHunterModelExecution(
        realtime_dep_acct_wide_table_path=dep_acct_realtime_table,
        offline_dep_acct_wide_table_path=dep_acct_offline_table,
        offline_cust_wide_table_path=cust_offline_table,
        online_models_info=online_models_info,
        generated_sql='',
        execution_start_time=execution_start_time,
        status='running'
    )
    db.add(execution_record)
    db.flush()
    execution_id = execution_record.id
    logger.debug(f"创建执行记录: execution_id={execution_id}")

    # 构建模型匹配SQL（4表关联：离线账户、离线客户、实时账户、实时客户）
    model_sql = _build_model_matching_sql(
        db, online_models, dep_acct_realtime_table, cust_realtime_table,
        dep_acct_offline_table, cust_offline_table
    )
    execution_record.generated_sql = model_sql
    db.flush()
    logger.debug("模型匹配SQL已生成")

    try:
        matched_df = AnalyzeDBConnector.execute_sql(model_sql, fetch_df=True)
        if matched_df is None or matched_df.empty:
            matched_df = pd.DataFrame()
        logger.info(f"实时模型匹配完成, 命中 {len(matched_df)} 条记录")
    except Exception as e:
        logger.error(f"执行模型匹配SQL失败: {e}", exc_info=True)
        execution_record.execution_end_time = datetime.now()
        execution_record.status = 'failed'
        execution_record.error_message = str(e)
        db.commit()
        return None, None

    if len(matched_df) == 0:
        logger.info("没有命中任何模型的记录")
        execution_record.execution_end_time = datetime.now()
        execution_record.status = 'success'
        db.commit()
        return None, None
    
    return matched_df, execution_record


@timing_it
def step3_hit_record(db, today, matched_df, execution_record, hit_time):
    logger.debug("=" * 60)
    logger.debug("步骤3: 记录模型运行结果")
    logger.debug("=" * 60)

    execution_id = execution_record.id

    manager = ModelHitAlertManager(db)
    
    whitelist_acct = SystemConfigManager(db).get_config_value('whitelist_acct', default=[])
    whitelist_set = set(whitelist_acct) if whitelist_acct else set()
    if whitelist_set:
        logger.debug(f"加载白名单账户 {len(whitelist_set)} 个")

    # 获取模型级别的白名单账户列表
    model_whitelist_acct_raw = SystemConfigManager(db).get_config_value('model_whitelist_acct', default=[])
    model_whitelist_acct = build_model_whitelist_dict(model_whitelist_acct_raw)
    if model_whitelist_acct:
        logger.info(f"加载模型白名单配置，模型数={len(model_whitelist_acct)}")

    all_hit_accounts = set()
    new_hit_accounts = set()
    whitelist_hit_accounts = set()

    from models.fraudhunter.model_execution_tracking import FraudHunterModelAlertControlRecord

    for _, row in matched_df.iterrows():
        account_id = str(row.get('目标ID', ''))
        branch_no = str(row.get('branch_no', '')) if pd.notna(row.get('branch_no')) else None
        offline_cust_type = str(row.get('客户类型', ''))

        cust_type_map = {'个人': '01', '对公': '02'}
        cust_type = cust_type_map.get(offline_cust_type, '03')

        hit_model_list = row.get('model_hit_array', [])
        if not hit_model_list:
            continue

        hit_models = []
        for model_id in hit_model_list:
            model = db.query(FraudHunterModelDefinition).filter(
                FraudHunterModelDefinition.id == model_id
            ).first()
            if model:
                hit_models.append(ModelHit(model_id=model.id, model_name=model.model_name))

        if not hit_models:
            continue

        # 检查模型白名单（如果账号在任何一个命中模型的白名单中，则跳过该记录）
        is_model_whitelist = False
        for hit_model in hit_models:
            model_whitelist = model_whitelist_acct.get(hit_model.model_id, [])
            if model_whitelist and account_id in model_whitelist:
                logger.debug(
                    f"跳过模型白名单账户: 账号={account_id}, "
                    f"模型={hit_model.model_name}"
                )
                is_model_whitelist = True
                break

        if is_model_whitelist:
            continue

        all_hit_accounts.add(account_id)
        is_whitelist = account_id in whitelist_set
        if is_whitelist:
            whitelist_hit_accounts.add(account_id)

        existing_record = db.query(FraudHunterModelAlertControlRecord).filter(
            and_(
                FraudHunterModelAlertControlRecord.account_id == account_id,
                FraudHunterModelAlertControlRecord.record_date == today
            )
        ).first()
        if not existing_record:
            new_hit_accounts.add(account_id)

        indicator_data = {
            k: (None if pd.isna(v) else (v.item() if hasattr(v, 'item') else v))
            for k, v in row.items() if k != 'model_hit_array'
        }

        hit_record = manager.create_hit_record(
            account_id=account_id,
            branch_no=branch_no,
            hit_models=hit_models,
            indicator_data=indicator_data,
            hit_time=hit_time,
            execution_id=execution_id
        )

        alert_control_record = manager.hit_record_processor(
            hit_record, is_whitelist=is_whitelist, cust_type=cust_type
        )
        whitelist_tag = "[白名单]" if is_whitelist else ""
        if alert_control_record.alert_status != "duplicate" or alert_control_record.control_status != "duplicate":
            logger.info(
                f"账户 {account_id} {whitelist_tag}命中 {len(hit_models)} 个模型: "
                f"{[m.model_name for m in hit_models]}"
            )

    execution_record.execution_end_time = datetime.now()
    execution_record.total_hit_accounts = len(all_hit_accounts)
    execution_record.new_hit_accounts = len(new_hit_accounts)
    execution_record.status = 'success'
    db.flush()

    logger.debug(
        f"执行记录已更新: execution_id={execution_id}, "
        f"命中账户数={len(all_hit_accounts)}, 新命中账户数={len(new_hit_accounts)}, "
        f"白名单命中账户数={len(whitelist_hit_accounts)}"
    )
    db.commit()

async def generate_realtime_wide_table_job():
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    now_str = datetime.now().strftime('%Y%m%d%H%M')

    
    try:
        hit_time = datetime.now()
        logger.debug(f"开始生成实时指标宽表并执行模型匹配 hit_time: {hit_time}")

        with get_db_session() as db:
            offline_tables, generated_realtime_tables = step1_generate_realtime_indicators(db, today, today_str, now_str)
            if offline_tables is None:
                return

        with get_db_session() as db:
            matched_df, execution_record = step2_online_model_executor(db, offline_tables, generated_realtime_tables)

            if matched_df is None:
                return

            step3_hit_record(db, today, matched_df, execution_record, hit_time)

            logger.debug("实时指标宽表生成及模型匹配完成")

    except Exception as e:
            logger.error(f"生成实时指标宽表失败: {e}", exc_info=True)
            if 'execution_record' in locals() and execution_record:
                execution_record.execution_end_time = datetime.now()
                execution_record.status = 'failed'
                execution_record.error_message = str(e)
                db.commit()
            db.rollback()
            raise


def _build_model_matching_sql(
    db: Session,
    models: List[FraudHunterModelDefinition],
    dep_acct_realtime_table: str,
    cust_realtime_table: Optional[str],
    dep_acct_offline_table: str,
    cust_offline_table: Optional[str]
) -> str:
    """
    构建实时模型匹配SQL（4表关联）

    关联的表：
    - 离线账户表 (dep_acct_offline_indicator)
    - 离线客户表 (cust_offline_indicator)
    - 实时账户表 (dep_acct_realtime_indicator)
    - 实时客户表 (cust_realtime_indicator)

    Args:
        db: 数据库会话
        models: 在线模型列表
        dep_acct_realtime_table: 实时账户表名
        cust_realtime_table: 实时客户表名（可选）
        dep_acct_offline_table: 离线账户表名
        cust_offline_table: 离线客户表名（可选）

    Returns:
        完整的模型匹配SQL
    """
    from services.fraudhunter.model_service.rule_engine import RuleEngine
    from schemas.fraudhunter.rule import RuleConfig

    # 构建CASE WHEN子句（模型匹配逻辑）
    case_when_clauses = []
    for model in models:
        model_history = db.query(FraudHunterModelHistory).filter(
            and_(
                FraudHunterModelHistory.model_id == model.id,
                FraudHunterModelHistory.version == model.current_version
            )
        ).first()

        if model_history and model_history.rule_config:
            rule_config_dict = model_history.rule_config
            logger.debug(f"模型 {model.model_code} 使用版本历史表的规则配置 (version={model.current_version})")
        else:
            rule_config_dict = model.rule_config
            logger.warning(
                f"模型 {model.model_code} 的版本历史记录不存在 (version={model.current_version}), "
                "降级使用模型表的规则配置"
            )

        rule_config = RuleConfig(**rule_config_dict)
        rule_engine = RuleEngine(db=db)
        # 构建指标别名映射（每个指标根据自身的类型和对象类型映射）
        indicator_alias_mapping = rule_engine.build_indicator_alias_mapping(
            rule_config, use_alias=True
        )
        where_condition = rule_engine.generate_sql_expression(
            rule_config,
            indicator_alias_mapping,
            numeric_columns_are_typed=True
        )
        case_when_clauses.append(f"CASE WHEN ({where_condition}) THEN {model.id} ELSE NULL END")

    array_expr = f"ARRAY(SELECT x FROM UNNEST(ARRAY[{', '.join(case_when_clauses)}]) x WHERE x IS NOT NULL)"

    # 查询所有在线的指标定义，构建动态 SELECT 字段
    online_indicators = db.query(FraudHunterIndicatorDefinition).filter(
        and_(
            FraudHunterIndicatorDefinition.status == 'online',
            FraudHunterIndicatorDefinition.object_type.in_(['dep_acct_no', 'cust_no'])
        )
    ).all()

    # 基础字段
    select_fields = [
        f"COALESCE(dep_acct_realtime_indicator.target_id, dep_acct_offline_indicator.target_id) AS \"目标ID\"",
        "dep_acct_offline_indicator.i_dep_acct_no_offline_00007 AS \"客户类型\"",
        "COALESCE(dep_acct_realtime_indicator.i_dep_acct_no_offline_00002, dep_acct_offline_indicator.i_dep_acct_no_offline_00002) AS branch_no",
        # 【新增】理财经理通知需要的客户号
        "COALESCE(dep_acct_realtime_indicator.i_dep_acct_no_offline_00001, dep_acct_offline_indicator.i_dep_acct_no_offline_00001) AS \"i_dep_acct_no_offline_00001\"",
        "dep_acct_realtime_indicator.etl_date AS \"[实时]ETL日期\"",
    ]

    # 添加指标字段
    for indicator in online_indicators:
        indicator_name = indicator.indicator_name or indicator.indicator_code
        object_type = indicator.object_type
        indicator_code = indicator.indicator_code

        # 确定表别名
        if indicator.indicator_type == 'realtime':
            # 实时指标：从实时表获取，带 [实时] 前缀
            if object_type == 'dep_acct_no' and dep_acct_realtime_table:
                table_alias = 'dep_acct_realtime_indicator'
                alias_name = f"[实时]{indicator_name}"
                select_fields.append(f"{table_alias}.{indicator_code} AS \"{alias_name}\"")
            elif object_type == 'cust_no' and cust_realtime_table:
                table_alias = 'cust_realtime_indicator'
                alias_name = f"[实时]{indicator_name}"
                select_fields.append(f"{table_alias}.{indicator_code} AS \"{alias_name}\"")
        else:
            # 离线指标：从离线表获取
            if object_type == 'dep_acct_no':
                table_alias = 'dep_acct_offline_indicator'
                select_fields.append(f"{table_alias}.{indicator_code} AS \"{indicator_name}\"")
            elif object_type == 'cust_no' and cust_offline_table:
                table_alias = 'cust_offline_indicator'
                select_fields.append(f"{table_alias}.{indicator_code} AS \"{indicator_name}\"")

    # 添加模型匹配数组
    select_fields.append(f"{array_expr} AS model_hit_array")

    # 构建JOIN子句（从离线账户表出发）
    join_clauses = [
        f"FROM {dep_acct_realtime_table} AS dep_acct_realtime_indicator",
        f"LEFT JOIN {dep_acct_offline_table} AS dep_acct_offline_indicator",
        f"  ON dep_acct_realtime_indicator.target_id = dep_acct_offline_indicator.target_id"
    ]

    # 如果有实时客户表，添加关联
    if cust_realtime_table:
        join_clauses.append(
            f"LEFT JOIN {cust_realtime_table} AS cust_realtime_indicator"
            f"  ON cust_realtime_indicator.target_id = dep_acct_offline_indicator.i_dep_acct_no_offline_00001"
        )

    # 如果有离线客户表，添加关联
    if cust_offline_table:
        join_clauses.append(
            f"LEFT JOIN {cust_offline_table} AS cust_offline_indicator"
            f"  ON cust_offline_indicator.target_id = dep_acct_offline_indicator.i_dep_acct_no_offline_00001"
        )

    select_clause = ",\n    ".join(select_fields)
    where_clause = "WHERE array_length(model_hit_array, 1) > 0"

    return f"""-- 实时模型匹配SQL
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 模型数量: {len(models)}
-- 指标数量: {len(online_indicators)}
-- 关联表: 离线账户、离线客户、实时账户、实时客户
with temp as (
SELECT
    {select_clause}
{chr(10).join(join_clauses)}
)
select * from temp
{where_clause}
"""


def _build_all_user_variable_config(db: Session) -> dict:
    manager = SystemConfigManager(db)
    return manager.build_sql_variable_dict()
