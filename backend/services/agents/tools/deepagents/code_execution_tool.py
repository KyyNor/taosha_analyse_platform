"""
Python 代码执行工具（Docker 沙箱版本）
使用 Docker 容器提供完全隔离的代码执行环境
"""

import json
import uuid
import shutil
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

import docker
from docker.models.containers import Container
from docker.errors import DockerException, ImageNotFound, ContainerError

from utils.logger import logger
from langfuse import observe


# ==================== 配置 ====================

# Docker 镜像配置
SANDBOX_IMAGE = "taosha-sandbox:latest"
SANDBOX_USER = "sandbox"  # 容器内用户
SANDBOX_UID = 1000

# 资源限制
CPU_LIMIT = 1.0  # CPU 核心数
MEMORY_LIMIT = "512m"  # 内存限制
TIMEOUT_DEFAULT = 30  # 默认超时时间（秒）

# Session 目录配置
SESSION_BASE_DIR = Path("/tmp/taosha_sessions")
SESSION_BASE_DIR.mkdir(exist_ok=True, parents=True)

# 容器内挂载路径
CONTAINER_WORKSPACE = "/workspace"


# ==================== 异常类 ====================

class CodeExecutionError(Exception):
    """代码执行错误"""
    pass


class SandboxNotAvailableError(Exception):
    """沙箱不可用错误"""
    pass


# ==================== Session 管理 ====================

class SessionManager:
    """管理代码执行会话的临时目录"""

    @staticmethod
    def create_session() -> tuple[str, Path]:
        """
        创建新的会话目录

        Returns:
            (session_id, session_path)
        """
        session_id = str(uuid.uuid4())
        session_path = SESSION_BASE_DIR / session_id
        session_path.mkdir(parents=True, exist_ok=True)

        # 设置权限，确保容器内的 sandbox 用户（UID 1000）可以读写
        session_path.chmod(0o777)

        logger.info(f"创建会话目录: {session_path} (session_id={session_id})")
        return session_id, session_path

    @staticmethod
    def cleanup_session(session_path: Path):
        """清理会话目录"""
        try:
            if session_path.exists():
                shutil.rmtree(session_path)
                logger.info(f"清理会话目录: {session_path}")
        except Exception as e:
            logger.warning(f"清理会话目录失败: {session_path}, 错误: {e}")

    @staticmethod
    def write_code_to_file(session_path: Path, code: str) -> Path:
        """
        将代码写入文件

        Args:
            session_path: 会话目录
            code: Python 代码

        Returns:
            代码文件路径
        """
        code_file = session_path / "execute.py"
        code_file.write_text(code, encoding="utf-8")
        code_file.chmod(0o666)  # 确保容器可以读取
        return code_file


# ==================== Docker 容器管理 ====================

