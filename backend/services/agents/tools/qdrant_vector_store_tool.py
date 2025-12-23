"""
知识库检索工具
基于 Qdrant 向量数据库的知识库检索功能
"""

import json
from typing import Optional, List
from langfuse import observe
from utils.logger import logger


@observe(name="search_knowledge_base")
def search_knowledge_base(
    query: str,
    top_k: int = 5,
    search_mode: str = "hybrid",
    score_threshold: Optional[float] = None
) -> str:
    """
    在知识库中检索相关文档和知识，知识库中包括表结构、关联关系等信息，如需确认可用表请使用本方法检索。

    Args:
        query: 查询文本。描述你想要查找的内容。

        top_k: 返回结果数量，默认 5 条。建议范围 3-10

        search_mode: 搜索模式，可选值:
                    - "vector_only": 纯向量语义搜索，适合概念理解和语义相似
                    - "fulltext_only": 纯全文关键词搜索，适合精确匹配
                    - "hybrid": 混合搜索（推荐），结合语义和关键词

        score_threshold: 分数阈值，仅返回分数高于此值的结果。设置为 None 则不过滤。

    Returns:
        JSON 格式的检索结果字符串，包含以下字段:
        - success: bool, 是否成功
        - query: str, 原始查询
        - result_count: int, 返回的结果数量
        - results: list, 检索结果列表，每个结果包含:
            - id: str, 文档ID
            - content: str, 文档内容
            - score: float, 相似度分数
            - rerank_score: float, 重排序分数
            - metadata: dict, 元数据（如来源、标签等）
        - error: str, 错误信息（仅在失败时）

    Examples:
        # 语义搜索
        search_knowledge_base("什么是用户留存率", top_k=5)

        # 精确关键词搜索
        search_knowledge_base("DAU MAU", search_mode="fulltext_only")

        # 混合搜索并设置分数阈值
        search_knowledge_base("风控规则配置", search_mode="hybrid", score_threshold=0.6)
    """
    logger.info(f"知识库检索: {query[:50]}... (mode={search_mode}, top_k={top_k})")

    try:
        # 延迟导入，避免循环依赖和启动时的初始化问题
        from services.vector_store.qdrant_vector_store import qdrant_vector_store

        # 执行检索
        results = qdrant_vector_store.search(
            query=query,
            top_k=top_k,
            search_mode=search_mode,
            score_threshold=score_threshold
        )

        # 格式化结果
        formatted_results = []
        for item in results:
            formatted_results.append({
                "id": item.get("id", ""),
                "content": item.get("content", ""),
                "score": round(item.get("score", 0.0), 4),
                "rerank_score": round(item.get("rerank_score", 0.0), 4),
                "metadata": {
                    k: v for k, v in item.get("metadata", {}).items()
                    if k not in ["content", "id"]  # 排除重复字段
                }
            })

        logger.info(f"知识库检索成功，返回 {len(formatted_results)} 条结果")

        return json.dumps({
            "success": True,
            "query": query,
            "search_mode": search_mode,
            "result_count": len(formatted_results),
            "results": formatted_results
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"知识库检索失败: {e}")
        return json.dumps({
            "success": False,
            "query": query,
            "error": str(e),
            "result_count": 0,
            "results": []
        }, ensure_ascii=False)
