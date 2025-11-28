"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronRight, CheckCircle, Clock, PlayCircle, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TodoItem {
  content: string;
  status: 'pending' | 'in_progress' | 'completed';
  activeForm: string;
}

export interface TodoListProps {
  items: TodoItem[];
  timestamp: Date;
}

export interface TodoListState {
  isLoading: boolean;
  error: string | null;
}

export function TodoList({ items, timestamp }: TodoListProps) {
  const [showAllResults, setShowAllResults] = useState(false);

  if (!items || items.length === 0) {
    return null;
  }

  const completedCount = items.filter(item => item.status === 'completed').length;
  const inProgressCount = items.filter(item => item.status === 'in_progress').length;
  const pendingCount = items.filter(item => item.status === 'pending').length;
  const totalCount = items.length;
  const progressPercentage = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  const getStatusIcon = (status: TodoItem['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'in_progress':
        return <PlayCircle className="w-4 h-4 text-blue-500" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: TodoItem['status']) => {
    const variants = {
      completed: 'bg-green-100 text-green-800',
      in_progress: 'bg-blue-100 text-blue-800',
      pending: 'bg-gray-100 text-gray-800'
    };

    return (
      <Badge className={cn(variants[status], 'text-xs')}>
        {status === 'completed' ? '已完成' :
         status === 'in_progress' ? '进行中' : '待处理'}
      </Badge>
    );
  };

  return (
    <Card className="w-full border-l-4 border-l-blue-500 shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <RotateCcw className="w-5 h-5 text-blue-500" />
            任务进度
          </CardTitle>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span>{timestamp.toLocaleTimeString()}</span>
            <Badge variant="outline" className="text-xs">
              {completedCount}/{totalCount}
            </Badge>
          </div>
        </div>

        <div className="space-y-2">
          <Progress value={progressPercentage} className="h-2" />
          <div className="flex justify-between text-xs text-gray-600">
            <span>已完成: {completedCount}</span>
            <span>进行中: {inProgressCount}</span>
            <span>待处理: {pendingCount}</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {items.map((item, index) => (
          <div
            key={index}
            className={cn(
              "flex items-start gap-3 p-3 rounded-lg border transition-all duration-200",
              item.status === 'completed' && 'bg-green-50 border-green-200',
              item.status === 'in_progress' && 'bg-blue-50 border-blue-200',
              item.status === 'pending' && 'bg-gray-50 border-gray-200'
            )}
          >
            <div className="flex-shrink-0 mt-0.5">
              {getStatusIcon(item.status)}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2 mb-2">
                <p className={cn(
                  "text-sm font-medium",
                  item.status === 'completed' && 'text-green-800 line-through',
                  item.status === 'in_progress' && 'text-blue-800',
                  item.status === 'pending' && 'text-gray-700'
                )}>
                  {item.content}
                </p>
                {getStatusBadge(item.status)}
              </div>

              {item.status === 'in_progress' && item.activeForm && (
                <div className="flex items-center gap-1 text-xs text-blue-600 mb-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                  <span>正在执行: {item.activeForm}</span>
                </div>
              )}
            </div>
          </div>
        ))}

        {items.length > 5 && (
          <div className="pt-2 border-t">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAllResults(!showAllResults)}
              className="w-full text-xs"
            >
              {showAllResults ? '收起' : '显示全部'} {items.length} 项任务
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}