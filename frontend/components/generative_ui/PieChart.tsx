/**
 * 饼图组件
 * 用于展示部分与整体关系的生成式UI组件
 */
import React from 'react';
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend
} from 'recharts';
import { PieChart as PieChartIcon, Percent, Circle } from 'lucide-react';

export interface PieChartData {
  name: string;
  value: number;
  color?: string;
}

export interface PieChartProps {
  title?: string;
  description?: string;
  data: PieChartData[];
  inner_radius?: number; // 内圆半径，用于创建环形图
  outer_radius?: number;
  start_angle?: number;
  end_angle?: number;
  show_percentage?: boolean;
  show_legend?: boolean;
  show_tooltip?: boolean;
  colors?: string[];
  height?: number;
  label_position?: 'inside' | 'outside' | 'none';
}

export interface PieChartState {
  state: 'loading' | 'success' | 'error';
  data?: PieChartProps;
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
  '#f97316', // orange-500
  '#6366f1', // indigo-500
];

// 自定义标签渲染器
const renderCustomizedLabel = ({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percent,
  name,
  showPercentage,
  position
}: any) => {
  if (position === 'none') return null;

  const RADIAN = Math.PI / 180;
  const radius = position === 'inside' ? innerRadius + (outerRadius - innerRadius) * 0.5 : outerRadius * 1.2;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  if (position === 'inside') {
    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        fontSize={12}
        fontWeight="bold"
      >
        {showPercentage ? `${(percent * 100).toFixed(0)}%` : ''}
      </text>
    );
  }

  return (
    <text
      x={x}
      y={y}
      fill="#374151"
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
      fontSize={12}
      className="dark:fill-gray-300"
    >
      {name}
    </text>
  );
};

/**
 * 饼图组件 - 成功状态
 */
export const PieChart: React.FC<PieChartProps> = ({
  title,
  description,
  data,
  inner_radius = 0,
  outer_radius = 80,
  start_angle = 0,
  end_angle = 360,
  show_percentage = true,
  show_legend = true,
  show_tooltip = true,
  colors = DEFAULT_COLORS,
  height = 300,
  label_position = 'outside'
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="my-4 p-6 max-w-4xl bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3 mb-4">
          <PieChartIcon className="w-6 h-6 text-gray-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              {title || '饼图'}
            </h3>
            {description && (
              <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center justify-center h-48 text-gray-400">
          <div className="text-center">
            <Circle className="w-12 h-12 mx-auto mb-2" />
            <p>暂无数据</p>
          </div>
        </div>
      </div>
    );
  }

  // 验证和过滤数据
  const validData = data.filter(item =>
    item &&
    typeof item === 'object' &&
    'name' in item &&
    'value' in item &&
    typeof item.value === 'number' &&
    item.value >= 0
  );

  if (validData.length === 0) {
    return (
      <div className="my-4 p-6 max-w-4xl bg-red-50 dark:bg-red-900/20 rounded-xl shadow-lg border border-red-200 dark:border-red-800">
        <div className="flex items-center gap-3 mb-4">
          <PieChartIcon className="w-6 h-6 text-red-500" />
          <div>
            <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
              数据格式错误
            </h3>
          </div>
        </div>
        <p className="text-sm text-red-700 dark:text-red-300">
          饼图需要包含 name 和 value 字段的有效数据
        </p>
      </div>
    );
  }

  // 计算总计和百分比
  const total = validData.reduce((sum, item) => sum + item.value, 0);
  const dataWithPercentage = validData.map((item, index) => ({
    ...item,
    percentage: total > 0 ? (item.value / total) * 100 : 0,
    color: item.color || colors[index % colors.length]
  }));

  return (
    <div className="my-4 p-6 max-w-4xl bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 transition-all hover:shadow-xl">
      {/* 标题栏 */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900 rounded-full flex items-center justify-center">
          <PieChartIcon className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {title || '饼图'}
          </h3>
          {description && (
            <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <Percent className="w-4 h-4" />
          <span>{validData.length} 项 | 总计: {total.toLocaleString()}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 饼图区域 */}
        <div className="lg:col-span-2">
          <div className="w-full" style={{ height: `${height}px` }}>
            <ResponsiveContainer width="100%" height="100%">
              <RechartsPieChart>
                <Pie
                  data={dataWithPercentage}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ ...props }) => renderCustomizedLabel({
                    ...props,
                    showPercentage: show_percentage,
                    position: label_position
                  })}
                  outerRadius={outer_radius}
                  innerRadius={inner_radius}
                  startAngle={start_angle}
                  endAngle={end_angle}
                  dataKey="value"
                >
                  {dataWithPercentage.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>

                {show_tooltip && (
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      fontSize: '12px'
                    }}
                    formatter={(value: number, name: string) => [
                      `${value.toLocaleString()} (${total > 0 ? ((value / total) * 100).toFixed(1) : 0}%)`,
                      name
                    ]}
                  />
                )}
              </RechartsPieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 数据列表 */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">数据明细</h4>
          {dataWithPercentage.map((item, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="flex items-center gap-3">
                <div
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
                  {item.name}
                </span>
              </div>
              <div className="text-right">
                <div className="text-sm font-semibold text-gray-800 dark:text-gray-100">
                  {item.value.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {item.percentage.toFixed(1)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 图例 */}
      {show_legend && label_position !== 'outside' && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex flex-wrap gap-4 justify-center">
            {dataWithPercentage.map((item, index) => (
              <div key={index} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-xs text-gray-600 dark:text-gray-400">
                  {item.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 统计摘要 */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">总计</div>
          <div className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {total.toLocaleString()}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">项目数</div>
          <div className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {validData.length}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">最大值</div>
          <div className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {Math.max(...validData.map(d => d.value)).toLocaleString()}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">平均值</div>
          <div className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {total > 0 ? Math.round(total / validData.length).toLocaleString() : 0}
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * 饼图加载状态组件
 */
export const PieChartSkeleton: React.FC = () => {
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="w-full h-64 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
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
 * 饼图错误状态组件
 */
export const PieChartError: React.FC<{ error: string; title?: string }> = ({
  error,
  title,
}) => {
  return (
    <div className="my-4 p-6 max-w-4xl bg-red-50 dark:bg-red-900/20 rounded-xl shadow-lg border border-red-200 dark:border-red-800">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
          <PieChartIcon className="w-6 h-6 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
            {title || '饼图生成失败'}
          </h3>
        </div>
      </div>
      <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
    </div>
  );
};