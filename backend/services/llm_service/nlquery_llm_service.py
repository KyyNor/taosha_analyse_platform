"""
NL2SQL 专用的 LLM 服务 - 业务级别的 SQL 生成和验证
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from .base_llm_service import BaseLLMService
from utils.prompt_template_renderer import PromptTemplateRenderer
from utils.logger import logger
from datetime import datetime


class NLQueryLLMService(BaseLLMService):
    """NL2SQL 专用的 LLM 服务

    提供业务级别的 SQL 生成、重试、验证等功能
    扩展 BaseLLMService 的基础能力，添加业务逻辑
    """

    def __init__(self, llm_client = None, config: Dict[str, Any] = None,
                 template_service=None):
        """初始化 NLQueryLLMService

        Args:
            llm_client: OpenAI 兼容的客户端
            config: 配置字典
            template_service: 提示词模板服务（可选）
        """
        super().__init__(llm_client, config)

        self.template_renderer = PromptTemplateRenderer(template_service)
        self.template_service = template_service

        logger.info("NLQueryLLMService 初始化完成")

    # ========== SQL 生成方法 ==========

    def generate_sql(self,
                     user_input: str,
                     context: str,
                     template_name: str = "sql_generation",
                     temperature: Optional[float] = None) -> Dict[str, Any]:
        """生成 SQL 查询 - 业务级别的 SQL 生成

        使用提示词模板和上下文生成 SQL

        Args:
            user_input: 用户的自然语言输入
            context: 数据库元数据和术语表上下文
            template_name: 提示词模板名称
            temperature: 温度参数（覆盖默认值）

        Returns:
            {
                "success": bool,
                "sql": str,
                "explanation": str,
                "confidence": float,  # 0.0-1.0
                "error": str (if success=False)
            }
        """
        try:
            logger.info(f"生成 SQL: user_input={user_input[:50]}...")

            # 1. 构建提示词
            prompt_params = {
                "user_input": user_input,
                "context": context,
                "current_date": datetime.now().strftime("%Y-%m-%d")
            }

            # 尝试从模板生成，如果失败则使用默认提示词
            default_template = self._get_default_sql_generation_template()

            try:
                system_prompt = self.template_renderer.render_template(
                    template_name, prompt_params, default_template
                )
            except Exception as e:
                logger.warning(f"模板渲染失败，使用默认模板: {e}")
                system_prompt = self._get_default_sql_generation_template().format(
                    context=context, user_input=user_input
                )

            # 2. 构建消息
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # 3. 调用 LLM 生成
            temp = temperature if temperature is not None else self.config.get('temperature', 0.1)
            response_text = self.call(
                messages,
                temperature=temp,
                max_tokens=self.config.get('max_tokens', 2000)
            )

            # 4. 解析响应
            result = self._parse_sql_response(response_text)

            if result.get("success"):
                logger.info(f"SQL 生成成功: {result['sql'][:100]}...")
            else:
                logger.warning(f"SQL 解析失败: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"SQL 生成失败: {e}")
            return {
                "success": False,
                "sql": "",
                "explanation": "",
                "confidence": 0.0,
                "error": str(e)
            }

    def retry_sql_generation(self,
                           user_input: str,
                           context: str,
                           previous_sql: str,
                           error_message: str,
                           template_name: str = "sql_retry",
                           temperature: Optional[float] = None) -> Dict[str, Any]:
        """重试 SQL 生成 - 基于错误反馈的 SQL 重新生成

        当 SQL 执行失败或验证不通过时，使用错误信息提示 LLM 重新生成

        Args:
            user_input: 用户的自然语言输入
            context: 数据库元数据和术语表上下文
            previous_sql: 之前失败的 SQL
            error_message: 执行或验证的错误信息
            template_name: 提示词模板名称
            temperature: 温度参数

        Returns:
            {
                "success": bool,
                "sql": str,
                "explanation": str,
                "confidence": float,
                "error": str (if success=False),
                "retry_count": int
            }
        """
        try:
            logger.info(f"重试 SQL 生成: error={error_message[:50]}...")

            # 1. 构建重试提示词
            prompt_params = {
                "user_input": user_input,
                "context": context,
                "previous_sql": previous_sql,
                "error_message": error_message
            }

            default_template = self._get_default_sql_retry_template()

            try:
                system_prompt = self.template_renderer.render_template(
                    template_name, prompt_params, default_template
                )
            except Exception as e:
                logger.warning(f"重试模板渲染失败，使用默认模板: {e}")
                system_prompt = default_template.format(
                    context=context,
                    user_input=user_input,
                    previous_sql=previous_sql,
                    error_message=error_message
                )

            # 2. 构建消息（提高温度以增加多样性）
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # 使用更高的温度促进多样性
            retry_temp = temperature if temperature is not None else 0.3

            response_text = self.call(
                messages,
                temperature=retry_temp,
                max_tokens=self.config.get('max_tokens', 2000)
            )

            # 3. 解析响应
            result = self._parse_sql_response(response_text)
            result["retry_count"] = 1

            if result.get("success"):
                logger.info(f"SQL 重试成功: {result['sql'][:100]}...")
            else:
                logger.warning(f"SQL 重试解析失败")

            return result

        except Exception as e:
            logger.error(f"SQL 重试生成失败: {e}")
            return {
                "success": False,
                "sql": "",
                "explanation": "",
                "confidence": 0.0,
                "error": str(e),
                "retry_count": 1
            }

    def validate_input_clarity(self,
                              user_input: str,
                              context: str,
                              sql_query: str,
                              flow_type: str = "fast",
                              temperature: Optional[float] = None) -> Dict[str, Any]:
        """验证输入清晰度 - 检查用户输入的清晰性和 SQL 的对应性

        在执行 SQL 前进行验证，确保 SQL 符合用户意图

        Args:
            user_input: 用户的自然语言输入
            context: 数据库元数据和术语表上下文
            sql_query: 生成的 SQL 查询
            flow_type: 流程类型 ("fast" 或 "thorough")
            temperature: 温度参数

        Returns:
            {
                "success": bool,
                "is_clear": bool,
                "confidence": float,  # 0.0-1.0
                "details": str,
                "suggestions": List[str],
                "error": str (if success=False)
            }
        """
        try:
            logger.info(f"验证输入清晰度: flow_type={flow_type}")

            # 1. 构建验证提示词
            prompt_params = {
                "user_input": user_input,
                "context": context,
                "sql_query": sql_query,
                "flow_type": flow_type
            }

            default_template = self._get_default_validation_template()

            try:
                system_prompt = self.template_renderer.render_template(
                    f"input_validation_{flow_type}", prompt_params, default_template
                )
            except Exception as e:
                logger.warning(f"验证模板渲染失败，使用默认模板: {e}")
                system_prompt = default_template.format(
                    context=context,
                    user_input=user_input,
                    sql_query=sql_query
                )

            # 2. 调用 LLM 进行验证
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            temp = temperature if temperature is not None else 0.1

            response_text = self.call_with_json_mode(
                messages,
                temperature=temp
            )

            # 3. 解析验证结果
            if isinstance(response_text, dict):
                validation_result = response_text
            else:
                validation_result = json.loads(response_text)

            logger.info(f"输入验证完成: is_clear={validation_result.get('is_clear')}")

            return {
                "success": True,
                "is_clear": validation_result.get("is_clear", False),
                "confidence": validation_result.get("confidence", 0.5),
                "details": validation_result.get("details", ""),
                "suggestions": validation_result.get("suggestions", [])
            }

        except json.JSONDecodeError as e:
            logger.error(f"验证结果 JSON 解析失败: {e}")
            return {
                "success": False,
                "is_clear": False,
                "confidence": 0.0,
                "details": "",
                "suggestions": [],
                "error": f"JSON 解析失败: {e}"
            }
        except Exception as e:
            logger.error(f"输入验证失败: {e}")
            return {
                "success": False,
                "is_clear": False,
                "confidence": 0.0,
                "details": "",
                "suggestions": [],
                "error": str(e)
            }

    # ========== SQL 解释方法 ==========

    def explain_sql(self,
                   sql_query: str,
                   user_input: str = "",
                   template_name: str = "sql_explanation",
                   temperature: Optional[float] = None) -> Dict[str, Any]:
        """解释 SQL 查询含义

        为用户解释生成的 SQL 查询的含义

        Args:
            sql_query: SQL 查询语句
            user_input: 用户的原始输入（可选）
            template_name: 提示词模板名称
            temperature: 温度参数

        Returns:
            {
                "success": bool,
                "explanation": str,
                "summary": str,
                "error": str (if success=False)
            }
        """
        try:
            logger.info(f"解释 SQL: {sql_query[:50]}...")

            # 1. 构建解释提示词
            prompt_params = {
                "sql_query": sql_query,
                "user_input": user_input
            }

            default_template = self._get_default_sql_explanation_template()

            try:
                system_prompt = self.template_renderer.render_template(
                    template_name, prompt_params, default_template
                )
            except Exception as e:
                logger.warning(f"解释模板渲染失败，使用默认模板: {e}")
                system_prompt = default_template.format(
                    sql_query=sql_query, user_input=user_input
                )

            # 2. 调用 LLM 解释
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            temp = temperature if temperature is not None else 0.2

            response_text = self.call(
                messages,
                temperature=temp,
                max_tokens=1000
            )

            logger.info("SQL 解释完成")

            # 3. 生成摘要
            summary = response_text[:100] + "..." if len(response_text) > 100 else response_text

            return {
                "success": True,
                "explanation": response_text,
                "summary": summary
            }

        except Exception as e:
            logger.error(f"SQL 解释失败: {e}")
            return {
                "success": False,
                "explanation": "",
                "summary": "",
                "error": str(e)
            }

    # ========== 内部工具方法 ==========

    def _parse_sql_response(self, response_text: str) -> Dict[str, Any]:
        """解析 LLM 生成的 SQL 响应

        尝试从响应中提取 SQL 和解释

        Args:
            response_text: LLM 的原始响应文本

        Returns:
            {
                "success": bool,
                "sql": str,
                "explanation": str,
                "confidence": float,
                "error": str (if success=False)
            }
        """
        try:
            # 1. 尝试解析 JSON 格式（首选）
            try:
                parsed = json.loads(response_text)
                if isinstance(parsed, dict):
                    sql = parsed.get("sql", "").strip()
                    explanation = parsed.get("explanation", "")
                    confidence = parsed.get("confidence", 0.8)

                    if sql:
                        return {
                            "success": True,
                            "sql": sql,
                            "explanation": explanation,
                            "confidence": confidence
                        }
            except json.JSONDecodeError:
                pass

            # 2. 尝试从文本中提取 SQL（正则表达式）
            import re

            # 查找 SQL 关键字
            sql_patterns = [
                r'```sql\s*(.*?)\s*```',  # SQL 代码块
                r'```\s*((?:SELECT|INSERT|UPDATE|DELETE|WITH)[\s\S]*?)\s*```',  # 通用代码块
                r'((?:SELECT|INSERT|UPDATE|DELETE|WITH).+?;)'  # 完整 SQL（带分号，贪心）
            ]

            sql_text = None
            for pattern in sql_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE | re.DOTALL)
                if matches:
                    sql_text = matches[0].strip()
                    if sql_text and not sql_text.endswith(';'):
                        sql_text += ';'
                    if sql_text:  # 只有在有内容时才break
                        break

            if sql_text:
                return {
                    "success": True,
                    "sql": sql_text.strip(),
                    "explanation": response_text,
                    "confidence": 0.7
                }

            # 3. 直接使用整个响应作为 SQL（最后的尝试）
            if response_text.strip():
                return {
                    "success": True,
                    "sql": response_text.strip(),
                    "explanation": "",
                    "confidence": 0.5
                }

            # 如果都失败，返回错误
            return {
                "success": False,
                "sql": "",
                "explanation": "",
                "confidence": 0.0,
                "error": "无法从响应中提取 SQL"
            }

        except Exception as e:
            logger.error(f"SQL 响应解析异常: {e}")
            return {
                "success": False,
                "sql": "",
                "explanation": "",
                "confidence": 0.0,
                "error": str(e)
            }

    # ========== 默认模板方法 ==========

    @staticmethod
    def _get_default_sql_generation_template() -> str:
        """获取默认的 SQL 生成提示词模板"""
        return """你是一个 SQL 专家。根据用户的自然语言输入和提供的数据库上下文，生成准确的 SQL 查询。

