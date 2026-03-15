"""
知识库检索工具
检索业务术语、关联配置、FineReport报表等非表结构知识

与 schema_linking_retrieve 工具的区别：
- schema_linking_retrieve: 只检索表结构，使用两阶段筛选（向量+LLM）
- knowledge_base_retrieve: 只检索非表结构知识（术语、关联、报表），使用向量检索
"""

import json
from typing import Optional, List
from langchain.tools import tool, ToolRuntime
from langfuse import observe

from utils.logger import logger


@tool
@observe(name="knowledge_base_retrieve")
def knowledge_base_retrieve(
    query: str,
    top_k: int = 5,
    resource_types: Optional[List[str]] = None,
    search_mode: str = "hybrid",
    runtime: Optional[ToolRuntime] = None,
) -> str:
    """
    知识库检索

    检索业务知识库中的非表结构知识，包括：
    - 业务术语（glossary）：业务概念定义、SQL问答示例、字典映射规则
    - 关联配置（relation）：表之间的关联关系
    - FineReport报表（fine_report）：报表配置信息
    - 知识片段（knowledge_fragment）：LLM生成或用户提取的知识片段

    与 schema_linking_retrieve 的区别：
    - schema_linking_retrieve: 检索表结构，返回表的完整schema
    - knowledge_base_retrieve: 检索业务知识，返回术语/关联/报表/知识片段信息

    Args:
        query: 查询文本，描述你想要查找的内容
        top_k: 返回结果数量，默认5条。建议范围 3-10。
        resource_types: 资源类型列表，默认 ["glossary", "relation", "fine_report", "knowledge_fragment"]
                     - ["glossary"]: 只检索业务术语
                     - ["relation"]: 只检索关联配置
                     - ["fine_report"]: 只检索报表
                     - ["knowledge_fragment"]: 只检索知识片段
                     - ["glossary", "knowledge_fragment"]: 检索术语和知识片段
        search_mode: 搜索模式，可选值:
                    - "vector_only": 纯向量语义搜索，适合概念理解和语义相似
                    - "fulltext_only": 纯全文关键词搜索，适合精确匹配
                    - "hybrid": 混合搜索（推荐），结合语义和关键词

    Returns:
        JSON格式字符串，包含以下字段:
        - success: bool, 是否成功
        - query: str, 原始查询
        - search_mode: str, 使用的搜索模式
        - result_count: int, 返回的总结果数量
        - results: list, 检索结果列表，每个结果包含:
            - id: str, 文档ID
            - content: str, 文档内容
            - score: float, 相似度分数
            - rerank_score: float, 重排序分数
            - resource_type: str, 资源类型（glossary/relation/fine_report/knowledge_fragment）
            - metadata: dict, 元数据（如来源、标签等）
        - error: str, 错误信息（仅在失败时）

    Examples:
        # 检索业务术语（默认）
        knowledge_base_retrieve("什么是用户留存率")

        # 只检索关联配置
        knowledge_base_retrieve("用户和订单的关联关系", resource_types=["relation"])

        # 只检索报表
        knowledge_base_retrieve("销售业绩报表", resource_types=["fine_report"])

        # 检索知识片段
        knowledge_base_retrieve("积分计算规则", resource_types=["knowledge_fragment"])

        # 使用关键词精确搜索
        knowledge_base_retrieve("DAU MAU", search_mode="fulltext_only")
    """
    _ = runtime  # ToolRuntime 接口要求，当前未使用
    logger.info(f"知识库检索: {query[:50]}... (mode={search_mode}, top_k={top_k})")

    try:
        # 延迟导入，避免循环依赖和启动时的初始化问题
        from services.vector_store.qdrant_vector_store import qdrant_vector_store
        from qdrant_client.http.models import Filter, FieldCondition, MatchAny

        # 默认检索所有非表结构资源
        if resource_types is None:
            resource_types = ["glossary", "relation", "fine_report", "knowledge_fragment"]

        # 构建过滤条件：只检索指定的资源类型，排除表结构
        logger.info(f"检索资源类型: {resource_types}")
        filters = Filter(must=[
            FieldCondition(key="resource_type", match=MatchAny(any=resource_types))
        ])

        # 执行检索
        results = qdrant_vector_store.search(
            query=query,
            top_k=top_k,
            search_mode=search_mode,
            filters=filters
        )

        # 格式化结果
        formatted_results = []
        for item in results:
            metadata = item.get("metadata", {})
            resource_type = metadata.get("resource_type", "unknown")

            formatted_results.append({
                "id": item.get("id", ""),
                "content": item.get("content", ""),
                "score": round(item.get("score", 0.0), 4),
                "rerank_score": round(item.get("rerank_score", 0.0), 4),
                "resource_type": resource_type,
                "metadata": {
                    k: v for k, v in metadata.items()
                    if k not in ["content", "id"]  # 排除重复字段
                }
            })

        # 按资源类型分组统计
        type_counts = {}
        for r in formatted_results:
            rt = r["resource_type"]
            type_counts[rt] = type_counts.get(rt, 0) + 1

        logger.info(
            f"知识库检索成功，返回 {len(formatted_results)} 条结果 "
            f"(细分: {type_counts})"
        )

        return json.dumps({
            "success": True,
            "query": query,
            "search_mode": search_mode,
            "result_count": len(formatted_results),
            "type_counts": type_counts,
            "results": formatted_results
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"知识库检索失败: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "query": query,
            "error": str(e),
            "result_count": 0,
            "results": []
        }, ensure_ascii=False)
