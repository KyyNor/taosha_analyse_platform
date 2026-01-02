"""
会话自动命名中间件
在 Agent 完成对话后自动为新会话生成标题
"""
from typing import Dict, Any, List
from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from services.llm_service.base_llm_service import BaseLLMService
from repositories.chat_repository import ChatRepository
from models.db_base import get_db_session
from utils.logger import logger


class SessionNamingMiddleware(AgentMiddleware):
    """会话自动命名中间件"""
    
    def __init__(self):
        """初始化中间件"""
        super().__init__()
        self.llm_service = BaseLLMService()
    
    async def generate_session_title(self, user_message: str, assistant_response: str) -> str:
        """
        根据用户消息和助手回复生成会话标题
        
        Args:
            user_message: 用户的消息
            assistant_response: 助手的回复
            
        Returns:
            生成的会话标题
        """
        try:
            # 构建提示词
            prompt = f"""请根据以下对话内容，生成一个简洁、准确的会话标题。标题应该：
1. 不超过20个字符
2. 概括对话的主要内容或用户的核心需求
3. 使用中文
4. 不要包含"对话"、"聊天"等词汇
5. 直接返回标题，不要其他解释

用户消息：{user_message[:200]}...

助手回复：{assistant_response[:300]}...

会话标题："""

            # 调用大模型生成标题
            response = await self.llm_service.client.ainvoke(prompt)
            
            # 提取标题内容
            title = response.content.strip()
            
            # 清理标题（移除引号、换行等）
            title = title.replace('"', '').replace("'", '').replace('\n', '').strip()
            
            # 限制长度
            if len(title) > 20:
                title = title[:20] + "..."
            
            # 如果标题为空或太短，使用默认标题
            if not title or len(title) < 2:
                title = "新对话"
                
            logger.info(f"生成会话标题: {title}")
            return title
            
        except Exception as e:
            logger.error(f"生成会话标题失败: {e}")
            return "新对话"
    
    async def update_session_title(self, session_id: str, title: str):
        """
        更新会话标题
        
        Args:
            session_id: 会话ID
            title: 新标题
        """
        try:
            with get_db_session() as db:
                repo = ChatRepository(db)
                repo.update_session_title(session_id, title)
            logger.info(f"会话 {session_id} 标题更新完成: {title}")
        except Exception as e:
            logger.error(f"更新会话标题失败: {e}")
    
    async def after_agent(self, messages: List[BaseMessage], config: Dict[str, Any]) -> List[BaseMessage]:
        """
        在 Agent 完成对话后的钩子
        检查是否为新会话的第一轮对话，如果是则自动生成标题
        
        Args:
            messages: 对话消息列表
            config: 配置信息，包含 thread_id 等
            
        Returns:
            原始消息列表（不修改）
        """
        try:
            # 获取会话配置
            configurable = config.get("configurable", {})
            session_id = configurable.get("thread_id")
            
            if not session_id:
                logger.debug("未找到 session_id，跳过自动命名")
                return messages
            
            # 检查是否为第一轮对话（只有一个用户消息和一个助手回复）
            user_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
            ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
            
            # 只在第一轮对话时触发命名
            if len(user_messages) != 1 or len(ai_messages) != 1:
                logger.debug(f"不是第一轮对话 (用户消息: {len(user_messages)}, AI消息: {len(ai_messages)})，跳过自动命名")
                return messages
            
            # 获取用户消息和助手回复
            user_message = user_messages[0].content
            ai_message = ai_messages[0].content
            
            if not user_message or not ai_message:
                logger.debug("消息内容为空，跳过自动命名")
                return messages
            
            # 检查会话是否已经有自定义标题（不是默认的"新会话"）
            with get_db_session() as db:
                from models.agent_chat_models import ChatSession
                session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
                if session and session.title and session.title != "新会话":
                    logger.debug(f"会话已有自定义标题: {session.title}，跳过自动命名")
                    return messages
            
            # 异步生成并更新标题（不阻塞对话流程）
            import asyncio
            asyncio.create_task(self._auto_name_session(session_id, str(user_message), str(ai_message)))
            
            logger.info(f"已触发会话 {session_id} 的自动命名")
            
        except Exception as e:
            logger.error(f"会话自动命名中间件执行失败: {e}")
        
        return messages
    
    async def _auto_name_session(self, session_id: str, user_message: str, assistant_response: str):
        """
        自动命名会话的内部方法
        
        Args:
            session_id: 会话ID
            user_message: 用户消息
            assistant_response: 助手回复
        """
        try:
            # 生成标题
            title = await self.generate_session_title(user_message, assistant_response)
            
            # 更新会话标题
            await self.update_session_title(session_id, title)
            
        except Exception as e:
            logger.error(f"自动命名会话失败: {e}")