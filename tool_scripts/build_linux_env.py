#!/usr/bin/env python3
"""
Linux环境Python依赖包打包脚本

功能：
1. 使用Docker创建CentOS7环境
2. 安装Python 3.11和项目依赖
3. 创建便携式Python环境包
4. 生成部署用的tar.gz包

使用方法：
python tool_scripts/build_linux_env.py
"""

import os
import shutil
import subprocess
import tempfile
import tarfile
from pathlib import Path
import sys
import json

class LinuxEnvBuilder:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.dist_dir / "taosha_linux_env"
        self.python_version = "3.11.7"
        
    def clean_build_dir(self):
        """清理构建目录"""
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ 构建目录已清理: {self.build_dir}")
    
    def check_docker(self):
        """检查Docker是否可用"""
        try:
            result = subprocess.run(["docker", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Docker可用: {result.stdout.strip()}")
                return True
            else:
                print("❌ Docker不可用")
                return False
        except FileNotFoundError:
            print("❌ 未找到Docker，请先安装Docker Desktop")
            return False
    
    def create_dockerfile(self):
        """创建Dockerfile"""
        dockerfile_content = f'''FROM centos:7

# 更新系统并安装基础工具
RUN yum update -y && \\
    yum groupinstall -y "Development Tools" && \\
    yum install -y \\
        wget curl \\
        openssl-devel \\
        bzip2-devel \\
        libffi-devel \\
        zlib-devel \\
        readline-devel \\
        sqlite-devel \\
        tk-devel \\
        gdbm-devel \\
        db4-devel \\
        libpcap-devel \\
        xz-devel \\
        expat-devel \\
        && yum clean all

# 创建工作目录
WORKDIR /build

# 下载并编译Python {self.python_version}
RUN wget https://www.python.org/ftp/python/{self.python_version}/Python-{self.python_version}.tgz && \\
    tar -xzf Python-{self.python_version}.tgz && \\
    cd Python-{self.python_version} && \\
    ./configure --prefix=/build/python_dist --enable-optimizations && \\
    make -j$(nproc) && \\
    make altinstall

# 创建符号链接
RUN cd /build/python_dist/bin && \\
    ln -s python{self.python_version[:4]} python3 && \\
    ln -s python{self.python_version[:4]} python

# 安装pip
RUN /build/python_dist/bin/python -m ensurepip --upgrade

# 升级pip并安装构建工具
RUN /build/python_dist/bin/python -m pip install --upgrade pip setuptools wheel

# 设置环境变量
ENV PATH="/build/python_dist/bin:$PATH"
ENV PYTHONPATH="/build/python_dist/lib/python{self.python_version[:4]}/site-packages"

# 工作目录
WORKDIR /workspace
'''
        
        dockerfile_path = self.build_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        print("✅ Dockerfile创建完成")
        return dockerfile_path
    
    def build_docker_image(self, dockerfile_path):
        """构建Docker镜像"""
        print("🐳 正在构建Docker镜像 (这可能需要较长时间)...")
        
        try:
            subprocess.run([
                "docker", "build", 
                "-t", "taosha-linux-builder",
                "-f", str(dockerfile_path),
                str(self.build_dir)
            ], check=True, cwd=self.project_root)
            
            print("✅ Docker镜像构建完成")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker镜像构建失败: {e}")
            return False
    
    def export_requirements(self):
        """导出项目依赖"""
        print("📋 正在导出项目依赖...")
        
        try:
            subprocess.run([
                "uv", "export", 
                "--format", "requirements-txt",
                "--output", str(self.build_dir / "requirements.txt")
            ], check=True, cwd=self.project_root)
            
            print("✅ 依赖列表导出完成")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖导出失败: {e}")
            print("请确保已安装UV并在项目根目录运行")
            return False
    
    def create_install_script(self):
        """创建依赖安装脚本"""
        install_script_content = f'''#!/bin/bash
set -e

echo "========================================="
echo "淘沙分析平台 - Linux环境依赖安装"
echo "Python版本: {self.python_version}"
echo "========================================="

# 检查requirements.txt
if [ ! -f "/workspace/requirements.txt" ]; then
    echo "❌ 未找到requirements.txt文件"
    exit 1
fi

echo "📦 正在安装项目依赖..."
python -m pip install -r /workspace/requirements.txt --no-cache-dir

echo "✅ 依赖安装完成"

# 显示已安装的包
echo "📋 已安装的包列表:"
python -m pip list

# 测试关键包导入
echo "🧪 测试关键包导入..."
python -c "
try:
    import streamlit
    print('✅ Streamlit: 可用')
except ImportError as e:
    print(f'❌ Streamlit: {{e}}')

try:
    import pandas
    print('✅ Pandas: 可用')
except ImportError as e:
    print(f'❌ Pandas: {{e}}')

try:
    import plotly
    print('✅ Plotly: 可用') 
except ImportError as e:
    print(f'❌ Plotly: {{e}}')
"

echo "========================================="
echo "🎉 Linux环境依赖安装完成!"
echo "========================================="
'''
        
        install_script = self.build_dir / "install_deps.sh"
        install_script.write_text(install_script_content)
        print("✅ 依赖安装脚本创建完成")
        return install_script
    
    def run_docker_build(self):
        """在Docker中运行依赖安装"""
        print("🐳 正在Docker容器中安装依赖...")
        
        try:
            # 运行Docker容器并安装依赖
            subprocess.run([
                "docker", "run", "--rm",
                "-v", f"{self.build_dir}:/workspace",
                "taosha-linux-builder",
                "/bin/bash", "/workspace/install_deps.sh"
            ], check=True)
            
            print("✅ Docker容器中依赖安装完成")
            
            # 从容器中复制Python环境
            print("📦 正在从容器中导出Python环境...")
            subprocess.run([
                "docker", "run", "--rm",
                "-v", f"{self.build_dir}:/output",
                "taosha-linux-builder",
                "/bin/bash", "-c", "cp -r /build/python_dist /output/"
            ], check=True)
            
            print("✅ Python环境导出完成")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker构建失败: {e}")
            return False
    
    def create_startup_scripts(self):
        """创建启动脚本"""
        print("📝 正在创建启动脚本...")
        
        python_dist = self.build_dir / "python_dist"
        
        # Bash启动脚本
        start_sh = python_dist / "start_python.sh"
        start_sh.write_text(f'''#!/bin/bash

echo "========================================"
echo "淘沙分析平台 - Linux Python环境"
echo "========================================"
echo "Python版本: {self.python_version}"
echo "环境路径: $(dirname $0)"
echo "========================================"
echo ""

# 设置环境变量
export PATH="$(dirname $0)/bin:$PATH"
export PYTHONPATH="$(dirname $0)/lib/python{self.python_version[:4]}/site-packages:$PYTHONPATH"

# 显示Python信息
echo "🐍 Python信息:"
./bin/python --version
echo "📍 Python路径: $(pwd)/bin/python"
echo ""

echo "🎯 Python环境已准备就绪!"
echo "使用方法: ./bin/python your_script.py"
echo ""

# 启动交互式bash
/bin/bash
''')
        start_sh.chmod(0o755)
        
        # 环境设置脚本
        activate_sh = python_dist / "activate.sh" 
        activate_sh.write_text(f'''#!/bin/bash
# 淘沙分析平台 Python环境激活脚本

# 保存原始PATH
if [ -z "$TAOSHA_ORIGINAL_PATH" ]; then
    export TAOSHA_ORIGINAL_PATH="$PATH"
fi

# 设置Python环境
export TAOSHA_PYTHON_HOME="$(dirname $0)"
export PATH="$TAOSHA_PYTHON_HOME/bin:$TAOSHA_ORIGINAL_PATH"
export PYTHONPATH="$TAOSHA_PYTHON_HOME/lib/python{self.python_version[:4]}/site-packages:$PYTHONPATH"

echo "✅ 淘沙Python环境已激活"
echo "Python路径: $TAOSHA_PYTHON_HOME/bin/python"

# 设置PS1提示符
export PS1="(taosha-python) $PS1"
''')
        activate_sh.chmod(0o755)
        
        print("✅ 启动脚本创建完成")
    
    def create_readme(self):
        """创建部署说明文档"""
        readme_content = f"""# 淘沙分析平台 - Linux Python环境包

## 环境信息  
- **Python版本**: {self.python_version}
- **目标平台**: CentOS 7 x86_64 (兼容其他Linux发行版)
- **打包时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 目录结构
```
taosha_linux_env/
├── python_dist/                 # Python环境目录
│   ├── bin/                     # Python可执行文件
│   │   ├── python              # Python解释器
│   │   ├── python3             # Python3链接
│   │   └── pip                 # pip包管理器
│   ├── lib/                    # Python库文件
│   │   └── python{self.python_version[:4]}/
│   │       └── site-packages/  # 已安装的包
│   ├── start_python.sh         # 启动脚本
│   ├── activate.sh             # 环境激活脚本
│   └── README.md              # 本文件
└── requirements.txt            # 依赖列表
```

## 使用方法

### 1. 解压部署包
```bash
tar -xzf taosha_linux_python_env_{self.python_version}.tar.gz
cd taosha_linux_env
```

### 2. 启动Python环境
```bash
# 方法1: 使用启动脚本 (推荐)
cd python_dist
chmod +x start_python.sh
./start_python.sh

# 方法2: 激活环境
source python_dist/activate.sh
python --version

# 方法3: 直接使用
./python_dist/bin/python --version
```

### 3. 运行项目
```bash
# 激活环境后运行
source python_dist/activate.sh
python /path/to/your/project/main.py

# 或直接指定Python路径
./python_dist/bin/python /path/to/your/project/main.py
```

### 4. 测试环境
```bash
# 测试Python和关键包
./python_dist/bin/python -c "
import sys
print('Python版本:', sys.version)
print('Python路径:', sys.executable)

# 测试关键包
try:
    import streamlit
    print('✅ Streamlit可用')
except ImportError:
    print('❌ Streamlit不可用')

try:
    import pandas
    print('✅ Pandas可用')  
except ImportError:
    print('❌ Pandas不可用')
"
```

## 兼容性说明
- **主要兼容**: CentOS 7, RHEL 7
- **理论兼容**: Ubuntu 16.04+, Debian 9+, SUSE Linux
- **架构要求**: x86_64

## 故障排除

### 1. 权限问题
```bash
chmod +x python_dist/bin/*
chmod +x python_dist/*.sh
```

### 2. 依赖库问题
```bash
# 检查系统依赖
ldd python_dist/bin/python

# 如果缺少依赖，安装基础包
yum install -y glibc libffi openssl
```

### 3. 路径问题
```bash
# 检查Python路径
./python_dist/bin/python -c "import sys; print(sys.path)"

# 手动设置PYTHONPATH
export PYTHONPATH="$PWD/python_dist/lib/python{self.python_version[:4]}/site-packages:$PYTHONPATH"
```

## 注意事项
1. 此环境包含项目所需的所有Python依赖包
2. 无需在目标机器安装Python或pip
3. 建议将整个环境目录放在固定位置使用
4. 如需安装额外包：`./python_dist/bin/pip install package_name`

## 技术支持
如有问题，请联系项目开发团队。
"""
        
        readme_file = self.build_dir / "python_dist" / "README.md"
        readme_file.parent.mkdir(parents=True, exist_ok=True)
        readme_file.write_text(readme_content, encoding="utf-8")
        print("✅ 部署文档创建完成")
    
    def create_package(self):
        """创建最终压缩包"""
        print("📦 正在创建部署包...")
        
        package_name = f"taosha_linux_python_env_{self.python_version}.tar.gz"
        package_path = self.dist_dir / package_name
        
        # 删除现有包
        if package_path.exists():
            package_path.unlink()
        
        # 创建tar.gz包
        with tarfile.open(package_path, "w:gz") as tar:
            tar.add(self.build_dir / "python_dist", 
                   arcname="taosha_linux_env/python_dist")
            tar.add(self.build_dir / "requirements.txt",
                   arcname="taosha_linux_env/requirements.txt")
        
        # 计算包大小
        size_mb = package_path.stat().st_size / 1024 / 1024
        
        print(f"✅ 部署包创建完成!")
        print(f"📦 包名称: {package_name}")
        print(f"📏 包大小: {size_mb:.1f} MB")
        print(f"📍 包路径: {package_path}")
        
        return package_path
    
    def cleanup_docker(self):
        """清理Docker资源"""
        print("🧹 正在清理Docker资源...")
        try:
            # 删除构建镜像
            subprocess.run(["docker", "rmi", "taosha-linux-builder"], 
                         capture_output=True)
            print("✅ Docker镜像已清理")
        except:
            pass  # 忽略清理错误
    
    def build(self):
        """执行完整构建流程"""
        print("🚀 开始构建Linux Python环境包...")
        print("=" * 50)
        
        try:
            # 1. 检查Docker
            if not self.check_docker():
                print("\n💡 替代方案:")
                print("1. 安装Docker Desktop")
                print("2. 在Linux机器上直接使用UV部署")
                print("3. 使用虚拟机运行Linux环境")
                return False
            
            # 2. 清理构建目录
            self.clean_build_dir()
            
            # 3. 导出依赖
            if not self.export_requirements():
                return False
            
            # 4. 创建Dockerfile
            dockerfile_path = self.create_dockerfile()
            
            # 5. 创建安装脚本
            self.create_install_script()
            
            # 6. 构建Docker镜像
            if not self.build_docker_image(dockerfile_path):
                return False
            
            # 7. 在Docker中安装依赖
            if not self.run_docker_build():
                return False
            
            # 8. 创建启动脚本
            self.create_startup_scripts()
            
            # 9. 创建说明文档
            self.create_readme()
            
            # 10. 打包
            package_path = self.create_package()
            
            # 11. 清理Docker资源
            self.cleanup_docker()
            
            print("=" * 50)
            print("🎉 Linux环境包构建成功!")
            print(f"📦 部署包位置: {package_path}")
            print("✅ 可以将此包复制到目标Linux机器上解压使用")
            
            return True
            
        except Exception as e:
            print(f"❌ 构建过程中发生错误: {e}")
            self.cleanup_docker()
            return False

def main():
    """主函数"""
    print("淘沙分析平台 - Linux环境构建工具")
    print("=" * 50)
    
    builder = LinuxEnvBuilder()
    success = builder.build()
    
    if success:
        print("\n🎯 下一步操作:")
        print("1. 将生成的tar.gz包复制到目标Linux机器")
        print("2. 解压: tar -xzf taosha_linux_python_env_*.tar.gz")
        print("3. 运行: cd taosha_linux_env && ./python_dist/start_python.sh")  
        print("4. 将项目代码复制到环境中并运行")
        return 0
    else:
        print("\n❌ 构建失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())