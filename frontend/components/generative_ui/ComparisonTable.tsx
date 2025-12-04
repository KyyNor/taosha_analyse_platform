/**
 * 双主体对比表组件
 * 用于对比两个主体（如支行、产品等）在多个指标上的表现
 */
import React from 'react';
import { GitCompare, TrendingUp, TrendingDown, Award, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ComparisonMetric {
  name: string;
  value_a: number;
  value_b: number;
  direction: 'higher_is_better' | 'lower_is_better';
  better: 'a' | 'b' | 'equal';
  unit?: string;
  description?: string;
}

export interface ComparisonTableProps {
  title?: string;
  description?: string;
  subject_a: string;
  subject_b: string;
  metrics: ComparisonMetric[];
  highlight_color?: string;
  decimal_places?: number;
}

export interface ComparisonTableState {
  state: 'loading' | 'success' | 'error';
  data?: ComparisonTableProps;
  error?: string;
}

/**
 * 格式化数值显示
 */
const formatValue = (value: number, decimalPlaces: number = 2, unit: string = ''): string => {
  const formatted = value.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimalPlaces
  });
  return unit ? `${formatted} ${unit}` : formatted;
};

/**
 * 双主体对比表组件 - 成功状态
 */
export const ComparisonTable: React.FC<ComparisonTableProps> = ({
  title,
  description,
  subject_a,
  subject_b,
  metrics,
  highlight_color = '#10b981',
  decimal_places = 2,
}) => {
  if (!metrics || metrics.length === 0) {
    return (
      <div className="my-4 p-6 max-w-4xl bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3 mb-4">
          <GitCompare className="w-6 h-6 text-gray-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              {title || '对比表'}
            </h3>
            {description && (
              <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center justify-center h-48 text-gray-400">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 mx-auto mb-2" />
            <p>暂无对比数据</p>
          </div>
        </div>
      </div>
    );
  }

  // 统计主体A和主体B各有多少指标更优
  const scoreA = metrics.filter(m => m.better === 'a').length;
  const scoreB = metrics.filter(m => m.better === 'b').length;
  const scoreEqual = metrics.filter(m => m.better === 'equal').length;

  return (
    <div className="my-4 p-6 max-w-5xl bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 transition-all hover:shadow-md">
      {/* 标题栏 */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center">
          <GitCompare className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {title || `${subject_a} vs ${subject_b}`}
          </h3>
          {description && (
            <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
          )}
        </div>
      </div>

      {/* 比分卡 */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className={cn(
          "p-4 rounded-lg text-center transition-all",
          scoreA > scoreB ? "bg-emerald-50 dark:bg-emerald-900/20 border-2 border-emerald-500" : "bg-gray-50 dark:bg-gray-700"
        )}>
          <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
            {subject_a}
          </div>
          <div className={cn(
            "text-3xl font-bold",
            scoreA > scoreB ? "text-emerald-600 dark:text-emerald-400" : "text-gray-700 dark:text-gray-300"
          )}>
            {scoreA}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            优势指标
          </div>
        </div>

        <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg text-center flex items-center justify-center">
          <div className="text-center">
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">持平</div>
            <div className="text-2xl font-bold text-gray-600 dark:text-gray-300">{scoreEqual}</div>
          </div>
        </div>

        <div className={cn(
          "p-4 rounded-lg text-center transition-all",
          scoreB > scoreA ? "bg-emerald-50 dark:bg-emerald-900/20 border-2 border-emerald-500" : "bg-gray-50 dark:bg-gray-700"
        )}>
          <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
            {subject_b}
          </div>
          <div className={cn(
            "text-3xl font-bold",
            scoreB > scoreA ? "text-emerald-600 dark:text-emerald-400" : "text-gray-700 dark:text-gray-300"
          )}>
            {scoreB}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            优势指标
          </div>
        </div>
      </div>

      {/* 对比表格 */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b-2 border-gray-200 dark:border-gray-600">
              <th className="px-4 py-3 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded-tl-lg">
                {subject_a}
              </th>
              <th className="px-4 py-3 text-center font-semibold text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-600">
                指标
              </th>
              <th className="px-4 py-3 text-right font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded-tr-lg">
                {subject_b}
              </th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric, index) => (
              <tr
                key={index}
                className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                {/* 主体A的值 */}
                <td className={cn(
                  "px-4 py-3 text-left font-medium transition-all",
                  metric.better === 'a' && "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 font-bold"
                )}>
                  <div className="flex items-center gap-2">
                    {metric.better === 'a' && (
                      <Award className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    )}
                    <span>{formatValue(metric.value_a, decimal_places, metric.unit)}</span>
                    {metric.better === 'a' && metric.direction === 'higher_is_better' && (
                      <TrendingUp className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    )}
                    {metric.better === 'a' && metric.direction === 'lower_is_better' && (
                      <TrendingDown className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    )}
                  </div>
                </td>

                {/* 指标名称（中间列） */}
                <td className="px-4 py-3 text-center bg-gray-50 dark:bg-gray-800">
                  <div className="font-medium text-gray-800 dark:text-gray-200">
                    {metric.name}
                  </div>
                  {metric.description && (
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {metric.description}
                    </div>
                  )}
                  <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    {metric.direction === 'higher_is_better' ? '↑ 越高越好' : '↓ 越低越好'}
                  </div>
                </td>

                {/* 主体B的值 */}
                <td className={cn(
                  "px-4 py-3 text-right font-medium transition-all",
                  metric.better === 'b' && "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 font-bold"
                )}>
                  <div className="flex items-center justify-end gap-2">
                    {metric.better === 'b' && metric.direction === 'lower_is_better' && (
                      <TrendingDown className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    )}
                    {metric.better === 'b' && metric.direction === 'higher_is_better' && (
                      <TrendingUp className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    )}
                    <span>{formatValue(metric.value_b, decimal_places, metric.unit)}</span>
                    {metric.better === 'b' && (
                      <Award className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 使用说明 */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          💡 提示：<Award className="w-3 h-3 inline" /> 标记表示该指标表现更优
        </p>
      </div>
    </div>
  );
};

/**
 * 对比表加载状态组件
 */
export const ComparisonTableSkeleton: React.FC = () => {
  return (
    <div className="my-4 p-6 max-w-5xl bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 animate-pulse">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
        <div className="flex-1">
          <div className="h-6 w-48 bg-gray-300 dark:bg-gray-600 rounded mb-2"></div>
          <div className="h-4 w-64 bg-gray-300 dark:bg-gray-600 rounded"></div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        {[1, 2, 3].map(i => (
          <div key={i} className="p-4 bg-gray-200 dark:bg-gray-700 rounded-lg">
            <div className="h-4 w-16 bg-gray-300 dark:bg-gray-600 rounded mx-auto mb-2"></div>
            <div className="h-8 w-12 bg-gray-300 dark:bg-gray-600 rounded mx-auto mb-1"></div>
            <div className="h-3 w-20 bg-gray-300 dark:bg-gray-600 rounded mx-auto"></div>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
        ))}
      </div>
    </div>
  );
};

/**
 * 对比表错误状态组件
 */
export const ComparisonTableError: React.FC<{ error: string; title?: string }> = ({
  error,
  title,
}) => {
  return (
    <div className="my-4 p-6 max-w-5xl bg-red-50 dark:bg-red-900/20 rounded-lg shadow-sm border border-red-200 dark:border-red-800">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
          <GitCompare className="w-6 h-6 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
            {title || '对比表生成失败'}
          </h3>
        </div>
      </div>
      <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
    </div>
  );
};
