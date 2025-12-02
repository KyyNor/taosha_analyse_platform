"use client";

import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { ChatMessage } from "@/lib/state/agent";
import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { GenerativeUIRenderer } from "./GenerativeUIRenderer";
import { MarkdownBlock } from "./MarkdownBlock";

interface MessageItemProps {
  message: ChatMessage;
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  const formatTime = (timestamp: Date) => {
    return timestamp.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className={cn(
      "flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300",
      isUser ? "justify-end" : "justify-start"
    )}>
      {/* Assistant Avatar */}
      {isAssistant && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-white border border-gray-200 text-primary flex items-center justify-center shadow-sm">
            <Bot className="w-5 h-5" />
          </div>
        </div>
      )}

      {/* Message Content */}
      <div className={cn(
        "max-w-3xl break-words",
        isUser ? "order-first" : "order-last"
      )}>
        <Card className={cn(
          "border shadow-sm transition-all hover:shadow-md",
          isUser
            ? "bg-primary text-primary-foreground border-primary"
            : "bg-white dark:bg-card border-border"
        )}>
          <CardContent className="p-4">
            {/* Main Message Content */}
            {message.parts ? (
              // 生成式UI渲染模式
              <GenerativeUIRenderer parts={message.parts} thinking={message.thinking} />
            ) : (
              // 传统渲染模式
              isAssistant ? (
                <MarkdownBlock content={message.content || ''} />
              ) : (
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <div className="whitespace-pre-wrap">{message.content}</div>
                </div>
              )
            )}

            {/* Timestamp */}
            {message.timestamp && (
              <div className="text-xs mt-2 opacity-70">
                {formatTime(message.timestamp)}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shadow-sm">
            <User className="w-5 h-5" />
          </div>
        </div>
      )}
    </div>
  );
}