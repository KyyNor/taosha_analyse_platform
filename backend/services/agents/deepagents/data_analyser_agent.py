"""
DeepAgents 数据分析智能体服务
基于 LangChain deepagents 框架构建的数据分析智能体
支持任务规划、SQL查询、代码执行、知识库检索等能力
"""

import uuid
import random
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from bs4 import BeautifulSoup

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend, CompositeBackend, StateBackend
from langchain.agents.middleware import ToolRetryMiddleware, ShellToolMiddleware, FilesystemFileSearchMiddleware
from services.agents.deepagents.custom_docker_execution_policy import CustomDockerExecutionPolicy
from langchain_core.messages import AIMessage

from services.llm_service.base_llm_service import BaseLLMService
from services.agents.tools.sql_query_tool import sql_query
from services.agents.tools.qdrant_vector_store_tool import search_knowledge_base
from services.agents.tools.chart_tool import create_chart
from services.agents.tools.common_tools import get_date_range
from services.agents.tools.metrics_tool import get_metrics
from utils.logger import logger
from services.agents.models.deep_agent_context import DataAnalysisContext

# 提示词模板名称常量
PROMPT_TEMPLATE_DATA_ANALYSIS = "deepagents_data_analysis_system_prompt"
PROMPT_TEMPLATE_SHELL_TOOL = "deepagents_shell_tool_description"

# 数据分析系统提示词 (默认值，当数据库中不存在时使用)
DEFAULT_DATA_ANALYSIS_SYSTEM_PROMPT = """你是淘沙分析平台的数据分析专家。你的任务是帮助用户分析数据并生成可视化报告。

## 工作流程
1. **理解问题**：仔细理解用户的分析需求。
2. **制定计划**：使用 write_todos 创建详细的分析计划。
3. **收集数据**：
   - 使用 sql_query 工具查询数据库获取数据。
   - 使用 search_knowledge_base 工具检索相关知识和文档。
4. **分析数据**：
   - 对数据进行处理和统计分析。
   - 务必基于全量数据分析，避免基于带 limit 的查询结果。
5. **可视化**：
   - 使用 shell 工具编写 Python 脚本（优先使用 seaborn/matplotlib）生成图片。
   - 必须配置中文字体：`plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']`。
   - 图片统一保存至 `/analysis/tmp/` 目录下。
6. **生成报告内容**：
   - 完成所有任务后，将分析结果的主体内容写入 `/analysis/report_content.html`。
   - 注意：该文件 **不应** 包含 `<html>`, `<head>`, `<body>`, `<style>` 等标签，只需包含语义化的 HTML 内容结构（如 h1, h2, p, table, img 等）。

## 工具使用规范
1. **查询限制**：调用查询工具（除维表 hxb_dh_data_dim 外）必须带 ETL_DATE 或 CDATE 过滤条件。
2. **安全第一**：禁止操作 `/analysis` 之外的任何目录。
3. **文件查看**：在未知文件大小时，切勿直接读取全部内容，防止 Token 溢出。
4. **单位换算**：涉及大额金额（>10000）时，请使用“万”或“亿”作为单位。

## HTML 报告内容要求
生成的 report_content.html 仅需包含以下语义化结构：
1. **主标题**：使用 `h1` 标签。
2. **章节标题**：使用 `h2` 标签。
3. **子标题**：使用 `h3` 标签（必要时可使用 `h4`）。
4. **正文**：使用 `p` 标签。
5. **强调**：使用 `strong` 或 `b` 标签加粗关键数据。
6. **关键洞察/总结**：使用 `blockquote` 标签包裹核心结论。
7. **列表**：使用 `ul`/`ol` 和 `li` 标签。
8. **表格**：使用 `table` 标签（无需添加 class，系统会自动处理）。
9. **图片**：使用 `img` 标签（src使用相对路径，必须填写 `alt` 属性作为图注）。

## 输出质量要求
- 结论必须基于客观数据，禁止臆造。
- **关键洞察**（blockquote）应放在章节开头或结尾，突出核心发现。
- 图表应选择最能体现数据特征的类型（如趋势用折线图，占比用饼图，对比用柱状图）。
- 报告应具备专业度，逻辑严密。
"""

