"""
DeepAgents 数据分析智能体服务 (多智能体版本)
基于 LangChain DeepAgents 框架构建的多智能体数据分析系统
采用 Supervisor + Subagents 架构，提升性能和指令遵循能力

架构设计：
- 主Agent (Coordinator): 任务规划和协调
- SubAgent 1 (sql_expert): SQL查询专家
- SubAgent 2 (data_analyst): 数据分析专家
- SubAgent 3 (viz_expert): 可视化专家
- SubAgent 4 (report_writer): 报告生成专家

版本: 2.0 (Multi-Agent)
创建日期: 2025-12-29
"""

import uuid
import random
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from bs4 import BeautifulSoup

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend, CompositeBackend, StateBackend
from langchain.agents.middleware import ToolRetryMiddleware, ShellToolMiddleware, FilesystemFileSearchMiddleware, ModelCallLimitMiddleware
from services.agents.deepagents.custom_docker_execution_policy import CustomDockerExecutionPolicy
from langchain_core.messages import AIMessage

from services.llm_service.base_llm_service import BaseLLMService
from services.agents.tools.sql_query_tool import sql_query
from services.agents.tools.qdrant_vector_store_tool import search_knowledge_base
from utils.logger import logger
from services.agents.models.deep_agent_context import DataAnalysisContext

# 提示词模板名称常量
PROMPT_TEMPLATE_COORDINATOR = "deepagents_coordinator_system_prompt"
PROMPT_TEMPLATE_SQL_EXPERT = "deepagents_sql_expert_prompt"
PROMPT_TEMPLATE_DATA_ANALYST = "deepagents_data_analyst_prompt"
PROMPT_TEMPLATE_VIZ_EXPERT = "deepagents_viz_expert_prompt"
PROMPT_TEMPLATE_REPORT_WRITER = "deepagents_report_writer_prompt"
PROMPT_TEMPLATE_SHELL_TOOL = "deepagents_shell_tool_description"

# ============================================================================
# SubAgent 系统提示词 (默认值，当数据库中不存在时使用)
# ============================================================================

DEFAULT_SQL_EXPERT_PROMPT = """你是SQL查询专家，擅长编写高效的SQL查询并预处理数据。

## 核心职责
1. 根据分析需求编写SQL查询
2. 确保查询包含时间过滤条件（ETL_DATE或CDATE），除非查询维表hxb_dh_data_dim
3. 对于大数据集，先用LIMIT预览结构，确认无误后再执行完整查询
4. 将查询结果保存为CSV文件到 /analysis/ 目录
5. 返回简洁的数据摘要（不要返回全部数据内容）

## 返回格式
请按照以下格式返回结果摘要：

```
查询完成：
- 记录数：X条
- 时间范围：YYYY-MM-DD 至 YYYY-MM-DD
- 字段列表：field1(说明), field2(说明), ...
- 数据质量说明：[如：无缺失值、发现3个异常高值等]
- 文件路径：/analysis/xxx.csv
```

## 注意事项
- **禁止**返回全部数据内容到对话，只返回摘要
- 金额字段大于10000时，在说明中建议使用"万"或"亿"单位
- 标注数据中的异常值和缺失值
- SQL查询优先考虑性能（合理使用索引、避免全表扫描）
- 如果数据量超过10万条，建议在摘要中说明采样策略
"""

DEFAULT_DATA_ANALYST_PROMPT = """你是数据分析专家，擅长统计分析和业务洞察提取。

## 核心职责
1. 读取CSV数据文件（通常由sql_expert提供）
2. 使用pandas进行描述性统计分析
3. 识别趋势、异常、相关性、模式
4. 提供业务解释和可行建议
5. 生成结构化的分析结果JSON文件

## 返回格式
请按照以下格式返回分析摘要：

```
分析完成：

核心发现：
1. [洞察1 - 用一句话描述关键发现]
2. [洞察2]
3. [洞察3]
...

统计指标：
- [指标名]: [值及解释]
- [指标名]: [值及解释]
...

建议：
- [建议1 - 基于数据的可行建议]
- [建议2]
...

详细结果文件：/analysis/analysis_results.json
```

## 注意事项
- 基于**全量数据**分析，避免采样偏差（除非数据量过大）
- 金额使用"万"或"亿"单位，提升可读性
- 提供置信区间或统计显著性（如适用）
- 洞察必须**客观**，基于数据，禁止臆造
- 如果发现数据质量问题，明确说明并给出处理建议
"""

