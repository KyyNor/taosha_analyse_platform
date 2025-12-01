"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage, ToolCall } from "@/lib/state/agent";
import { ChevronDown, ChevronUp, Bot, User, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";
import { GenerativeUIRenderer } from "./GenerativeUIRenderer";

interface MessageItemProps {
  message: ChatMessage;
}

export function MessageItem({ message }: MessageItemProps) {
  const [toolCallsOpen, setToolCallsOpen] = useState(false);

  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  const formatTime = (timestamp: Date) => {
    return timestamp.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderToolCallStatus = (toolCall: ToolCall) => {
    const statusColors = {
      pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
      completed: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
      failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
    };

    return (
      <Badge className={cn("text-xs", statusColors[toolCall.status])}>
        {toolCall.status === 'pending' && '执行中'}
        {toolCall.status === 'completed' && '已完成'}
        {toolCall.status === 'failed' && '失败'}
      </Badge>
    );
  };

  return (
    <div className={cn(
      "flex gap-3",
      isUser ? "justify-end" : "justify-start"
    )}>
      {/* Assistant Avatar */}
      {isAssistant && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center shadow-md">
            <Bot className="w-4 h-4" />
          </div>
        </div>
      )}

      {/* Message Content */}
      <div className={cn(
        "max-w-2xl shadow-md break-words",
        isUser ? "order-first" : "order-last"
      )}>
        <Card className={cn(
          "border-0",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground"
        )}>
          <CardContent className="p-4">
            {/* Main Message Content */}
            {message.parts ? (
              // 生成式UI渲染模式
              <GenerativeUIRenderer parts={message.parts} thinking={message.thinking} />
            ) : (
              // 传统渲染模式
              <div className="prose prose-sm max-w-none dark:prose-invert">
                {isAssistant ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code({ className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '');
                        const isInline = !className?.includes('language-') && !match;
                        return !isInline && match ? (
                          <SyntaxHighlighter
                            style={vscDarkPlus as any}
                            language={match[1]}
                            PreTag="div"
                            className="rounded-md"
                            {...props}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
                          <code
                            className={cn(
                              "px-1 py-0.5 rounded text-sm font-mono",
                              isUser
                                ? "bg-primary-foreground/20 text-primary-foreground"
                                : "bg-accent text-accent-foreground"
                            )}
                            {...props}
                          >
                            {children}
                          </code>
                        );
                      }
                    }}
                  >
                    {message.content || ''}
                  </ReactMarkdown>
                ) : (
                  <div className="whitespace-pre-wrap">{message.content}</div>
                )}
              </div>
            )}

            {/* Tool Calls Display */}
            {isAssistant && message.tool_calls && message.tool_calls.length > 0 && (
              <Collapsible
                open={toolCallsOpen}
                onOpenChange={setToolCallsOpen}
                className="mt-3"
              >
                <CollapsibleTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 px-2 text-xs font-mono bg-background/20 hover:bg-background/30"
                  >
                    <Wrench className="w-3 h-3 mr-1" />
                    工具调用 ({message.tool_calls.length})
                    {toolCallsOpen ? (
                      <ChevronUp className="w-3 h-3 ml-1" />
                    ) : (
                      <ChevronDown className="w-3 h-3 ml-1" />
                    )}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2 space-y-2">
                  {message.tool_calls.map((toolCall) => (
                    <Card key={toolCall.id} className="bg-background/50 border border-border/50">
                      <CardContent className="p-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Wrench className="w-3 h-3" />
                            <span className="text-sm font-mono font-medium">
                              {toolCall.name}
                            </span>
                          </div>
                          {renderToolCallStatus(toolCall)}
                        </div>

                        {/* Arguments */}
                        {Object.keys(toolCall.arguments).length > 0 && (
                          <div className="mb-2">
                            <div className="text-xs font-medium mb-1">参数:</div>
                            <ScrollArea className="h-16 w-full">
                              <pre className="text-xs font-mono bg-background/30 p-2 rounded">
                                {JSON.stringify(toolCall.arguments, null, 2)}
                              </pre>
                            </ScrollArea>
                          </div>
                        )}

                        {/* Result */}
                        {toolCall.result && (
                          <div>
                            <div className="text-xs font-medium mb-1">结果:</div>
                            <ScrollArea className="h-16 w-full">
                              <pre className="text-xs font-mono bg-background/30 p-2 rounded">
                                {typeof toolCall.result === 'string'
                                  ? toolCall.result
                                  : JSON.stringify(toolCall.result, null, 2)
                                }
                              </pre>
                            </ScrollArea>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </CollapsibleContent>
              </Collapsible>
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
          <div className="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center shadow-md">
            <User className="w-4 h-4" />
          </div>
        </div>
      )}
    </div>
  );
}