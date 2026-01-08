"use client";
import { createContext, useContext, useMemo, useState, useCallback, useRef, useEffect } from "react";
import { chatApi, type Session } from "@/lib/api";

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
  sessions: Session[]; // 历史会话列表

  // UI状态
  sidebarOpen: boolean;

  // TodoList状态 - 单轮对话中只有一个活跃的todo list
  currentTodoList: TodoList | null;

  // 当前请求的 trace_id（全局单一）
  currentTraceId: string | null;
  currentTraceIdTodos: TodoItem[]; // 当前 trace_id 对应的 TodoList 数据

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

  // 新增方法
  setCurrentTraceId: (traceId: string) => void;
  updateCurrentTraceIdTodos: (todos: TodoItem[]) => void;
  getCurrentTraceIdTodos: () => TodoItem[];

  // 会话管理
  loadHistory: () => Promise<void>;
  switchSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  createNewSession: () => void;
}

type FullAgentState = AgentState & AgentActions;

const Ctx = createContext<FullAgentState | null>(null);

export function AgentProvider({
  children,
  userId
}: {
  children: React.ReactNode;
  userId: string;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingText, setProcessingText] = useState('正在思考中...');
  const [currentResponse, setCurrentResponse] = useState('');
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentUserId] = useState<string>(userId);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentTodoList, setCurrentTodoList] = useState<TodoList | null>(null);
  const [currentTraceId, setCurrentTraceId] = useState<string | null>(null);
  const [currentTraceIdTodos, setCurrentTraceIdTodos] = useState<TodoItem[]>([]);

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

  // 加载历史会话列表
  const loadHistory = useCallback(async () => {
    try {
      const history = await chatApi.getHistory(currentUserId);
      setSessions(history);
    } catch (error) {
      console.error("Failed to load history:", error);
    }
  }, [currentUserId]);

  // 初始化加载
  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // 切换会话
  const switchSession = useCallback(async (sessionId: string) => {
    try {
      if (isProcessing) return; // 防止在生成时切换

      setIsProcessing(true);
      setMessages([]); // 先清空当前显示
      setCurrentTodoList(null);
      setCurrentTraceId(null);
      setCurrentTraceIdTodos([]);

      const historyMessages = await chatApi.getSessionMessages(sessionId);
      
      // 转换后端消息格式到前端格式
      const formattedMessages: ChatMessage[] = historyMessages.map(msg => {
        const isTool = msg.role === 'tool';
        const isAssistant = msg.role === 'assistant';
        
        let parts: MessagePart[] = [];
        // let toolCalls: ToolCall[] = [];

        // 简化的转换逻辑，实际可能更复杂，需要处理 tool_calls 和 tool_results 的配对
        if (msg.role === 'user') {
          parts = [{ type: 'text', text: msg.content }];
        } else if (isAssistant) {
           // 这里简单处理为文本，如果历史记录包含结构化 parts 更好，目前只能当做纯文本
           parts = [{ type: 'text', text: msg.content }];
        } else if (isTool) {
           // 工具结果
           try {
             const contentObj = JSON.parse(msg.content);
             parts = [{
               type: 'tool-result',
               toolCallId: msg.meta_info?.tool_call_id || 'unknown',
               toolName: msg.meta_info?.tool_name || 'unknown',
               result: contentObj,
               isError: false
             }];
           } catch {
             parts = [{
                type: 'tool-result',
                toolCallId: msg.meta_info?.tool_call_id || 'unknown',
                toolName: msg.meta_info?.tool_name || 'unknown',
                result: msg.content,
                isError: false
             }];
           }
        }

        return {
          id: msg.id,
          role: isTool ? 'assistant' : (msg.role as any), // tool result 在前端通常归属为 assistant 的一部分或者单独渲染，这里视 UI 实现而定，通常作为 MessagePart 附加在 assistant 消息里，或者独立的 ToolMessage。这里简化处理。
          content: msg.content,
          timestamp: new Date(msg.created_at),
          parts: parts
        };
      });

      // 重新组合消息：将 tool-result 合并到对应的 assistant 消息，或者保持独立
      // 这里的简单实现：直接设置消息列表
      // 注意：上面的转换逻辑对于复杂的 Agent 输出可能不够完美，因为后端存储是平铺的 ChatMessage
      // 而前端是基于 MessagePart 的聚合。为了完美还原，后端应该存 MessagePart 结构。
      // 临时方案：直接显示
      setMessages(formattedMessages);
      setCurrentSessionId(sessionId);
    } catch (error) {
      console.error("Failed to load session:", error);
    } finally {
      setIsProcessing(false);
    }
  }, [isProcessing]);

  // 删除会话
  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await chatApi.deleteSession(sessionId, currentUserId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setMessages([]);
        setCurrentSessionId(null);
        setCurrentTodoList(null);
      }
    } catch (error) {
      console.error("Failed to delete session:", error);
    }
  }, [currentUserId, currentSessionId]);

  // 创建新会话
  const createNewSession = useCallback(() => {
    if (isProcessing) return;
    setMessages([]);
    setCurrentSessionId(null);
    setCurrentTodoList(null);
    setCurrentTraceId(null);
    setCurrentTraceIdTodos([]);
    // URL 或状态更新逻辑
  }, [isProcessing]);

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
              const updatedParts = [...(lastMessage.parts || [])];
              
              // 检查最后一个部分是否是文本类型
              const lastPart = updatedParts[updatedParts.length - 1];
              
              if (lastPart && lastPart.type === 'text') {
                // 如果最后一个部分是文本，则追加内容
                updatedParts[updatedParts.length - 1] = {
                  type: 'text',
                  text: (lastPart.text || '') + eventPayload.content
                };
              } else {
                // 如果最后一个部分不是文本（比如是工具调用/结果），则创建新的文本部分
                updatedParts.push({
                  type: 'text',
                  text: eventPayload.content
                });
              }

              newMessages[newMessages.length - 1] = {
                ...lastMessage,
                parts: updatedParts,
                content: updatedParts.filter(p => p.type === 'text').map(p => p.text).join('')
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
          // 特殊处理 TodoList 工具 - 忽略 part.trace_id，直接处理数据
          if (eventPayload.name === 'todo_list_tool') {
            const result = eventPayload.result;

            // 解析 TodoList 数据
            let todoData = result;
            if (result && result.content && typeof result.content === 'object') {
              todoData = result.content;
            }

            if (Array.isArray(todoData) && todoData.length > 0) {
              const todoItems = todoData.map((item: any) => ({
                content: item.content,
                status: item.status,
                activeForm: item.activeForm,
                timestamp: item.timestamp || new Date()
              }));

              // 直接更新当前 trace_id 的 TodoList，不依赖任何 trace_id 字段
              updateCurrentTraceIdTodos(todoItems);
            }
          }

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

  /**
   * 生成 trace_id 的辅助函数
   */
  const generateTraceId = (): string => {
    return `trace_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  // Send message
  const sendMessage = useCallback(async (userMessage: string) => {
    if (isProcessing || !userMessage.trim()) return;

    // Add user message
    addMessage('user', userMessage);

    // Generate and set current trace_id (global variable)
    const newTraceId = generateTraceId();
    setCurrentTraceIdCallback(newTraceId);

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
        user_id: currentUserId,
        trace_id: newTraceId
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

    // 新增：清理当前 trace_id 相关数据
    setCurrentTraceId(null);
    setCurrentTraceIdTodos([]);

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

  // 设置当前 trace_id
  const setCurrentTraceIdCallback = useCallback((traceId: string) => {
    setCurrentTraceId(traceId);
    // 同时清理对应的 todos，等待新数据
    setCurrentTraceIdTodos([]);
  }, []);

  // 更新当前 trace_id 对应的 TodoList
  const updateCurrentTraceIdTodos = useCallback((todos: TodoItem[]) => {
    setCurrentTraceIdTodos(todos);
    // 同时更新原有的 currentTodoList 以保持兼容
    setCurrentTodoList({
      id: generateId(),
      items: todos,
      timestamp: new Date(),
      isActive: true
    });
  }, [generateId]);

  // 获取当前 trace_id 对应的 TodoList
  const getCurrentTraceIdTodos = useCallback((): TodoItem[] => {
    return currentTraceIdTodos;
  }, [currentTraceIdTodos]);

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
    sessions,
    sidebarOpen,
    currentTodoList,
    currentTraceId,
    currentTraceIdTodos,

    // Computed
    hasMessages,

    // Actions
    sendMessage,
    clearMessages,
    addMessage,
    setSidebarOpen: setSidebarOpenCallback,
    updateTodoList,
    clearTodoList,
    setCurrentTraceId: setCurrentTraceIdCallback,
    updateCurrentTraceIdTodos,
    getCurrentTraceIdTodos,
    loadHistory,
    switchSession,
    deleteSession,
    createNewSession,
  }), [
    messages,
    isProcessing,
    processingText,
    currentResponse,
    currentSessionId,
    currentUserId,
    sessions,
    sidebarOpen,
    currentTodoList,
    currentTraceId,
    currentTraceIdTodos,
    hasMessages,
    sendMessage,
    clearMessages,
    addMessage,
    setSidebarOpenCallback,
    updateTodoList,
    clearTodoList,
    setCurrentTraceIdCallback,
    updateCurrentTraceIdTodos,
    getCurrentTraceIdTodos,
    loadHistory,
    switchSession,
    deleteSession,
    createNewSession,
  ]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAgentState() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAgentState must be used within AgentProvider");
  return v;
}