DEFAULT_VIZ_EXPERT_PROMPT = """你是数据可视化专家，擅长用matplotlib/seaborn生成专业图表。

## 核心职责
1. 读取分析结果（通常由data_analyst提供）
2. 选择最佳图表类型：
   - 趋势分析 → 折线图
   - 占比分布 → 饼图或环形图
   - 对比分析 → 柱状图或条形图
   - 相关性 → 散点图或热力图
3. 编写Python可视化代码
4. **必须**配置中文字体：`plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']`
5. 保存图片到 /analysis/tmp/ 目录，DPI设置为100

## 返回格式
请按照以下格式返回可视化摘要：

```
可视化完成：

生成图表：
1. [图表标题] ([文件名])
   - 类型：[折线图/饼图/柱状图等]
   - 说明：[图表含义，这将用于HTML img标签的alt属性]
   - 路径：/analysis/tmp/xxx.png

2. [图表标题] ([文件名])
   ...

设计说明：
- [配色理由 - 如：使用蓝色系表示销售数据，体现专业感]
- [布局选择 - 如：横向布局便于对比]
```

## 注意事项
- **必须**配置中文字体，否则会显示乱码：
  ```python
  plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
  plt.rcParams['axes.unicode_minus'] = False
  ```
- 图片DPI设置为100（`plt.savefig(..., dpi=100)`），适合web显示
- 文件名使用**英文**，避免路径问题（如：sales_trend.png）
- 图表标题、坐标轴标签使用**中文**
- 如果数据点过多（>100个），考虑聚合或采样，避免图表过于拥挤
- 添加图例、网格线、数据标签，提升可读性
"""

DEFAULT_REPORT_WRITER_PROMPT = """你是技术报告撰写专家，擅长生成结构化的HTML报告。

## 核心职责
1. 整合以下内容：
   - SQL查询摘要（数据概览）
   - 数据分析结果（统计指标、核心发现）
   - 可视化图表路径
2. 编写专业的数据分析报告
3. 使用语义化HTML标签
4. 生成 /analysis/report_content.html

## HTML结构要求
使用以下语义化标签：
- `<h1>`: 主标题（分析主题）
- `<h2>`: 章节标题（数据概览、趋势分析、结论等）
- `<h3>`: 子标题
- `<p>`: 正文段落
- `<blockquote>`: **关键洞察**和核心结论（高亮显示）
- `<table>`: 数据表格（无需添加class，系统会自动处理样式）
- `<ul>`/`<ol>` + `<li>`: 列表
- `<img>`: 图表（src使用相对路径，**必须**填写alt属性作为图注）
- `<strong>`/`<b>`: 关键数据加粗

## 报告结构模板
```html
<h1>[分析主题]</h1>

<blockquote>
执行摘要：用3-5句话概括核心发现和结论
</blockquote>

<h2>一、数据概览</h2>
<p>数据来源、时间范围、记录数等基本信息</p>
<table>
  <thead>...</thead>
  <tbody>...</tbody>
</table>

<h2>二、[分析章节标题]</h2>
<p>详细分析文字...</p>
<img src="tmp/chart1.png" alt="图表说明">
<p>图表解读...</p>

<blockquote>
关键洞察：本章节的核心发现
</blockquote>

<h2>三、结论与建议</h2>
<ul>
  <li><strong>结论1</strong>: 说明</li>
  <li><strong>结论2</strong>: 说明</li>
</ul>

<blockquote>
总结：最终结论
</blockquote>
```

## 注意事项
- **不要**包含 `<html>`, `<head>`, `<body>`, `<style>` 等标签
- 只生成内容部分的语义化HTML（系统会自动包装完整HTML结构）
- 图片路径使用**相对路径**（如 `tmp/sales_trend.png`，不要加 `/analysis/`）
- 表格无需添加CSS类，系统会自动处理样式
- 关键数据**必须**用 `<strong>` 加粗
- `<blockquote>` 用于突出**关键洞察**，每个大章节至少一个
- 确保逻辑严密，避免口语化表达
"""

