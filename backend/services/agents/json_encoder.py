"""
自定义JSON编码器，用于处理LangChain不可序列化的对象
"""
import json
from typing import Any
from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage, AIMessage


class LangChainJSONEncoder(json.JSONEncoder):
    """处理LangChain对象的自定义JSON编码器"""

    def default(self, obj: Any) -> Any:
        """
        处理不可序列化的对象

        Args:
            obj: 待编码的对象

        Returns:
            可序列化的对象
        """
        # 处理LangChain消息对象
        if isinstance(obj, ToolMessage):
            return {
                "type": "tool_message",
                "content": str(obj.content),
                "tool_call_id": getattr(obj, "tool_call_id", None),
                "name": getattr(obj, "name", None)
            }

        if isinstance(obj, (HumanMessage, AIMessage)):
            return {
                "type": obj.__class__.__name__.lower(),
                "content": str(obj.content)
            }

        if isinstance(obj, BaseMessage):
            return {
                "type": "message",
                "content": str(obj.content)
            }

        # 处理其他对象，转为字符串
        if hasattr(obj, '__dict__'):
            try:
                return obj.__dict__
            except Exception:
                return str(obj)

        # 最后的fallback
        return str(obj)


def serialize_event_data(data: Any) -> str:
    """
    将事件数据序列化为JSON字符串

    Args:
        data: 事件数据

    Returns:
        JSON字符串
    """
    return json.dumps(data, cls=LangChainJSONEncoder, ensure_ascii=False)


def to_serializable(obj: Any) -> Any:
    """
    将对象转换为可序列化的格式

    Args:
        obj: 待转换的对象

    Returns:
        可序列化的对象
    """
    if isinstance(obj, ToolMessage):
        return {
            "type": "tool_message",
            "content": str(obj.content),
            "tool_call_id": getattr(obj, "tool_call_id", None),
            "name": getattr(obj, "name", None)
        }

    if isinstance(obj, (HumanMessage, AIMessage)):
        return {
            "type": obj.__class__.__name__.lower(),
            "content": str(obj.content)
        }

    if isinstance(obj, BaseMessage):
        return {
            "type": "message",
            "content": str(obj.content)
        }

    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [to_serializable(item) for item in obj]

    if hasattr(obj, '__dict__'):
        try:
            return obj.__dict__
        except Exception:
            return str(obj)

    return obj
