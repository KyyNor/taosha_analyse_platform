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

export interface TodoItem {
  content: string;
  status: 'pending' | 'in_progress' | 'completed';
  activeForm: string;
}

export interface TodoList {
  id: string;
  items: TodoItem[];
  timestamp: Date;
  isActive: boolean;
}

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

  // TodoList状态 - 单轮对话中只有一个活跃的todo list
  currentTodoList: TodoList | null;

  // Computed
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
  updateTodoList: (todos: TodoItem[]) => void;
  clearTodoList: () => void;
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
  const [currentTodoList, setCurrentTodoList] = useState<TodoList | null>(null);

  // Refs for streaming
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentMessageIdRef = useRef<string | null>(null);

  // Refs for TodoList optimization
  const todoUpdateDebouncer = useRef<NodeJS.Timeout | null>(null);
  const lastTodoItemsRef = useRef<string>(''); // 用于比较TodoList内容

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

  // Process stream data - 原生LangChain事件格式处理
  const processStreamData = useCallback((eventData: StreamEventData) => {
    const eventType = eventData.event;
    const eventPayload = eventData.data || {};
    const currentMessageId = currentMessageIdRef.current;

    switch (eventType) {
      case 'start':
        // 保存后端返回的session_id
        if (eventPayload.session_id) {
          setCurrentSessionId(eventPayload.session_id);
        }

      case 'text':
        // 文本token流
        if (eventPayload.content) {
          setProcessingText('正在生成回答...');
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
                  text: (updatedParts[existingTextIndex] as any).text + eventPayload.content
                };
              } else {
                // 添加新的文本部分
                updatedParts.unshift({
                  type: 'text',
                  text: eventPayload.content
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

      case 'tool_call':
        // 工具调用（开始/参数更新）
        if (eventPayload.name && (eventPayload.status === 'pending' || eventPayload.type === 'start' || eventPayload.type === 'args_update')) {
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];

            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id === currentMessageId) {
              const toolCallPart: MessagePart = {
                type: 'tool-call',
                toolCallId: eventPayload.id,
                toolName: eventPayload.name,
                args: eventPayload.args
              };

              // 查找是否已存在该工具调用
              const existingIndex = (lastMessage.parts || []).findIndex(part =>
                part.type === 'tool-call' && part.toolCallId === eventPayload.id
              );

              let updatedParts = [...(lastMessage.parts || [])];
              if (existingIndex >= 0) {
                // 更新现有工具调用的参数
                updatedParts[existingIndex] = toolCallPart;
              } else {
                // 添加新的工具调用
                updatedParts.push(toolCallPart);
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

      case 'tool_result':
        // 工具执行结果
        if (eventPayload.name && (eventPayload.status === 'completed' || eventPayload.status === 'failed')) {
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];

            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id === currentMessageId) {
              const toolResultPart: MessagePart = {
                type: 'tool-result',
                toolCallId: eventPayload.id,
                toolName: eventPayload.name,
                result: eventPayload.result,
                isError: eventPayload.status === 'failed'
              };

              // 替换对应的tool-call部分
              const updatedParts = (lastMessage.parts || []).map(part => {
                if (part.type === 'tool-call' && part.toolCallId === eventPayload.id) {
                  return toolResultPart;
                }
                return part;
              });

              // 如果没有找到对应的tool-call，则添加新的
              if (!updatedParts.some(part => part.type === 'tool-result' && part.toolCallId === eventPayload.id)) {
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

      case 'error':
        // 错误信息
        const errorMessage = eventPayload.error || 'Unknown error occurred';
        console.error('❌ Stream error:', errorMessage);
        throw new Error(errorMessage);

      default:
        // 处理其他未知事件类型
        console.log('🔄 Unknown event type:', eventType, eventPayload);
        break;
    }
  }, []);

  // Send message
  const sendMessage = useCallback(async (userMessage: string) => {
    if (isProcessing || !userMessage.trim()) return;

    // Add user message
    addMessage('user', userMessage);

    // Clear current todo list when starting new conversation
    setCurrentTodoList(null);

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
        user_id: currentUserId
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
  }, [isProcessing, addMessage, currentSessionId, currentUserId, processStreamData]);

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentResponse('');
    setCurrentSessionId(null); // 清理session_id，下次请求将生成新的
    currentMessageIdRef.current = null;
    setCurrentTodoList(null); // 清理当前todo list

    // 清理TodoList防抖定时器
    if (todoUpdateDebouncer.current) {
      clearTimeout(todoUpdateDebouncer.current);
      todoUpdateDebouncer.current = null;
    }
    lastTodoItemsRef.current = ''; // 重置内容比较

    // Cancel any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  // Update todo list
  const updateTodoList = useCallback((todos: TodoItem[]) => {
    setCurrentTodoList({
      id: generateId(),
      items: todos,
      timestamp: new Date(),
      isActive: true
    });
  }, [generateId]);

  // Clear todo list
  const clearTodoList = useCallback(() => {
    setCurrentTodoList(null);
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
    currentTodoList,

    // Computed
    hasMessages,

    // Actions
    sendMessage,
    clearMessages,
    addMessage,
    setSidebarOpen: setSidebarOpenCallback,
    updateTodoList,
    clearTodoList,
  }), [
    messages,
    isProcessing,
    processingText,
    currentResponse,
    currentSessionId,
    currentUserId,
    sidebarOpen,
    currentTodoList,
    hasMessages,
    sendMessage,
    clearMessages,
    addMessage,
    setSidebarOpenCallback,
    updateTodoList,
    clearTodoList,
  ]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAgentState() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAgentState must be used within AgentProvider");
  return v;
}