import os
from datetime import datetime

THEMES_DIR = "../../backend/assets/themes"
OUTPUT_DIR = "."
SAMPLE_CONTENT_FILE = "sample_content.html"

def generate_demos():
    # Read sample content
    with open(SAMPLE_CONTENT_FILE, "r", encoding="utf-8") as f:
        content_html = f.read()

    # Iterate over themes
    for theme_file in os.listdir(THEMES_DIR):
        if not theme_file.endswith(".css"):
            continue

        theme_name = theme_file.replace(".css", "")
        theme_path = os.path.join(THEMES_DIR, theme_file)
        
        with open(theme_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        # Generate HTML
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>演示报告 - {theme_name}</title>
    <style>
    {css_content}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="report-header">
            <h1 class="report-title">数据分析报告示例</h1>
            <p class="report-meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 主题: {theme_name}</p>
        </div>
        {content_html}
    </div>
</body>
</html>
"""
        output_file = os.path.join(OUTPUT_DIR, f"demo_{theme_name}.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Generated {output_file}")

if __name__ == "__main__":
    generate_demos()