DEFAULT_COORDINATOR_PROMPT = """你是淘沙分析平台的数据分析协调专家。你的任务是理解用户的分析需求，制定分析计划，并协调专门的子智能体完成分析任务。

## 工作流程
1. **理解需求**：仔细理解用户的分析问题，必要时向用户澄清
2. **制定计划**：使用 write_todos 创建分析计划（通常包括：查询→分析→可视化→报告）
3. **协调执行**：按顺序调用专门的子智能体，传递清晰的指令
4. **整合结果**：汇总各子智能体的输出，回答用户问题

## 可用的子智能体
通过 `task` 工具调用以下子智能体：

### 1. sql_expert - SQL查询专家
- **擅长**：编写SQL查询、数据预处理、数据质量检查
- **返回**：数据摘要（记录数、字段、文件路径）
- **何时使用**：需要从数据库获取数据时
- **调用示例**：
  ```
  task(
      subagent="sql_expert",
      instructions="查询最近30天的销售数据，按日期和产品分组，包含销售额和数量字段。确保包含时间过滤条件。"
  )
  ```

### 2. data_analyst - 数据分析专家
- **擅长**：统计分析、趋势识别、洞察提取、业务建议
- **返回**：统计指标、核心发现、业务建议
- **何时使用**：需要分析数据、发现规律时
- **调用示例**：
  ```
  task(
      subagent="data_analyst",
      instructions="分析 /analysis/sales_data.csv 中的销售趋势，识别增长模式，提供业务建议。"
  )
  ```

### 3. viz_expert - 可视化专家
- **擅长**：生成专业图表（matplotlib/seaborn）、选择合适图表类型
- **返回**：图片文件路径、图表说明
- **何时使用**：需要将分析结果可视化时
- **调用示例**：
  ```
  task(
      subagent="viz_expert",
      instructions="根据 /analysis/analysis_results.json 生成销售趋势折线图和产品占比饼图。"
  )
  ```

### 4. report_writer - 报告生成专家
- **擅长**：编写结构化HTML报告、整合图表和分析结果
- **返回**：报告文件路径、完成确认
- **何时使用**：完成所有分析，需要生成最终报告时
- **调用示例**：
  ```
  task(
      subagent="report_writer",
      instructions="整合数据摘要、分析结果和图表，生成完整的销售趋势分析报告。"
  )
  ```

## 协调原则
1. **顺序执行**：严格按照 查询→分析→可视化→报告 的顺序调用（除非特殊情况）
2. **清晰指令**：给子智能体明确、具体的任务描述，包含：
   - 输入数据（文件路径或数据描述）
   - 期望输出（具体要求）
   - 特殊约束（如时间范围、数据筛选条件）
3. **结果传递**：理解每个子智能体返回的摘要，将关键信息（如文件路径）传递给下一个子智能体
4. **用户交互**：在关键节点向用户确认或澄清需求

## 示例对话

**用户**: "分析最近一个月的销售趋势"

**你的思考过程**（内部）:
1. 这是一个销售趋势分析任务
2. 需要调用4个子智能体：sql_expert → data_analyst → viz_expert → report_writer
3. 先制定待办清单

**你的回复**:
"好的，我将帮您分析最近一个月的销售趋势。让我制定分析计划..."

[调用 write_todos 创建计划：
1. 查询最近30天的销售数据
2. 分析销售趋势和模式
3. 生成趋势可视化图表
4. 编写完整分析报告
]

"计划已制定。现在开始第一步：查询销售数据..."

[调用 task(subagent="sql_expert", instructions="查询最近30天的销售数据...")]

[等待sql_expert返回]

"数据查询完成，共获取1250条记录。现在进行趋势分析..."

[调用 task(subagent="data_analyst", instructions="分析 /analysis/sales_data.csv...")]

[等待data_analyst返回]

"分析完成，发现销售额呈上升趋势。现在生成可视化图表..."

[调用 task(subagent="viz_expert", instructions="...")]

[最后调用 report_writer]

"分析报告已生成完成！"

## 注意事项
- 你**不直接执行**SQL查询或编写代码，而是**协调**子智能体
- 子智能体返回的是**摘要**，不是全部数据（避免上下文膨胀）
- 保持对话简洁，专注于协调而非技术细节
- 如果子智能体执行失败，分析原因并重试（或调整指令）
- 在所有子智能体完成后，向用户总结核心发现
"""