# Shell 工具描述 (默认值，当数据库中不存在时使用)
DEFAULT_SHELL_TOOL_DESCRIPTION = """
在持久会话中执行 shell 命令。运行命令前，请确认当前工作目录正确（例如用 ls 或 pwd 检查），并确保所有父目录已存在。
优先使用绝对路径；若路径包含空格，请用引号包裹，例如 cd "/path/with spaces"。多个命令请用 && 或 ; 串联，不要使用换行。
除非确实需要，否则避免频繁使用 cd,以保持会话稳定。
输出过大时可能被截断，长时间运行的命令在达到配置的超时时间后将被强制终止。
本系统中包含Python3.11环境,并包含科学计算相关的库,如numpy、pandas、matplotlib等,你可以使用pip list来查看环境清单。
系统已安装中文字体(WenQuanYi Micro Hei、WenQuanYi Zen Hei)。
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
            "shell_tool_docker_cpu_size": "2",
        }

        # 会话管理 - 按会话ID隔离文件
        self.session_id = session_id or str(uuid.uuid4())
        self.output_dir = Path(self._config["output_base_dir"]) / self.session_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.chmod(0o777)

        # LLM 服务
        self.llm_service = BaseLLMService()

        # Agent 实例
        self.agent = None

        # 分析结果
        self.llm_output: Optional[str] = None

        logger.info(f"DataAnalyserAgent 初始化完成，会话ID: {self.session_id}")
        logger.info(f"输出目录: {self.output_dir}")

    def _get_prompt_template(self, template_name: str, default_value: str) -> str:
        """从数据库获取提示词模板，不存在则使用默认值

        Args:
            template_name: 模板名称
            default_value: 默认值

        Returns:
            模板内容
        """
        try:
            from models.db_base import get_db_session
            from services.metadata_service.metadata_service import PromptTemplateService

            with get_db_session() as db:
                service = PromptTemplateService(db)
                template = service.get_template_by_name(template_name)
                if template and template.get("template"):
                    logger.info(f"从数据库加载提示词模板: {template_name}")
                    return template.get("template")
                else:
                    logger.warning(f"提示词模板 {template_name} 不存在，使用默认值")
                    return default_value
        except Exception as e:
            logger.error(f"获取提示词模板失败: {e}，使用默认值")
            return default_value

    def create_agent(self) -> None:
        """创建 DeepAgent 实例"""
        try:
            # 从数据库加载提示词模板
            system_prompt = self._get_prompt_template(
                PROMPT_TEMPLATE_DATA_ANALYSIS,
                DEFAULT_DATA_ANALYSIS_SYSTEM_PROMPT
            )
            shell_tool_description = self._get_prompt_template(
                PROMPT_TEMPLATE_SHELL_TOOL,
                DEFAULT_SHELL_TOOL_DESCRIPTION
            )

            # 准备工具列表
            tools = [
                sql_query,                  # SQL 查询工具（支持 ToolRuntime）
                search_knowledge_base,      # 知识库检索工具
                # get_date_range,             # 日期范围工具
                # get_metrics,                # 指标数据工具
            ]

            composite_backend = lambda rt: CompositeBackend(
                    default=StateBackend(rt),
                    routes={
                        "/analysis/": FilesystemBackend(root_dir=str(self.output_dir.resolve()), virtual_mode=True)
                    }
                )

            # 创建 DeepAgent
            # deepagents 自动包含: TodoListMiddleware, FilesystemMiddleware, SubAgentMiddleware， SummarizationMiddleware
            self.agent = create_deep_agent(
                model=self.llm_service.client,
                tools=tools,
                system_prompt=system_prompt,
                context_schema=DataAnalysisContext,
                backend=composite_backend,
                middleware=[
                    ToolRetryMiddleware(
                        max_retries=2, # 指的是重试的次数
                        on_failure="continue" # 会包装错误信息返回给LLM
                    ),
                    ShellToolMiddleware(
                        tool_description=shell_tool_description,
                        workspace_root=self.output_dir.resolve(),
                        execution_policy=CustomDockerExecutionPolicy(
                            image="taosha-sandbox:latest",   # 刚才 build 的镜像
                            user='root',                     # 容器内用户名
                            cpus=self._config["shell_tool_docker_cpu_size"],
                            memory_bytes=self._config["shell_tool_docker_mem_size"] * 1024 * 1024 * 1024,  # 4GB内存
                            network_enabled=False,
                            target_workspace='/analysis',
                        ),   # 用 Docker 隔离
                    ),
                    FilesystemFileSearchMiddleware(
                        root_path=str(self.output_dir)
                    ),
                ]
            )
            self.agent

            logger.info("DeepAgent 创建成功")

        except Exception as e:
            logger.error(f"DeepAgent 创建失败: {e}")
            raise

    def run_analysis(self, question: str, user_id: str = "default") -> Dict[str, Any]:
        """运行数据分析

        Args:
            question: 用户的数据分析问题
            user_id: 用户ID，用于权限控制和日志追踪

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
            from langfuse.langchain import CallbackHandler

            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
            os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
            os.environ["LANGFUSE_HOST"] = settings.langfuse_host
            _langfuse_client = get_client()
            _langfuse_handler = CallbackHandler()

            # 创建运行时上下文
            analysis_context = DataAnalysisContext(
                session_id=self.session_id,
                output_dir=str(self.output_dir),
                code_execution_timeout=self._config["code_execution_timeout"],
                user_id=user_id
            )

            with _langfuse_client.start_as_current_span(name="deep_agent"):
                with propagate_attributes(user_id=user_id, session_id=self.session_id):
                    result = self.agent.invoke(
                        {"messages": [{"role": "user", "content": question}]},
                        context=analysis_context,
                        config={"callbacks":[_langfuse_handler]}
                    )

            for i, message in enumerate(result['messages']):
                if isinstance(message, AIMessage):
                    logger.info(f"第 {i+1} 条 AI 消息:")
                    logger.info(message.content)
                    logger.info("-" * 50)

            # 生成最终报告（样式注入 + 归一化）
            self._inject_styles_and_generate_final_report()

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
    
    def _inject_styles_and_generate_final_report(self) -> None:
        """注入样式并生成最终的 report.html (包含归一化逻辑)"""
        try:
            content_path = self.output_dir / "report_content.html"
            if not content_path.exists():
                logger.warning(f"未找到报告内容文件: {content_path}")
                return

            # 读取原始内容
            raw_html = content_path.read_text(encoding="utf-8")
            
            # 使用 BeautifulSoup 进行归一化处理
            soup = BeautifulSoup(raw_html, "html.parser")

            # 1. 标题类名注入
            for h1 in soup.find_all("h1"):
                h1['class'] = h1.get('class', []) + ['report-title']
            for h2 in soup.find_all("h2"):
                h2['class'] = h2.get('class', []) + ['section-title']
            for h3 in soup.find_all("h3"):
                h3['class'] = h3.get('class', []) + ['subsection-title']
            for h4 in soup.find_all("h4"):
                h4['class'] = h4.get('class', []) + ['subsection-title']

            # 2. 正文类名注入
            for p in soup.find_all("p"):
                # 如果 p 是 img 的直接容器，不添加 content-text
                if not p.find("img"):
                    p['class'] = p.get('class', []) + ['content-text']
            
            # 3. 列表类名注入
            for ul in soup.find_all(["ul", "ol"]):
                ul['class'] = ul.get('class', []) + ['content-list']

            # 4. 表格处理 (添加类名 + 外部包裹 div)
            for table in soup.find_all("table"):
                table['class'] = table.get('class', []) + ['data-table']
                # 检查是否已经被 wrap (防止重复运行)
                if table.parent and "table-wrapper" in table.parent.get("class", []):
                    continue
                # 创建 wrapper
                wrapper = soup.new_tag("div", attrs={"class": "table-wrapper"})
                table.wrap(wrapper)

            # 5. 图片处理 (添加类名 + 外部包裹 div + 图注)
            for img in soup.find_all("img"):
                img['class'] = img.get('class', []) + ['chart-img']
                
                # 检查父级是否已经是 chart-wrapper
                parent = img.parent
                if parent and "chart-wrapper" in parent.get("class", []):
                    # 已经处理过，可能只需要检查 caption
                    continue
                
                # 如果父级是 p 标签且只包含这个 img，可以将 p 转换为 div.chart-wrapper
                if parent.name == 'p' and len(parent.contents) == 1:
                    parent.name = 'div'
                    parent['class'] = ['chart-wrapper']
                    # 添加 caption
                    if img.get('alt'):
                        caption = soup.new_tag("p", attrs={"class": "chart-caption"})
                        caption.string = img.get('alt')
                        parent.append(caption)
                else:
                    # 创建新的 wrapper
                    wrapper = soup.new_tag("div", attrs={"class": "chart-wrapper"})
                    img.wrap(wrapper)
                    # 添加 caption
                    if img.get('alt'):
                        caption = soup.new_tag("p", attrs={"class": "chart-caption"})
                        caption.string = img.get('alt')
                        wrapper.append(caption)

            # 获取处理后的 body 内容
            # 如果 raw_html 本身包含了 body，则取 body 内部，否则直接取 soup
            body_content = soup.body.encode_contents().decode('utf-8') if soup.body else soup.encode_contents().decode('utf-8')

            # 随机选择主题
            theme_dir = Path("backend/assets/themes")
            if not theme_dir.exists(): # fallback if running from wrong pwd?
                 theme_dir = Path("/home/kyynor/code/taosha_workspace/taosha_analyse_platform/backend/assets/themes")
            
            themes = list(theme_dir.glob("*.css"))
            if themes:
                selected_theme = random.choice(themes)
                css_content = selected_theme.read_text(encoding="utf-8")
                theme_name = selected_theme.stem
            else:
                css_content = ""
                theme_name = "default"
                logger.warning("未找到 CSS 主题文件，将生成无样式报告")

            # 构建最终 HTML
            final_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据分析报告</title>
    <style>
    {css_content}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="report-header">
            <h1 class="report-title">数据分析报告</h1>
            <p class="report-meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 主题: {theme_name}</p>
        </div>
        {body_content}
    </div>
