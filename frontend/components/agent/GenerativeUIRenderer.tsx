"use client";

import React from "react";
import type { MessagePart } from "@/types/agent";
import { WeatherCard, WeatherCardSkeleton, WeatherCardError } from "@/components/generative_ui";
import { Sparkles } from "lucide-react";

interface GenerativeUIRendererProps {
  parts: MessagePart[];
}

export function GenerativeUIRenderer({ parts }: GenerativeUIRendererProps) {
  const renderMessagePart = (part: MessagePart, index: number) => {
    if (part.type === 'text') {
      return (
        <div key={index} className="prose prose-sm max-w-none dark:prose-invert">
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
          return <WeatherCard key={index} {...result} />;
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

  return (
    <div className="space-y-3">
      {parts.map((part, index) => renderMessagePart(part, index))}
    </div>
  );
}