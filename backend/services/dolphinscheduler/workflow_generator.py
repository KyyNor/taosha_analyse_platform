"""
工作流生成服务
根据指标任务数据生成 DolphinScheduler 工作流定义
"""

from typing import List, Dict, Any, Optional
from loguru import logger
from pydolphinscheduler.core import Workflow
from pydolphinscheduler.tasks.shell import Shell
from pydolphinscheduler.tasks.sql import Sql
from models.fraudhunter.indicator import FraudHunterIndicatorTask, FraudHunterIndicatorDefinition
from .ds_service import DolphinSchedulerService


class WorkflowGenerator:
    """工作流生成器"""

    def __init__(self, ds_service: DolphinSchedulerService):
        """
        初始化工作流生成器

        Args:
            ds_service: DolphinScheduler 服务实例
        """
        self.ds_service = ds_service
        self.task_config = ds_service.task_config

    def generate_workflow_from_task(
        self,
        indicator_task: FraudHunterIndicatorTask,
        indicators: List[FraudHunterIndicatorDefinition]
    ) -> Workflow:
        """
        根据指标任务生成工作流

        Args:
            indicator_task: 指标任务对象
            indicators: 关联的指标列表

        Returns:
            Workflow: 生成的工作流对象
        """
        try:
            # 生成工作流名称（使用任务编码）
            workflow_name = f"indicator_task_{indicator_task.task_code}"
            description = f"{indicator_task.task_name} - {indicator_task.description or ''}"

            logger.info(f"开始生成工作流: {workflow_name}")

            # 创建工作流
            workflow = self.ds_service.create_workflow(
                workflow_name=workflow_name,
                description=description
            )

            # 1. 生成 Shell 节点（表检查任务）
            shell_tasks = self._generate_shell_tasks(
                workflow=workflow,
                source_tables=indicator_task.source_tables
            )

            # 2. 生成 SQL 节点（指标计算任务）
            sql_task = self._generate_sql_task(
                workflow=workflow,
                indicator_task=indicator_task,
                indicators=indicators,
                upstream_tasks=shell_tasks
            )

            logger.info(f"工作流生成成功: {workflow_name}, Shell节点数={len(shell_tasks)}")

            return workflow

        except Exception as e:
            logger.error(f"生成工作流失败: {str(e)}")
            raise

    def _generate_shell_tasks(
        self,
        workflow: Workflow,
        source_tables: Optional[str]
    ) -> List[Shell]:
        """
        生成 Shell 任务节点（用于表检查）

        Args:
            workflow: 工作流对象
            source_tables: 源表列表（逗号分隔）

        Returns:
            List[Shell]: Shell 任务列表
        """
        shell_tasks = []

        if not source_tables:
            logger.warning("未配置源表，跳过 Shell 节点生成")
            return shell_tasks

        # 解析源表列表
        tables = [t.strip() for t in source_tables.split(",") if t.strip()]

        # 获取表检查任务配置
        table_check_config = self.task_config.get("table_check", {})
        timeout = table_check_config.get("timeout", 30)
        fail_retry_times = table_check_config.get("fail_retry_times", 3)
        fail_retry_interval = table_check_config.get("fail_retry_interval", 1)

        # 为每个表创建一个 Shell 任务
        for idx, table in enumerate(tables, start=1):
            task_name = f"check_table_{table.replace('.', '_')}"

            # Shell 脚本：检查表是否存在数据
            # 这里需要根据实际的数据源类型（Hive/Spark/MySQL等）调整脚本
            shell_script = self._generate_table_check_script(table)

            try:
                shell_task = Shell(
                    name=task_name,
                    command=shell_script,
                    workflow=workflow,
                    timeout=timeout,
                    fail_retry_times=fail_retry_times,
                    fail_retry_interval=fail_retry_interval
                )

                shell_tasks.append(shell_task)
                logger.debug(f"创建 Shell 任务: {task_name}")

            except Exception as e:
                logger.error(f"创建 Shell 任务失败: {task_name}, 错误: {str(e)}")
                raise

        return shell_tasks

    def _generate_table_check_script(self, table_name: str) -> str:
        """
        生成表检查脚本

        Args:
            table_name: 表名

        Returns:
            str: Shell 脚本内容
        """
        # 这里提供一个示例脚本，实际使用时需要根据数据源类型调整
        # 例如：Hive 查询、Spark SQL 查询等

        script = f"""#!/bin/bash
# 表检查脚本: {table_name}
# 检查表是否存在且有数据

echo "开始检查表: {table_name}"

# 示例：使用 beeline 查询 Hive 表
# beeline -u "jdbc:hive2://localhost:10000" -e "SELECT COUNT(*) FROM {table_name} WHERE etl_date='${{date}}'"

# 临时示例：简单的 echo
echo "表 {table_name} 检查完成"

exit 0
"""

        return script

    def _generate_sql_task(
        self,
        workflow: Workflow,
        indicator_task: FraudHunterIndicatorTask,
        indicators: List[FraudHunterIndicatorDefinition],
        upstream_tasks: List[Shell]
    ) -> Sql:
        """
        生成 SQL 任务节点（指标计算）

        Args:
            workflow: 工作流对象
            indicator_task: 指标任务对象
            indicators: 指标列表
            upstream_tasks: 上游 Shell 任务列表

        Returns:
            Sql: SQL 任务对象
        """
        try:
            task_name = f"calculate_indicators_{indicator_task.task_code}"

            # 获取 SQL 任务配置
            sql_task_config = self.task_config.get("sql_task", {})
            timeout = sql_task_config.get("timeout", 60)
            fail_retry_times = sql_task_config.get("fail_retry_times", 288)
            fail_retry_interval = sql_task_config.get("fail_retry_interval", 5)

            # 使用任务的 logic_content 作为 SQL 内容
            sql_content = indicator_task.logic_content

            # 创建 SQL 任务
            # 注意：这里需要根据实际的数据源类型选择合适的 SQL 任务类型
            # pydolphinscheduler 支持多种 SQL 数据源，需要配置数据源连接
            sql_task = Sql(
                name=task_name,
                sql=sql_content,
                workflow=workflow,
                timeout=timeout,
                fail_retry_times=fail_retry_times,
                fail_retry_interval=fail_retry_interval
            )

            # 设置依赖关系：SQL 任务依赖所有 Shell 任务
            if upstream_tasks:
                for shell_task in upstream_tasks:
                    sql_task.set_upstream(shell_task)

            logger.debug(f"创建 SQL 任务: {task_name}, 上游任务数={len(upstream_tasks)}")

            return sql_task

        except Exception as e:
            logger.error(f"创建 SQL 任务失败: {str(e)}")
            raise

    def publish_workflow(
        self,
        workflow: Workflow,
        indicator_task: FraudHunterIndicatorTask
    ) -> Dict[str, Any]:
        """
        发布工作流到 DolphinScheduler

        Args:
            workflow: 工作流对象
            indicator_task: 指标任务对象

        Returns:
            Dict[str, Any]: 发布结果
        """
        try:
            # 1. 提交工作流
            result = self.ds_service.submit_workflow(workflow)

            # 2. 上线调度
            online_success = self.ds_service.online_schedule(workflow)

            # 3. 更新指标任务的 DS 信息
            # 注意：这里需要在调用方法中更新数据库
            result["ds_task_name"] = workflow.name
            result["ds_task_code"] = result.get("workflow_code")
            result["online_success"] = online_success

            logger.info(f"工作流发布成功: {workflow.name}")

            return result

        except Exception as e:
            logger.error(f"发布工作流失败: {str(e)}")
            raise

    def update_workflow_from_task(
        self,
        indicator_task: FraudHunterIndicatorTask,
        indicators: List[FraudHunterIndicatorDefinition]
    ) -> Dict[str, Any]:
        """
        更新现有工作流

        Args:
            indicator_task: 指标任务对象
            indicators: 关联的指标列表

        Returns:
            Dict[str, Any]: 更新结果
        """
        try:
            # 由于 pydolphinscheduler 的更新机制，通常是重新生成并提交工作流
            # 这会覆盖同名的工作流

            workflow = self.generate_workflow_from_task(indicator_task, indicators)
            result = self.publish_workflow(workflow, indicator_task)

            result["action"] = "updated"
            logger.info(f"工作流更新成功: {workflow.name}")

            return result

        except Exception as e:
            logger.error(f"更新工作流失败: {str(e)}")
            raise
