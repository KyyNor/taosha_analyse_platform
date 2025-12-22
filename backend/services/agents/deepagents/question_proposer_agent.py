"""
问题提出智能体

阅读历史分析问题，查询业务数据概况，提出5个有价值的分析主题，并标记最有价值的1个主题。
使用普通 LangChain ReAct Agent，不使用 deepagents 框架。
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langfuse.decorators import observe

from services.llm_service.base_llm_service import BaseLLMService
from services.agents.tools.sql_query_tool import sql_query
from services.agents.tools.common_tools import get_date_range
from services.agents.tools.history_analysis_tool import (
    get_analysis_history,
    search_analysis_history
)
from utils.logger import logger


# 问题提出智能体系统提示词
QUESTION_PROPOSER_PROMPT = """你是淘沙分析平台的分析选题专家。

## 任务
1. 使用 get_analysis_history 工具阅读历史分析问题，了解已完成的分析
2. 可选：使用 sql_query 工具查询业务数据概况，了解当前数据状态
3. 提出5个有价值的分析主题
4. 标记最有价值的1个主题作为推荐

## 选题原则
- 避免与历史分析问题重复
- 选择有业务价值的分析方向
- 考虑数据可获取性和分析可行性
- 优先选择能产生可操作洞察的主题

## 输出格式
请严格按照以下 JSON 格式输出：
```json
{
    "topics": [
        {
            "id": 1,
            "title": "分析主题标题",
            "description": "详细描述该分析的目标和范围",
            "data_requirements": ["需要的数据表或字段"],
            "expected_insights": "预期能获得的洞察",
            "priority": "high/medium/low",
            "is_recommended": true
        },
        {
            "id": 2,
            "title": "第二个分析主题",
            "description": "...",
            "data_requirements": ["..."],
            "expected_insights": "...",
            "priority": "medium",
            "is_recommended": false
        }
    ],
    "recommended_topic_id": 1,
    "recommendation_reason": "推荐这个主题的原因"
}
```

注意：
- topics 数组必须包含5个主题
- 只有1个主题的 is_recommended 为 true
- recommended_topic_id 必须与 is_recommended=true 的主题 id 一致
"""


class QuestionProposerAgent:
    """问题提出智能体"""

    def __init__(self):
        """初始化问题提出智能体"""
        self.llm_service = BaseLLMService()
        self.agent = None

        logger.info("QuestionProposerAgent 初始化完成")

    def create_agent(self) -> None:
        """创建 Agent 实例"""
        try:
            tools = [
                get_analysis_history,
                search_analysis_history,
                get_date_range,
                # sql_query,  # 可选：查询业务数据概况
            ]

            self.agent = create_agent(
                model=self.llm_service.client,
                tools=tools,
                system_prompt=QUESTION_PROPOSER_PROMPT,
            )

            logger.info("QuestionProposerAgent Agent 创建成功")

        except Exception as e:
            logger.error(f"QuestionProposerAgent Agent 创建失败: {e}")
            raise

    @observe(name="propose_topics")
    def propose_topics(self, context: Optional[str] = None) -> Dict[str, Any]:
        """提出分析主题

        Args:
            context: 可选的业务上下文信息

        Returns:
            包含分析主题的字典
        """
        if not self.agent:
            self.create_agent()

        start_time = datetime.now()

        # 构建用户消息
        user_message = "请阅读历史分析记录，然后提出5个有价值的分析主题。"
        if context:
            user_message += f"\n\n业务上下文：{context}"

        try:
            # 执行 Agent
            result = self.agent.invoke({
                "messages": [HumanMessage(content=user_message)]
            })

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 提取 AI 输出
            ai_output = self._extract_ai_output(result)

            # 尝试解析 JSON
            topics_data = self._parse_topics_json(ai_output)

            logger.info(f"问题提出完成，耗时: {duration:.2f}秒")

            return {
                "success": True,
                "topics": topics_data.get("topics", []),
                "recommended_topic_id": topics_data.get("recommended_topic_id"),
                "recommendation_reason": topics_data.get("recommendation_reason"),
                "raw_output": ai_output,
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"问题提出失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _extract_ai_output(self, result: Dict[str, Any]) -> str:
        """从结果中提取 AI 输出"""
        try:
            messages = result.get("messages", [])
            if messages:
                for msg in reversed(messages):
                    if hasattr(msg, "content") and msg.content:
                        return str(msg.content)
            return ""
        except Exception as e:
            logger.warning(f"提取 AI 输出失败: {e}")
            return ""

    def _parse_topics_json(self, output: str) -> Dict[str, Any]:
        """从 AI 输出中解析主题 JSON

        Args:
            output: AI 输出文本

        Returns:
            解析后的主题数据
        """
        try:
            # 尝试直接解析
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 代码块
        import re
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", output)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 { ... } 结构
        brace_match = re.search(r"\{[\s\S]*\}", output)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning("无法解析主题 JSON，返回空结构")
        return {"topics": [], "recommended_topic_id": None, "recommendation_reason": None}

    def get_recommended_question(self, context: Optional[str] = None) -> Optional[str]:
        """获取推荐的分析问题

        Args:
            context: 可选的业务上下文

        Returns:
            推荐的分析问题，或 None
        """
        result = self.propose_topics(context)

        if not result.get("success"):
            return None

        topics = result.get("topics", [])
        recommended_id = result.get("recommended_topic_id")

        # 找到推荐的主题
        for topic in topics:
            if topic.get("id") == recommended_id or topic.get("is_recommended"):
                title = topic.get("title", "")
                description = topic.get("description", "")
                return f"{title}。{description}" if description else title

        # 如果没有标记推荐，返回第一个
        if topics:
            topic = topics[0]
            title = topic.get("title", "")
            description = topic.get("description", "")
            return f"{title}。{description}" if description else title

        return None


# 便捷函数
def create_question_proposer_agent() -> QuestionProposerAgent:
    """创建问题提出智能体实例"""
    agent = QuestionProposerAgent()
    agent.create_agent()
    return agent
