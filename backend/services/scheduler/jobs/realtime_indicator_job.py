"""
实时指标宽表定时生成任务
从原 realtime_scheduler.py 迁移而来
"""

from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Any, Optional
import json
import duckdb
import pandas as pd

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from models.db_base import get_db_session
from models.fraudhunter.indicator import FraudHunterIndicatorTask
from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot, FraudHunterWideTableVersion
from models.fraudhunter.risk_control_model import FraudHunterModelDefinition
from models.fraudhunter.model_execution_tracking import FraudHunterModelExecution, FraudHunterModelUserVariableConfig
from services.fraudhunter.model_service.model_hit_alert_manager import ModelHitAlertManager, ModelHit
from utils.logger import logger
from utils.config import settings


def _get_latest_offline_snapshot(
    db: Session,
    wide_table_name: str
) -> Optional[FraudHunterWideTableSnapshot]:
    """获取最新的离线宽表快照

    Args:
        db: 数据库会话
        wide_table_name: 宽表名称

    Returns:
        最新的快照记录，如果不存在返回None
    """
    # 获取current版本
    current_version = db.query(FraudHunterWideTableVersion).filter(
        and_(
            FraudHunterWideTableVersion.wide_table_name == wide_table_name,
            FraudHunterWideTableVersion.status == 'current'
        )
    ).first()

    if not current_version:
        logger.warning(f"未找到 {wide_table_name} 的current版本")
        return None

    # 获取该版本最新日期的快照
    snapshot = db.query(FraudHunterWideTableSnapshot).filter(
        and_(
            FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
            FraudHunterWideTableSnapshot.version_hash == current_version.version_hash,
            FraudHunterWideTableSnapshot.status == 'ready'
        )
    ).order_by(desc(FraudHunterWideTableSnapshot.etl_date)).first()

    if not snapshot:
        logger.warning(f"未找到 {wide_table_name} 的任何ready状态快照")
        return None

    return snapshot


def _update_realtime_snapshot(
    db: Session,
    wide_table_name: str,
    etl_date: date,
    parquet_path: str,
    row_count: int,
    column_count: int,
    file_size: int
):
    """更新实时宽表快照记录

    Args:
        db: 数据库会话
        wide_table_name: 宽表名称
        etl_date: ETL日期
        parquet_path: Parquet文件路径
        row_count: 行数
        column_count: 列数
        file_size: 文件大小
    """
    # 查找是否已存在当天的快照
    snapshot = db.query(FraudHunterWideTableSnapshot).filter(
        and_(
            FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
            FraudHunterWideTableSnapshot.etl_date == etl_date,
            FraudHunterWideTableSnapshot.version_hash.is_(None)  # 实时宽表version_hash为NULL
        )
    ).first()

    if snapshot:
        # 更新已有记录
        snapshot.parquet_file_path = parquet_path
        snapshot.row_count = row_count
        snapshot.column_count = column_count
        snapshot.file_size_bytes = file_size
        snapshot.status = 'ready'
        snapshot.generation_time = datetime.now()
        snapshot.error_message = None
    else:
        # 创建新记录
        snapshot = FraudHunterWideTableSnapshot(
            wide_table_name=wide_table_name,
            etl_date=etl_date,
            version_hash=None,  # 实时宽表没有版本号
            parquet_file_path=parquet_path,
            row_count=row_count,
            column_count=column_count,
            file_size_bytes=file_size,
            status='ready',
            generation_time=datetime.now()
        )
        db.add(snapshot)

    db.flush()
    logger.info(f"更新实时宽表快照: {wide_table_name}, etl_date={etl_date}, rows={row_count}")


