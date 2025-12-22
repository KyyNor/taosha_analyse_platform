"""
会话读取工具

提供分析会话信息的读取功能，供评分智能体使用
"""

from typing import Optional
from langchain_core.tools import tool

from models import SessionLocal
from repositories.deepagents import AnalysisSessionRepository
from utils.logger import logger


@tool
def read_session_info(session_id: str) -> str:
    """读取分析会话的基本信息

    获取指定会话的问题、状态、耗时等基本信息。

    Args:
        session_id: 分析会话ID

    Returns:
        会话基本信息的文本描述
    """
    try:
        db = SessionLocal()
        try:
            repo = AnalysisSessionRepository(db)
            session = repo.get_by_session_id(session_id)

            if not session:
                return f"未找到会话 {session_id}"

            lines = [
                f"会话ID: {session.session_id}",
                f"分析问题: {session.question}",
                f"问题来源: {session.question_source or '手动输入'}",
                f"状态: {session.status}",
            ]

            if session.duration_seconds:
                lines.append(f"耗时: {session.duration_seconds:.1f} 秒")

            if session.start_time:
                lines.append(f"开始时间: {session.start_time.isoformat()}")

            if session.end_time:
                lines.append(f"结束时间: {session.end_time.isoformat()}")

            if session.report_path:
                lines.append(f"报告路径: {session.report_path}")

            return "\n".join(lines)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"读取会话信息失败: {e}")
        return f"读取会话信息时出错: {str(e)}"


@tool
def read_session_report(session_id: str) -> str:
    """读取分析会话的 HTML 报告内容

    获取指定会话生成的分析报告。

    Args:
        session_id: 分析会话ID

    Returns:
        报告 HTML 内容或错误信息
    """
    try:
        db = SessionLocal()
        try:
            repo = AnalysisSessionRepository(db)
            session = repo.get_by_session_id(session_id)

            if not session:
                return f"未找到会话 {session_id}"

            if not session.report_content:
                return f"会话 {session_id} 没有报告内容"

            # 返回报告内容（可能很长）
            content = session.report_content
            if len(content) > 10000:
                return content[:10000] + f"\n\n... (报告内容过长，已截断，完整长度: {len(content)} 字符)"

            return content

        finally:
            db.close()

    except Exception as e:
        logger.error(f"读取会话报告失败: {e}")
        return f"读取会话报告时出错: {str(e)}"


@tool
def read_session_llm_output(session_id: str) -> str:
    """读取分析会话中大模型的完整输出

    获取指定会话中大模型生成的所有文本输出，包括分析过程和结论。

    Args:
        session_id: 分析会话ID

    Returns:
        LLM 输出内容或错误信息
    """
    try:
        db = SessionLocal()
        try:
            repo = AnalysisSessionRepository(db)
            session = repo.get_by_session_id(session_id)

            if not session:
                return f"未找到会话 {session_id}"

            if not session.llm_output:
                return f"会话 {session_id} 没有 LLM 输出记录"

            # 返回 LLM 输出
            output = session.llm_output
            if len(output) > 15000:
                return output[:15000] + f"\n\n... (输出过长，已截断，完整长度: {len(output)} 字符)"

            return output

        finally:
            db.close()

    except Exception as e:
        logger.error(f"读取 LLM 输出失败: {e}")
        return f"读取 LLM 输出时出错: {str(e)}"


def get_session_data(session_id: str) -> Optional[dict]:
    """获取会话完整数据（内部使用）

    Args:
        session_id: 分析会话ID

    Returns:
        会话数据字典或 None
    """
    try:
        db = SessionLocal()
        try:
            repo = AnalysisSessionRepository(db)
            session = repo.get_by_session_id(session_id)

            if not session:
                return None

            return {
                "session_id": session.session_id,
                "question": session.question,
                "question_source": session.question_source,
                "status": session.status,
                "start_time": session.start_time.isoformat() if session.start_time else None,
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "duration_seconds": session.duration_seconds,
                "report_path": session.report_path,
                "report_content": session.report_content,
                "llm_output": session.llm_output,
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"获取会话数据失败: {e}")
        return None
