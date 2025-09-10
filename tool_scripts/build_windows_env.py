#!/usr/bin/env python3
"""
Windows环境Python依赖包打包脚本

功能：
1. 下载Python嵌入式版本
2. 安装项目依赖包 
3. 创建便携式Python环境包
4. 生成部署用的压缩包

使用方法：
python tool_scripts/build_windows_env.py
"""

import os
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
import sys

class WindowsEnvBuilder:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.dist_dir / "taosha_windows_env"
        self.python_version = "3.11.7"
        
    def clean_build_dir(self):
        """清理构建目录"""
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ 构建目录已清理: {self.build_dir}")
    
    def download_python_embed(self):
        """下载Python嵌入式版本"""
        embed_url = f"https://www.python.org/ftp/python/{self.python_version}/python-{self.python_version.replace('.', '')[:3]}-embed-amd64.zip"
        embed_file = self.build_dir / "python_embed.zip"
        
        print(f"📥 正在下载Python嵌入式版本: {self.python_version}")
        print(f"下载地址: {embed_url}")
        
        try:
            urllib.request.urlretrieve(embed_url, embed_file)
            print("✅ Python嵌入式版本下载完成")
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            print("请手动下载并放置到构建目录中")
            return False
            
        return embed_file
    
    def extract_python(self, embed_file):
        """解压Python嵌入式版本"""
        print("📦 正在解压Python嵌入式版本...")
        
        with zipfile.ZipFile(embed_file, 'r') as zip_ref:
            zip_ref.extractall(self.build_dir)
        
        # 配置python路径文件，启用site-packages
        pth_files = list(self.build_dir.glob("python*.._pth"))
        if pth_files:
            pth_file = pth_files[0]
            with pth_file.open("a", encoding="utf-8") as f:
                f.write("\nimport site\n")
            print(f"✅ 已配置Python路径文件: {pth_file.name}")
        
        # 删除下载的zip文件
        embed_file.unlink()
        print("✅ Python嵌入式版本解压完成")
        
    def install_pip(self):
        """安装pip"""
        print("🔧 正在安装pip...")
        
        # 下载get-pip.py
        get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
        get_pip_file = self.build_dir / "get-pip.py"
        
        try:
            urllib.request.urlretrieve(get_pip_url, get_pip_file)
            
            # 安装pip
            python_exe = self.build_dir / "python.exe"
            subprocess.run([str(python_exe), str(get_pip_file)], 
                         cwd=self.build_dir, check=True)
            
            # 删除get-pip.py
            get_pip_file.unlink()
            print("✅ pip安装完成")
            
        except Exception as e:
            print(f"❌ pip安装失败: {e}")
            return False
            
        return True
    
    def install_project_dependencies(self):
        """安装项目依赖"""
        print("📦 正在安装项目依赖...")
        
        requirements_file = self.project_root / "pyproject.toml"
        if not requirements_file.exists():
            print("❌ 未找到pyproject.toml文件")
            return False
        
        python_exe = self.build_dir / "python.exe"
        
        # 先安装uv
        try:
            subprocess.run([str(python_exe), "-m", "pip", "install", "uv"], 
                         cwd=self.project_root, check=True)
            print("✅ UV包管理器安装完成")
        except subprocess.CalledProcessError as e:
            print(f"❌ UV安装失败: {e}")
            return False
        
        # 使用uv导出requirements.txt
        try:
            subprocess.run([str(python_exe), "-m", "uv", "export", 
                          "--format", "requirements-txt", 
                          "--output", "requirements.txt"], 
                         cwd=self.project_root, check=True)
            print("✅ 依赖列表导出完成")
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖导出失败: {e}")
            return False
        
        # 安装所有依赖到嵌入式Python
        requirements_txt = self.project_root / "requirements.txt"
        if requirements_txt.exists():
            try:
                subprocess.run([str(python_exe), "-m", "pip", "install", 
                              "-r", str(requirements_txt), 
                              "--no-warn-script-location"], 
                             cwd=self.build_dir, check=True)
                print("✅ 项目依赖安装完成")
                
                # 删除临时requirements.txt
                requirements_txt.unlink()
                
            except subprocess.CalledProcessError as e:
                print(f"❌ 依赖安装失败: {e}")
                return False
        
        return True
    
    def create_startup_scripts(self):
        """创建启动脚本"""
        print("📝 正在创建启动脚本...")
        
        # Windows批处理启动脚本
        start_bat = self.build_dir / "start_python.bat"
        start_bat.write_text("""@echo off
echo ========================================
echo 淘沙分析平台 - Python环境
echo ========================================
echo Python版本: 3.11.7
echo 环境路径: %~dp0
echo ========================================
echo.
cd /d %~dp0
set PYTHONPATH=%~dp0;%PYTHONPATH%
cmd /k
""", encoding="gbk")
        
        # PowerShell启动脚本
        start_ps1 = self.build_dir / "start_python.ps1"
        start_ps1.write_text("""# 淘沙分析平台 - Python环境启动脚本
Write-Host "========================================" -ForegroundColor Green
Write-Host "淘沙分析平台 - Python环境" -ForegroundColor Green  
Write-Host "========================================" -ForegroundColor Green
Write-Host "Python版本: 3.11.7" -ForegroundColor Yellow
Write-Host "环境路径: $PSScriptRoot" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Set-Location $PSScriptRoot
$env:PYTHONPATH = "$PSScriptRoot;$env:PYTHONPATH"

# 启动PowerShell会话
Write-Host "Python环境已准备就绪，可以运行您的应用了！" -ForegroundColor Cyan
Write-Host "使用方法: .\\python.exe your_script.py" -ForegroundColor White
""", encoding="utf-8")
        
        print("✅ 启动脚本创建完成")
    
    def create_readme(self):
        """创建部署说明文档"""
        readme_content = f"""# 淘沙分析平台 - Windows Python环境包

## 环境信息
- **Python版本**: {self.python_version}
- **平台**: Windows 10/11 x64
- **打包时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 目录结构
```
taosha_windows_env/
├── python.exe              # Python解释器
├── python{self.python_version.replace('.', '')[:3]}.dll         # Python核心库
├── Lib/                    # Python标准库
├── Scripts/                # Python脚本
├── start_python.bat        # 批处理启动脚本
├── start_python.ps1        # PowerShell启动脚本
└── README.md              # 本文件
```

## 使用方法

### 1. 基本使用
```cmd
# 方式1：双击启动脚本
start_python.bat

# 方式2：命令行启动
python.exe --version

# 方式3：PowerShell启动  
powershell -ExecutionPolicy Bypass -File start_python.ps1
```

### 2. 运行项目
```cmd
# 将项目代码复制到此环境目录中，然后运行
python.exe path\\to\\your\\main.py

# 或者设置Python路径
set PYTHONPATH=path\\to\\your\\project;%PYTHONPATH%
python.exe -c "import sys; print(sys.path)"
```

### 3. 安装额外包 (如需要)
```cmd
python.exe -m pip install package_name
```

## 注意事项
1. 此环境包含项目所需的所有依赖包
2. 无需在目标机器安装Python或任何依赖
3. 可以直接复制到任何Windows机器使用  
4. 建议将项目代码放置在此环境目录中运行

## 技术支持
如有问题，请联系项目开发团队。
"""
        
        readme_file = self.build_dir / "README.md"
        readme_file.write_text(readme_content, encoding="utf-8")
        print("✅ 部署文档创建完成")
    
    def create_package(self):
        """创建最终压缩包"""
        print("📦 正在创建部署包...")
        
        package_name = f"taosha_windows_python_env_{self.python_version}.zip"
        package_path = self.dist_dir / package_name
        
        # 删除现有包
        if package_path.exists():
            package_path.unlink()
        
        # 创建zip包
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in self.build_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.build_dir)
                    zipf.write(file_path, arcname)
        
        # 计算包大小
        size_mb = package_path.stat().st_size / 1024 / 1024
        
        print(f"✅ 部署包创建完成!")
        print(f"📦 包名称: {package_name}")  
        print(f"📏 包大小: {size_mb:.1f} MB")
        print(f"📍 包路径: {package_path}")
        
        return package_path
    
    def build(self):
        """执行完整构建流程"""
        print("🚀 开始构建Windows Python环境包...")
        print("=" * 50)
        
        try:
            # 1. 清理构建目录
            self.clean_build_dir()
            
            # 2. 下载Python嵌入式版本
            embed_file = self.download_python_embed()
            if not embed_file:
                return False
            
            # 3. 解压Python
            self.extract_python(embed_file)
            
            # 4. 安装pip
            if not self.install_pip():
                return False
            
            # 5. 安装项目依赖
            if not self.install_project_dependencies():
                return False
            
            # 6. 创建启动脚本
            self.create_startup_scripts()
            
            # 7. 创建说明文档
            self.create_readme()
            
            # 8. 打包
            package_path = self.create_package()
            
            print("=" * 50)
            print("🎉 Windows环境包构建成功!")
            print(f"📦 部署包位置: {package_path}")
            print("✅ 可以将此包复制到目标Windows机器上解压使用")
            
            return True
            
        except Exception as e:
            print(f"❌ 构建过程中发生错误: {e}")
            return False

def main():
    """主函数"""
    print("淘沙分析平台 - Windows环境构建工具")
    print("=" * 50)
    
    builder = WindowsEnvBuilder()
    success = builder.build()
    
    if success:
        print("\n🎯 下一步操作:")
        print("1. 将生成的zip包复制到目标Windows机器")
        print("2. 解压zip包到任意目录") 
        print("3. 运行 start_python.bat 启动Python环境")
        print("4. 将项目代码放入环境目录并运行")
        return 0
    else:
        print("\n❌ 构建失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())