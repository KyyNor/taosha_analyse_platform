"""
基础 LLM 服务 - 提供原始的大模型调用能力
"""

import json
from typing import List, Dict, Optional, Any

from langchain_openai import ChatOpenAI
from utils.logger import logger
from utils.config import settings


class BaseLLMService:
    """基础 LLM 服务

    提供对 OpenAI 兼容 API 的原始调用能力（无任何业务逻辑）
    """

    def __init__(self, llm_client = None):
        """初始化基础 LLM 服务

        Args:
            llm_client: OpenAI 兼容的客户端（通常是 ChatOpenAI 实例）
        """

        if llm_client is None:
            openai_client = ChatOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                temperature=settings.openai_temperature,
                model=settings.openai_model,
                profile={
                    "max_input_tokens": 180000
                }
            )
            self.client = openai_client
        else:
            self.client = llm_client
        
        logger.info("LLM service 初始化完毕")
