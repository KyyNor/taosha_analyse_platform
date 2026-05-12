"""
DolphinScheduler 服务基类
负责与 DS 的连接管理和基础项目/工作流操作
"""
import os
import requests
from typing import Optional, Dict, Any
from loguru import logger
from pydolphinscheduler.tasks.shell import Shell
from pydolphinscheduler.tasks.sql import Sql
from pydolphinscheduler.core.process_definition import ProcessDefinition
from pydolphinscheduler import configuration

from utils.config import settings

from models.fraudhunter.indicator import FraudHunterIndicatorTask, FraudHunterIndicatorDefinition
from sqlalchemy.orm import Session

class DolphinSchedulerService:
    """DolphinScheduler 服务基类"""

    def __init__(self):
        """初始化 DS 服务"""
        # 初始化 pydolphinscheduler 配置
        self._init_configuration()

    def _init_configuration(self):
        """初始化 pydolphinscheduler 配置"""
        try:
            # 设置 DS 连接配置
            configuration.JAVA_GATEWAY_ADDRESS = settings.dolphinscheduler_gateway_host
            configuration.PYDS_JAVA_GATEWAY_PORT = str(settings.dolphinscheduler_gateway_api_port)
            configuration.PYDS_USER_NAME = settings.dolphinscheduler_gateway_user
            configuration.PYDS_USER_PASSWORD = settings.dolphinscheduler_gateway_password

            logger.info(f"DolphinScheduler 配置初始化成功")

        except Exception as e:
            logger.error(f"初始化 DolphinScheduler 配置失败: {str(e)}")
            raise

    def submit_indicator_task_workflow(self, indicator_task: FraudHunterIndicatorTask, db: Session) -> Dict[str, Any]:
        """
        提交工作流到 DolphinScheduler

        Args:
            indicator_task: 指标任务对象
            db: 数据库会话

        Returns:
            Dict[str, Any]: 提交结果
        """
        try:
            workflow_code = None

            # 查询关联的所有指标定义
            indicators = db.query(FraudHunterIndicatorDefinition).filter(
                FraudHunterIndicatorDefinition.indicator_task_id == indicator_task.id
            ).all()

            if not indicators:
                raise ValueError(f"指标任务 {indicator_task.id} 没有关联的指标定义")

            # 获取所有指标编码
            indicator_codes = [ind.indicator_code for ind in indicators]
            logger.info(f"指标任务 {indicator_task.id} 关联的指标: {indicator_codes}")

            # 尝试清理历史工作流
            if indicator_task.ds_task_code:
                self.offline_ds_workflow(indicator_task.ds_task_code, indicator_task.task_code)
                self.delete_ds_workflow(indicator_task.ds_task_code)

            logger.info(settings.dolphinscheduler_workflow_params)

            # 提交工作流
            with ProcessDefinition(
                name=f"{indicator_task.task_code}_{indicator_task.task_name}",
                schedule=settings.dolphinscheduler_schedule_cron_expression,
                start_time="2025-01-01",
                tenant="default",
                project=settings.dolphinscheduler_project_name,
                user=settings.dolphinscheduler_gateway_user,
                param=settings.dolphinscheduler_workflow_params,
            ) as workflow:
                # [start task_declare]

                # 依赖表检查
                check_shell_group = []
                for table in indicator_task.source_tables.split(","):
                    temp_shell = Shell(
                        name=f"check_table_{table}",
                        command=f"sh /home/bdspk/hxb_dh/datafactory_scripts/project/hadoop_operations/sh/table_check/check-hive-table.sh {table} ${{date}} ${{hive.host}} ${{hive.port}} ${{hive.user}} ${{hive.passwd}}",
                        environment_name="bdspk",
                        fail_retry_times=settings.dolphinscheduler_task_table_check_fail_retry_times,
                        fail_retry_interval=settings.dolphinscheduler_task_table_check_fail_retry_interval,
                    )
                    check_shell_group.append(temp_shell)

