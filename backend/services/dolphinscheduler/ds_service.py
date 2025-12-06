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
from pydolphinscheduler.tasks.http import Http
from pydolphinscheduler.core.process_definition import ProcessDefinition

from utils.config import settings

from models.fraudhunter.indicator import FraudHunterIndicatorTask

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
            os.environ["PYDS_JAVA_GATEWAY_ADDRESS"] = settings.dolphinscheduler_gateway_host
            os.environ["PYDS_JAVA_GATEWAY_PORT"] = str(settings.dolphinscheduler_gateway_api_port)
            os.environ["PYDS_USER_NAME"] = settings.dolphinscheduler_gateway_user
            os.environ["PYDS_USER_PASSWORD"] = settings.dolphinscheduler_gateway_password

            logger.info(f"DolphinScheduler 配置初始化成功")

        except Exception as e:
            logger.error(f"初始化 DolphinScheduler 配置失败: {str(e)}")
            raise

    def submit_indicator_task_workflow(self, indicator_task: FraudHunterIndicatorTask) -> Dict[str, Any]:
        """
        提交工作流到 DolphinScheduler

        Args:
            workflow: 工作流对象

        Returns:
            Dict[str, Any]: 提交结果
        """
        try:
            workflow_code = None

            if indicator_task.ds_task_code:
                self.offline_ds_workflow(indicator_task.ds_task_code, indicator_task.task_code)
                self.delete_ds_workflow(indicator_task.ds_task_code)

            # 提交工作流
            with ProcessDefinition(
                name=f"{indicator_task.task_code}",
                schedule=settings.dolphinscheduler_schedule_cron_expression,
                start_time="2025-01-01",
                tenant="tenant_exists",
                project=settings.dolphinscheduler_project_name,
                user=settings.dolphinscheduler_gateway_user
            ) as workflow:
                # [start task_declare]

                # 依赖表检查
                # todo
                check_shell1 = Shell(name="check_shell", command="echo hello pydolphinscheduler")
                check_shell2 = Shell(name="check_shell", command="echo hello pydolphinscheduler")
                check_shell_group = [check_shell2, check_shell1]

                # 指标SQL执行
                # indicator_task_sql = Sql(
                #     name="indicator_task_sql",
                #     sql="select 1",
                #     datasource_name="ssxxz"
                # )
                indicator_task_sql = Shell(name="indicator_task_sql", command="echo hello pydolphinscheduler")

                # 任务结束回调
                task_callback = Http(
                    name='task_callback',
                    url="http://127.0.0.1"
                )

                # [end task_declare]

                # [start task_relation_declare]
                
                # 配置依赖关系
                check_shell_group >> indicator_task_sql >> task_callback
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
            # 注意：这需要根据实际的 pydolphinscheduler API 实现补数逻辑
            # 目前 pydolphinscheduler 可能没有直接的补数 API
            # 这里仅提供接口定义

            logger.info(f"开始补数任务: workflow_code={workflow_code}, start={start_date}, end={end_date}")

            result = {
                "success": True,
                "workflow_code": workflow_code,
                "start_date": start_date,
                "end_date": end_date,
                "message": "补数任务已提交"
            }

            return result

        except Exception as e:
            logger.error(f"补数任务失败: {str(e)}")
            raise
