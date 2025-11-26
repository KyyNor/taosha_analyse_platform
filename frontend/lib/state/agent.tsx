"use client";
import { createContext, useContext, useMemo, useState, useCallback, useRef } from "react";

import type { MessagePart, SSEEvent } from "@/types/agent";

// Types
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content?: string; // 兼容字段
  timestamp: Date;
  parts?: MessagePart[]; // Vercel格式的消息部分
  tool_calls?: ToolCall[]; // 兼容字段
  thinking?: string; // 思维链内容
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
  result?: any;
  status: 'pending' | 'completed' | 'failed';
}

export interface ConversationHistory {
  role: 'user' | 'assistant';
  content: string;
}

// Vercel AI SDK 格式事件类型（来自SSEEvent）
type StreamEventData = SSEEvent;

interface AgentState {
  // 消息状态
  messages: ChatMessage[];
  isProcessing: boolean;
  processingText: string;
  currentResponse: string;

  // 会话状态
  currentSessionId: string | null;
  currentUserId: string;

  // UI状态
  sidebarOpen: boolean;

  // Computed
  conversationHistory: ConversationHistory[];
  hasMessages: boolean;
}

interface AgentActions {
  sendMessage: (message: string) => Promise<void>;
  clearMessages: () => void;
  addMessage: (role: 'user' | 'assistant' | 'system', content: string, options?: {
    tool_calls?: ToolCall[];
    thinking?: string;
  }) => ChatMessage;
  setSidebarOpen: (open: boolean) => void;
}

type FullAgentState = AgentState & AgentActions;

const Ctx = createContext<FullAgentState | null>(null);