#                 # 临时表名：hxb_dh_data_tmp.taosha_tmp_{task_code}_{date}
#                 temp_table_name = f"hxb_dh_data_tmp.taosha_tmp_{indicator_task.task_code}_${{date}}"

#                 # 处理 logic_content：去掉末尾的分号（如果有）
#                 logic_content = indicator_task.logic_content.strip()
#                 if logic_content.endswith(';'):
#                     logic_content = logic_content[:-1].strip()

#                 # 构建完整的SQL语句
#                 sql_statements = []

#                 # 1. 删除临时表
#                 sql_statements.append(f"drop table if exists {temp_table_name}")

#                 # 2. 创建临时表
#                 sql_statements.append(f"create table {temp_table_name} as\n{logic_content}")

#                 # 3. 逐个指标入库
#                 for indicator_code in indicator_codes:
#                     insert_sql = f"""INSERT OVERWRITE TABLE hxb_dh_data_dwm.dwm_taosha_indicator_details
# SELECT
#     target_id,
#     {indicator_code} as indicator_value,
#     '{indicator_task.object_type}' as object_type,
#     etl_date as etl_date,
#     '{indicator_code}' as indicator_id
# FROM {temp_table_name}"""
#                     sql_statements.append(insert_sql)

#                 # 4. 删除临时表
#                 sql_statements.append(f"drop table if exists {temp_table_name}")

