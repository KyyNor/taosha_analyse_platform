"""
LLM 服务模块 - 统一的大模型调用服务
"""

from .base_llm_service import BaseLLMService
from .nlquery_llm_service import NLQueryLLMService

__all__ = [
    'BaseLLMService',
    'NLQueryLLMService',
]

