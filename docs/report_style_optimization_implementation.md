# 数据分析报告样式优化实施文档

## 1. 概述
本方案旨在通过解耦“内容生成”与“视觉样式”，提升 AI 生成报告的美观度与专业性。核心思路是让 Agent 仅生成包含特定 HTML 结构和类名的内容片段，再由后端在后处理阶段随机注入预置的高质量 CSS 样式表，最终合成单文件 HTML 报告。

## 2. 详细实施步骤

### 2.1 阶段一：样式资源准备 (Asset Preparation)

需要创建 `backend/assets/themes/` 目录，并编写多套 CSS 主题文件。

#### 2.1.1 目录结构
```bash
backend/
└── assets/
    └── themes/
        ├── theme_corporate_blue.css   # 稳重蓝（默认/通用）
        ├── theme_premium_gold.css     # 黑金/雅致金（高端分析）
        ├── theme_clean_light.css      # 简约白（打印友好）
        └── theme_tech_dark.css        # 科技黑（大屏/深色模式）
```

#### 2.1.2 核心 CSS 类名定义 (Style Guide)
Agent 生成的 HTML 必须严格遵循以下类名结构：

*   `.report-container`: 报告主容器
*   `.report-header`: 报告头部（包含标题、生成时间等）
*   `.report-title`: 主标题 (`h1`)
*   `.report-meta`: 元数据区域
*   `.section-container`: 章节容器
*   `.section-title`: 章节标题 (`h2`)
*   `.content-text`: 正文段落 (`p`)
*   `.chart-wrapper`: 图表容器 (包含 `img` 和图注)
*   `.chart-img`: 图表图片 (`img`)
*   `.chart-caption`: 图表说明/图注
*   `.data-table`: 数据表格 (`table`)
*   `.insight-box`: 关键结论/洞察框
*   `.summary-card`: 摘要卡片

#### 2.1.3 样式文件示例 (theme_corporate_blue.css)
```css
/* 基础重置 */
body { font-family: "Microsoft YaHei", sans-serif; margin: 0; padding: 0; background-color: #f5f7fa; color: #333; }

/* 容器 */
.report-container { max-width: 1000px; margin: 40px auto; background: #fff; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); border-radius: 8px; }

/* 头部 */
.report-header { text-align: center; border-bottom: 2px solid #eef1f6; padding-bottom: 20px; margin-bottom: 30px; }
.report-title { color: #2c3e50; font-size: 28px; margin-bottom: 10px; }
.report-meta { color: #7f8c8d; font-size: 14px; }

/* 章节 */
.section-container { margin-bottom: 40px; }
.section-title { color: #2980b9; font-size: 22px; border-left: 4px solid #2980b9; padding-left: 12px; margin-bottom: 20px; }

/* 内容 */
.content-text { line-height: 1.8; color: #444; margin-bottom: 16px; text-align: justify; }

/* 摘要/结论框 */
.summary-card, .insight-box { background: #f0f7ff; border: 1px solid #d6eaf8; border-radius: 6px; padding: 20px; margin: 20px 0; }
.insight-box { border-left: 4px solid #3498db; }

/* 表格 */
.data-table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }
.data-table th { background-color: #f8f9fa; color: #2c3e50; padding: 12px; text-align: left; border-bottom: 2px solid #ddd; }
.data-table td { padding: 12px; border-bottom: 1px solid #eee; }

/* 图表 */
.chart-wrapper { text-align: center; margin: 30px 0; padding: 20px; background: #fafafa; border-radius: 8px; }
.chart-img { max-width: 100%; height: auto; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.chart-caption { margin-top: 10px; color: #666; font-size: 13px; font-style: italic; }
```

### 2.2 阶段二：后端逻辑改造 (Backend Logic Update)

需要修改 `backend/services/agents/deepagents/data_analyser_agent.py`。

#### 2.2.1 修改 Prompt
更新 `DATA_ANALYSIS_SYSTEM_PROMPT`，移除关于“自包含 HTML”的要求，改为要求生成“HTML 内容片段”。

**Prompt 变更点：**
*   **Old:** 生成的 report.html 必须是自包含的完整 HTML 文件...包含内联 CSS...
*   **New:**
    1.  生成的报告文件名必须为 `report_content.html`。
    2.  **不要** 包含 `<html>`, `<head>`, `<body>` 标签。仅生成报告的主体内容 (`div` 结构)。
    3.  **不要** 编写任何 CSS 样式 (`<style>` 或 `style="..."`)。
    4.  必须严格使用指定的 CSS 类名构建结构（提供类名列表）。

#### 2.2.2 样式注入逻辑
在 `DataAnalyserAgent` 类中新增 `_inject_styles_and_generate_final_report` 方法，并在 `run_analysis` 结束前调用。

**核心增强：HTML 标准化 (Report Normalizer)**
为了防止模型未能正确生成 CSS 类名，我们需要在注入样式前，使用 `BeautifulSoup` 对 HTML 内容进行“归一化”处理，强制添加标准类名。

**处理逻辑：**
1.  **Tag 映射**：
    *   `h1` -> 添加 class `report-title`
    *   `h2` -> 添加 class `section-title`
    *   `h3`, `h4` -> 添加 class `subsection-title`
    *   `p` -> 添加 class `content-text`
    *   `table` -> 添加 class `data-table` (并包裹在 `.table-wrapper` 中以支持滚动)
    *   `ul`, `ol` -> 添加 class `content-list`
2.  **图表增强**：
    *   查找所有 `img` 标签。
    *   检查其父元素是否已经是 `.chart-wrapper`。
    *   如果不是，将其包裹在 `<div class="chart-wrapper">` 中。
    *   尝试提取 `img` 的 `alt` 属性作为图注，插入 `<p class="chart-caption">{alt}</p>`。

**伪代码逻辑：**
1.  检查 `report_content.html` 是否存在。
2.  读取内容并使用 `BeautifulSoup` 解析。
3.  执行上述“归一化”逻辑，修改 DOM 树。
4.  列出 `backend/assets/themes/` 下的所有 `.css` 文件。
5.  随机选择一个 CSS 文件，读取内容。
6.  拼接最终 HTML：
    ```python
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
                <p class="report-meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            {soup.body.encode_contents() if soup.body else soup.encode_contents()}
        </div>
    </body>
    </html>
    """
    ```
7.  将 `final_html` 写入 `report.html`。

### 2.3 阶段三：验证 (Verification)

1.  运行 Agent 生成一份报告。
2.  检查 `report_content.html` 是否仅包含内容片段（无 CSS）。
3.  检查 `report.html` 是否包含 CSS 且渲染正常。
4.  多次运行，验证是否会随机切换不同样式。

## 3. 需新增/修改的文件清单

1.  `backend/assets/themes/theme_corporate_blue.css` (新增)
2.  `backend/assets/themes/theme_premium_gold.css` (新增)
3.  `backend/assets/themes/theme_clean_light.css` (新增)
4.  `backend/assets/themes/theme_tech_dark.css` (新增)
5.  `backend/services/agents/deepagents/data_analyser_agent.py` (修改)
