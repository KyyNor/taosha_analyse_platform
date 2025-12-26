#!/usr/bin/env python3
"""
主题列表更新脚本

用法：新增或删除 themes/ 目录下的 CSS 文件后，运行此脚本更新 theme_preview.html 中的主题列表。

运行方式：
    python3 update_theme_list.py

注意：修改 CSS 内容不需要运行此脚本，刷新浏览器即可。
"""

import re
from pathlib import Path
from typing import List, Dict

# 主题名称到中文标签的映射
THEME_LABELS = {
    "theme_clean_light": "简约白 (Clean Light)",
    "theme_corporate_blue": "稳重蓝 (Corporate Blue)",
    "theme_premium_gold": "黑金 (Premium Gold)",
    "theme_tech_dark": "科技黑 (Tech Dark)",
}


def get_theme_label(theme_name: str) -> str:
    """获取主题的显示标签"""
    if theme_name in THEME_LABELS:
        return THEME_LABELS[theme_name]
    # 未知主题：将下划线转为空格，首字母大写
    return theme_name.replace("_", " ").replace("theme ", "").title()


def scan_themes(themes_dir: Path) -> List[Dict]:
    """扫描主题目录，返回主题列表"""
    themes = []
    for css_file in sorted(themes_dir.glob("*.css")):
        theme_name = css_file.stem  # 文件名（不含扩展名）
        themes.append({
            "name": theme_name,
            "label": get_theme_label(theme_name)
        })
    return themes


def generate_themes_js(themes: List[Dict]) -> str:
    """生成 JavaScript 主题数组代码"""
    lines = ["        const themes = ["]
    for i, theme in enumerate(themes):
        comma = "," if i < len(themes) - 1 else ""
        lines.append(f'            {{ name: "{theme["name"]}", label: "{theme["label"]}" }}{comma}')
    lines.append("        ];")
    return "\n".join(lines)


def update_html(html_path: Path, themes_js: str) -> bool:
    """更新 HTML 文件中的主题列表"""
    content = html_path.read_text(encoding="utf-8")

    # 匹配主题数组区域（从注释标记到数组结束）
    pattern = r"(// =+\n        // 主题列表.*?\n        // =+\n)        const themes = \[.*?\];$"
    replacement = r"\1" + themes_js

    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

    if count == 0:
        print("警告：未找到主题列表区域，请检查 HTML 文件格式")
        return False

    html_path.write_text(new_content, encoding="utf-8")
    return True


def main():
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    themes_dir = script_dir / "themes"
    html_path = script_dir / "theme_preview.html"

    # 检查目录和文件
    if not themes_dir.exists():
        print(f"错误：主题目录不存在: {themes_dir}")
        return 1

    if not html_path.exists():
        print(f"错误：HTML 文件不存在: {html_path}")
        return 1

    # 扫描主题
    themes = scan_themes(themes_dir)
    if not themes:
        print("警告：未找到任何 CSS 主题文件")
        return 1

    print(f"发现 {len(themes)} 个主题:")
    for theme in themes:
        print(f"  - {theme['name']}: {theme['label']}")

    # 生成 JavaScript 代码
    themes_js = generate_themes_js(themes)

    # 更新 HTML
    if update_html(html_path, themes_js):
        print(f"\n已更新: {html_path}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())
