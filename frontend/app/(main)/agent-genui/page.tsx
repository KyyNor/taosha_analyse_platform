'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles } from 'lucide-react';
import {
  WeatherCard,
  WeatherCardSkeleton,
  WeatherCardError,
} from '@/src/components/generative_ui';
import type {
  SSEEvent,
  GenerativeUIMessage,
  MessagePart,
  WeatherData,
} from '@/src/types/generativeUI';

/**
 * 生成式UI演示页面
 * 展示基于LangChain Agent + Vercel格式的流式生成UI功能
 */
export default function AgentGenUIPage() {
  const [messages, setMessages] = useState<GenerativeUIMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  /**
   * 发送消息并处理SSE流
   */
  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: GenerativeUIMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: input.trim(),
      createdAt: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

  const baseUrl = process.env.NEXT_PUBLIC_API_STREAM_BASE
    || process.env.NEXT_PUBLIC_API_BASE
    || "/api/taosha/v1";
  const url = `${baseUrl}/agents/chat/vercel-stream`;

    try {
      // 构建请求
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: `genui_${Date.now()}`,
          user_id: 'demo_user',
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('响应体为空');
      }

      // 创建一个新的助手消息
      const assistantMessageId = `assistant_${Date.now()}`;
      const assistantMessage: GenerativeUIMessage = {
        id: assistantMessageId,
        role: 'assistant',
        parts: [],
        createdAt: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // 解析SSE流
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      // 当前消息的文本缓冲区和工具调用映射
      let textBuffer = '';
      const toolCalls = new Map<string, MessagePart>();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue;

          try {
            const jsonStr = line.slice(6); // 移除 "data: " 前缀
            const event: SSEEvent = JSON.parse(jsonStr);

            console.log('收到SSE事件:', event);

            // 处理不同类型的事件
            switch (event.type) {
              case 'text_delta':
                // 文本增量
                if (event.content) {
                  textBuffer += event.content;
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            parts: [
                              { type: 'text', text: textBuffer },
                              ...Array.from(toolCalls.values()),
                            ],
                          }
                        : msg
                    )
                  );
                }
                break;

              case 'tool_call_start':
                // 工具调用开始
                if (event.toolCallId && event.toolName) {
                  toolCalls.set(event.toolCallId, {
                    type: 'tool-call',
                    toolCallId: event.toolCallId,
                    toolName: event.toolName,
                  });
                }
                break;

              case 'tool_call_input':
                // 工具输入参数
                if (event.toolCallId) {
                  const existing = toolCalls.get(event.toolCallId);
                  if (existing && existing.type === 'tool-call') {
                    toolCalls.set(event.toolCallId, {
                      ...existing,
                      args: event.input,
                    });
                  }
                }
                break;

              case 'tool_call_result':
                // 工具执行结果
                if (event.toolCallId && event.toolName) {
                  toolCalls.set(event.toolCallId, {
                    type: 'tool-result',
                    toolCallId: event.toolCallId,
                    toolName: event.toolName,
                    result: event.result,
                  });

                  // 更新消息
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            parts: [
                              { type: 'text', text: textBuffer },
                              ...Array.from(toolCalls.values()),
                            ],
                          }
                        : msg
                    )
                  );
                }
                break;

              case 'tool_call_error':
                // 工具调用错误
                if (event.toolCallId && event.toolName) {
                  toolCalls.set(event.toolCallId, {
                    type: 'tool-result',
                    toolCallId: event.toolCallId,
                    toolName: event.toolName,
                    result: { error: event.error },
                    isError: true,
                  });
                }
                break;

              case 'assistant_message_complete':
              case 'done':
                // 流结束
                console.log('流式响应完成');
                break;

              case 'error':
                console.error('流式错误:', event.error);
                throw new Error(event.error || '未知错误');
            }
          } catch (err) {
            console.error('解析SSE事件失败:', err, 'line:', line);
          }
        }
      }
    } catch (error) {
      console.error('发送消息失败:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: `error_${Date.now()}`,
          role: 'assistant',
          content: `错误: ${error instanceof Error ? error.message : '未知错误'}`,
          createdAt: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * 渲染消息部分（文本或工具调用UI）
   */
  const renderMessagePart = (part: MessagePart, index: number) => {
    if (part.type === 'text') {
      return (
        <div key={index} className="prose dark:prose-invert max-w-none">
          <p className="whitespace-pre-wrap">{part.text}</p>
        </div>
      );
    }

    if (part.type === 'tool-call') {
      return (
        <div
          key={index}
          className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg border border-blue-200 dark:border-blue-800"
        >
          <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
            <Sparkles className="w-4 h-4" />
            <span className="font-medium">调用工具: {part.toolName}</span>
          </div>
          {part.args && (
            <pre className="text-xs mt-2 text-gray-600 dark:text-gray-400 overflow-x-auto">
              {JSON.stringify(part.args, null, 2)}
            </pre>
          )}
        </div>
      );
    }

    if (part.type === 'tool-result') {
      // 特殊处理天气工具 - 渲染WeatherCard
      if (part.toolName === 'get_weather') {
        const result = part.result as any;

        if (part.isError || result?.error) {
          return (
            <WeatherCardError
              key={index}
              error={result?.error || '获取天气失败'}
              city={result?.city}
            />
          );
        }

        if (result) {
          return <WeatherCard key={index} {...(result as WeatherData)} />;
        }
      }

      // 默认工具结果显示
      return (
        <div
          key={index}
          className={`p-3 rounded-lg border ${
            part.isError
              ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
              : 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
          }`}
        >
          <div
            className={`flex items-center gap-2 ${
              part.isError
                ? 'text-red-700 dark:text-red-300'
                : 'text-green-700 dark:text-green-300'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span className="font-medium">
              {part.isError ? '工具错误' : '工具结果'}: {part.toolName}
            </span>
          </div>
          <pre className="text-xs mt-2 text-gray-600 dark:text-gray-400 overflow-x-auto max-h-40">
            {JSON.stringify(part.result, null, 2)}
          </pre>
        </div>
      );
    }

    return null;
  };

  /**
   * 预设示例问题
   */
  const exampleQuestions = [
    '北京天气怎么样?',
    '福州现在多少度?',
    '上海今天的天气如何?',
  ];

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      {/* 顶部标题栏 */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-blue-500" />
          生成式UI演示
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          基于LangChain Agent的流式生成UI功能展示
        </p>
      </div>

      {/* 消息列表区域 */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <Sparkles className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-600 dark:text-gray-400 mb-2">
              开始你的生成式UI之旅
            </h2>
            <p className="text-gray-500 dark:text-gray-500 mb-6">
              试试问问天气，体验智能卡片生成
            </p>
            <div className="flex flex-wrap gap-2 justify-center max-w-2xl mx-auto">
              {exampleQuestions.map((question) => (
                <button
                  key={question}
                  onClick={() => {
                    setInput(question);
                  }}
                  className="px-4 py-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-3xl ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white p-4 rounded-lg'
                  : 'w-full space-y-3'
              }`}
            >
              {/* 用户消息 */}
              {message.role === 'user' && message.content && (
                <p className="whitespace-pre-wrap">{message.content}</p>
              )}

              {/* 助手消息 - 渲染parts */}
              {message.role === 'assistant' && message.parts && (
                <div className="space-y-3">
                  {message.parts.map((part, index) =>
                    renderMessagePart(part, index)
                  )}
                </div>
              )}

              {/* 助手消息 - 兼容content字段 */}
              {message.role === 'assistant' &&
                !message.parts &&
                message.content && (
                  <div className="prose dark:prose-invert max-w-none bg-white dark:bg-gray-800 p-4 rounded-lg">
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>
                )}
            </div>
          </div>
        ))}

        {/* 加载骨架屏 */}
        {isLoading && (
          <div className="flex justify-start">
            <WeatherCardSkeleton />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入框区域 */}
      <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-4">
        <div className="max-w-4xl mx-auto flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            placeholder="输入消息... (试试问问天气)"
            disabled={isLoading}
            className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:opacity-50"
          />
          <button
            onClick={handleSendMessage}
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Send className="w-5 h-5" />
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
