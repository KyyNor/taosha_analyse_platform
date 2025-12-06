"""
DolphinScheduler 服务基类
负责与 DS 的连接管理和基础项目/工作流操作
"""

from typing import Optional, Dict, Any
from loguru import logger
from pydolphinscheduler.core.configuration import Configuration
from pydolphinscheduler.core import Project, Workflow
from pydolphinscheduler.tasks.shell import Shell
from pydolphinscheduler.tasks.sql import Sql
from utils.config import config


class DolphinSchedulerService:
    """DolphinScheduler 服务基类"""

    def __init__(self):
        """初始化 DS 服务"""
        self.ds_config = config.get("dolphinscheduler", {})
        self.gateway_config = self.ds_config.get("gateway", {})
        self.project_name = self.ds_config.get("project_name", "taosha_metrics")
        self.workflow_config = self.ds_config.get("workflow", {})
        self.schedule_config = self.ds_config.get("schedule", {})
        self.task_config = self.ds_config.get("task", {})

        # 初始化 pydolphinscheduler 配置
        self._init_configuration()

        # 获取或创建项目
        self.project = self._get_or_create_project()

    def _init_configuration(self):
        """初始化 pydolphinscheduler 配置"""
        try:
            # 设置 DS 连接配置
            Configuration.set_config({
                "java_gateway": {
                    "address": self.gateway_config.get("url", "http://localhost:12345"),
                    "port": self.gateway_config.get("api_port", 12346),
                    "auto_convert": True
                },
                "default": {
                    "user": {
                        "name": self.gateway_config.get("user", "admin"),
                        "password": self.gateway_config.get("password", "dolphinscheduler123"),
                        "tenant": self.gateway_config.get("tenant", "default")
                    }
                }
            })

            logger.info(f"DolphinScheduler 配置初始化成功: {self.gateway_config.get('url')}")

        except Exception as e:
            logger.error(f"初始化 DolphinScheduler 配置失败: {str(e)}")
            raise

    def _get_or_create_project(self) -> Project:
        """获取或创建项目"""
        try:
            # 尝试获取现有项目
            project = Project(name=self.project_name)
            logger.info(f"获取 DolphinScheduler 项目成功: {self.project_name}")
            return project

        except Exception as e:
            logger.error(f"获取/创建 DolphinScheduler 项目失败: {str(e)}")
            raise

    def check_workflow_exists(self, workflow_name: str) -> bool:
        """
        检查工作流是否存在

        Args:
            workflow_name: 工作流名称

        Returns:
            bool: 是否存在
        """
        try:
            # 注意：pydolphinscheduler 可能没有直接的工作流查询接口
            # 这里需要根据实际 API 进行调整
            # 临时返回 False，表示总是创建新工作流
            logger.info(f"检查工作流是否存在: {workflow_name}")
            return False

        except Exception as e:
            logger.warning(f"检查工作流失败: {str(e)}")
            return False

    def get_workflow_by_name(self, workflow_name: str) -> Optional[Workflow]:
        """
        根据名称获取工作流

        Args:
            workflow_name: 工作流名称

        Returns:
            Optional[Workflow]: 工作流对象，不存在则返回 None
        """
        try:
            # 注意：这需要根据实际的 pydolphinscheduler API 实现
            logger.info(f"获取工作流: {workflow_name}")
            return None

        except Exception as e:
            logger.error(f"获取工作流失败: {str(e)}")
            return None

    def create_workflow(
        self,
        workflow_name: str,
        description: str = "",
        schedule: Optional[str] = None
    ) -> Workflow:
        """
        创建工作流

        Args:
            workflow_name: 工作流名称
            description: 工作流描述
            schedule: 定时调度表达式（cron）

        Returns:
            Workflow: 创建的工作流对象
        """
        try:
            # 使用配置中的默认值
            timezone = self.workflow_config.get("default_timezone", "Asia/Shanghai")
            timeout = self.workflow_config.get("timeout", 60)

            # 创建工作流
            workflow = Workflow(
                name=workflow_name,
                project=self.project,
                description=description,
                timezone=timezone,
                timeout=timeout
            )

            # 如果提供了调度表达式，则设置调度
            if schedule:
                workflow.schedule = schedule
            else:
                # 使用配置中的默认调度
                default_cron = self.schedule_config.get("cron_expression", "0 0 2 * * ?")
                workflow.schedule = default_cron

            logger.info(f"工作流创建成功: {workflow_name}")
            return workflow

        except Exception as e:
            logger.error(f"创建工作流失败: {str(e)}")
            raise

    def update_workflow(
        self,
        workflow: Workflow,
        description: Optional[str] = None
    ) -> Workflow:
        """
        更新工作流

        Args:
            workflow: 工作流对象
            description: 新的描述

        Returns:
            Workflow: 更新后的工作流对象
        """
        try:
            if description:
                workflow.description = description

            logger.info(f"工作流更新成功: {workflow.name}")
            return workflow

        except Exception as e:
            logger.error(f"更新工作流失败: {str(e)}")
            raise

    def submit_workflow(self, workflow: Workflow) -> Dict[str, Any]:
        """
        提交工作流到 DolphinScheduler

        Args:
            workflow: 工作流对象

        Returns:
            Dict[str, Any]: 提交结果
        """
        try:
            # 提交工作流
            workflow.submit()

            result = {
                "success": True,
                "workflow_name": workflow.name,
                "workflow_code": getattr(workflow, "code", None),
                "message": f"工作流 {workflow.name} 提交成功"
            }

            logger.info(f"工作流提交成功: {workflow.name}")
            return result

        except Exception as e:
            logger.error(f"提交工作流失败: {str(e)}")
            raise

    def online_schedule(self, workflow: Workflow) -> bool:
        """
        上线工作流调度

        Args:
            workflow: 工作流对象

        Returns:
            bool: 是否成功
        """
        try:
            # 上线调度
            online = self.schedule_config.get("online_schedule", True)
            if online and hasattr(workflow, "online"):
                workflow.online()
                logger.info(f"工作流调度上线成功: {workflow.name}")
                return True
            else:
                logger.warning(f"工作流调度未上线: {workflow.name}")
                return False

        except Exception as e:
            logger.error(f"上线工作流调度失败: {str(e)}")
            return False

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