DEFAULT_SHELL_TOOL_DESCRIPTION = """
在持久会话中执行 shell 命令。运行命令前，请确认当前工作目录正确（例如用 ls 或 pwd 检查），并确保所有父目录已存在。
优先使用绝对路径；若路径包含空格，请用引号包裹，例如 cd "/path/with spaces"。多个命令请用 && 或 ; 串联，不要使用换行。
除非确实需要，否则避免频繁使用 cd,以保持会话稳定。
输出过大时可能被截断，长时间运行的命令在达到配置的超时时间后将被强制终止。
本系统中包含Python3.11环境,并包含科学计算相关的库,如numpy、pandas、matplotlib等,你可以使用pip list来查看环境清单。
系统已安装中文字体(WenQuanYi Micro Hei、WenQuanYi Zen Hei)。
"""

# ============================================================================
# 多智能体数据分析服务
# ============================================================================

class DataAnalyserAgentMulti:
    """DeepAgents 数据分析智能体（多智能体版本）"""

    def __init__(
        self,
        session_id: Optional[str] = None,
        output_base_dir: str = "./analysis_output",
    ):
        """初始化数据分析智能体（多智能体版本）

        Args:
            session_id: 会话ID，用于文件隔离。如果不传入则自动生成
            output_base_dir: 输出基础目录
        """
        # 配置
        self._config = {
            "output_base_dir": output_base_dir,
            "code_execution_enabled": True,
            "code_execution_timeout": 30,
            "max_iterations": 150,  # 增加迭代次数（因为有SubAgent调用）
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

        logger.info(f"DataAnalyserAgentMulti 初始化完成，会话ID: {self.session_id}")
        logger.info(f"输出目录: {self.output_dir}")
        logger.info("架构：Supervisor + 4个SubAgents (sql_expert, data_analyst, viz_expert, report_writer)")

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
        """创建 DeepAgent 实例（多智能体版本）"""
        try:
            # 从数据库加载各Agent的提示词
            coordinator_prompt = self._get_prompt_template(
                PROMPT_TEMPLATE_COORDINATOR,
                DEFAULT_COORDINATOR_PROMPT
            )
            sql_expert_prompt = self._get_prompt_template(
                PROMPT_TEMPLATE_SQL_EXPERT,
                DEFAULT_SQL_EXPERT_PROMPT
            )
            data_analyst_prompt = self._get_prompt_template(
                PROMPT_TEMPLATE_DATA_ANALYST,
                DEFAULT_DATA_ANALYST_PROMPT
            )
            viz_expert_prompt = self._get_prompt_template(
                PROMPT_TEMPLATE_VIZ_EXPERT,
                DEFAULT_VIZ_EXPERT_PROMPT
            )
            report_writer_prompt = self._get_prompt_template(
                PROMPT_TEMPLATE_REPORT_WRITER,
                DEFAULT_REPORT_WRITER_PROMPT
            )
            shell_tool_description = self._get_prompt_template(
                PROMPT_TEMPLATE_SHELL_TOOL,
                DEFAULT_SHELL_TOOL_DESCRIPTION
            )

            # 准备主Agent工具（只保留协调相关的工具）
            tools = [
                search_knowledge_base,  # 知识库检索
            ]

            # 准备SubAgent配置
            subagents_config = {
                "sql_expert": {
                    "tools": [sql_query],
                    "system_prompt": sql_expert_prompt,
                },
                "data_analyst": {
                    "tools": [],  # 使用Shell工具（自动注入）
                    "system_prompt": data_analyst_prompt,
                },
                "viz_expert": {
                    "tools": [],  # 使用Shell工具（自动注入）
                    "system_prompt": viz_expert_prompt,
                },
                "report_writer": {
                    "tools": [],  # 使用Filesystem工具（自动注入）
                    "system_prompt": report_writer_prompt,
                },
            }

            # 创建Composite Backend（主Agent和SubAgent共享）
            composite_backend = lambda rt: CompositeBackend(
                default=StateBackend(rt),
                routes={
                    "/analysis/": FilesystemBackend(
                        root_dir=str(self.output_dir.resolve()),
                        virtual_mode=True
                    )
                }
            )

            # 创建DeepAgent（多智能体版本）
            # deepagents 自动包含: TodoListMiddleware, FilesystemMiddleware, SubAgentMiddleware, SummarizationMiddleware
            self.agent = create_deep_agent(
                model=self.llm_service.client,
                tools=tools,  # 主Agent工具
                system_prompt=coordinator_prompt,
                context_schema=DataAnalysisContext,
                backend=composite_backend,
                middleware=[
                    ModelCallLimitMiddleware(
                        run_limit=150,  # 增加限制（因为有SubAgent调用）
                        exit_behavior='end'
                    ),
                    ToolRetryMiddleware(
                        max_retries=2,
                        on_failure="continue"
                    ),
                    ShellToolMiddleware(
                        tool_description=shell_tool_description,
                        workspace_root=self.output_dir.resolve(),
                        execution_policy=CustomDockerExecutionPolicy(
                            image="taosha-sandbox:latest",
                            user='root',
                            cpus=self._config["shell_tool_docker_cpu_size"],
                            memory_bytes=self._config["shell_tool_docker_mem_size"] * 1024 * 1024 * 1024,
                            network_enabled=False,
                            target_workspace='/analysis',
                        ),
                    ),
                    FilesystemFileSearchMiddleware(
                        root_path=str(self.output_dir)
                    ),
                ],
                subagents=subagents_config,  # ✅ 关键：配置SubAgent
            )

            logger.info("DeepAgent（多智能体版本）创建成功")
            logger.info(f"已配置 {len(subagents_config)} 个子智能体: {', '.join(subagents_config.keys())}")

        except Exception as e:
            logger.error(f"DeepAgent 创建失败: {e}")
            raise

    def run_analysis(self, question: str, user_id: str = "default") -> Dict[str, Any]:
        """运行数据分析（多智能体版本）

        Args:
            question: 用户的数据分析问题
            user_id: 用户ID，用于权限控制和日志追踪

        Returns:
            包含分析结果的字典
        """
        if not self.agent:
            self.create_agent()

        logger.info(f"开始分析（多智能体模式）: {question[:100]}...")
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

            with _langfuse_client.start_as_current_span(name="deep_agent_multi"):
                with propagate_attributes(
                    user_id=user_id,
                    session_id=self.session_id,
                    architecture="multi_agent"
                ):
                    result = self.agent.invoke(
                        {"messages": [{"role": "user", "content": question}]},
                        context=analysis_context,
                        config={"callbacks": [_langfuse_handler]}
                    )

            # 打印AI消息（调试用）
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

            logger.info(f"分析完成（多智能体模式），耗时: {duration:.2f}秒")

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
                "architecture": "multi_agent",
                "result": result,
            }

        except Exception as e:
            logger.error(f"分析执行失败: {e}")
            return {
                "success": False,
                "session_id": self.session_id,
                "question": question,
                "output_dir": str(self.output_dir),
                "architecture": "multi_agent",
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
                 theme_dir = Path("/data/taosha/taosha_analyse_platform/backend/assets/themes")

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
            <p class="report-meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 主题: {theme_name} | 架构: 多智能体 (Multi-Agent)</p>
        </div>
        {body_content}
    </div>
</body>
</html>
"""
            # 写入 report.html
            report_path = self.output_dir / "report.html"
            report_path.write_text(final_html, encoding="utf-8")
            logger.info(f"已生成最终报告（多智能体版本）: {report_path} (主题: {theme_name})")

        except Exception as e:
            logger.error(f"生成最终报告失败: {e}", exc_info=True)

    async def run_analysis_stream(self, question: str, user_id: str = "default"):
        """流式运行数据分析（多智能体版本）

        Args:
            question: 用户的数据分析问题
            user_id: 用户ID，用于权限控制和日志追踪

        Yields:
            分析过程中的事件
        """
        if not self.agent:
            self.create_agent()

        logger.info(f"开始流式分析（多智能体模式）: {question[:100]}...")
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
                context=analysis_context
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
                    "output_dir": str(self.output_dir),
                    "architecture": "multi_agent"
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
        logger.info(f"会话 {self.session_id} 资源已清理（多智能体版本）")


# 便捷函数：创建服务实例（多智能体版本）
def create_data_analyser_agent_multi(
    session_id: Optional[str] = None,
    output_base_dir: str = "./analysis_output"
) -> DataAnalyserAgentMulti:
    """创建数据分析智能体实例（多智能体版本）

    Args:
        session_id: 会话ID，用于文件隔离
        output_base_dir: 输出基础目录

    Returns:
        DataAnalyserAgentMulti 实例
    """
    agent = DataAnalyserAgentMulti(
        session_id=session_id,
        output_base_dir=output_base_dir
    )
    agent.create_agent()
    return agent
