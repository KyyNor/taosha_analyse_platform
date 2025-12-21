# DeepAgents 工具体系优化计划

## 一、当前工具体系概览

### 标准工具目录 (`backend/services/agents/tools/`)

| 工具文件 | 工具函数 | 功能描述 | 状态 |
|---------|---------|---------|------|
| sql_query_tool.py | `sql_query` | 执行SQL查询 | ✅ 可用 |
| sql_query_tool.py | `get_table_schema` | 获取表结构 | ✅ 可用 |
| sql_query_tool.py | `list_tables` | 列出所有表 | ✅ 可用 |
| code_execution_tool.py | `execute_code` | Docker沙箱执行Python | ✅ 可用 |
| chart_tool.py | `create_chart` | 创建图表JSON配置 | ✅ 可用 |
| chart_tool.py | `create_chart_html` | 生成离线HTML图表(Bokeh) | ✅ 可用 |
| comparison_tool.py | `create_comparison` | 双主体对比分析 | ✅ 可用 |
| metrics_tool.py | `get_metrics` | 获取指标数据 | ✅ 可用 |
| qdrant_vector_store_tool.py | `search_knowledge_base` | 知识库向量检索 | ✅ 可用 |
| common_tools.py | `get_date_range` | 获取日期范围 | ✅ 可用 |
| common_tools.py | `get_hotboard` | 获取平台热榜 | ✅ 可用 |
| weather_tool.py | `get_weather` | 获取天气信息 | ✅ 可用 |
| fine_report_tools.py | `get_report_sample` | 获取FineReport报表样例 | ✅ 可用 |
| fine_report_tools.py | `batch_filter_report_and_get_data` | 批量获取报表数据 | ✅ 可用 |

### DeepAgents专用工具 (`backend/services/agents/deepagents/tools/`)

| 工具文件 | 工具函数 | 功能描述 | 使用者 |
|---------|---------|---------|-------|
| history_analysis_tool.py | `get_analysis_history` | 获取历史分析记录 | QuestionProposerAgent |
| history_analysis_tool.py | `search_analysis_history` | 搜索历史分析 | QuestionProposerAgent |
| session_reader_tool.py | `read_session_info` | 读取会话基本信息 | ScorerAgent |
| session_reader_tool.py | `read_session_report` | 读取分析报告 | ScorerAgent |
| session_reader_tool.py | `read_session_llm_output` | 读取LLM完整输出 | ScorerAgent |

---

## 二、DataAnalyserAgent 当前工具配置

```python
# data_analyser_agent.py 中的工具配置
tools = [
    # sql_query,                  # SQL 查询工具 (已注释)
    execute_code,               # Python 代码执行工具 (启用)
    # search_knowledge_base,      # 知识库检索工具 (已注释)
    # get_date_range,             # 日期范围工具 (已注释)
    # get_metrics,                # 指标数据工具 (已注释)
    get_weather,                # 天气工具 (启用，用于测试)
]
```

**问题**：当前启用的工具过少，无法支持完整的数据分析流程。

---

## 三、建议补充的工具

### 3.1 元数据查询工具 (高优先级)

**目的**：让Agent了解数据结构，才能写出正确的SQL

**文件**：`backend/services/agents/tools/metadata_tool.py`

```python
@tool
def get_available_tables() -> str:
    """获取可用的数据表清单

    返回所有可查询的表名及其简要描述。

    Returns:
        表名和描述的列表
    """
    pass

@tool
def get_table_metadata(table_name: str) -> str:
    """获取指定表的元数据信息

    包括表描述、所有列的名称、类型、描述等信息。

    Args:
        table_name: 表名

    Returns:
        表结构的详细描述
    """
    pass

@tool
def search_business_glossary(keyword: str) -> str:
    """搜索业务术语表

    查找业务术语的定义和相关说明。

    Args:
        keyword: 搜索关键词

    Returns:
        匹配的业务术语及其定义
    """
    pass
```

### 3.2 数据文件读取工具 (高优先级)

**目的**：DataAnalyserAgent的FilesystemBackend可以保存文件，但Agent需要显式工具来读取数据文件

**文件**：`backend/services/agents/deepagents/tools/file_reader_tool.py`

```python
@tool
def read_data_file(file_path: str, format: str = "auto") -> str:
    """读取数据文件

    支持CSV、JSON、Excel、Parquet等格式。

    Args:
        file_path: 文件路径（相对于工作目录）
        format: 文件格式，auto表示自动检测

    Returns:
        数据的JSON表示（前100行预览）
    """
    pass

@tool
def list_data_files(directory: str = "/data") -> str:
    """列出目录下的数据文件

    Args:
        directory: 目录路径

    Returns:
        文件列表及其基本信息
    """
    pass
```

### 3.3 报告生成工具 (中优先级)

**目的**：辅助生成结构化的分析报告

**文件**：`backend/services/agents/deepagents/tools/report_tool.py`

```python
@tool
def create_report_section(
    section_type: str,
    title: str,
    content: str,
    charts: list = None
) -> str:
    """创建报告段落

    Args:
        section_type: 段落类型 (summary/analysis/conclusion/recommendation)
        title: 段落标题
        content: 段落内容（Markdown格式）
        charts: 图表HTML列表

    Returns:
        生成的HTML段落
    """
    pass

@tool
def assemble_report(sections: list, title: str) -> str:
    """组装完整报告

    将多个段落组装成完整的HTML报告。

    Args:
        sections: 段落HTML列表
        title: 报告标题

    Returns:
        完整报告的HTML
    """
    pass
```

### 3.4 统计分析工具 (中优先级)

**目的**：提供常用统计分析的快捷方式，避免每次都写Python代码

**文件**：`backend/services/agents/tools/statistics_tool.py`

