"""
DeepAgents 数据分析智能体服务
基于 LangChain deepagents 框架构建的数据分析智能体
支持任务规划、SQL查询、代码执行、知识库检索等能力
"""

import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import ToolRetryMiddleware, ShellToolMiddleware, FilesystemFileSearchMiddleware
from langchain.agents.middleware._execution import DockerExecutionPolicy
from langchain_core.messages import AIMessage

from services.llm_service.base_llm_service import BaseLLMService
from services.agents.tools.sql_query_tool import sql_query
from services.agents.tools.deepagents.code_execution_tool import execute_code
from services.agents.tools.qdrant_vector_store_tool import search_knowledge_base
from services.agents.tools.chart_tool import create_chart, create_chart_html
from services.agents.tools.common_tools import get_date_range
from services.agents.tools.metrics_tool import get_metrics
from utils.logger import logger


# 数据分析系统提示词
DATA_ANALYSIS_SYSTEM_PROMPT = """你是淘沙分析平台的数据分析专家。你的任务是帮助用户分析数据并生成可视化报告。

## 工作流程
1. **理解问题**：仔细理解用户的分析需求
2. **制定计划**：使用 write_todos 创建详细的分析计划
3. **收集数据**：
   - 使用 sql_query 工具查询数据库获取数据
   - 使用 search_knowledge_base 工具检索相关知识和文档
4. **分析数据**：
   - 使用 execute_code 工具执行 Python 代码进行数据处理和统计分析
   - 可以使用 pandas、numpy 等库
5. **可视化**：
   - 使用 create_chart_html 工具生成离线 HTML 图表（完全不依赖 CDN）
   - 支持 line/bar/pie 图表类型
6. **保存结果**：
   - 将分析过程和中间结果写入文件系统
   - 将图表 HTML 直接嵌入报告
7. **生成报告**：
   - 完成所有 todos 后，将最终分析报告写入 /report.html
   - 报告应包含：分析背景、数据来源、分析过程、关键发现、结论建议

## 可用工具
- **sql_query**: 执行 SQL 查询，支持 DuckDB 和 Spark
- **execute_code**: 执行 Python 代码进行数据处理（支持 pandas、numpy）
- **search_knowledge_base**: 检索知识库获取相关文档和知识
- **create_chart_html**: 创建离线 HTML 图表（line/bar/pie），可直接嵌入报告
- **get_date_range**: 获取日期范围
- **get_metrics**: 获取指标数据

## 文件系统使用
- /data/ - 存放查询到的原始数据
- /analysis/ - 存放分析过程和中间结果
- /report.html - 最终的 HTML 分析报告

## HTML 报告格式要求
生成的 report.html 应该是一个完整的、独立的 HTML 文件，包含：
1. 完整的 HTML 结构（<!DOCTYPE html>, <html>, <head>, <body>）
2. 内嵌 CSS 样式（不依赖外部 CSS）
3. 清晰的报告结构：标题、摘要、数据分析、图表、结论
4. 图表使用 create_chart_html 工具生成的 HTML 代码块直接嵌入
5. 所有资源完全离线，不依赖任何外部 CDN

## 输出要求
- 分析要有理有据，结论要基于数据
- 图表要清晰展示数据特征
- 报告要结构清晰，易于理解
"""


DATA_ANALYSIS_SYSTEM_PROMPT = """你是淘沙分析平台的数据分析专家。你的任务是帮助用户分析数据并生成可视化报告。

## 工作流程
1. **理解问题**：仔细理解用户的分析需求
2. **制定计划**：使用 write_todos 创建详细的分析计划
3. **收集数据**：
   - 使用 sql_query 工具查询数据库获取数据
   - 使用 search_knowledge_base 工具检索相关知识和文档
4. **分析数据**：
   - 对数据处理和统计分析
5. **保存结果**：
   - 将分析过程和中间结果写入文件系统
   - 将图表配置保存到 /charts/ 目录
6. **生成报告**：
   - 完成所有 todos 后，将最终分析报告写入 /report.html
   - 报告应包含：分析背景、数据来源、分析过程、关键发现、结论建议


## 文件系统使用
- /data/ - 存放查询到的原始数据
- /analysis/ - 存放分析过程和中间结果
- /charts/ - 存放图表配置（JSON格式）
- /report.html - 最终的 HTML 分析报告

## HTML 报告格式要求
生成的 report.html 应该是一个完整的、独立的 HTML 文件，包含：
1. 完整的 HTML 结构（<!DOCTYPE html>, <html>, <head>, <body>）
2. 内嵌 CSS 样式（不依赖外部 CSS/JS）
3. 清晰的报告结构：标题、摘要、数据分析、图表、结论

## 输出要求
- 分析要有理有据，结论要基于数据
- 图表要清晰展示数据特征
- 报告要结构清晰，易于理解
"""

