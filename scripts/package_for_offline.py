#!/usr/bin/env python3
"""
淘沙分析平台 - 内网部署打包脚本

此脚本用于将整个项目打包，准备在内网环境中离线部署。
包括：
1. Python 依赖包下载
2. UV 工具下载
3. 前端依赖打包
4. 配置文件准备
5. 部署脚本生成

使用方法:
    python package_for_offline.py

作者: Claude
日期: 2024
"""

import os
import sys
import shutil
import subprocess
import zipfile
import tarfile
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 配置常量
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# 打包配置
PACKAGE_NAME = "taosha-offline-package"
PACKAGE_VERSION = "1.0.0"
TARGET_DIR = SCRIPTS_DIR / f"{PACKAGE_NAME}-{PACKAGE_VERSION}"

# Python 版本要求
PYTHON_VERSION = "3.11"
PYTHON_INSTALLER_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"

# UV 下载配置
UV_RELEASES_API = "https://api.github.com/repos/astral-sh/uv/releases/latest"
UV_VERSION = "0.5.9"  # 固定版本确保稳定性

class Colors:
    """终端颜色配置"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_message(message: str, color: str = Colors.GREEN):
    """打印带颜色的消息"""
    print(f"{color}{message}{Colors.END}")

def print_error(message: str):
    """打印错误消息"""
    print(f"{Colors.RED}错误: {message}{Colors.END}")

def print_warning(message: str):
    """打印警告消息"""
    print(f"{Colors.YELLOW}警告: {message}{Colors.END}")

def print_info(message: str):
    """打印信息消息"""
    print(f"{Colors.BLUE}{message}{Colors.END}")

def run_command(command: List[str], cwd: Optional[Path] = None) -> bool:
    """运行命令并处理错误"""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"命令执行失败: {' '.join(command)}")
        print_error(f"错误信息: {e.stderr}")
        return False

def check_file_integrity(file_path: Path, expected_hash: Optional[str] = None) -> str:
    """检查文件完整性并返回MD5哈希值"""
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

    file_hash = hash_md5.hexdigest()
    if expected_hash and file_hash != expected_hash:
        raise ValueError(f"文件完整性校验失败: {file_path}")

    return file_hash

def download_file(url: str, target_path: Path, description: str = "文件") -> bool:
    """下载文件"""
    print_info(f"正在下载 {description}...")
    try:
        import urllib.request
        urllib.request.urlretrieve(url, target_path)
        print_message(f"{description} 下载完成: {target_path}")
        return True
    except Exception as e:
        print_error(f"{description} 下载失败: {e}")
        return False

def prepare_python_packages():
    """准备 Python 依赖包"""
    print_message("=== 准备 Python 依赖包 ===", Colors.BLUE)

    packages_dir = TARGET_DIR / "backend" / "packages"
    packages_dir.mkdir(parents=True, exist_ok=True)

    # 生成 requirements.txt
    requirements_path = TARGET_DIR / "backend" / "requirements.txt"
    print_info("正在生成 requirements.txt...")

    if not run_command([
        sys.executable, "-m", "uv", "pip", "compile",
        str(PROJECT_ROOT / "pyproject.toml"),
        "-o", str(requirements_path)
    ], cwd=PROJECT_ROOT):
        print_error("生成 requirements.txt 失败")
        return False

    print_message("requirements.txt 生成完成")

    # 检测当前平台和目标平台
    import platform
    current_system = platform.system().lower()
    current_machine = platform.machine().lower()

    # 默认目标平台配置（CentOS 7 / Python 3.11）
    target_platforms = [
        "manylinux2014_x86_64",  # CentOS 7/RHEL 7 兼容
        "manylinux_2_17_x86_64",  # 更新的 Linux 发行版
        "linux_x86_64",  # 通用 Linux
    ]

    print_info(f"当前平台: {current_system} {current_machine}")
    print_info(f"目标平台: {', '.join(target_platforms)}")

    # 下载所有依赖包（支持多平台）
    print_info("正在下载 Python 依赖包...")

    download_success = False

    if current_system == "windows":
        # 在 Windows 上下载时，需要指定目标平台
        for platform_tag in target_platforms:
            print_info(f"尝试为平台 {platform_tag} 下载包...")
            if run_command([
                sys.executable, "-m", "pip", "download",
                "--platform", platform_tag,
                "--only-binary=:all:",
                "--python-version", "311",
                "--implementation", "cp",
                "--abi", "cp311",
                "-r", str(requirements_path),
                "-d", str(packages_dir)
            ], cwd=PROJECT_ROOT):
                print_message(f"平台 {platform_tag} 下载成功")
                download_success = True
                break
            else:
                print_warning(f"平台 {platform_tag} 下载失败，尝试下一个平台...")
    else:
        # 在 Linux/Mac 上直接下载
        if run_command([
            sys.executable, "-m", "pip", "download",
            "-r", str(requirements_path),
            "-d", str(packages_dir)
        ], cwd=PROJECT_ROOT):
            download_success = True

    if not download_success:
        print_error("所有平台尝试失败，尝试下载源码包...")
        # 最后尝试下载源码包
        if run_command([
            sys.executable, "-m", "pip", "download",
            "--no-binary=:all:",
            "-r", str(requirements_path),
            "-d", str(packages_dir)
        ], cwd=PROJECT_ROOT):
            print_message("源码包下载成功")
        else:
            print_error("Python 依赖包下载失败")
            return False

    # 生成包文件清单
    wheel_count = len(list(packages_dir.glob("*.whl")))
    tar_count = len(list(packages_dir.glob("*.tar.gz")))
    zip_count = len(list(packages_dir.glob("*.zip")))

    package_manifest = {
        "target_platforms": target_platforms,
        "wheel_packages": wheel_count,
        "source_packages": tar_count + zip_count,
        "total_packages": wheel_count + tar_count + zip_count,
        "requirements_file": "requirements.txt",
        "packages_directory": "packages/",
        "target_python_version": PYTHON_VERSION
    }

    with open(packages_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(package_manifest, f, indent=2, ensure_ascii=False)

    print_message(f"Python 依赖包准备完成，共 {package_manifest['total_packages']} 个包")
    print_message(f"  - 二进制包: {wheel_count}")
    print_message(f"  - 源码包: {tar_count + zip_count}")
    return True

def prepare_uv_tool():
    """准备 UV 工具"""
    print_message("=== 准备 UV 工具 ===", Colors.BLUE)

    uv_dir = TARGET_DIR / "backend" / "tools"
    uv_dir.mkdir(parents=True, exist_ok=True)

    # 检测操作系统和架构
    import platform
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        uv_filename = f"uv-{UV_VERSION}-x86_64-pc-windows-msvc.zip"
        uv_executable = "uv.exe"
    elif system == "linux":
        if machine in ["x86_64", "amd64"]:
            uv_filename = f"uv-{UV_VERSION}-x86_64-unknown-linux-gnu.tar.gz"
            uv_executable = "uv"
        else:
            print_error(f"不支持的 Linux 架构: {machine}")
            return False
    else:
        print_error(f"不支持的操作系统: {system}")
        return False

    uv_download_url = f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/{uv_filename}"
    uv_archive_path = uv_dir / uv_filename

    # 下载 UV
    if not download_file(uv_download_url, uv_archive_path, "UV 工具"):
        return False

    # 解压
    print_info("正在解压 UV 工具...")
    try:
        if uv_filename.endswith(".zip"):
            with zipfile.ZipFile(uv_archive_path, 'r') as zip_ref:
                zip_ref.extractall(uv_dir)
        else:
            with tarfile.open(uv_archive_path, 'r:*') as tar_ref:
                tar_ref.extractall(uv_dir)

        # 查找可执行文件
        for root, dirs, files in os.walk(uv_dir):
            for file in files:
                if file == uv_executable:
                    src_path = Path(root) / file
                    dst_path = uv_dir / uv_executable
                    shutil.move(src_path, dst_path)

                    # 设置执行权限（Linux）
                    if system != "windows":
                        os.chmod(dst_path, 0o755)

                    print_message(f"UV 工具准备完成: {dst_path}")
                    return True

        print_error("未找到 UV 可执行文件")
        return False

    except Exception as e:
        print_error(f"解压 UV 工具失败: {e}")
        return False

def prepare_frontend_packages():
    """准备前端依赖包"""
    print_message("=== 准备前端依赖包 ===", Colors.BLUE)

    frontend_packages_dir = TARGET_DIR / "frontend" / "packages"
    frontend_packages_dir.mkdir(parents=True, exist_ok=True)

    # 检查 node_modules 是否存在
    node_modules_path = FRONTEND_ROOT / "node_modules"
    if not node_modules_path.exists():
        print_warning("前端 node_modules 不存在，正在安装...")
        if not run_command(["npm", "install"], cwd=FRONTEND_ROOT):
            print_error("前端依赖安装失败")
            return False

    # 压缩 node_modules
    print_info("正在压缩 node_modules...")
    node_modules_zip = frontend_packages_dir / "node_modules.zip"

    with zipfile.ZipFile(node_modules_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(node_modules_path):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(node_modules_path.parent)
                zipf.write(file_path, arcname)

    # 复制 package.json 和 package-lock.json
    shutil.copy2(FRONTEND_ROOT / "package.json", frontend_packages_dir)
    package_lock_path = FRONTEND_ROOT / "package-lock.json"
    if package_lock_path.exists():
        shutil.copy2(package_lock_path, frontend_packages_dir)

    print_message("前端依赖包准备完成")
    return True

def create_deployment_readme():
    """创建部署说明文档"""
    print_message("=== 创建部署说明文档 ===", Colors.BLUE)

    readme_content = f"""# 淘沙分析平台 - 内网部署说明

