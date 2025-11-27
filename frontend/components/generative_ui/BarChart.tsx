/**
 * 柱状图组件
 * 用于展示分类数据比较的生成式UI组件
 */
import React from 'react';
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts';
import { BarChart3 } from 'lucide-react';

export interface BarChartData {
  name: string;
  value?: number | string;
  [key: string]: any; // 支持多个数据系列
}

export interface BarChartProps {
  title?: string;
  description?: string;
  data: BarChartData[];
  x_key?: string;
  y_keys?: string[];
  orientation?: 'vertical' | 'horizontal';
  stacked?: boolean;
  colors?: string[];
  height?: number;
  show_grid?: boolean;
  show_legend?: boolean;
  show_tooltip?: boolean;
  bar_radius?: number;
}

export interface BarChartState {
  state: 'loading' | 'success' | 'error';
  data?: BarChartProps;
  error?: string;
}

// 默认颜色方案
const DEFAULT_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'
];

/**
 * 自定义工具提示
 */
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white dark:bg-gray-800 p-3 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
        <p className="font-medium text-gray-800 dark:text-gray-100 mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center justify-between gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-gray-600 dark:text-gray-400">{entry.name}:</span>
            </div>
            <span className="font-medium text-gray-800 dark:text-gray-100">
              {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

/**
 * 柱状图组件 - 成功状态
 */
export const BarChart: React.FC<BarChartProps> = ({
  title,
  description,
  data,
  x_key = 'name',
  y_keys = ['value'],
  orientation = 'vertical',
  stacked = false,
  colors = DEFAULT_COLORS,
  height = 300,
  show_grid = true,
  show_legend = true,
  show_tooltip = true,
  bar_radius = 4,
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="my-4 p-6 max-w-4xl bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3 mb-4">
          <BarChart3 className="w-6 h-6 text-gray-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              {title || '柱状图'}
            </h3>
            {description && (
              <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center justify-center h-48 text-gray-400">
          <div className="text-center">
            <BarChart3 className="w-12 h-12 mx-auto mb-2" />
            <p>暂无数据</p>
          </div>
        </div>
      </div>
    );
  }

  // 验证数据格式
  const validData = data.filter(item =>
    item && typeof item === 'object' && x_key in item
  );

  if (validData.length === 0) {
    return (
      <div className="my-4 p-6 max-w-4xl bg-red-50 dark:bg-red-900/20 rounded-xl shadow-lg border border-red-200 dark:border-red-800">
        <div className="flex items-center gap-3 mb-4">
          <BarChart3 className="w-6 h-6 text-red-500" />
          <div>
            <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
              数据格式错误
            </h3>
          </div>
        </div>
        <p className="text-sm text-red-700 dark:text-red-300">
          缺少必要的 x_key 字段: {x_key}
        </p>
      </div>
    );
  }

  return (
    <div className="my-4 p-6 max-w-4xl bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 transition-all hover:shadow-xl">
      {/* 标题栏 */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-amber-100 dark:bg-amber-900 rounded-full flex items-center justify-center">
          <BarChart3 className="w-6 h-6 text-amber-600 dark:text-amber-400" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {title || '柱状图'}
          </h3>
          {description && (
            <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <BarChart3 className="w-4 h-4" />
          <span>{validData.length} 个数据点</span>
          {stacked && <span className="px-2 py-1 bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-200 rounded-full">堆叠</span>}
          {orientation === 'horizontal' && <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full">横向</span>}
        </div>
      </div>

      {/* 图表区域 */}
      <div className="w-full" style={{ height: `${height}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <RechartsBarChart
            data={validData}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            layout={orientation === 'horizontal' ? 'horizontal' : 'vertical'}
          >
            {show_grid && (
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#e5e7eb"
                strokeOpacity={0.5}
                className="dark:stroke-gray-700"
              />
            )}

            {orientation === 'vertical' ? (
              <>
                <XAxis
                  dataKey={x_key}
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                  className="dark:fill-gray-400"
                  stroke="#9ca3af"
                  angle={validData.length > 6 ? -45 : 0}
                  textAnchor={validData.length > 6 ? 'end' : 'middle'}
                  height={validData.length > 6 ? 80 : 30}
                />
                <YAxis
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                  className="dark:fill-gray-400"
                  stroke="#9ca3af"
                />
              </>
            ) : (
              <>
                <XAxis
                  type="number"
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                  className="dark:fill-gray-400"
                  stroke="#9ca3af"
                />
                <YAxis
                  type="category"
                  dataKey={x_key}
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                  className="dark:fill-gray-400"
                  stroke="#9ca3af"
                  width={100}
                />
              </>
            )}

            <Tooltip />

            {show_legend && (
              <Legend
                wrapperStyle={{ fontSize: '12px' }}
                className="dark:text-gray-300"
              />
            )}

            {y_keys.map((key, index) => (
              <Bar
                key={key}
                dataKey={key}
                fill={colors[index % colors.length]}
                radius={[bar_radius, bar_radius, 0, 0]}
                stackId={stacked ? 'stack' : undefined}
              >
                {validData.map((entry, entryIndex) => (
                  <Cell
                    key={`cell-${entryIndex}`}
                    fill={colors[index % colors.length]}
                  />
                ))}
              </Bar>
            ))}
          </RechartsBarChart>
        </ResponsiveContainer>
      </div>

      {/* 数据统计 */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">数据统计</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {y_keys.map((key) => {
            const values = validData.map(item => Number(item[key]) || 0).filter(v => !isNaN(v));
            if (values.length === 0) {
              return (
                <div key={key} className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                  <div className="text-sm font-medium text-gray-600 dark:text-gray-400">{key}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">无数据</div>
                </div>
              );
            }

            const max = Math.max(...values);
            const min = Math.min(...values);
            const sum = values.reduce((a, b) => a + b, 0);
            const avg = sum / values.length;

            return (
              <div key={key} className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">{key}</div>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">最大值:</span>
                    <span className="font-medium text-gray-800 dark:text-gray-100">
                      {max.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">平均值:</span>
                    <span className="font-medium text-gray-800 dark:text-gray-100">
                      {avg.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">总计:</span>
                    <span className="font-medium text-gray-800 dark:text-gray-100">
                      {sum.toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

/**
 * 柱状图加载状态组件
 */
export const BarChartSkeleton: React.FC = () => {
  return (
    <div className="my-4 p-6 max-w-4xl bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 animate-pulse">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
        <div className="flex-1">
          <div className="h-6 w-32 bg-gray-300 dark:bg-gray-600 rounded mb-2"></div>
          <div className="h-4 w-48 bg-gray-300 dark:bg-gray-600 rounded"></div>
        </div>
        <div className="h-4 w-24 bg-gray-300 dark:bg-gray-600 rounded"></div>
      </div>

      <div className="w-full h-64 bg-gray-200 dark:bg-gray-700 rounded-lg mb-6"></div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-gray-200 dark:bg-gray-700 p-4 rounded-lg">
            <div className="h-4 w-16 bg-gray-300 dark:bg-gray-600 rounded mb-3"></div>
            <div className="space-y-2">
              <div className="h-3 w-20 bg-gray-300 dark:bg-gray-600 rounded"></div>
              <div className="h-3 w-16 bg-gray-300 dark:bg-gray-600 rounded"></div>
              <div className="h-3 w-24 bg-gray-300 dark:bg-gray-600 rounded"></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * 柱状图错误状态组件
 */
export const BarChartError: React.FC<{ error: string; title?: string }> = ({
  error,
  title,
}) => {
  return (
    <div className="my-4 p-6 max-w-4xl bg-red-50 dark:bg-red-900/20 rounded-xl shadow-lg border border-red-200 dark:border-red-800">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
          <BarChart3 className="w-6 h-6 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
            {title || '柱状图生成失败'}
          </h3>
        </div>
      </div>
      <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
    </div>
  );
};