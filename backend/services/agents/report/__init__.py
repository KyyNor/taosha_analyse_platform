"""
报告资源模块
存放 HTML 报告所需的静态资源

静态资源目录结构:
  static/
    charts.bundle.js    # 打包的图表组件 (由前端构建生成)
    react.min.js        # React 运行时 (可选)
    react-dom.min.js    # ReactDOM 运行时 (可选)
"""

from pathlib import Path

# 静态资源目录
STATIC_DIR = Path(__file__).parent / "static"

# 图表 JS 文件路径
CHARTS_BUNDLE_PATH = STATIC_DIR / "charts.bundle.js"


def get_charts_js() -> str:
    """获取图表 JS 内容

    Returns:
        图表 JS 文件内容，如果文件不存在则返回空字符串
    """
    if CHARTS_BUNDLE_PATH.exists():
        return CHARTS_BUNDLE_PATH.read_text(encoding="utf-8")
    return ""


def get_static_file(filename: str) -> str:
    """获取静态文件内容

    Args:
        filename: 文件名

    Returns:
        文件内容，如果文件不存在则返回空字符串
    """
    file_path = STATIC_DIR / filename
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return ""