export function AgentProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingText, setProcessingText] = useState('正在思考中...');
  const [currentResponse, setCurrentResponse] = useState('');
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentUserId] = useState<string>('api_user');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Refs for streaming
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentMessageIdRef = useRef<string | null>(null);

  // Computed values
  const conversationHistory = useMemo(() => {
    return messages
      .filter(msg => msg.role === 'user' || msg.role === 'assistant')
      .map(msg => ({
        role: msg.role as 'user' | 'assistant',
        content: msg.content
      }));
  }, [messages]);

  const hasMessages = useMemo(() => messages.length > 0, [messages]);

  // Helper function to generate ID
  const generateId = useCallback(() => {
    return Date.now().toString(36) + Math.random().toString(36).substring(2);
  }, []);

  // Add message helper
  const addMessage = useCallback((role: 'user' | 'assistant' | 'system', content: string, options?: {
    tool_calls?: ToolCall[];
    thinking?: string;
  }) => {
    const message: ChatMessage = {
      id: generateId(),
      role,
      content,
      timestamp: new Date(),
      ...options
    };

    setMessages(prev => [...prev, message]);
    return message;
  }, [generateId]);

  // 保持工具调用状态
  const pendingToolCallsRef = useRef<Map<string, ToolCall>>(new Map());

  // Process stream data - Vercel AI SDK格式事件处理
  const processStreamData = useCallback((eventData: StreamEventData) => {
    const eventType = eventData.type;
    const currentMessageId = currentMessageIdRef.current;

    switch (eventType) {
      case 'assistant_message_start':
        setProcessingText('正在生成回答...');
        break;

      case 'text_delta':
        // 文本增量
        if (eventData.content) {
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];

            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id === currentMessageId) {
              // 查找或创建文本部分
              const existingTextIndex = (lastMessage.parts || []).findIndex(part => part.type === 'text');
              const updatedParts = [...(lastMessage.parts || [])];

              if (existingTextIndex >= 0) {
                // 更新现有文本部分
                updatedParts[existingTextIndex] = {
                  type: 'text',
                  text: (updatedParts[existingTextIndex] as any).text + eventData.content
                };
              } else {
                // 添加新的文本部分
                updatedParts.unshift({
                  type: 'text',
                  text: eventData.content
                });
              }

              newMessages[newMessages.length - 1] = {
                ...lastMessage,
                parts: updatedParts,
                content: updatedParts.find(p => p.type === 'text')?.text || ''
              };
            }
            return newMessages;
          });
        }
        break;

      case 'tool_call_start':
        // 工具调用开始
        if (eventData.toolCallId && eventData.toolName) {
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];

            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id === currentMessageId) {
              const toolCallPart: MessagePart = {
                type: 'tool-call',
                toolCallId: eventData.toolCallId!,
                toolName: eventData.toolName!
              };

              newMessages[newMessages.length - 1] = {
                ...lastMessage,
                parts: [...(lastMessage.parts || []), toolCallPart]
              };
            }
            return newMessages;
          });
        }
        break;

      case 'tool_call_input':
        // 工具输入参数
        if (eventData.toolCallId) {
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];

            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id === currentMessageId) {
              const updatedParts = lastMessage.parts?.map(part => {
                if (part.type === 'tool-call' && part.toolCallId === eventData.toolCallId) {
                  return {
                    ...part,
                    args: eventData.input
                  };
                }
                return part;
              }) || [];

              newMessages[newMessages.length - 1] = {
                ...lastMessage,
                parts: updatedParts
              };
            }
            return newMessages;
          });
        }
        break;

      case 'tool_call_result':
        // 工具执行结果
        if (eventData.toolCallId && eventData.toolName) {
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];

            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id === currentMessageId) {
              const toolResultPart: MessagePart = {
                type: 'tool-result',
                toolCallId: eventData.toolCallId!,
                toolName: eventData.toolName!,
                result: eventData.result
              };

              // 替换对应的tool-call部分或添加新的
              const updatedParts = (lastMessage.parts || []).map(part => {
                if (part.type === 'tool-call' && part.toolCallId === eventData.toolCallId) {
                  return toolResultPart;
                }
                return part;
              });

              // 如果没有找到对应的tool-call，则添加新的
              if (!updatedParts.some(part => part.type === 'tool-result' && part.toolCallId === eventData.toolCallId)) {
                updatedParts.push(toolResultPart);
              }

              newMessages[newMessages.length - 1] = {
                ...lastMessage,
                parts: updatedParts
              };
            }
            return newMessages;
          });
        }
        break;

      case 'tool_call_error':
        // 工具调用错误
        if (eventData.toolCallId && eventData.toolName) {
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];

            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id === currentMessageId) {
              const toolErrorPart: MessagePart = {
                type: 'tool-result',
                toolCallId: eventData.toolCallId!,
                toolName: eventData.toolName!,
                result: { error: eventData.error },
                isError: true
              };

              const updatedParts = (lastMessage.parts || []).map(part => {
                if (part.type === 'tool-call' && part.toolCallId === eventData.toolCallId) {
                  return toolErrorPart;
                }
                return part;
              });

              if (!updatedParts.some(part => part.type === 'tool-result' && part.toolCallId === eventData.toolCallId)) {
                updatedParts.push(toolErrorPart);
              }

              newMessages[newMessages.length - 1] = {
                ...lastMessage,
                parts: updatedParts
              };
            }
            return newMessages;
          });
        }
        break;

      case 'assistant_message_complete':
      case 'done':
        console.log('✅ Stream ended, message completed');
        setProcessingText('回答完成');
        setTimeout(() => {
          currentMessageIdRef.current = null;
        }, 100);
        break;

      case 'error':
        const errorMessage = eventData.error || 'Unknown error occurred';
        console.error('❌ Stream error:', errorMessage);
        throw new Error(errorMessage);
    }
  }, []);

  // Send message
  const sendMessage = useCallback(async (userMessage: string) => {
    if (isProcessing || !userMessage.trim()) return;

    // Add user message
    addMessage('user', userMessage);

    // Set processing state
    setIsProcessing(true);
    setProcessingText('正在思考中...');
    setCurrentResponse(''); // Reset for new streaming response

    try {
      // Import agent service dynamically to avoid circular dependencies
      const { chatStream } = await import("../services/agentService");

      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      // Add empty assistant message for streaming
      const assistantMessage = addMessage('assistant', '');
      currentMessageIdRef.current = assistantMessage.id;

      // Start streaming response
      const response = await chatStream({
        message: userMessage,
        session_id: currentSessionId || undefined,
        user_id: currentUserId,
        conversation_history: conversationHistory.slice(0, -1) // Exclude current user message
      }, abortControllerRef.current.signal);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('无法获取响应流');
      }

      let eventCount = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ') && line.trim() !== 'data: ') {
            try {
              eventCount++;
              const jsonStr = line.slice(6); // 移除 "data: " 前缀
              const data = JSON.parse(jsonStr) as StreamEventData;

              // 调试日志：验证流式接收
              console.log(`[SSE Event ${eventCount}] ${data.type}:`, data);

              processStreamData(data);

              // 仅对text_delta事件添加延迟，实现打字机效果
              if (data.type === 'text_delta') {
                await new Promise(resolve => setTimeout(resolve, 30)); // 30ms延迟
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', line, e);
            }
          }
        }
      }

  
    } catch (error) {
      console.error('Error sending message:', error);

      // Add error message
      addMessage('assistant', `抱歉，处理您的请求时出现错误：${error instanceof Error ? error.message : '未知错误'}`);
      currentMessageIdRef.current = null;

    } finally {
      // Reset processing state (but keep currentResponse for potential reuse)
      setIsProcessing(false);
      setProcessingText('正在思考中...');
      // Note: Don't reset currentResponse here as it should be preserved in the message content
      abortControllerRef.current = null;
    }
  }, [isProcessing, addMessage, currentSessionId, currentUserId, conversationHistory, processStreamData]);

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentResponse('');
    setCurrentSessionId(null); // 清理session_id，下次请求将生成新的
    currentMessageIdRef.current = null;

    // Cancel any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  const setSidebarOpenCallback = useCallback((open: boolean) => {
    setSidebarOpen(open);
  }, []);

  // Cleanup on unmount
  useState(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  });

  
  const value = useMemo<FullAgentState>(() => ({
    // State
    messages,
    isProcessing,
    processingText,
    currentResponse,
    currentSessionId,
    currentUserId,
    sidebarOpen,

    // Computed
    conversationHistory,
    hasMessages,

    // Actions
    sendMessage,
    clearMessages,
    addMessage,
    setSidebarOpen: setSidebarOpenCallback,
  }), [
    messages,
    isProcessing,
    processingText,
    currentResponse,
    currentSessionId,
    currentUserId,
    sidebarOpen,
    conversationHistory,
    hasMessages,
    sendMessage,
    clearMessages,
    addMessage,
    setSidebarOpenCallback,
  ]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAgentState() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAgentState must be used within AgentProvider");
  return v;
}