数据库上下文信息：
{context}

用户输入：{user_input}

请生成对应的 SQL 查询。返回 JSON 格式的响应，包含以下字段：
- sql: 生成的 SQL 查询语句
- explanation: SQL 查询的简短解释
- confidence: 置信度（0.0-1.0）

示例响应：
{{
  "sql": "SELECT * FROM users WHERE age > 18;",
  "explanation": "查询年龄大于18岁的用户",
  "confidence": 0.95
}}"""

    @staticmethod
    def _get_default_sql_retry_template() -> str:
        """获取默认的 SQL 重试提示词模板"""
        return """你是一个 SQL 专家。用户的 SQL 查询执行失败了，需要你根据错误信息重新生成查询。

数据库上下文信息：
{context}

用户输入：{user_input}

之前失败的 SQL：
{previous_sql}

错误信息：
{error_message}

请根据错误信息修正 SQL 查询。返回 JSON 格式的响应，包含：
- sql: 修正后的 SQL 查询语句
- explanation: 修正说明
- confidence: 置信度（0.0-1.0）"""

    @staticmethod
    def _get_default_validation_template() -> str:
        """获取默认的输入验证提示词模板"""
        return """你是一个 SQL 查询验证专家。请验证用户的自然语言输入和生成的 SQL 是否匹配。

数据库上下文信息：
{context}

用户输入：{user_input}

生成的 SQL：{sql_query}

请评估：
1. 用户输入的清晰度（是否明确表达了查询意图）
2. 生成的 SQL 是否正确对应了用户的意图
3. 提供改进建议

返回 JSON 格式的响应：
{{
  "is_clear": true/false,
  "confidence": 0.0-1.0,
  "details": "详细说明",
  "suggestions": ["建议1", "建议2"]
}}"""

    @staticmethod
    def _get_default_sql_explanation_template() -> str:
        """获取默认的 SQL 解释提示词模板"""
        return """请用自然语言解释以下 SQL 查询的含义。

SQL 查询：
{sql_query}

用户原始输入（如有）：{user_input}

请用简洁、清晰的语言解释这个 SQL 查询做了什么，它的执行逻辑是怎样的。"""