## 版本信息
- 版本: {PACKAGE_VERSION}
- 打包时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Python 版本要求: {PYTHON_VERSION}+

## 系统要求

### 硬件要求
- CPU: 2核心以上
- 内存: 4GB 以上（推荐8GB）
- 磁盘空间: 5GB 可用空间

### 软件要求
- 操作系统: CentOS 7+ / Ubuntu 18+ / Windows 10+
- Python: {PYTHON_VERSION}+（如果没有，脚本会自动下载安装包）

## 部署步骤

### 1. 解压部署包
```bash
tar -xzf {PACKAGE_NAME}-{PACKAGE_VERSION}.tar.gz
cd {PACKAGE_NAME}-{PACKAGE_VERSION}
```

### 2. 运行自动部署脚本
```bash
# Linux/macOS
chmod +x scripts/deploy_on_offline.sh
./scripts/deploy_on_offline.sh

# Windows
scripts\\deploy_on_offline.bat
```

### 3. 手动部署（可选）
如果自动脚本失败，可以按照以下步骤手动部署：

#### 3.1 安装 Python（如果没有）
```bash
# CentOS 7
sudo yum install -y gcc zlib-devel bzip2-devel readline-devel ncurses-devel sqlite-devel openssl-devel tk-devel
# 然后运行 scripts/install_python.sh

# Ubuntu/Debian
sudo apt-get install -y build-essential libssl-dev zlib1g-dev libncurses5-dev libncursesw5-dev libreadline-dev libsqlite3-dev libgdbm-dev libdb5.3-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev
# 然后运行 scripts/install_python.sh
```

