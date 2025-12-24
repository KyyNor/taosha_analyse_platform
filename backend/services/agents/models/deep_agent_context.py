from dataclasses import dataclass

# ==================== Context Schema ====================

@dataclass
class DataAnalysisContext:
    """数据分析智能体的运行时上下文配置

    这是不可变的上下文，在运行时传递给工具，使工具能够访问会话级别的配置信息
    """
    session_id: str
    """会话ID，用于标识和隔离不同的分析会话"""

    output_dir: str
    """输出目录路径，用于保存分析结果和中间文件"""

    code_execution_timeout: int
    """代码执行的超时时间（秒）"""

    user_id: str = "default"
    """用户ID，用于权限控制和日志追踪"""