"use client";
import { createContext, useContext, useMemo, useState, useCallback, useRef } from "react";

// Types
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  tool_calls?: ToolCall[];
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

// 新的Agent事件数据格式

// 流开始事件
interface StreamStartEvent {
  event: 'start';
  data: {
    session_id?: string;
  };
}

// 文本响应事件
interface StreamTextEvent {
  event: 'text';
  data: {
    content: string;
    type: 'token';
  };
}

// 工具调用事件
interface StreamToolCallEvent {
  event: 'tool_call';
  data: {
    id: string;
    name: string;
    args: string | Record<string, any>;
    status?: 'pending';
    type?: 'start' | 'args_update';
  };
}

// 工具结果事件
interface StreamToolResultEvent {
  event: 'tool_result';
  data: {
    id: string;
    name: string;
    result: any;
    status: 'completed' | 'failed';
  };
}

// 流结束事件
interface StreamEndEvent {
  event: 'end';
  data: Record<string, any>;
}

// 错误事件
interface StreamErrorEvent {
  event: 'error';
  data: {
    error: string;
  };
}

// 联合类型
type StreamEventData = StreamStartEvent | StreamTextEvent | StreamToolCallEvent | StreamToolResultEvent | StreamEndEvent | StreamErrorEvent;

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

  // Process stream data - 新的事件格式处理
  const processStreamData = useCallback((eventData: StreamEventData) => {
    const event = eventData.event;

    switch (event) {
      case 'start':
        setProcessingText('正在生成回答...');
        if (eventData.data.session_id) {
          setCurrentSessionId(eventData.data.session_id);
        }
        break;

      case 'text':
        // 文本token，添加到当前助手消息
        const currentMessageId = currentMessageIdRef.current;
        const content = eventData.data.content;

        setCurrentResponse(prev => {
          const newResponse = prev + content;

          setMessages(messagesPrev => {
            const newMessages = [...messagesPrev];
            const lastMessage = newMessages[newMessages.length - 1];

            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id === currentMessageId) {
              newMessages[newMessages.length - 1] = {
                ...lastMessage,
                content: newResponse
              };
            }
            return newMessages;
          });
          return newResponse;
        });
        break;

      case 'tool_call':
        // 工具调用事件
        const toolData = eventData.data;
        const toolId = toolData.id;

        if (toolData.type === 'start' || !toolData.type) {
          // 新的工具调用开始
          const toolCall: ToolCall = {
            id: toolId,
            name: toolData.name,
            arguments: typeof toolData.args === 'string' ? { raw: toolData.args } : (toolData.args as Record<string, any>),
            status: 'pending'
          };

          pendingToolCallsRef.current.set(toolId, toolCall);

          // 更新当前消息的工具调用列表
          setMessages(messagesPrev => {
            const newMessages = [...messagesPrev];
            const lastMessage = newMessages[newMessages.length - 1];

            if (lastMessage && lastMessage.role === 'assistant') {
              const updatedToolCalls = [...(lastMessage.tool_calls || [])];
              const existingIndex = updatedToolCalls.findIndex(tc => tc.id === toolId);
              if (existingIndex >= 0) {
                updatedToolCalls[existingIndex] = toolCall;
              } else {
                updatedToolCalls.push(toolCall);
              }

              newMessages[newMessages.length - 1] = {
                ...lastMessage,
                tool_calls: updatedToolCalls
              };
            }
            return newMessages;
          });
        } else if (toolData.type === 'args_update') {
          // 参数更新
          const existingToolCall = pendingToolCallsRef.current.get(toolId);
          if (existingToolCall) {
            const updatedArgs = typeof toolData.args === 'string'
              ? { raw: toolData.args }
              : (toolData.args as Record<string, any>);

            const updatedToolCall = {
              ...existingToolCall,
              arguments: updatedArgs
            };

            pendingToolCallsRef.current.set(toolId, updatedToolCall);

            // 更新消息中的工具调用参数
            setMessages(messagesPrev => {
              const newMessages = [...messagesPrev];
              const lastMessage = newMessages[newMessages.length - 1];

              if (lastMessage && lastMessage.role === 'assistant' && lastMessage.tool_calls) {
                const updatedToolCalls = lastMessage.tool_calls.map(tc =>
                  tc.id === toolId ? updatedToolCall : tc
                );

                newMessages[newMessages.length - 1] = {
                  ...lastMessage,
                  tool_calls: updatedToolCalls
                };
              }
              return newMessages;
            });
          }
        }
        break;

      case 'tool_result':
        // 工具执行结果
        const resultData = eventData.data;
        const resultToolId = resultData.id;

        setMessages(messagesPrev => {
          const newMessages = [...messagesPrev];
          const lastMessage = newMessages[newMessages.length - 1];

          if (lastMessage && lastMessage.role === 'assistant' && lastMessage.tool_calls) {
            const updatedToolCalls = lastMessage.tool_calls.map(tc => {
              if (tc.id === resultToolId) {
                return {
                  ...tc,
                  status: resultData.status as 'completed' | 'failed',
                  result: resultData.result
                };
              }
              return tc;
            });

            newMessages[newMessages.length - 1] = {
              ...lastMessage,
              tool_calls: updatedToolCalls
            };
          }
          return newMessages;
        });

        // 清理ref中的工具调用
        pendingToolCallsRef.current.delete(resultToolId);
        break;

      case 'end':
        console.log('✅ Stream ended, message completed');
        setProcessingText('回答完成');
        // 清理ref中的所有待处理工具调用
        pendingToolCallsRef.current.clear();
        // Delay clearing the message ID to ensure all content is processed
        setTimeout(() => {
          currentMessageIdRef.current = null;
        }, 100);
        break;

      case 'error':
        const errorMessage = eventData.data.error || 'Unknown error occurred';
        console.error('❌ Stream error:', errorMessage);
        // 清理ref
        pendingToolCallsRef.current.clear();
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
          if (line.startsWith('data: ')) {
            try {
              eventCount++;
              const data = JSON.parse(line.slice(6)) as StreamEventData;
              // 调试日志：验证流式接收
              console.log(`[SSE Event ${eventCount}] ${data.event}:`, data);
              console.time(`Event_${eventCount}`);
              processStreamData(data);
              console.timeEnd(`Event_${eventCount}`);
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