async def generate_realtime_wide_table_job():
    """
    生成实时指标宽表并执行模型匹配

    流程:
    1. 实时指标加工：
       - 只读模式连接 realtime_consumer.py 中的 DuckDB
       - 获取所有状态为上线的 dep_acct_no 的指标任务的实时指标 SQL
       - 替换 SQL 中的离线表名为 read_parquet(最新离线宽表路径)
       - 合并所有指标结果生成实时宽表
       - 更新 snapshot 中的实时宽表记录

    2. 已上线模型执行：
       - 汇总所有状态为上线的模型
       - 组装查询语句（实时宽表 LEFT JOIN 离线宽表）
       - 使用 array + case when 生成命中模型列表
       - 执行查询获取命中结果

    3. 记录模型运行结果：
       - 调用 create_hit_record 生成命中记录
       - 调用 hit_record_processor 处置命中记录
       - 对需要告警或管控的账户进行处理
    """
    logger.info("开始生成实时指标宽表并执行模型匹配")

    with get_db_session() as db:
        duckdb_conn = None
        try:
            # ========== 步骤1: 实时指标加工 ==========
            logger.info("=" * 60)
            logger.info("步骤1: 实时指标加工")
            logger.info("=" * 60)

            # 1.1 只读模式连接 DuckDB
            duckdb_path = Path(settings.fraudhunter_realtime_data_storage_path) / "realtime_data.duckdb"
            if not duckdb_path.exists():
                logger.warning(f"DuckDB文件不存在: {duckdb_path}")
                return

            logger.info(f"连接DuckDB: {duckdb_path} (只读模式)")
            duckdb_conn = duckdb.connect(str(duckdb_path), read_only=True)

            today = date.today()
            today_str = today.strftime('%Y-%m-%d')

            # 1.2 获取所有状态为上线的 dep_acct_no 的指标任务
            realtime_tasks = db.query(FraudHunterIndicatorTask).filter(
                and_(
                    FraudHunterIndicatorTask.status == 'online',
                    FraudHunterIndicatorTask.object_type == 'dep_acct_no',
                    FraudHunterIndicatorTask.realtime_logic_content.isnot(None)
                )
            ).all()

            if not realtime_tasks:
                logger.info("没有在线的 dep_acct_no 实时指标任务，跳过生成")
                return

            logger.info(f"找到 {len(realtime_tasks)} 个在线的 dep_acct_no 实时指标任务")

            # 1.3 获取最新的离线宽表路径
            offline_dep_acct_snapshot = _get_latest_offline_snapshot(db, 'dep_acct_wide_table')
            offline_cust_snapshot = _get_latest_offline_snapshot(db, 'cust_wide_table')

            if not offline_dep_acct_snapshot:
                logger.warning("没有找到最新的 dep_acct_wide_table 离线快照")
                return

            dep_acct_parquet_path = offline_dep_acct_snapshot.parquet_file_path
            cust_parquet_path = offline_cust_snapshot.parquet_file_path if offline_cust_snapshot else None

            logger.info(f"离线存款账户宽表路径: {dep_acct_parquet_path}")
            if cust_parquet_path:
                logger.info(f"离线客户宽表路径: {cust_parquet_path}")

            # 1.4 执行所有实时指标 SQL 并合并结果
            all_indicator_results = []
            user_variable_config = _build_all_user_variable_config()

            for task in realtime_tasks:
                sql = task.realtime_logic_content

                # 替换表名为 read_parquet
                for k,v in user_variable_config.items():
                    sql = sql.replace("${"+k+"}", v)

                sql = sql.replace("${date}", today_str)
                sql = sql.replace('offline_dep_acct_no_table', f"read_parquet('{dep_acct_parquet_path}')")
                if cust_parquet_path:
                    sql = sql.replace('offline_cust_no_table', f"read_parquet('{cust_parquet_path}')")

                logger.info(f"执行指标任务 {task.task_code} 的实时SQL")
                logger.debug(f"SQL: {sql[:200]}...")

                try:
                    result_df = duckdb_conn.execute(sql).df()
                    all_indicator_results.append(result_df)
                    logger.info(f"  -> 返回 {len(result_df)} 行，{len(result_df.columns)} 列")
                except Exception as e:
                    logger.error(f"执行指标任务 {task.task_code} 失败: {e}")
                    continue

            if not all_indicator_results:
                logger.warning("没有成功执行的实时指标任务")
                return

            # 1.5 合并所有指标结果（基于 target_id）
            logger.info("合并所有指标结果...")
            final_result = all_indicator_results[0]
            for i in range(1, len(all_indicator_results)):
                final_result = final_result.merge(
                    all_indicator_results[i],
                    on='target_id',
                    how='outer',
                    suffixes=('', f'_dup_{i}')
                )

            # 1.6 保存实时宽表文件
            output_dir = Path(settings.fraudhunter_wide_table_storage_path) / "dep_acct_wide_table_realtime"
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / f"dep_acct_realtime_{datetime.now().strftime("%Y%m%d_%H%M%S")}.parquet"

            final_result.to_parquet(output_file)
            row_count = len(final_result)
            column_count = len(final_result.columns)
            file_size = output_file.stat().st_size

            logger.info(f"实时宽表已生成: {output_file}")
            logger.info(f"  行数: {row_count}, 列数: {column_count}, 大小: {file_size} bytes")

            # 1.7 更新 snapshot 中的实时宽表记录
            _update_realtime_snapshot(
                db,
                'dep_acct_wide_table_realtime',
                today,
                str(output_file),
                row_count,
                column_count,
                file_size
            )

            db.commit()
            realtime_wide_table_path = str(output_file)

            # ========== 步骤2: 已上线模型执行 ==========
            logger.info("=" * 60)
            logger.info("步骤2: 已上线模型执行")
            logger.info("=" * 60)

            # 2.1 关闭只读连接，创建内存DuckDB连接用于模型执行
            duckdb_conn.close()

            duckdb_conn = duckdb.connect(":memory:")

            # 2.2 汇总所有状态为上线的模型
            online_models = db.query(FraudHunterModelDefinition).filter(
                FraudHunterModelDefinition.status == 'online'
            ).all()

            if not online_models:
                logger.info("没有在线的模型，跳过模型执行")
                return

            logger.info(f"找到 {len(online_models)} 个在线模型")

            # 2.2.1 创建执行记录
            online_models_info = [
                {
                    'id': model.id,
                    'name': model.model_name,
                    'code': model.model_code,
                    'version': model.current_version
                }
                for model in online_models
            ]

            execution_start_time = datetime.now()
            execution_record = FraudHunterModelExecution(
                realtime_dep_acct_wide_table_path=realtime_wide_table_path,
                offline_dep_acct_wide_table_path=dep_acct_parquet_path,
                offline_cust_wide_table_path=cust_parquet_path,
                online_models_info=online_models_info,
                generated_sql='',  # 稍后更新
                execution_start_time=execution_start_time,
                status='running'
            )
            db.add(execution_record)
            db.flush()  # 获取execution_id

            execution_id = execution_record.id
            logger.info(f"创建执行记录: execution_id={execution_id}")

            # 2.3 组装查询语句
            model_sql = _build_model_matching_sql(
                online_models,
                realtime_wide_table_path,
                dep_acct_parquet_path,
                cust_parquet_path
            )

            # 更新执行记录的SQL
            execution_record.generated_sql = model_sql
            db.flush()

            logger.info("模型匹配SQL已生成")
            logger.debug(f"SQL: {model_sql[:500]}...")

            # 2.4 执行模型匹配查询
            try:
                matched_df = duckdb_conn.execute(model_sql).df()
                logger.info(f"模型匹配完成，命中 {len(matched_df)} 条记录")
            except Exception as e:
                logger.error(f"执行模型匹配SQL失败: {e}", exc_info=True)
                return

            if len(matched_df) == 0:
                logger.info("没有命中任何模型的记录")
                return

            # ========== 步骤3: 记录模型运行结果 ==========
            logger.info("=" * 60)
            logger.info("步骤3: 记录模型运行结果")
            logger.info("=" * 60)

            # 3.1 处理每条命中记录
            manager = ModelHitAlertManager(db)
            hit_time = datetime.now()

            # 用于统计的集合
            all_hit_accounts = set()  # 所有命中账户
            new_hit_accounts = set()  # 新命中账户（当日第一次）

            for _, row in matched_df.iterrows():
                account_id = str(row.get('账号', ''))
                hit_model_list = row.get('命中模型情况', [])

                if not hit_model_list or len(hit_model_list) == 0:
                    continue

                # 提取模型信息
                hit_models = []
                for model_name in hit_model_list:
                    # 查找模型
                    model = db.query(FraudHunterModelDefinition).filter(
                        FraudHunterModelDefinition.model_name == model_name
                    ).first()

                    if model:
                        hit_models.append(ModelHit(
                            model_id=model.id,
                            model_name=model.model_name
                        ))

                if not hit_models:
                    continue

                # 记录命中账户
                all_hit_accounts.add(account_id)

                # 检查是否为当日第一次命中
                from models.fraudhunter.model_execution_tracking import FraudHunterModelAlertControlRecord
                existing_record = db.query(FraudHunterModelAlertControlRecord).filter(
                    and_(
                        FraudHunterModelAlertControlRecord.account_id == account_id,
                        FraudHunterModelAlertControlRecord.record_date == today
                    )
                ).first()

                if not existing_record:
                    new_hit_accounts.add(account_id)

                # 构建指标数据（排除命中模型情况列）
                indicator_data = {
                    k: (v.item() if hasattr(v, 'item') else v)
                    for k, v in row.items()
                    if k != '命中模型情况'
                }

                # 3.2 创建命中记录
                hit_record = manager.create_hit_record(
                    account_id=account_id,
                    hit_models=hit_models,
                    indicator_data=indicator_data,
                    hit_time=hit_time,
                    execution_id=execution_id  # 传递execution_id
                )

                # 3.3 处理命中记录（生成告警管控记录）
                alert_control_records = manager.hit_record_processor(hit_record)

                # 3.4 对需要告警的记录发送告警
                alert_records = [r for r in alert_control_records if r.alert_status == 'sent']
                if alert_records:
                    manager.send_alert_message(alert_records)

                # 3.5 对需要管控的记录执行管控
                control_records = [r for r in alert_control_records if r.control_status == 'executed']
                if control_records:
                    manager.process_alert_control(control_records)

                logger.info(
                    f"账户 {account_id} 命中 {len(hit_models)} 个模型: "
                    f"{[m.model_name for m in hit_models]}"
                )

            # 3.6 更新执行记录的统计信息
            execution_record.execution_end_time = datetime.now()
            execution_record.total_hit_accounts = len(all_hit_accounts)
            execution_record.new_hit_accounts = len(new_hit_accounts)
            execution_record.status = 'success'
            db.flush()

            logger.info(
                f"执行记录已更新: execution_id={execution_id}, "
                f"命中账户数={len(all_hit_accounts)}, "
                f"新命中账户数={len(new_hit_accounts)}"
            )

            db.commit()
            logger.info("实时指标宽表生成及模型匹配完成")

        except Exception as e:
            logger.error(f"生成实时指标宽表失败: {e}", exc_info=True)

            # 如果执行记录已创建，更新为失败状态
            if 'execution_record' in locals() and execution_record:
                execution_record.execution_end_time = datetime.now()
                execution_record.status = 'failed'
                execution_record.error_message = str(e)
                db.commit()

            db.rollback()
            raise
        finally:
            if duckdb_conn:
                duckdb_conn.close()


