"""
Vercel AI SDK 桥接层
将 LangChain Agent 的 astream_events 转换为 Vercel AI SDK 兼容的流式格式
"""
import json
import uuid
from typing import AsyncGenerator, Dict, Any, Optional
from utils.logger import logger


class LangChainToVercelBridge:
    """LangChain 到 Vercel AI SDK 的事件转换桥接"""

    def __init__(self):
        """初始化桥接器"""
        self.tool_call_ids: Dict[str, str] = {}  # 工具名称 -> tool_call_id 映射
        self.current_tool_inputs: Dict[str, Any] = {}  # 存储当前工具的输入参数
        self.current_text_buffer = ""  # 文本缓冲区

    @staticmethod
    def _generate_tool_call_id(tool_name: str, run_id: str = None) -> str:
        """生成工具调用ID"""
        if run_id:
            return f"toolu_{tool_name}_{run_id[:8]}"
        return f"toolu_{tool_name}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _format_sse_message(data: Dict[str, Any]) -> str:
        """
        格式化为 Server-Sent Events 消息格式

        Args:
            data: 消息数据

        Returns:
            SSE格式的字符串
        """
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def convert_stream(self, langchain_stream: AsyncGenerator[dict, None]) -> AsyncGenerator[str, None]:
        """
        将 LangChain 的 astream_events 转换为 Vercel AI SDK 兼容的 SSE 流

        Args:
            langchain_stream: LangChain astream_events 生成器

        Yields:
            SSE 格式的消息字符串
        """
        try:
            # 发送对话开始消息
            yield self._format_sse_message({
                "type": "assistant_message_start",
                "id": f"msg_{uuid.uuid4().hex[:12]}",
                "role": "assistant"
            })

            async for event in langchain_stream:
                event_type = event.get("event")
                event_data = event.get("data", {})
                event_name = event.get("name", "")
                run_id = event.get("run_id", "")

                logger.debug(f"处理LangChain事件: {event_type}, name: {event_name}")

                # 1. 处理文本流（LLM token）
                if event_type == "on_chat_model_stream":
                    content = event_data.get("chunk")
                    if content and hasattr(content, 'content') and content.content:
                        text = content.content
                        self.current_text_buffer += text

                        # 发送文本增量
                        yield self._format_sse_message({
                            "type": "text_delta",
                            "content": text
                        })

                # 2. 处理工具调用开始
                elif event_type == "on_tool_start":
                    tool_name = event_name
                    tool_input = event_data.get("input", {})

                    # 生成 tool_call_id
                    tool_call_id = self._generate_tool_call_id(tool_name, run_id)
                    self.tool_call_ids[tool_name] = tool_call_id
                    self.current_tool_inputs[tool_name] = tool_input

                    logger.info(f"工具调用开始: {tool_name}, tool_call_id: {tool_call_id}")

                    # 发送工具调用开始事件
                    yield self._format_sse_message({
                        "type": "tool_call_start",
                        "toolCallId": tool_call_id,
                        "toolName": tool_name
                    })

                    # 发送工具输入参数
                    yield self._format_sse_message({
                        "type": "tool_call_input",
                        "toolCallId": tool_call_id,
                        "toolName": tool_name,
                        "input": tool_input
                    })

                # 3. 处理工具调用完成
                elif event_type == "on_tool_end":
                    tool_name = event_name
                    tool_output = event_data.get("output")
                    tool_call_id = self.tool_call_ids.get(tool_name)

                    if not tool_call_id:
                        logger.warning(f"未找到工具 {tool_name} 的 tool_call_id")
                        tool_call_id = self._generate_tool_call_id(tool_name)

                    logger.info(f"工具调用完成: {tool_name}, output: {str(tool_output)[:100]}...")

                    # 解析工具输出（如果是JSON字符串）
                    parsed_output = tool_output
                    if isinstance(tool_output, str):
                        try:
                            parsed_output = json.loads(tool_output)
                        except json.JSONDecodeError:
                            parsed_output = {"result": tool_output}

                    # 发送工具调用结果
                    yield self._format_sse_message({
                        "type": "tool_call_result",
                        "toolCallId": tool_call_id,
                        "toolName": tool_name,
                        "result": parsed_output
                    })

                # 4. 处理工具调用错误
                elif event_type == "on_tool_error":
                    tool_name = event_name
                    error_message = str(event_data.get("error", "Unknown error"))
                    tool_call_id = self.tool_call_ids.get(tool_name)

                    if not tool_call_id:
                        tool_call_id = self._generate_tool_call_id(tool_name)

                    logger.error(f"工具调用错误: {tool_name}, error: {error_message}")

                    # 发送工具调用错误
                    yield self._format_sse_message({
                        "type": "tool_call_error",
                        "toolCallId": tool_call_id,
                        "toolName": tool_name,
                        "error": error_message
                    })

                # 5. 处理链结束
                elif event_type == "on_chain_end":
                    logger.info("Agent链执行完成")
                    # 不发送额外事件，继续等待最终完成

            # 发送对话完成消息
            yield self._format_sse_message({
                "type": "assistant_message_complete",
                "content": self.current_text_buffer
            })

            # 发送流结束标记
            yield self._format_sse_message({
                "type": "done"
            })

        except Exception as e:
            logger.error(f"桥接层转换错误: {e}")
            yield self._format_sse_message({
                "type": "error",
                "error": str(e)
            })

    def reset(self):
        """重置桥接器状态"""
        self.tool_call_ids.clear()
        self.current_tool_inputs.clear()
        self.current_text_buffer = ""