class DockerSandboxManager:
    """管理 Docker 沙箱容器的生命周期"""

    def __init__(self):
        """初始化 Docker 客户端"""
        try:
            self.client = docker.from_env()
            # 验证 Docker 连接
            self.client.ping()
            logger.info("Docker 客户端初始化成功")
        except DockerException as e:
            logger.error(f"无法连接到 Docker: {e}")
            raise SandboxNotAvailableError(f"Docker 不可用: {e}")

    def check_image_exists(self) -> bool:
        """检查沙箱镜像是否存在"""
        try:
            self.client.images.get(SANDBOX_IMAGE)
            return True
        except ImageNotFound:
            return False

    @asynccontextmanager
    async def create_container(
        self,
        session_path: Path,
        timeout: int = TIMEOUT_DEFAULT
    ):
        """
        创建并管理容器的生命周期（异步上下文管理器）

        Args:
            session_path: 会话目录（将被挂载到容器内）
            timeout: 执行超时时间

        Yields:
            Docker 容器对象
        """
        container = None
        try:
            # 创建容器配置
            container_config = {
                "image": SANDBOX_IMAGE,
                "command": "sleep infinity",  # 保持容器运行
                "detach": True,
                "user": f"{SANDBOX_UID}:{SANDBOX_UID}",  # 使用 sandbox 用户
                "working_dir": CONTAINER_WORKSPACE,
                "volumes": {
                    str(session_path.absolute()): {
                        "bind": CONTAINER_WORKSPACE,
                        "mode": "rw"
                    }
                },
                # 资源限制
                "nano_cpus": int(CPU_LIMIT * 1e9),  # 转换为纳秒
                "mem_limit": MEMORY_LIMIT,
                # 网络隔离
                "network_mode": "none",
                # 安全配置
                "cap_drop": ["ALL"],  # 移除所有 capabilities
                "security_opt": ["no-new-privileges"],  # 禁止提权
                "read_only": False,  # 允许写入（仅限挂载的 workspace）
                # 其他限制
                "pids_limit": 100,  # 限制进程数
                "remove": False,  # 手动删除以便获取日志
            }

            # 创建容器
            logger.info(f"创建 Docker 容器: session={session_path.name}")
            container = await asyncio.to_thread(
                self.client.containers.create,
                **container_config
            )

            # 启动容器
            await asyncio.to_thread(container.start)
            logger.info(f"容器已启动: {container.short_id}")

            # 返回容器供使用
            yield container

        except ImageNotFound:
            error_msg = f"Docker 镜像 '{SANDBOX_IMAGE}' 不存在，请先构建镜像"
            logger.error(error_msg)
            raise SandboxNotAvailableError(error_msg)

        except DockerException as e:
            logger.error(f"Docker 容器创建失败: {e}")
            raise CodeExecutionError(f"容器创建失败: {e}")

        finally:
            # 清理容器
            if container:
                try:
                    await asyncio.to_thread(container.stop, timeout=2)
                    await asyncio.to_thread(container.remove)
                    logger.info(f"容器已清理: {container.short_id}")
                except Exception as e:
                    logger.warning(f"容器清理失败: {e}")

    async def execute_in_container(
        self,
        container: Container,
        command: list[str],
        timeout: int = TIMEOUT_DEFAULT
    ) -> tuple[int, str, str]:
        """
        在容器内执行命令

        Args:
            container: Docker 容器对象
            command: 要执行的命令（列表形式）
            timeout: 执行超时时间

        Returns:
            (exit_code, stdout, stderr)
        """
        try:
            # 使用 asyncio.wait_for 实现超时
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    container.exec_run,
                    command,
                    user=f"{SANDBOX_UID}:{SANDBOX_UID}",
                    workdir=CONTAINER_WORKSPACE,
                    demux=True  # 分离 stdout 和 stderr
                ),
                timeout=timeout
            )

            exit_code = result.exit_code
            stdout_bytes, stderr_bytes = result.output

            # 解码输出
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            return exit_code, stdout, stderr

        except asyncio.TimeoutError:
            logger.error(f"容器执行超时（{timeout}秒）")
            raise CodeExecutionError(f"代码执行超时（{timeout}秒）")

        except Exception as e:
            logger.error(f"容器执行失败: {e}")
            raise CodeExecutionError(f"容器执行失败: {e}")


# ==================== 代码执行主函数 ====================

