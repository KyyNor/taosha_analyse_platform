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

// Stream data types
interface StreamStartData {
  type: 'start';
  session_id?: string;
}

interface StreamContentData {
  type: 'content';
  content: string;
}

interface StreamEndData {
  type: 'end';
}

interface StreamErrorData {
  type: 'error';
  content: string;
}

type StreamData = StreamStartData | StreamContentData | StreamEndData | StreamErrorData;

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
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
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

  // Process stream data
  const processStreamData = useCallback((data: StreamData) => {
    switch (data.type) {
      case 'start':
        setProcessingText('正在生成回答...');
        if (data.session_id) {
          setCurrentSessionId(data.session_id);
        }
        break;
      case 'content':
        setCurrentResponse(prev => prev + data.content);
        // Update the assistant message content
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id === currentMessageIdRef.current) {
            lastMessage.content = currentResponse + data.content;
          }
          return newMessages;
        });
        break;
      case 'end':
        setProcessingText('回答完成');
        currentMessageIdRef.current = null;
        break;
      case 'error':
        throw new Error(data.content);
    }
  }, [currentResponse]);

  // Send message
  const sendMessage = useCallback(async (userMessage: string) => {
    if (isProcessing || !userMessage.trim()) return;

    // Add user message
    addMessage('user', userMessage);

    // Set processing state
    setIsProcessing(true);
    setProcessingText('正在思考中...');
    setCurrentResponse('');

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

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6)) as StreamData;
              processStreamData(data);
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
      // Reset processing state
      setIsProcessing(false);
      setProcessingText('正在思考中...');
      setCurrentResponse('');
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
    setSidebarOpenCallback,
  ]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAgentState() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAgentState must be used within AgentProvider");
  return v;
}