def _build_model_matching_sql(
    models: List[FraudHunterModelDefinition],
    realtime_wide_table_path: str,
    dep_acct_offline_path: str,
    cust_offline_path: Optional[str]
) -> str:
    """构建模型匹配SQL

    按 model_executor 的 execute_backtest 模式组装查询语句：
    - 实时宽表使用上文生成的实时宽表
    - 离线宽表使用各类最新的离线宽表
    - SQL组装形式为：
        SELECT
            所有指标,
            array[
                case when 模型1条件 then '模型1',
                case when 模型2条件 then '模型2',
                ...
            ] as 命中模型情况
        FROM 实时存款账户指标宽表
        LEFT JOIN 离线存款账户指标宽表
        LEFT JOIN 离线客户指标宽表
        WHERE 命中模型清单不为空

    Args:
        models: 模型列表
        realtime_wide_table_path: 实时宽表路径
        dep_acct_offline_path: 离线存款账户宽表路径
        cust_offline_path: 离线客户宽表路径（可选）

    Returns:
        SQL语句
    """
    from services.fraudhunter.model_service.rule_engine import RuleEngine
    from schemas.fraudhunter.rule import RuleConfig

    # 构建CASE WHEN子句列表
    case_when_clauses = []
    for model in models:
        rule_config_dict = model.rule_config
        rule_config = RuleConfig(**rule_config_dict)

        # 使用 RuleEngine 生成 WHERE 条件
        rule_engine = RuleEngine(db=None)  # 此处不需要db，因为不需要中文名
        indicator_alias_mapping = rule_engine.build_indicator_alias_mapping(
            rule_config,
            use_alias=True
        )

        where_condition = rule_engine.generate_sql_expression(rule_config, indicator_alias_mapping)

        # 生成 CASE WHEN 子句
        case_when_clauses.append(
            f"CASE WHEN ({where_condition}) THEN '{model.model_name}' ELSE NULL END"
        )

    # 构建 array 表达式（过滤NULL值）
    array_expr = f"list_filter([{', '.join(case_when_clauses)}], x -> x IS NOT NULL)"

    # 构建 SELECT 字段列表
    select_fields = [
        "dep_acct_realtime_indicator.target_id AS 账号",
        "dep_acct_realtime_indicator.etl_date AS 实时数据日期",
        "dep_acct_realtime_indicator.*",  # 实时存款指标
        "dep_acct_offline_indicator.*",   # 离线存款指标
        "cust_offline_indicator.*",       # 离线客户指标
        f"{array_expr} AS model_hit_array"
    ]

    select_clause = ",\n    ".join(select_fields)

    # 构建 FROM 和 JOIN 子句
    join_clauses = [
        f"FROM read_parquet('{realtime_wide_table_path}') AS dep_acct_realtime_indicator",
        f"LEFT JOIN read_parquet('{dep_acct_offline_path}') AS dep_acct_offline_indicator",
        "    ON dep_acct_realtime_indicator.target_id = dep_acct_offline_indicator.target_id"
    ]

    if cust_offline_path:
        join_clauses.extend([
            f"LEFT JOIN read_parquet('{cust_offline_path}') AS cust_offline_indicator",
            "    ON dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_offline_indicator.target_id"
        ])

    # 构建 WHERE 子句（命中模型清单不为空）
    where_clause = "WHERE list_count(model_hit_array) > 0"

    # 组装完整SQL
    sql = f"""-- 实时模型匹配SQL
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 模型数量: {len(models)}

SELECT
    {select_clause}
{chr(10).join(join_clauses)}
{where_clause}
"""

    return sql


def _build_all_user_variable_config(
    db: Session,
) -> dict:
    all_user_config = db.query(FraudHunterModelUserVariableConfig).all()
    _user_config = {}
    for c in all_user_config:
        if c.config_type == "pure_value":
            _user_config[c.config_key] = _user_config[c.config_value]['value']
        
        if c.config_type == "list_to_in_str":
            tmp_list = [f"'{_}'" for _ in _user_config[c.config_value]['value']]
            _user_config[c.config_key] = ','.join(tmp_list)
    
    logger.info(f"用户变量组装完毕：{_user_config}")
    return _user_config