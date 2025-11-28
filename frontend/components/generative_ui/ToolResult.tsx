"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ToolResultProps {
  toolName: string;
  result: any;
  isError?: boolean;
  duration?: number;
  className?: string;
}

export function ToolResult({
  toolName,
  result,
  isError = false,
  duration,
  className
}: ToolResultProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const getVariant = () => {
    if (isError) return "destructive";
    return "secondary";
  };

  return (
    <div className={cn(
      "rounded-lg border transition-all duration-200",
      isError
        ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
        : "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800",
      className
    )}>
      {/* 可点击的头部 - 默认显示 */}
      <Button
        variant="ghost"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-3 h-auto justify-start hover:bg-transparent/10"
      >
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
            <Badge variant={getVariant()} className="text-xs">
              {isError ? '工具错误' : '工具结果'}
            </Badge>
            <span className="font-medium text-sm">
              {toolName}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {duration && (
              <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                <Clock className="w-3 h-3" />
                <span>{formatDuration(duration)}</span>
              </div>
            )}
            {!isExpanded && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                点击展开
              </span>
            )}
          </div>
        </div>
      </Button>

      {/* 展开的内容 - 详细结果 */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-current/20">
          <div className="pt-2">
            <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-x-auto max-h-60 bg-white/50 dark:bg-black/20 p-2 rounded">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}