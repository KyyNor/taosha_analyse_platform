"""
历史分析记录工具

提供历史分析问题和结果的查询功能，供问题提出智能体使用
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import tool

from models import SessionLocal
from repositories.deepagents import AnalysisSessionRepository
from utils.logger import logger


@tool
def get_analysis_history(limit: int = 10) -> str:
    """获取历史分析问题和评分摘要

    查询最近完成的分析会话，包括问题、来源、耗时和评分。
    用于了解已经分析过的主题，避免重复分析。

    Args:
        limit: 返回的历史记录数量，默认10条

    Returns:
        历史分析记录的文本摘要
    """
    try:
        db = SessionLocal()
        try:
            repo = AnalysisSessionRepository(db)
            summaries = repo.get_history_summary(limit=limit)

            if not summaries:
                return "暂无历史分析记录。这是一个全新的分析平台，请提出有价值的分析主题。"

            result_lines = [f"最近 {len(summaries)} 条历史分析记录：\n"]

            for i, summary in enumerate(summaries, 1):
                line = f"{i}. 问题: {summary['question']}"
                if summary.get("question_source"):
                    line += f" (来源: {summary['question_source']})"
                if summary.get("duration_seconds"):
                    line += f" [耗时: {summary['duration_seconds']:.1f}秒]"
                if summary.get("overall_score"):
                    line += f" [评分: {summary['overall_score']}分]"
                if summary.get("created_at"):
                    line += f" [{summary['created_at'][:10]}]"
                result_lines.append(line)

            result_lines.append("\n请基于以上历史记录，提出新的、有价值的分析主题，避免重复。")
            return "\n".join(result_lines)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"获取历史分析记录失败: {e}")
        return f"获取历史分析记录时出错: {str(e)}。请继续提出分析主题。"


@tool
def search_analysis_history(keyword: str) -> str:
    """根据关键词搜索历史分析记录

    搜索历史分析问题中包含指定关键词的记录。
    用于检查某个主题是否已经分析过。

    Args:
        keyword: 搜索关键词

    Returns:
        匹配的历史分析记录
    """
    try:
        db = SessionLocal()
        try:
            repo = AnalysisSessionRepository(db)
            sessions = repo.search_by_question(keyword)

            if not sessions:
                return f"没有找到包含 '{keyword}' 的历史分析记录。这个主题可以作为新的分析方向。"

            result_lines = [f"找到 {len(sessions)} 条包含 '{keyword}' 的历史分析记录：\n"]

            for i, session in enumerate(sessions[:5], 1):  # 最多显示5条
                line = f"{i}. {session.question}"
                if session.status:
                    line += f" [状态: {session.status}]"
                result_lines.append(line)

            if len(sessions) > 5:
                result_lines.append(f"\n... 还有 {len(sessions) - 5} 条记录")

            return "\n".join(result_lines)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"搜索历史分析记录失败: {e}")
        return f"搜索历史分析记录时出错: {str(e)}"


def get_history_for_prompt(limit: int = 10) -> List[Dict[str, Any]]:
    """获取历史分析记录（内部使用，返回原始数据）

    Args:
        limit: 返回的历史记录数量

    Returns:
        历史分析记录列表
    """
    try:
        db = SessionLocal()
        try:
            repo = AnalysisSessionRepository(db)
            return repo.get_history_summary(limit=limit)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"获取历史分析记录失败: {e}")
        return []