#                 # 将所有SQL语句用分号连接
#                 full_sql = ";\n\n".join(sql_statements) + ";"

                # 生成横表转纵表的SQL（使用 LATERAL VIEW STACK 替代 UNION ALL）
                n_cols = len(indicator_codes)
                stack_pairs = ", ".join([
                    f"'{code}', cast(ifnull({code}, '') as string)"
                    for code in indicator_codes
                ])
                lateral_view_stack = (
                    f"LATERAL VIEW STACK({n_cols}, {stack_pairs}) "
                    f"AS indicator_id, indicator_value"
                )

                # 指标SQL执行
                sql_header_comment = (
                    f"-- 任务ID: {indicator_task.id}, "
                    f"任务名称: {indicator_task.task_name}, "
                    f"修改时间: ${{date}}"
                )
                indicator_task_sql = Sql(
                    name="indicator_task_sql",
                    sql=f"""{sql_header_comment}
WITH temp_data AS (
                                    {indicator_task.logic_content}
                                )
                                INSERT OVERWRITE TABLE hxb_dh_data_dwm.dwm_taosha_indicator_details
                                SELECT
                                    target_id,
                                    indicator_value,
                                    '{indicator_task.object_type}' AS object_type,
                                    etl_date,
                                    indicator_id
                                FROM temp_data
                                {lateral_view_stack}
                                """,
                    datasource_name=settings.dolphinscheduler_task_sql_task_datasource_name,
                    sql_type="1",  # NOT_SELECT 非查询
                    environment_name="bdspk",
                    fail_retry_times=settings.dolphinscheduler_task_sql_task_fail_retry_times,
                    fail_retry_interval=settings.dolphinscheduler_task_sql_task_fail_retry_interval,
                )

                # 任务结束回调
                task_callback = Shell(
                    name='task_finish_callback',
                    command=f"""curl -X POST http://125.1.129.76:8080/taosha/api/taosha/v1/fraudhunter/wide-table/indicator-runs/callback -H 'Content-Type: application/json' -d '{{"indicator_task_id":{indicator_task.id},"indicator_version":{indicator_task.latest_version},"etl_date":"${{date}}"}}'""",
                    environment_name="bdspk",
                    fail_retry_times=settings.dolphinscheduler_task_sql_task_fail_retry_times,
                    fail_retry_interval=settings.dolphinscheduler_task_sql_task_fail_retry_interval,
                )
                
                # [end task_declare]

                # [start task_relation_declare]
                # 配置依赖关系
                if len(check_shell_group) > 0:
                    check_shell_group >> indicator_task_sql >> task_callback
                else:
                    indicator_task_sql >> task_callback
                # [end task_relation_declare]

                workflow_code = workflow.submit()

            result = {
                "success": True,
                "workflow_name": indicator_task.task_code,
                "workflow_code": str(workflow_code),
                "message": f"工作流 {indicator_task.task_code} 提交成功"
            }

            logger.info(f"工作流提交成功: {result}")
            return result

        except Exception as e:
            logger.error(f"提交工作流失败: {str(e)}")
            raise

    def offline_ds_workflow(self, workflow_code, workflow_name):
        response = requests.post(
            url=f"http://{settings.dolphinscheduler_gateway_host}:12345/dolphinscheduler/projects/{settings.dolphinscheduler_project_code}/process-definition/{workflow_code}/release",
            data={
                "name": workflow_name,
                "releaseState": "OFFLINE"
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "token": settings.dolphinscheduler_gateway_api_token
            }
        )
        logger.info(f"offline_ds_workflow: {response.status_code} content:{response.content}")

    def delete_ds_workflow(self, workflow_code):
        response = requests.delete(
            url=f"http://{settings.dolphinscheduler_gateway_host}:12345/dolphinscheduler/projects/{settings.dolphinscheduler_project_code}/process-definition/{workflow_code}",
            headers={
                "token": settings.dolphinscheduler_gateway_api_token
            }
        )
        logger.info(f"delete_ds_workflow: {response.status_code} content:{response.content}")

    def run_backfill(
        self,
        workflow_code: str,
        start_date: str,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行补数任务

        Args:
            workflow_code: 工作流编码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)，默认为今天

        Returns:
            Dict[str, Any]: 补数结果
        """
        try:
            # 如果没有提供结束日期，使用开始日期作为结束日期
            if not end_date:
                end_date = start_date

            # 构建scheduleTime参数
            schedule_time_data = {
                "complementStartDate": f"{start_date} 00:00:00",
                "complementEndDate": f"{end_date} 00:00:00"
            }
            import json
            schedule_time_encoded = json.dumps(schedule_time_data)

            # 构建请求参数
            params = {
                "processDefinitionCode": workflow_code,
                "failureStrategy": "CONTINUE",
                "warningType": "NONE",
                "warningGroupId": "",
                "execType": "COMPLEMENT_DATA",
                "startNodeList": "",
                "taskDependType": "TASK_POST",
                "complementDependentMode": "OFF_MODE",
                "runMode": "RUN_MODE_SERIAL",
                "processInstancePriority": "MEDIUM",
                "workerGroup": "default",
                "environmentCode": "",
                "startParams": "",
                "expectedParallelismNumber": "",
                "dryRun": "0",
                "scheduleTime": schedule_time_encoded
            }

            logger.info(f"开始补数任务: workflow_code={workflow_code}, start={start_date}, end={end_date}")

            # 调用DolphinScheduler API
            response = requests.post(
                url=f"http://{settings.dolphinscheduler_gateway_host}:12345/dolphinscheduler/projects/{settings.dolphinscheduler_project_code}/executors/start-process-instance",
                data=params,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "token": settings.dolphinscheduler_gateway_api_token
                }
            )

            logger.info(f"run_backfill response: {response.status_code} content:{response.content}")

            if response.status_code == 200:
                response_data = response.json() if response.content else {}
                result = {
                    "success": True,
                    "workflow_code": workflow_code,
                    "start_date": start_date,
                    "end_date": end_date,
                    "message": "补数任务提交成功",
                    "response_data": response_data
                }
            else:
                result = {
                    "success": False,
                    "workflow_code": workflow_code,
                    "start_date": start_date,
                    "end_date": end_date,
                    "message": f"补数任务提交失败，状态码: {response.status_code}",
                    "error_content": response.content.decode('utf-8')
                }

            return result

        except Exception as e:
            logger.error(f"补数任务失败: {str(e)}")
            raise
