/**
 * 折线图组件
 * 用于展示时间序列或连续数据的生成式UI组件
 */
import React from 'react';
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';
import { TrendingUp, Calendar, BarChart3, Inbox } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

export interface LineChartData {
  name: string;
  value?: number | string;
  [key: string]: any; // 支持多个数据系列
}

export interface LineChartProps {
  title?: string;
  description?: string;
  data: LineChartData[];
  x_key?: string;
  y_keys?: string[];
  colors?: string[];
  area?: boolean; // 是否显示为面积图
  height?: number;
  show_grid?: boolean;
  show_legend?: boolean;
  show_tooltip?: boolean;
}

export interface LineChartState {
  state: 'loading' | 'success' | 'error';
  data?: LineChartProps;
  error?: string;
}

// 默认颜色方案
const DEFAULT_COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#06b6d4', // cyan-500
  '#84cc16', // lime-500
];

/**
 * 折线图组件 - 成功状态
 */
export const LineChart: React.FC<LineChartProps> = ({
  title,
  description,
  data,
  x_key = 'name',
  y_keys = ['value'],
  colors = DEFAULT_COLORS,
  area = false,
  height = 300,
  show_grid = true,
  show_legend = true,
  show_tooltip = true,
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="my-4 p-6 max-w-4xl bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3 mb-4">
          <TrendingUp className="w-6 h-6 text-gray-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              {title || '折线图'}
            </h3>
            {description && (
              <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
            )}
          </div>
        </div>
        <Alert className="border-dashed">
          <Inbox className="h-4 w-4" />
          <AlertDescription className="text-center">
            暂无数据
          </AlertDescription>
        </Alert>
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
          <TrendingUp className="w-6 h-6 text-red-500" />
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

  const ChartComponent = area ? AreaChart : RechartsLineChart;
  const DataComponent = area ? Area : Line;

  return (
    <div className="my-4 p-6 max-w-4xl bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 transition-all hover:shadow-md">
      {/* 标题栏 */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
          <TrendingUp className="w-6 h-6 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {title || '折线图'}
          </h3>
          {description && (
            <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <Calendar className="w-4 h-4" />
          <span>{validData.length} 个数据点</span>
        </div>
      </div>

      {/* 图表区域 */}
      <div className="w-full" style={{ height: `${height}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <ChartComponent data={validData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            {show_grid && (
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#e5e7eb"
                strokeOpacity={0.5}
                className="dark:stroke-gray-700"
              />
            )}

            <XAxis
              dataKey={x_key}
              tick={{ fontSize: 12, fill: '#6b7280' }}
              className="dark:fill-gray-400"
              stroke="#9ca3af"
            />

            <YAxis
              tick={{ fontSize: 12, fill: '#6b7280' }}
              className="dark:fill-gray-400"
              stroke="#9ca3af"
            />

            {show_tooltip && (
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  fontSize: '12px'
                }}
              />
            )}

            {show_legend && (
              <Legend
                wrapperStyle={{ fontSize: '12px' }}
                className="dark:text-gray-300"
              />
            )}

            {y_keys.map((key, index) => (
              <DataComponent
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                strokeWidth={2}
                fill={area ? colors[index % colors.length] : undefined}
                fillOpacity={area ? 0.3 : undefined}
                dot={{ r: 4, fill: colors[index % colors.length] }}
                activeDot={{ r: 6 }}
              />
            ))}
          </ChartComponent>
        </ResponsiveContainer>
      </div>

      {/* 数据摘要 */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 grid grid-cols-2 md:grid-cols-4 gap-4">
        {y_keys.map((key) => {
          const values = validData.map(item => Number(item[key]) || 0).filter(v => !isNaN(v));
          if (values.length === 0) return null;

          const max = Math.max(...values);
          const min = Math.min(...values);
          const avg = values.reduce((a, b) => a + b, 0) / values.length;

          return (
            <div key={key} className="text-center">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">{key}</div>
              <div className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                {avg.toFixed(1)}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {min.toFixed(1)} - {max.toFixed(1)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/**
 * 折线图加载状态组件
 */
export const LineChartSkeleton: React.FC = () => {
  return (
    <div className="my-4 p-6 max-w-4xl bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 animate-pulse">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
        <div>
          <div className="h-6 w-32 bg-gray-300 dark:bg-gray-600 rounded mb-2"></div>
          <div className="h-4 w-48 bg-gray-300 dark:bg-gray-600 rounded"></div>
        </div>
      </div>

      <div className="w-full h-64 bg-gray-200 dark:bg-gray-700 rounded-lg mb-4"></div>

      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="text-center">
            <div className="h-4 w-12 bg-gray-300 dark:bg-gray-600 rounded mx-auto mb-2"></div>
            <div className="h-6 w-16 bg-gray-300 dark:bg-gray-600 rounded mx-auto mb-1"></div>
            <div className="h-3 w-20 bg-gray-300 dark:bg-gray-600 rounded mx-auto"></div>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * 折线图错误状态组件
 */
export const LineChartError: React.FC<{ error: string; title?: string }> = ({
  error,
  title,
}) => {
  return (
    <div className="my-4 p-6 max-w-4xl bg-red-50 dark:bg-red-900/20 rounded-lg shadow-sm border border-red-200 dark:border-red-800">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
          <TrendingUp className="w-6 h-6 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
            {title || '折线图生成失败'}
          </h3>
        </div>
      </div>
      <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
    </div>
  );
};