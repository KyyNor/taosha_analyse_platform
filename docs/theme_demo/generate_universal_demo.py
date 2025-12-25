import os
import json
from datetime import datetime

THEMES_DIR = "../../backend/assets/themes"
OUTPUT_DIR = "."
SAMPLE_CONTENT_FILE = "sample_content.html"

def generate_universal_demo():
    # Read sample content
    with open(SAMPLE_CONTENT_FILE, "r", encoding="utf-8") as f:
        content_html = f.read()

    # Read all themes into a dictionary
    themes = {}
    for theme_file in os.listdir(THEMES_DIR):
        if not theme_file.endswith(".css"):
            continue
        theme_name = theme_file.replace(".css", "")
        theme_path = os.path.join(THEMES_DIR, theme_file)
        with open(theme_path, "r", encoding="utf-8") as f:
            themes[theme_name] = f.read()

    # Generate HTML with JS switcher
    themes_json = json.dumps(themes)
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据分析报告 - 样式通用演示</title>
    <style id="dynamic-style">
        /* Default Style Placeholder */
    </style>
    <style>
        /* UI Control Panel Style (Fixed) */
        #ui-control-panel {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.8);
            padding: 15px;
            border-radius: 8px;
            z-index: 9999;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            font-family: sans-serif;
            color: white;
        }}
        #ui-control-panel h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            text-align: center;
        }}
        .theme-btn {{
            display: block;
            width: 100%;
            padding: 8px 12px;
            margin-bottom: 8px;
            background: #444;
            color: white;
            border: 1px solid #666;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.2s;
        }}
        .theme-btn:hover {{
            background: #666;
        }}
        .theme-btn.active {{
            background: #3b82f6;
            border-color: #3b82f6;
        }}
    </style>
</head>
<body>

    <!-- Control Panel -->
    <div id="ui-control-panel">
        <h3>切换主题样式</h3>
        <button class="theme-btn" onclick="switchTheme('theme_corporate_blue')">稳重蓝 (Corporate)</button>
        <button class="theme-btn" onclick="switchTheme('theme_premium_gold')">雅致金 (Premium)</button>
        <button class="theme-btn" onclick="switchTheme('theme_clean_light')">简约白 (Clean)</button>
        <button class="theme-btn" onclick="switchTheme('theme_tech_dark')">科技黑 (Tech)</button>
    </div>

    <!-- Report Container -->
    <div class="report-container">
        <div class="report-header">
            <h1 class="report-title">数据分析报告示例</h1>
            <p class="report-meta" id="meta-text">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        {content_html}
    </div>

    <script>
        // Embedded Themes
        const themes = {themes_json};

        function switchTheme(themeName) {{
            const styleTag = document.getElementById('dynamic-style');
            if (themes[themeName]) {{
                styleTag.textContent = themes[themeName];
                
                // Update Meta Text
                document.getElementById('meta-text').innerText = "生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 当前主题: " + themeName;

                // Update Buttons
                document.querySelectorAll('.theme-btn').forEach(btn => btn.classList.remove('active'));
                const activeBtn = document.querySelector(`button[onclick="switchTheme('${{themeName}}')"]`);
                if(activeBtn) activeBtn.classList.add('active');
            }}
        }}

        // Initialize with default
        switchTheme('theme_corporate_blue');
    </script>
</body>
</html>
"""
    output_file = os.path.join(OUTPUT_DIR, "index.html")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated {output_file}")

if __name__ == "__main__":
    generate_universal_demo()
