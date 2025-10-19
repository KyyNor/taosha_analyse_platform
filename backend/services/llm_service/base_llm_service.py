"""
基础 LLM 服务 - 提供原始的大模型调用能力
"""

import json
from typing import List, Dict, Optional, Any

from utils.logger import logger


class BaseLLMService:
    """基础 LLM 服务

    提供对 OpenAI 兼容 API 的原始调用能力（无任何业务逻辑）
    """

    def __init__(self, llm_client, config: Dict[str, Any]):
        """初始化基础 LLM 服务

        Args:
            llm_client: OpenAI 兼容的客户端（通常是 openai.OpenAI 实例）
            config: 配置字典，应包含：
                - model: 模型名称（如 "gpt-4", "kimi-k2-0905-preview"）
                - temperature: 温度参数（默认 0.1）
                - max_tokens: 最大令牌数（可选）
        """
        self.client = llm_client
        self.config = config

        logger.info(f"LLM 服务初始化: model={config.get('model')}, "
                   f"temperature={config.get('temperature', 0.1)}")

    def call(self,
            messages: List[Dict[str, str]],
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None) -> str:
        """调用 LLM 获取文本响应

        Args:
            messages: 消息列表，格式如 [{"role": "user", "content": "..."}]
            temperature: 温度参数（覆盖默认值）
            max_tokens: 最大令牌数

        Returns:
            模型的文本响应

        Raises:
            RuntimeError: API 调用失败时抛出
        """
        try:
            # 使用提供的温度或默认温度
            temp = temperature if temperature is not None else self.config.get('temperature', 0.1)

            # 构建请求参数
            kwargs = {
                'model': self.config.get('model'),
                'messages': messages,
                'temperature': temp
            }

            # 添加可选参数
            if max_tokens:
                kwargs['max_tokens'] = max_tokens

            logger.debug(f"调用 LLM API: model={kwargs['model']}, "
                        f"messages_count={len(messages)}")

            # 调用 API
            response = self.client.chat.completions.create(**kwargs)

            # 提取响应文本
            response_text = response.choices[0].message.content

            logger.debug(f"LLM 响应成功: {len(response_text)} 字符")
            return response_text

        except Exception as e:
            logger.error(f"LLM API 调用失败: {e}")
            raise RuntimeError(f"LLM 调用失败: {e}")

    def call_with_json_mode(self,
                           messages: List[Dict[str, str]],
                           temperature: Optional[float] = None) -> Dict:
        """调用 LLM 获取 JSON 格式的响应

        适用于需要返回结构化数据的场景（如模型支持 JSON mode 时）

        Args:
            messages: 消息列表
            temperature: 温度参数

        Returns:
            解析后的 JSON 对象

        Raises:
            RuntimeError: 调用失败或 JSON 解析失败时抛出
        """
        try:
            # 使用提供的温度或默认温度
            temp = temperature if temperature is not None else self.config.get('temperature', 0.1)

            # 构建请求参数
            kwargs = {
                'model': self.config.get('model'),
                'messages': messages,
                'temperature': temp,
                'response_format': {"type": "json_object"}  # 要求返回 JSON
            }

            logger.debug(f"调用 LLM API (JSON 模式): model={kwargs['model']}")

            # 调用 API
            response = self.client.chat.completions.create(**kwargs)

            # 提取响应文本
            response_text = response.choices[0].message.content

            # 解析 JSON
            try:
                result = json.loads(response_text)
                logger.debug("JSON 解析成功")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析失败: {e}，原始响应: {response_text[:100]}")
                raise RuntimeError(f"JSON 解析失败: {e}")

        except Exception as e:
            logger.error(f"LLM JSON 模式调用失败: {e}")
            raise RuntimeError(f"LLM 调用失败: {e}")

    def get_model_name(self) -> str:
        """获取当前使用的模型名称

        Returns:
            模型名称
        """
        return self.config.get('model', 'unknown')

    def get_temperature(self) -> float:
        """获取当前温度参数

        Returns:
            温度参数
        """
        return self.config.get('temperature', 0.1)