#### 3.2 安装 UV 工具
```bash
# Linux/macOS
cp backend/tools/uv /usr/local/bin/uv
chmod +x /usr/local/bin/uv

# Windows
# 将 backend/tools/uv.exe 添加到 PATH
```

#### 3.3 安装 Python 依赖

**重要提示**: 本包已针对 CentOS 7 / Python 3.11 优化，包含以下平台兼容包：
- manylinux2014_x86_64 (CentOS 7/RHEL 7 兼容)
- manylinux_2_17_x86_64 (更新的 Linux 发行版)
- linux_x86_64 (通用 Linux)

**方法1: 使用 pip 安装（推荐）**
```bash
cd backend
python -m pip install --no-index --find-links packages/ -r requirements.txt
```

**方法2: 使用 uv 安装**
```bash
cd backend
../tools/uv pip install --no-index --find-links packages/ -r requirements.txt
```

**方法3: 使用虚拟环境安装**
```bash
cd backend
../tools/uv venv
source .venv/bin/activate  # Linux
../tools/uv pip install --no-index --find-links packages/ -r requirements.txt
```

**如果安装失败**:
1. 检查 Python 版本是否为 3.11
2. 尝试只安装源码包: `python -m pip install --no-index --find-links packages/ --no-binary=:all: -r requirements.txt`
3. 检查系统依赖是否完整（gcc, openssl-devel 等）

#### 3.4 配置环境变量
```bash
# 复制配置文件模板
cp config/config.template.yaml backend/config/config.yaml
cp config/.env.template backend/.env

# 编辑配置文件，设置数据库路径、API密钥等
```

#### 3.5 启动服务
```bash
# 启动后端
cd backend
python main.py

# 启动前端（另一个终端）
cd frontend/dist
# 使用 nginx 或其他 Web 服务器托管静态文件
```

## 配置说明

### 主要配置文件
- `backend/config/config.yaml`: 主配置文件
- `backend/.env`: 环境变量配置

### 内网配置调整
1. **数据库配置**: 使用相对路径，确保数据文件存在
2. **API 配置**: 如果需要访问外部 API，配置内网代理
3. **日志配置**: 调整日志路径和级别
4. **追踪配置**: 如果不需要外部追踪，设置为禁用

## 服务访问

部署成功后：
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 前端界面: 需要配置 Web 服务器托管 frontend/dist 目录

## 故障排除

### 常见问题

1. **Python 版本不兼容**
   - 确保使用 Python {PYTHON_VERSION}+
   - 运行 `python --version` 检查版本

2. **依赖安装失败**
   - 检查 UV 工具是否正确安装
   - 确认 packages 目录包含所有必需的包文件