async def execute_code_async(
    code: str,
    timeout: int = TIMEOUT_DEFAULT,
    session_id: Optional[str] = None
) -> dict:
    """
    异步执行 Python 代码（内部实现）

    Args:
        code: Python 代码字符串
        timeout: 执行超时时间（秒）
        session_id: 可选的会话 ID（如果提供，将使用该会话目录）

    Returns:
        执行结果字典
    """
    session_manager = SessionManager()
    sandbox_manager = DockerSandboxManager()

    # 检查镜像是否存在
    if not sandbox_manager.check_image_exists():
        error_msg = f"Docker 镜像 '{SANDBOX_IMAGE}' 不存在。请先构建镜像:\n" \
                   f"cd backend/scripts && docker build -t {SANDBOX_IMAGE} -f Dockerfile.sandbox ."
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

    # 创建或使用现有会话目录
    if session_id:
        session_path = SESSION_BASE_DIR / session_id
        if not session_path.exists():
            session_path.mkdir(parents=True, exist_ok=True)
            session_path.chmod(0o777)
        cleanup_after = False
    else:
        session_id, session_path = session_manager.create_session()
        cleanup_after = True

    try:
        # 将代码写入文件
        code_file = session_manager.write_code_to_file(session_path, code)

        # 创建执行结果文件路径
        result_file = session_path / "result.json"
        c_file = {code.replace("'", "\\'")}

        # 包装代码以捕获结果
        wrapped_code = f"""
import sys
import json
import traceback
from io import StringIO

# 重定向 stdout 和 stderr
old_stdout = sys.stdout
old_stderr = sys.stderr
stdout_capture = StringIO()
stderr_capture = StringIO()
sys.stdout = stdout_capture
sys.stderr = stderr_capture

result_data = {{
    "success": True,
    "result": None,
    "stdout": "",
    "stderr": ""
}}

try:
    # 执行用户代码
    exec_globals = {{}}
    exec('''{c_file}''', exec_globals)

    # 获取 result 变量（如果存在）
    if 'result' in exec_globals:
        result_data["result"] = exec_globals["result"]

except Exception as e:
    result_data["success"] = False
    result_data["error"] = str(e)
    result_data["traceback"] = traceback.format_exc()
finally:
    # 恢复 stdout 和 stderr
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    # 获取输出
    result_data["stdout"] = stdout_capture.getvalue()
    result_data["stderr"] = stderr_capture.getvalue()

    # 序列化结果
    def serialize(obj):
        # pandas DataFrame
        if hasattr(obj, 'to_dict'):
            try:
                return obj.to_dict('records')
            except:
                return str(obj)
        # numpy array
        if hasattr(obj, 'tolist'):
            try:
                return obj.tolist()
            except:
                return str(obj)
        # pandas Series
        if hasattr(obj, 'to_list'):
            try:
                return obj.to_list()
            except:
                return str(obj)
        return obj

    if result_data.get("result") is not None:
        result_data["result"] = serialize(result_data["result"])

    # 写入结果文件
    with open("{CONTAINER_WORKSPACE}/result.json", "w") as f:
        json.dump(result_data, f, ensure_ascii=False, default=str)
"""

        # 写入包装后的代码
        wrapped_file = session_path / "wrapped_execute.py"
        wrapped_file.write_text(wrapped_code, encoding="utf-8")
        wrapped_file.chmod(0o666)

        # 创建容器并执行代码
        async with sandbox_manager.create_container(session_path, timeout) as container:
            # 执行 Python 代码
            exit_code, stdout, stderr = await sandbox_manager.execute_in_container(
                container,
                ["python3", f"{CONTAINER_WORKSPACE}/wrapped_execute.py"],
                timeout=timeout
            )

            # 读取结果文件
            if result_file.exists():
                try:
                    result_data = json.loads(result_file.read_text(encoding="utf-8"))
                    return result_data
                except json.JSONDecodeError as e:
                    logger.error(f"解析结果文件失败: {e}")
                    return {
                        "success": False,
                        "error": "结果文件解析失败",
                        "stdout": stdout,
                        "stderr": stderr
                    }
            else:
                # 没有结果文件，返回标准输出和错误
                return {
                    "success": exit_code == 0,
                    "error": f"Exit code: {exit_code}" if exit_code != 0 else None,
                    "stdout": stdout,
                    "stderr": stderr
                }

    except CodeExecutionError as e:
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"代码执行异常: {e}")
        return {
            "success": False,
            "error": f"执行异常: {str(e)}"
        }
    finally:
        # 清理会话目录（如果是临时创建的）
        if cleanup_after:
            session_manager.cleanup_session(session_path)


