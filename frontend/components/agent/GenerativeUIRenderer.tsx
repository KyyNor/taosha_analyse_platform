"use client";

import React from "react";
import type { MessagePart } from "@/types/agent";
import { useAgentState } from "@/lib/state/agent";
import {
  WeatherCard,
  WeatherCardSkeleton,
  WeatherCardError,
  LineChart,
  LineChartSkeleton,
  LineChartError,
  PieChart,
  PieChartSkeleton,
  PieChartError,
  BarChart,
  BarChartSkeleton,
  BarChartError,
  TodoList,
  ToolResult,
  type LineChartProps,
  type PieChartProps,
  type BarChartProps,
  type TodoListProps
} from "@/components/generative_ui";
import { Sparkles } from "lucide-react";

interface GenerativeUIRendererProps {
  parts: MessagePart[];
}

export function GenerativeUIRenderer({ parts }: GenerativeUIRendererProps) {
  // 1. 从 Agent Context 获取当前 trace_id 的 TodoList 数据
  const { currentTraceId, getCurrentTraceIdTodos } = useAgentState();

  // 2. 获取当前 TodoList 数据
  const currentTodos = getCurrentTraceIdTodos();

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

        // 处理工具结果的嵌套结构
        let weatherData = result;

        // 如果结果包含content字段，则提取实际的天气数据
        if (result && result.content && typeof result.content === 'object') {
          weatherData = result.content;
        }

        if (part.isError || weatherData?.error) {
          return (
            <WeatherCardError
              key={index}
              error={weatherData?.error || '获取天气失败'}
              city={weatherData?.city}
            />
          );
        }

        if (weatherData) {
          return <WeatherCard key={index} {...weatherData} />;
        }
      }

      // TodoList 工具结果 - 完全依赖全局状态，不依赖 part.trace_id
      if (part.toolName === 'todo_list_tool') {
        // 如果当前有 TodoList 数据，直接渲染
        if (currentTodos && currentTodos.length > 0) {
          return (
            <TodoList
              key={currentTraceId || index} // 使用当前 trace_id 作为 key
              items={currentTodos}
              timestamp={new Date()}
            />
          );
        }
        // 如果没有数据，不渲染任何内容
        return null;
      }

      // 特殊处理图表工具 - 渲染图表组件
      if (part.toolName === 'create_chart') {
        const result = part.result as any;

        // 处理工具结果的嵌套结构
        let chartData = result;

        // 如果结果包含content字段，则提取实际的图表数据
        if (result && result.content && typeof result.content === 'object') {
          chartData = result.content;
        }

        // 检查是否有错误
        if (part.isError || chartData?.error) {
          const chartType = chartData?.chart_type || '图表';
          switch (chartType) {
            case 'line':
              return (
                <LineChartError
                  key={index}
                  error={chartData?.error || '折线图生成失败'}
                  title={chartData?.title}
                />
              );
            case 'pie':
              return (
                <PieChartError
                  key={index}
                  error={chartData?.error || '饼图生成失败'}
                  title={chartData?.title}
                />
              );
            case 'bar':
              return (
                <BarChartError
                  key={index}
                  error={chartData?.error || '柱状图生成失败'}
                  title={chartData?.title}
                />
              );
            default:
              return (
                <div
                  key={index}
                  className="my-4 p-6 max-w-4xl bg-red-50 dark:bg-red-900/20 rounded-xl shadow-lg border border-red-200 dark:border-red-800"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <Sparkles className="w-6 h-6 text-red-600 dark:text-red-400" />
                    <div>
                      <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
                        {chartData?.title || '图表生成失败'}
                      </h3>
                    </div>
                  </div>
                  <p className="text-sm text-red-700 dark:text-red-300">
                    {chartData?.error || '未知错误'}
                  </p>
                </div>
              );
          }
        }

        // 渲染图表
        if (chartData && chartData.chart_type) {
          const chartType = chartData.chart_type;
          const commonProps = {
            key: index,
            title: chartData.title,
            description: chartData.description,
            ...chartData // 传递所有图表特定参数
          };

          try {
            switch (chartType) {
              case 'line':
                return <LineChart {...commonProps as LineChartProps} />;
              case 'pie':
                // 饼图需要特殊处理数据格式
                const pieProps = {
                  ...commonProps,
                  data: chartData.data || [],
                  colors: chartData.colors,
                  height: chartData.height,
                  show_legend: chartData.show_legend,
                  show_percentage: chartData.show_percentage,
                  inner_radius: chartData.inner_radius,
                  outer_radius: chartData.outer_radius,
                  start_angle: chartData.start_angle,
                  end_angle: chartData.end_angle,
                  label_position: chartData.label_position
                };
                return <PieChart {...pieProps as PieChartProps} />;
              case 'bar':
                // 柱状图需要特殊处理数据格式
                const barProps = {
                  ...commonProps,
                  data: chartData.data || [],
                  x_key: chartData.x_key || 'name',
                  y_keys: chartData.y_keys || ['value'],
                  orientation: chartData.orientation || 'vertical',
                  stacked: chartData.stacked || false,
                  colors: chartData.colors,
                  height: chartData.height,
                  show_grid: chartData.show_grid,
                  show_legend: chartData.show_legend,
                  bar_radius: chartData.bar_radius
                };
                return <BarChart {...barProps as BarChartProps} />;
              default:
                // 不支持的图表类型，显示通用错误
                return (
                  <div
                    key={index}
                    className="my-4 p-6 max-w-4xl bg-amber-50 dark:bg-amber-900/20 rounded-xl shadow-lg border border-amber-200 dark:border-amber-800"
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <Sparkles className="w-6 h-6 text-amber-600 dark:text-amber-400" />
                      <div>
                        <h3 className="text-lg font-semibold text-amber-800 dark:text-amber-200">
                          不支持的图表类型
                        </h3>
                      </div>
                    </div>
                    <p className="text-sm text-amber-700 dark:text-amber-300">
                      图表类型: {chartType}，支持的类型: line, pie, bar
                    </p>
                  </div>
                );
            }
          } catch (error) {
            // 渲染错误处理
            console.error('图表渲染错误:', error);
            return (
              <div
                key={index}
                className="my-4 p-6 max-w-4xl bg-red-50 dark:bg-red-900/20 rounded-xl shadow-lg border border-red-200 dark:border-red-800"
              >
                <div className="flex items-center gap-3 mb-4">
                  <Sparkles className="w-6 h-6 text-red-600 dark:text-red-400" />
                  <div>
                    <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
                      图表渲染失败
                    </h3>
                  </div>
                </div>
                <p className="text-sm text-red-700 dark:text-red-300">
                  {error instanceof Error ? error.message : '未知渲染错误'}
                </p>
              </div>
            );
          }
        }
      }

      // 默认工具结果 - 使用可折叠组件
      return (
        <ToolResult
          key={index}
          toolName={part.toolName || '未知工具'}
          result={part.result}
          isError={part.isError}
          duration={part.duration}
        />
      );
    }

    return null;
  };

  // 4. 确保 TodoList 在最后渲染（在所有文本信息之后）
  return (
    <div className="space-y-3">
      {/* 首先渲染所有非 TodoList 的工具结果，包括文本信息 */}
      {parts.filter((part, index) => {
        // 如果是 TodoList 工具，则跳过，稍后单独处理
        if (part.toolName === 'todo_list_tool') {
          return false;
        }
        return true;
      }).map((part, index) => renderMessagePart(part, index))}

      {/* 最后单独渲染 TodoList 组件，确保在消息末尾 */}
      {(() => {
        const todoListPart = parts.find(part => part.toolName === 'todo_list_tool');
        if (todoListPart && currentTodos && currentTodos.length > 0) {
          return (
            <div key={currentTraceId} className="mb-4">
              <TodoList
                key={currentTraceId}
                items={currentTodos}
                timestamp={new Date()}
              />
            </div>
          );
        }
        return null;
      })()}
    </div>
  );
}