SHELL_TOOL_DESCRIPTION = """
在持久会话中执行 shell 命令。运行命令前，请确认当前工作目录正确（例如用 ls 或 pwd 检查），并确保所有父目录已存在。
优先使用绝对路径；若路径包含空格，请用引号包裹，例如 cd "/path/with spaces"。多个命令请用 && 或 ; 串联，不要使用换行。
除非确实需要，否则避免频繁使用 cd,以保持会话稳定。
输出过大时可能被截断，长时间运行的命令在达到配置的超时时间后将被强制终止。
本系统中包含Python3.11环境,并包含科学计算相关的库,如numpy、pandas、matplotlib等,你可以使用pip list来查看环境清单。
"""

class DataAnalyserAgent:
    """DeepAgents 数据分析智能体"""

    def __init__(
        self,
        session_id: Optional[str] = None,
        output_base_dir: str = "./analysis_output",
    ):
        """初始化数据分析智能体

        Args:
            session_id: 会话ID，用于文件隔离。如果不传入则自动生成
            output_base_dir: 输出基础目录
        """
        # 配置
        self._config = {
            "output_base_dir": output_base_dir,
            "code_execution_enabled": True,
            "code_execution_timeout": 30,
            "max_iterations": 50,
            "default_query_limit": 1000,
            "max_tokens_before_summary": 50000,
            "messages_to_keep": 20,
            "shell_tool_docker_mem_size": 4,
            "shell_tool_docker_cpu_size": 2,
        }

        # 会话管理 - 按会话ID隔离文件
        self.session_id = session_id or str(uuid.uuid4())
        self.output_dir = Path(self._config["output_base_dir"]) / self.session_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # LLM 服务
        self.llm_service = BaseLLMService()

        # Agent 实例
        self.agent = None

        # 分析结果
        self.llm_output: Optional[str] = None

        logger.info(f"DataAnalyserAgent 初始化完成，会话ID: {self.session_id}")
        logger.info(f"输出目录: {self.output_dir}")

    def create_agent(self) -> None:
        """创建 DeepAgent 实例"""
        try:
            # 准备工具列表
            tools = [
                # sql_query,                  # SQL 查询工具
                # execute_code,               # Python 代码执行工具
                # search_knowledge_base,      # 知识库检索工具
                # get_date_range,             # 日期范围工具
                # get_metrics,                # 指标数据工具
            ]

            # 创建 DeepAgent
            # deepagents 自动包含: TodoListMiddleware, FilesystemMiddleware, SubAgentMiddleware， SummarizationMiddleware
            self.agent = create_deep_agent(
                model=self.llm_service.client,
                tools=tools,
                system_prompt=DATA_ANALYSIS_SYSTEM_PROMPT,
                backend=FilesystemBackend(
                    root_dir=str(self.output_dir),
                    virtual_mode=True
                ),
                middleware=[
                    ToolRetryMiddleware(
                        max_retries=2, # 指的是重试的次数
                        on_failure="continue" # 会包装错误信息返回给LLM
                    ),
                    ShellToolMiddleware(
                        tool_description=SHELL_TOOL_DESCRIPTION,
                        workspace_root=self.output_dir.resolve(),
                        execution_policy=DockerExecutionPolicy(
                            image="taosha-sandbox:latest",  # 刚才 build 的镜像
                            user='sandbox',                  # 容器内用户名
                            read_only_rootfs=True,           # 根分区只读，写操作只能挂 volume
                            cpus=self.shell_tool_docker_cpu_size,
                            memory_bytes=self.shell_tool_docker_mem_size * 1024 * 1024 * 1024,  # 4GB内存
                            network_enabled=False,
                        ),   # 用 Docker 隔离
                    ),
                    FilesystemFileSearchMiddleware(
                        root_path=str(self.output_dir)
                    ),
                ],
            )

            logger.info("DeepAgent 创建成功")

        except Exception as e:
            logger.error(f"DeepAgent 创建失败: {e}")
            raise

    def run_analysis(self, question: str) -> Dict[str, Any]:
        """运行数据分析

        Args:
            question: 用户的数据分析问题

        Returns:
            包含分析结果的字典
        """
        if not self.agent:
            self.create_agent()

        logger.info(f"开始分析: {question[:100]}...")
        start_time = datetime.now()

        try:
            # 执行 Agent
            import os
            from utils.config import settings
            from langfuse import get_client
            from langfuse import propagate_attributes

            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
            os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
            os.environ["LANGFUSE_HOST"] = settings.langfuse_host
            _langfuse_client = get_client()

            with _langfuse_client.start_as_current_span(name="deep_agent") as span:
                with propagate_attributes(user_id='deep_agent_test', session_id=self.session_id):
                    result = self.agent.invoke({
                        "messages": [{"role": "user", "content": question}]
                    })

            for i, message in enumerate(result['messages']):
                if isinstance(message, AIMessage):
                    logger.info(f"第 {i+1} 条 AI 消息:")
                    logger.info(message.content)
                    logger.info("-" * 50)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 提取 LLM 输出
            self.llm_output = self._extract_llm_output(result)

            # 检查是否生成了报告文件
            report_path = self.output_dir / "report.html"
            report_exists = report_path.exists()
            report_content = None
            if report_exists:
                try:
                    report_content = report_path.read_text(encoding="utf-8")
                except Exception as e:
                    logger.warning(f"读取报告文件失败: {e}")

            logger.info(f"分析完成，耗时: {duration:.2f}秒")

            return {
                "success": True,
                "session_id": self.session_id,
                "question": question,
                "output_dir": str(self.output_dir),
                "report_path": str(report_path) if report_exists else None,
                "report_exists": report_exists,
                "report_content": report_content,
                "llm_output": self.llm_output,
                "duration_seconds": duration,
                "result": result,
            }

        except Exception as e:
            logger.error(f"分析执行失败: {e}")
            return {
                "success": False,
                "session_id": self.session_id,
                "question": question,
                "output_dir": str(self.output_dir),
                "error": str(e),
            }

    def _extract_llm_output(self, result: Dict[str, Any]) -> Optional[str]:
        """从结果中提取 LLM 输出

        Args:
            result: Agent 返回的结果

        Returns:
            LLM 输出文本
        """
        try:
            messages = result.get("messages", [])
            if messages:
                # 获取最后一条 AI 消息
                for msg in reversed(messages):
                    if hasattr(msg, "content") and msg.content:
                        return str(msg.content)
            return None
        except Exception as e:
            logger.warning(f"提取 LLM 输出失败: {e}")
            return None

    async def run_analysis_stream(self, question: str):
        """流式运行数据分析

        Args:
            question: 用户的数据分析问题

        Yields:
            分析过程中的事件
        """
        if not self.agent:
            self.create_agent()

        logger.info(f"开始流式分析: {question[:100]}...")
        llm_output_chunks = []

        try:
            async for event in self.agent.astream_events(
                {"messages": [{"role": "user", "content": question}]},
            ):
                event_type = event.get("event", "")
                data = event.get("data", {})

                # 处理不同类型的事件
                if event_type == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        llm_output_chunks.append(chunk.content)
                        yield {
                            "event": "text",
                            "data": {"content": chunk.content}
                        }

                elif event_type == "on_tool_start":
                    yield {
                        "event": "tool_start",
                        "data": {
                            "name": data.get("name", "unknown"),
                            "input": data.get("input", {})
                        }
                    }

                elif event_type == "on_tool_end":
                    yield {
                        "event": "tool_end",
                        "data": {
                            "name": data.get("name", "unknown"),
                            "output": str(data.get("output", ""))[:500]  # 截断输出
                        }
                    }

            # 保存 LLM 输出
            self.llm_output = "".join(llm_output_chunks)

            # 发送完成事件
            yield {
                "event": "done",
                "data": {
                    "session_id": self.session_id,
                    "output_dir": str(self.output_dir)
                }
            }

        except Exception as e:
            logger.error(f"流式分析失败: {e}")
            yield {
                "event": "error",
                "data": {"error": str(e)}
            }

    def get_session_files(self) -> List[Dict[str, Any]]:
        """获取当前会话的所有文件

        Returns:
            文件信息列表
        """
        files = []
        for file_path in self.output_dir.rglob("*"):
            if file_path.is_file():
                files.append({
                    "path": str(file_path.relative_to(self.output_dir)),
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat()
                })
        return files

    def read_file(self, relative_path: str) -> Optional[str]:
        """读取会话目录中的文件

        Args:
            relative_path: 相对于会话目录的文件路径

        Returns:
            文件内容或 None
        """
        file_path = self.output_dir / relative_path
        if file_path.exists() and file_path.is_file():
            try:
                return file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"读取文件失败: {e}")
                return None
        return None

    def get_report_content(self) -> Optional[str]:
        """获取报告内容

        Returns:
            报告 HTML 内容或 None
        """
        return self.read_file("report.html")

    def cleanup(self) -> None:
        """清理会话资源"""
        self.agent = None
        logger.info(f"会话 {self.session_id} 资源已清理")


# 便捷函数：创建服务实例
def create_data_analyser_agent(
    session_id: Optional[str] = None,
    output_base_dir: str = "./analysis_output"
) -> DataAnalyserAgent:
    """创建数据分析智能体实例

    Args:
        session_id: 会话ID，用于文件隔离
        output_base_dir: 输出基础目录

    Returns:
        DataAnalyserAgent 实例
    """
    agent = DataAnalyserAgent(
        session_id=session_id,
        output_base_dir=output_base_dir
    )
    agent.create_agent()
    return agent


# 向后兼容别名
DeepAnalyseAgentService = DataAnalyserAgent
create_deep_analyse_service = create_data_analyser_agent