3. **数据库连接失败**
   - 检查数据库文件路径配置
   - 确认有足够的磁盘空间

4. **前端无法访问后端**
   - 检查后端服务是否正常启动
   - 确认防火墙设置

### 日志文件
- 后端日志: `backend/logs/`
- 错误日志: `backend/logs/error.log`

## 技术支持

如果遇到问题，请检查：
1. 系统日志和错误信息
2. 配置文件是否正确
3. 网络连接和防火墙设置
4. 文件权限和磁盘空间

## 文件清单

### 后端文件
- `backend/source/`: 后端源码
- `backend/packages/`: Python 离线包
- `backend/tools/`: UV 工具
- `backend/requirements.txt`: Python 依赖列表

### 前端文件
- `frontend/source/`: 前端源码
- `frontend/node_modules.zip`: 前端依赖包
- `frontend/dist/`: 构建后的前端文件（如果构建成功）

### 配置和脚本
- `config/`: 配置文件模板
- `scripts/`: 部署和安装脚本

---
打包时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    readme_path = TARGET_DIR / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print_message("部署说明文档创建完成")
    return True

def create_final_package():
    """创建最终的部署包"""
    print_message("=== 创建最终部署包 ===", Colors.BLUE)

    # 生成文件清单
    manifest = {
        "package_name": PACKAGE_NAME,
        "version": PACKAGE_VERSION,
        "created_at": datetime.now().isoformat(),
        "python_version": PYTHON_VERSION,
        "directories": {
            "backend": "后端源码和依赖",
            "frontend": "前端源码和依赖",
            "config": "配置文件模板",
            "scripts": "部署脚本"
        }
    }

    with open(TARGET_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # 创建最终压缩包
    final_package = PROJECT_ROOT / f"{PACKAGE_NAME}-{PACKAGE_VERSION}.tar.gz"
    print_info(f"正在创建最终部署包: {final_package}")

    with tarfile.open(final_package, "w:gz") as tar:
        tar.add(TARGET_DIR, arcname=TARGET_DIR.name)

    # 计算文件大小
    package_size = final_package.stat().st_size / (1024 * 1024)  # MB

    print_message(f"最终部署包创建完成!")
    print_message(f"文件路径: {final_package}")
    print_message(f"文件大小: {package_size:.1f} MB")

    # 生成校验和
    package_hash = check_file_integrity(final_package)
    print_message(f"MD5 校验和: {package_hash}")

    # 保存校验和到文件
    with open(f"{final_package}.md5", "w") as f:
        f.write(f"{package_hash}  {final_package.name}\n")

    return True

def main():
    """主函数"""
    print_message("=== 淘沙分析平台内网部署打包工具 ===", Colors.BOLD)
    print_message(f"版本: {PACKAGE_VERSION}")
    print_message(f"Python 版本: {PYTHON_VERSION}")
    print_message(f"项目根目录: {PROJECT_ROOT}")
    print()

    # 检查项目结构
    if not PROJECT_ROOT.exists():
        print_error("项目根目录不存在")
        return 1

    if not BACKEND_ROOT.exists():
        print_error("后端目录不存在")
        return 1

    if not FRONTEND_ROOT.exists():
        print_error("前端目录不存在")
        return 1

    # 清理目标目录
    if TARGET_DIR.exists():
        print_warning(f"目标目录已存在，正在清理: {TARGET_DIR}")
        shutil.rmtree(TARGET_DIR)

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # 执行打包步骤
    steps = [
        ("准备 Python 依赖包", prepare_python_packages),
        ("准备前端依赖包", prepare_frontend_packages),
        ("准备 UV 工具", prepare_uv_tool),
        ("创建部署说明文档", create_deployment_readme),
        ("创建最终部署包", create_final_package)
    ]

    failed_steps = []

    for step_name, step_func in steps:
        print_info(f"执行步骤: {step_name}")
        try:
            if not step_func():
                print_error(f"步骤失败: {step_name}")
                failed_steps.append(step_name)
        except Exception as e:
            print_error(f"步骤异常: {step_name} - {e}")
            failed_steps.append(step_name)

        print()

    # 检查结果
    if failed_steps:
        print_error(f"打包完成，但有 {len(failed_steps)} 个步骤失败:")
        for step in failed_steps:
            print_error(f"  - {step}")
        return 1
    else:
        print_message("🎉 打包完成！所有步骤都成功执行。")
        print_message(f"部署包位置: {PROJECT_ROOT / f'{PACKAGE_NAME}-{PACKAGE_VERSION}.tar.gz'}")
        print_message("请将部署包传输到内网环境，然后按照 README.md 中的说明进行部署。")
        return 0

if __name__ == "__main__":
    sys.exit(main())