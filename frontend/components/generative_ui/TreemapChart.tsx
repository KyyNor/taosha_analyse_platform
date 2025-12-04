/**
 * 树图组件（矩形树图）
 * 用于展示层级数据和占比关系的生成式UI组件
 */
import React from 'react';
import {
  Treemap,
  ResponsiveContainer,
  Tooltip
} from 'recharts';
import { Network, BarChart3, Layers } from 'lucide-react';

export interface TreemapNode {
  name: string;
  value: number;
  children?: TreemapNode[];
  [key: string]: any;
}

export interface TreemapChartProps {
  title?: string;
  description?: string;
  data: TreemapNode[];
  name_key?: string;
  value_key?: string;
  colors?: string[];
  height?: number;
  show_values?: boolean;
}

export interface TreemapChartState {
  state: 'loading' | 'success' | 'error';
  data?: TreemapChartProps;
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

// 自定义内容渲染器
const CustomizedContent: React.FC<any> = (props) => {
  const { root, depth, x, y, width, height, index, name, value, colors } = props;

  // 只显示面积足够大的标签
  const showLabel = width > 60 && height > 40;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{
          fill: depth < 2 ? colors[index % colors.length] : colors[0],
          stroke: '#fff',
          strokeWidth: 2,
          strokeOpacity: 1,
          opacity: depth === 0 ? 1 : 0.9 - depth * 0.1,
        }}
      />
      {showLabel && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 8}
            textAnchor="middle"
            fill="#fff"
            fontSize={14}
            fontWeight="bold"
          >
            {name}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 10}
            textAnchor="middle"
            fill="#fff"
            fontSize={12}
            opacity={0.9}
          >
            {value ? value.toLocaleString() : ''}
          </text>
        </>
      )}
    </g>
  );
};

/**
 * 计算总计
 */
const calculateTotal = (nodes: TreemapNode[]): number => {
  return nodes.reduce((sum, node) => {
    if (node.children && node.children.length > 0) {
      return sum + calculateTotal(node.children);
    }
    return sum + (node.value || 0);
  }, 0);
};

/**
 * 统计节点数量
 */
const countNodes = (nodes: TreemapNode[]): number => {
  return nodes.reduce((count, node) => {
    if (node.children && node.children.length > 0) {
      return count + 1 + countNodes(node.children);
    }
    return count + 1;
  }, 0);
};

/**
 * 树图组件 - 成功状态
 */
export const TreemapChart: React.FC<TreemapChartProps> = ({
  title,
  description,
  data,
  colors = DEFAULT_COLORS,
  height = 400,
  show_values = true,
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="my-4 p-6 max-w-6xl bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3 mb-4">
          <Network className="w-6 h-6 text-gray-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              {title || '树图'}
            </h3>
            {description && (
              <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center justify-center h-64 text-gray-400">
          <div className="text-center">
            <Layers className="w-12 h-12 mx-auto mb-2" />
            <p>暂无数据</p>
          </div>
        </div>
      </div>
    );
  }

  // 验证数据格式
  const hasValidData = data.some(item =>
    item &&
    typeof item === 'object' &&
    'name' in item &&
    'value' in item
  );

  if (!hasValidData) {
    return (
      <div className="my-4 p-6 max-w-6xl bg-red-50 dark:bg-red-900/20 rounded-xl shadow-lg border border-red-200 dark:border-red-800">
        <div className="flex items-center gap-3 mb-4">
          <Network className="w-6 h-6 text-red-500" />
          <div>
            <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
              数据格式错误
            </h3>
          </div>
        </div>
        <p className="text-sm text-red-700 dark:text-red-300">
          树图需要包含 name 和 value 字段的层级数据
        </p>
      </div>
    );
  }

  // 计算统计信息
  const total = calculateTotal(data);
  const nodeCount = countNodes(data);

  return (
    <div className="my-4 p-6 max-w-6xl bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 transition-all hover:shadow-md">
      {/* 标题栏 */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
          <Network className="w-6 h-6 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {title || '树图'}
          </h3>
          {description && (
            <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <BarChart3 className="w-4 h-4" />
          <span>{nodeCount} 个节点 | 总计: {total.toLocaleString()}</span>
        </div>
      </div>

      {/* 树图区域 */}
      <div className="w-full bg-gray-50 dark:bg-gray-900 rounded-lg p-4" style={{ height: `${height}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <Treemap
            data={data}
            dataKey="value"
            stroke="#fff"
            fill="#8884d8"
            content={<CustomizedContent colors={colors} />}
          >
            <Tooltip
              contentStyle={{
                backgroundColor: '#ffffff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value: number) => [
                `${value.toLocaleString()} (${total > 0 ? ((value / total) * 100).toFixed(1) : 0}%)`,
                '数值'
              ]}
            />
          </Treemap>
        </ResponsiveContainer>
      </div>

      {/* 使用说明 */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          💡 提示：矩形大小表示数值大小，颜色深浅表示层级深度，鼠标悬停查看详情
        </p>
      </div>

      {/* 统计摘要 */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">总计</div>
          <div className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {total.toLocaleString()}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">节点数</div>
          <div className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {nodeCount}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">根节点数</div>
          <div className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {data.length}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">平均值</div>
          <div className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {nodeCount > 0 ? Math.round(total / nodeCount).toLocaleString() : 0}
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * 树图加载状态组件
 */
export const TreemapChartSkeleton: React.FC = () => {
  return (
    <div className="my-4 p-6 max-w-6xl bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 animate-pulse">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
        <div className="flex-1">
          <div className="h-6 w-32 bg-gray-300 dark:bg-gray-600 rounded mb-2"></div>
          <div className="h-4 w-48 bg-gray-300 dark:bg-gray-600 rounded"></div>
        </div>
        <div className="h-4 w-24 bg-gray-300 dark:bg-gray-600 rounded"></div>
      </div>

      <div className="w-full h-96 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>

      <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="text-center">
            <div className="h-4 w-12 bg-gray-300 dark:bg-gray-600 rounded mx-auto mb-2"></div>
            <div className="h-6 w-16 bg-gray-300 dark:bg-gray-600 rounded mx-auto"></div>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * 树图错误状态组件
 */
export const TreemapChartError: React.FC<{ error: string; title?: string }> = ({
  error,
  title,
}) => {
  return (
    <div className="my-4 p-6 max-w-6xl bg-red-50 dark:bg-red-900/20 rounded-lg shadow-sm border border-red-200 dark:border-red-800">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
          <Network className="w-6 h-6 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
            {title || '树图生成失败'}
          </h3>
        </div>
      </div>
      <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
    </div>
  );
};
