"""
Schema Linking 智能检索工具

基于 SchemaLinkingService 的高级检索能力，使用两阶段筛选流程：
1. 向量检索召回候选表（top_k=10）
2. LLM精确筛选最相关表（top_k=3-5）

此工具已内置 reranker 能力。
"""

import json
from typing import Optional
from langchain.tools import tool, ToolRuntime
from langfuse import observe

from utils.logger import logger
from models.db_base import get_db_session
from services.agents.schema_linking_service import SchemaLinkingService, SchemaLinkingResult
from services.agents.models.deep_agent_context import DataAnalysisContext


@tool
@observe(name="schema_linking_retrieve")
def schema_linking_retrieve(
    question: str,
    candidate_top_k: int = 10,
    selected_top_k: int = 5,
    use_cache: bool = True,
    runtime: Optional[ToolRuntime] = None,
) -> str:
    """
    Schema Linking 智能检索

    使用两阶段筛选流程，从向量数据库中智能检索最相关的表结构：
    1. 向量检索召回候选表（基于语义相似度）
    2. LLM精确筛选最相关表（返回表及其完整schema信息）

    该工具已内置 reranker 能力，无需额外配置。

    Args:
        question: 用户问题，描述需要查询的数据需求
        candidate_top_k: 候选表召回数量，默认10。建议范围 5-20。
        selected_top_k: 最终选中的表数量，默认5。建议范围 3-10。
        use_cache: 是否使用缓存，默认True。相同问题会直接返回缓存结果。

    Returns:
        JSON格式的检索结果字符串，包含以下字段:
        - success: bool, 是否成功
        - question: str, 原始问题
        - candidate_count: int, 向量检索召回的候选表数量
        - selected_count: int, 最终选中的表数量
        - selected_tables: list, 选中的表名列表
        - table_schemas: dict, 每个选中表的完整schema信息 {table_name: schema_str}
        - reasoning: str, 筛选理由
        - use_fallback: bool, 是否使用了降级策略
        - error: str, 错误信息（仅在失败时）

    Examples:
        # 检索与"用户留存"相关的表
        schema_linking_retrieve("查询用户的留存率数据")

        # 自定义召回和筛选数量
        schema_linking_retrieve("风控告警相关数据", candidate_top_k=15, selected_top_k=8)
    """
    _ = runtime  # ToolRuntime 接口要求，当前未使用
    logger.info(
        f"Schema Linking 智能检索: {question[:50]}... "
        f"(candidate_top_k={candidate_top_k}, selected_top_k={selected_top_k})"
    )

    try:
        # 获取数据库会话
        with get_db_session() as db:
            # 初始化 SchemaLinkingService（传入db以查询表元数据）
            service = SchemaLinkingService(db)

            # 调用两阶段检索（同步执行）
            import asyncio
            import inspect

            # 检查 select_relevant_tables 是否是协程函数
            if inspect.iscoroutinefunction(service.select_relevant_tables):
                # 协程函数，使用 asyncio.run
                try:
                    # 尝试在当前线程中运行
                    result = asyncio.run(
                        service.select_relevant_tables(
                            question=question,
                            candidate_top_k=candidate_top_k,
                            selected_top_k=selected_top_k,
                            use_cache=use_cache,
                        ),
                        debug=False
                    )
                except RuntimeError as e:
                    # 如果已有 event loop 在运行，使用同步降级策略
                    logger.warning(f"无法在当前 context 运行异步函数: {e}，使用降级策略")
                    result = SchemaLinkingResult(
                        selected_tables=[],
                        reasoning="当前环境不支持异步调用",
                        candidate_count=0,
                        use_fallback=True
                    )
            else:
                # 非协程函数，直接调用
                result = service.select_relevant_tables(
                    question=question,
                    candidate_top_k=candidate_top_k,
                    selected_top_k=selected_top_k,
                    use_cache=use_cache,
                )

        # 格式化返回结果
        response = {
            "success": True,
            "question": question,
            "candidate_count": result.candidate_count,
            "selected_count": len(result.selected_tables),
            "selected_tables": result.selected_tables,
            "table_schemas": result.table_schemas,
            "reasoning": result.reasoning,
            "use_fallback": result.use_fallback,
        }

        logger.info(
            f"Schema Linking 检索成功: 召回 {result.candidate_count} 个候选表, "
            f"选中 {len(result.selected_tables)} 个表"
        )

        return json.dumps(response, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Schema Linking 检索失败: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "question": question,
            "error": str(e),
            "candidate_count": 0,
            "selected_count": 0,
            "selected_tables": [],
            "table_schemas": {},
        }, ensure_ascii=False)