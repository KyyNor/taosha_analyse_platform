"""实时指标宽表定时生成任务"""

from datetime import date, datetime
from typing import List, Dict, Any, Optional

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
from utils.logger import logger
from utils.config import settings
from utils.analyze_db_utils import AnalyzeDBConnector, AnalyzeDBPartitionManager


def _get_current_version_table_name(db: Session, wide_table_name: str) -> Optional[str]:
    version = db.query(FraudHunterWideTableVersion).filter(
        and_(
            FraudHunterWideTableVersion.wide_table_name == wide_table_name,
            FraudHunterWideTableVersion.status == 'current'
        )
    ).first()
    if not version:
        return None
    return f"{wide_table_name}_{version.version_hash[:8]}"


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


async def generate_realtime_wide_table_job():
    logger.debug("开始生成实时指标宽表并执行模型匹配")

    with get_db_session() as db:
        try:
            today = date.today()
            today_str = today.strftime('%Y-%m-%d')

            logger.debug("=" * 60)
            logger.debug("步骤1: 实时指标加工")
            logger.debug("=" * 60)

            realtime_tasks = db.query(FraudHunterIndicatorTask).join(
                FraudHunterIndicatorDefinition,
                FraudHunterIndicatorDefinition.indicator_task_id == FraudHunterIndicatorTask.id
            ).filter(
                and_(
                    FraudHunterIndicatorDefinition.status == 'online',
                    FraudHunterIndicatorDefinition.object_type == 'dep_acct_no',
                    FraudHunterIndicatorDefinition.indicator_type == 'realtime'
                )
            ).all()

            if not realtime_tasks:
                logger.info("没有在线的 dep_acct_no 实时指标任务，跳过生成")
                return
            logger.debug(f"找到 {len(realtime_tasks)} 个在线的 dep_acct_no 实时指标任务")

            offline_dep_acct_table = _get_current_version_table_name(db, 'dep_acct_wide_table')
            offline_cust_table = _get_current_version_table_name(db, 'cust_wide_table')

            if not offline_dep_acct_table:
                logger.warning("没有找到 dep_acct_wide_table 的当前版本")
                return
            logger.debug(f"离线存款账户宽表: {offline_dep_acct_table}")
            if offline_cust_table:
                logger.debug(f"离线客户宽表: {offline_cust_table}")

            current_version = db.query(FraudHunterWideTableVersion).filter(
                and_(
                    FraudHunterWideTableVersion.wide_table_name == 'dep_acct_wide_table',
                    FraudHunterWideTableVersion.status == 'current'
                )
            ).first()

            if not current_version:
                logger.warning("没有找到 dep_acct_wide_table 的current版本")
                return

            realtime_table_name = f"dep_acct_wide_table_realtime_{current_version.version_hash[:8]}"

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
                    realtime_table_name, current_version.indicator_metadata, is_realtime=True
                )
                logger.info(f"创建实时宽表: {realtime_table_name}")

            AnalyzeDBPartitionManager.ensure_partition(realtime_table_name, today)

            all_indicator_results = []
            user_variable_config = _build_all_user_variable_config(db)

            for task in realtime_tasks:
                sql = task.realtime_logic_content
                for k, v in user_variable_config.items():
                    sql = sql.replace("${" + k + "}", v)
                sql = sql.replace("${date}", today_str)
                sql = sql.replace('realtime_oss_inct_new', 'realtime_oss_inct_new')
                sql = sql.replace('offline_dep_acct_no_table', offline_dep_acct_table)
                if offline_cust_table:
                    sql = sql.replace('offline_cust_no_table', offline_cust_table)

                logger.debug(f"执行指标任务 {task.task_code} 的实时SQL")
                try:
                    result_df = AnalyzeDBConnector.execute_sql(sql, fetch_df=True)
                    if result_df is not None and not result_df.empty:
                        all_indicator_results.append(result_df)
                        logger.debug(f"  -> 返回 {len(result_df)} 行，{len(result_df.columns)} 列")
                except Exception as e:
                    logger.error(f"执行指标任务 {task.task_code} 失败: {e}")
                    continue

            if not all_indicator_results:
                logger.warning("没有成功执行的实时指标任务")
                return

            logger.debug("合并所有指标结果...")
            final_result = all_indicator_results[0]
            for i in range(1, len(all_indicator_results)):
                final_result = final_result.merge(
                    all_indicator_results[i], on='target_id', how='outer', suffixes=('', f'_dup_{i}')
                )
            final_result['etl_date'] = today

            batch_size = settings.fraudhunter_realtime_writer_batch_insert_size
            AnalyzeDBConnector.batch_insert(
                realtime_table_name, final_result, chunksize=batch_size, if_exists='append'
            )

            row_count = len(final_result)
            column_count = len(final_result.columns)
            logger.debug(f"实时宽表已写入PG: {realtime_table_name}, 行数: {row_count}, 列数: {column_count}")

            _update_realtime_snapshot(
                db, 'dep_acct_wide_table_realtime', today, realtime_table_name, row_count, column_count
            )
            db.commit()

            logger.debug("=" * 60)
            logger.debug("步骤2: 已上线模型执行")
            logger.debug("=" * 60)

            online_models = db.query(FraudHunterModelDefinition).filter(
                FraudHunterModelDefinition.status == 'online'
            ).all()

            if not online_models:
                logger.warning("没有在线的模型，跳过模型执行")
                return
            logger.debug(f"找到 {len(online_models)} 个在线模型")

            online_models_info = [
                {'id': m.id, 'name': m.model_name, 'code': m.model_code, 'version': m.current_version}
                for m in online_models
            ]

            execution_start_time = datetime.now()
            execution_record = FraudHunterModelExecution(
                realtime_dep_acct_wide_table_path=realtime_table_name,
                offline_dep_acct_wide_table_path=offline_dep_acct_table,
                offline_cust_wide_table_path=offline_cust_table,
                online_models_info=online_models_info,
                generated_sql='',
                execution_start_time=execution_start_time,
                status='running'
            )
            db.add(execution_record)
            db.flush()
            execution_id = execution_record.id
            logger.debug(f"创建执行记录: execution_id={execution_id}")

            model_sql = _build_model_matching_sql(db, online_models, realtime_table_name, offline_dep_acct_table, offline_cust_table)
            execution_record.generated_sql = model_sql
            db.flush()
            logger.debug("模型匹配SQL已生成")

            try:
                matched_df = AnalyzeDBConnector.execute_sql(model_sql, fetch_df=True) or pd.DataFrame()
                logger.info(f"实时模型匹配完成，命中 {len(matched_df)} 条记录")
            except Exception as e:
                logger.error(f"执行模型匹配SQL失败: {e}", exc_info=True)
                return

            if len(matched_df) == 0:
                logger.debug("没有命中任何模型的记录")
                return

            logger.debug("=" * 60)
            logger.debug("步骤3: 记录模型运行结果")
            logger.debug("=" * 60)

            manager = ModelHitAlertManager(db)
            hit_time = datetime.now()
            whitelist_acct = SystemConfigManager(db).get_config_value('whitelist_acct', default=[])
            whitelist_set = set(whitelist_acct) if whitelist_acct else set()
            if whitelist_set:
                logger.debug(f"加载白名单账户 {len(whitelist_set)} 个")

            all_hit_accounts = set()
            new_hit_accounts = set()
            whitelist_hit_accounts = set()

            from models.fraudhunter.model_execution_tracking import FraudHunterModelAlertControlRecord

            for _, row in matched_df.iterrows():
                account_id = str(row.get('realtime_target_id', ''))
                offline_cust_type = str(row.get('offline_cust_type', ''))

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
                    hit_models=hit_models,
                    indicator_data=indicator_data,
                    hit_time=hit_time,
                    execution_id=execution_id
                )

                alert_control_record = manager.hit_record_processor(hit_record, is_whitelist=is_whitelist, cust_type=cust_type)
                whitelist_tag = "[白名单]" if is_whitelist else ""
                if alert_control_record.alert_status != "duplicate" or alert_control_record.control_status != "duplicate":
                    logger.info(f"账户 {account_id} {whitelist_tag}命中 {len(hit_models)} 个模型: {[m.model_name for m in hit_models]}")

            execution_record.execution_end_time = datetime.now()
            execution_record.total_hit_accounts = len(all_hit_accounts)
            execution_record.new_hit_accounts = len(new_hit_accounts)
            execution_record.status = 'success'
            db.flush()

            logger.debug(f"执行记录已更新: execution_id={execution_id}, 命中账户数={len(all_hit_accounts)}, 新命中账户数={len(new_hit_accounts)}, 白名单命中账户数={len(whitelist_hit_accounts)}")
            db.commit()
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
    realtime_table_name: str,
    dep_acct_offline_table: str,
    cust_offline_table: Optional[str]
) -> str:
    from services.fraudhunter.model_service.rule_engine import RuleEngine
    from schemas.fraudhunter.rule import RuleConfig

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
            logger.warning(f"模型 {model.model_code} 的版本历史记录不存在 (version={model.current_version}), 降级使用模型表的规则配置")

        rule_config = RuleConfig(**rule_config_dict)
        rule_engine = RuleEngine(db=db)
        indicator_alias_mapping = rule_engine.build_indicator_alias_mapping(rule_config, use_alias=True)
        where_condition = rule_engine.generate_sql_expression(rule_config, indicator_alias_mapping)
        case_when_clauses.append(f"CASE WHEN ({where_condition}) THEN {model.id} ELSE NULL END")

    array_expr = f"ARRAY(SELECT x FROM UNNEST(ARRAY[{', '.join(case_when_clauses)}]) x WHERE x IS NOT NULL)"

    select_fields = [
        "COALESCE(dep_acct_realtime_indicator.target_id, dep_acct_offline_indicator.target_id) AS realtime_target_id",
        "dep_acct_offline_indicator.i_dep_acct_no_offline_00007 AS offline_cust_type",
        "dep_acct_realtime_indicator.etl_date AS realtime_etl_date",
        "dep_acct_realtime_indicator.*",
        "dep_acct_offline_indicator.*",
        f"{array_expr} AS model_hit_array"
    ]

    join_clauses = [
        f"FROM {dep_acct_offline_table} AS dep_acct_offline_indicator",
        f"LEFT JOIN {realtime_table_name} AS dep_acct_realtime_indicator ON dep_acct_realtime_indicator.target_id = dep_acct_offline_indicator.target_id"
    ]

    if cust_offline_table:
        join_clauses.append(f"LEFT JOIN {cust_offline_table} AS cust_offline_indicator ON dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_offline_indicator.target_id")
        select_fields.append("cust_offline_indicator.*")

    select_clause = ",\n    ".join(select_fields)
    where_clause = "WHERE array_length(model_hit_array, 1) > 0"

    return f"""-- 实时模型匹配SQL
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 模型数量: {len(models)}

SELECT
    {select_clause}
{chr(10).join(join_clauses)}
{where_clause}
"""


def _build_all_user_variable_config(db: Session) -> dict:
    manager = SystemConfigManager(db)
    return manager.build_sql_variable_dict()