```python
@tool
def describe_dataframe(data_json: str) -> str:
    """计算描述性统计

    Args:
        data_json: 数据的JSON表示

    Returns:
        描述性统计结果（count, mean, std, min, max, percentiles）
    """
    pass

@tool
def calculate_correlation(data_json: str, columns: list = None) -> str:
    """计算相关性矩阵

    Args:
        data_json: 数据的JSON表示
        columns: 要分析的列名列表，None表示所有数值列

    Returns:
        相关性矩阵
    """
    pass

@tool
def detect_outliers(data_json: str, column: str, method: str = "iqr") -> str:
    """检测异常值

    Args:
        data_json: 数据的JSON表示
        column: 要检测的列名
        method: 检测方法 (iqr/zscore)

    Returns:
        异常值检测结果
    """
    pass
```

### 3.5 进度追踪工具 (低优先级)

**目的**：让Agent能够汇报分析进度，便于外部监控

**文件**：`backend/services/agents/deepagents/tools/progress_tool.py`

```python
@tool
def update_analysis_progress(
    step: str,
    status: str,
    message: str,
    progress_percent: int = None
) -> str:
    """更新分析进度

    Args:
        step: 当前步骤名称
        status: 状态 (started/running/completed/failed)
        message: 进度消息
        progress_percent: 进度百分比 (0-100)

    Returns:
        确认消息
    """
    pass
```

---

## 四、现有工具调整建议

### 4.1 sql_query 工具增强

**当前问题**：
- 缺少预览模式，可能返回过多数据
- get_table_schema 和 list_tables 未暴露给Agent

**建议修改**：

```python
@tool
def sql_query(
    sql: str,
    limit: int = 100,
    preview_only: bool = False,
    engine_type: str = "duckdb"
) -> str:
    """执行SQL查询

    Args:
        sql: SQL语句
        limit: 最大返回行数（默认100）
        preview_only: 是否只返回前5行预览
        engine_type: 查询引擎类型

    Returns:
        查询结果
    """
    pass
```

### 4.2 create_chart_html 工具优化

**当前问题**：
- 不支持保存到指定路径
- 不支持多图仪表盘

**建议增加**：

```python
@tool
def create_dashboard(
    charts: list,
    title: str = "",
    layout: str = "vertical"
) -> str:
    """创建多图仪表盘

    将多个图表组合成一个仪表盘页面。

    Args:
        charts: 图表配置列表，每个元素包含 chart_type, data, title 等
        title: 仪表盘标题
        layout: 布局方式 (vertical/grid-2/grid-3)

    Returns:
        仪表盘HTML代码
    """
    pass
```

### 4.3 execute_code 工具增强

**当前问题**：
- 难以传入已有的DataFrame数据
- 难以获取代码中的变量结果

**建议修改**：

```python
@tool
def execute_code(
    code: str,
    timeout: int = 30,
    session_id: str = None,
    input_data: dict = None,      # 新增：输入数据
    return_vars: list = None       # 新增：要返回的变量名
) -> str:
    """执行Python代码

    Args:
        code: Python代码
        timeout: 超时时间（秒）
        session_id: 会话ID（用于状态持久化）
        input_data: 输入数据字典，会作为变量注入代码环境
        return_vars: 要返回的变量名列表

    Returns:
        执行结果（包含stdout、返回变量等）
    """
    pass
```

---

## 五、DataAnalyserAgent 推荐工具配置

```python
# 建议的工具配置
tools = [
    # === 数据获取 ===
    sql_query,              # SQL查询
    get_available_tables,   # 获取表清单 (新增)
    get_table_metadata,     # 获取表结构 (新增)

    # === 代码执行 ===
    execute_code,           # Python代码执行

    # === 可视化 ===
    create_chart_html,      # 生成离线图表
    create_dashboard,       # 生成仪表盘 (新增)

    # === 知识辅助 ===
    search_knowledge_base,  # 知识库检索
    search_business_glossary,  # 业务术语查询 (新增)

    # === 时间辅助 ===
    get_date_range,         # 日期范围
]
```

---

## 六、实施计划

### 阶段 1：高优先级工具 (建议首先实现)

| 任务 | 文件 | 预计工作量 |
|-----|------|-----------|
| 创建元数据查询工具 | metadata_tool.py | 中 |
| 创建数据文件读取工具 | file_reader_tool.py | 中 |
| 暴露现有的 get_table_schema 给 Agent | sql_query_tool.py | 小 |

### 阶段 2：中优先级工具

| 任务 | 文件 | 预计工作量 |
|-----|------|-----------|
| 创建报告生成工具 | report_tool.py | 中 |
| 创建统计分析工具 | statistics_tool.py | 中 |
| 增加 create_dashboard 函数 | chart_tool.py | 中 |

### 阶段 3：优化现有工具

| 任务 | 文件 | 预计工作量 |
|-----|------|-----------|
| sql_query 增加预览模式 | sql_query_tool.py | 小 |
| execute_code 增加数据传入/返回 | code_execution_tool.py | 中 |

### 阶段 4：低优先级工具

| 任务 | 文件 | 预计工作量 |
|-----|------|-----------|
| 创建进度追踪工具 | progress_tool.py | 小 |

---

## 七、工具设计原则

1. **单一职责**：每个工具只做一件事
2. **错误友好**：返回清晰的错误信息，不抛出异常
3. **结果精简**：避免返回过多数据，使用预览/摘要
4. **参数合理**：提供合理的默认值，减少必填参数
5. **文档完整**：使用详细的 docstring 帮助 LLM 理解工具用途
6. **可观测**：使用 `@observe` 装饰器进行追踪

---

**文档创建日期**：2025-12-21
**最后更新**：2025-12-21