</body>
</html>
"""
            # 写入 report.html
            report_path = self.output_dir / "report.html"
            report_path.write_text(final_html, encoding="utf-8")
            logger.info(f"已生成最终报告: {report_path} (主题: {theme_name})")

        except Exception as e:
            logger.error(f"生成最终报告失败: {e}", exc_info=True)

    async def run_analysis_stream(self, question: str, user_id: str = "default"):
        """流式运行数据分析

        Args:
            question: 用户的数据分析问题
            user_id: 用户ID，用于权限控制和日志追踪

        Yields:
            分析过程中的事件
        """
        if not self.agent:
            self.create_agent()

        logger.info(f"开始流式分析: {question[:100]}...")
        llm_output_chunks = []

        # 创建运行时上下文
        analysis_context = DataAnalysisContext(
            session_id=self.session_id,
            output_dir=str(self.output_dir),
            code_execution_timeout=self._config["code_execution_timeout"],
            user_id=user_id
        )

        try:
            async for event in self.agent.astream_events(
                {"messages": [{"role": "user", "content": question}]},
                context=analysis_context  # ✅ 传递上下文
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
            
            # 生成最终报告（样式注入 + 归一化）
            self._inject_styles_and_generate_final_report()

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
create_deep_analyse_service = create_data_analyser_agent