@observe(name="execute_code")
def execute_code(
    code: str,
    timeout: int = TIMEOUT_DEFAULT,
    session_id: Optional[str] = None
) -> str:
    """
    执行 Python 代码进行数据处理和分析（同步接口）

    使用 Docker 容器提供完全隔离的执行环境，具有以下安全特性：
    - 独立的文件系统（仅可访问 session 目录）
    - 禁用网络访问
    - CPU 和内存限制
    - 无特权容器
    - 自动超时和清理

    Args:
        code: Python 代码字符串。代码中可以使用预加载的库：
              - pandas (pd): 数据处理
              - numpy (np): 数值计算
              - matplotlib: 绘图
              - seaborn: 统计可视化
              - scipy: 科学计算
              - scikit-learn: 机器学习
              - statsmodels: 统计模型
              - plotly: 交互式可视化

              如果需要返回结果，请将结果赋值给名为 'result' 的变量

        timeout: 执行超时时间（秒），默认 30 秒

        session_id: 可选的会话 ID。如果提供：
                   - 将使用持久化的会话目录（不会自动清理）
                   - 可以在多次调用之间共享文件
                   - 会话目录路径：/tmp/taosha_sessions/{session_id}/

    Returns:
        JSON 格式的执行结果字符串，包含以下字段:
        - success: bool, 是否成功
        - result: any, 代码执行结果（如果定义了 result 变量）
        - stdout: str, 标准输出内容
        - stderr: str, 标准错误内容（仅在有错误时）
        - error: str, 错误信息（仅在失败时）
        - traceback: str, 错误堆栈（仅在失败时）

    Examples:
        # 简单计算
        execute_code('''
        result = 1 + 2 + 3
        ''')
        # 返回: {"success": true, "result": 6, ...}

        # 数据处理
        execute_code('''
        import pandas as pd
        data = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]
        df = pd.DataFrame(data)
        result = df.describe().to_dict()
        ''')

        # 使用 session 持久化数据
        session_id = "my-analysis-session"

        # 第一次调用：生成并保存数据
        execute_code('''
        import pandas as pd
        df = pd.DataFrame({"x": range(10), "y": range(10, 20)})
        df.to_csv("/workspace/data.csv", index=False)
        result = "数据已保存"
        ''', session_id=session_id)

        # 第二次调用：读取之前保存的数据
        execute_code('''
        import pandas as pd
        df = pd.read_csv("/workspace/data.csv")
        result = df.mean().to_dict()
        ''', session_id=session_id)
    """
    logger.info(f"执行 Python 代码（Docker 沙箱）: {code[:100]}...")

    # 在新的事件循环中执行异步代码
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            execute_code_async(code, timeout, session_id)
        )
        loop.close()

        if result["success"]:
            logger.info("Python 代码执行成功")
        else:
            logger.error(f"Python 代码执行失败: {result.get('error')}")

        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"执行环境错误: {e}")
        return json.dumps({
            "success": False,
            "error": f"执行环境错误: {str(e)}"
        }, ensure_ascii=False)


# ==================== 异步接口（供 Agent 使用）====================

async def execute_code_tool_async(
    code: str,
    timeout: int = TIMEOUT_DEFAULT,
    session_id: Optional[str] = None
) -> str:
    """
    异步执行 Python 代码（供 Agent 工具使用）

    这是真正的异步实现，可以直接在 FastAPI 异步路由中调用
    """
    logger.info(f"执行 Python 代码（异步，Docker 沙箱）: {code[:100]}...")

    result = await execute_code_async(code, timeout, session_id)

    if result["success"]:
        logger.info("Python 代码执行成功")
    else:
        logger.error(f"Python 代码执行失败: {result.get('error')}")

    return json.dumps(result, ensure_ascii=False, default=str)


# ==================== Session 文件操作工具 ====================

def list_session_files(session_id: str) -> str:
    """
    列出 session 目录中的文件

    Args:
        session_id: 会话 ID

    Returns:
        JSON 格式的文件列表
    """
    session_path = SESSION_BASE_DIR / session_id

    if not session_path.exists():
        return json.dumps({
            "success": False,
            "error": f"Session 不存在: {session_id}"
        }, ensure_ascii=False)

    try:
        files = []
        for item in session_path.iterdir():
            files.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else None,
                "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
            })

        return json.dumps({
            "success": True,
            "files": files
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


def read_session_file(session_id: str, filename: str) -> str:
    """
    读取 session 目录中的文件内容

    Args:
        session_id: 会话 ID
        filename: 文件名

    Returns:
        JSON 格式的文件内容
    """
    session_path = SESSION_BASE_DIR / session_id
    file_path = session_path / filename

    if not file_path.exists():
        return json.dumps({
            "success": False,
            "error": f"文件不存在: {filename}"
        }, ensure_ascii=False)

    try:
        content = file_path.read_text(encoding="utf-8")
        return json.dumps({
            "success": True,
            "content": content
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


def cleanup_session_directory(session_id: str) -> str:
    """
    清理 session 目录

    Args:
        session_id: 会话 ID

    Returns:
        JSON 格式的清理结果
    """
    session_path = SESSION_BASE_DIR / session_id

    try:
        if session_path.exists():
            SessionManager.cleanup_session(session_path)
            return json.dumps({
                "success": True,
                "message": f"Session 目录已清理: {session_id}"
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "success": False,
                "error": f"Session 不存在: {session_id}"
            }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)
