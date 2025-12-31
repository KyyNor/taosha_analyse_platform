/**
 * 通用表格组件
 * 用于展示结构化数据的生成式UI组件
 */
import React, { useState, useMemo } from 'react';
import { Table as ShadcnTable, Inbox, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export interface TableColumn {
  key: string;
  label: string;
  type?: 'text' | 'number' | 'percentage' | 'currency' | 'date' | 'boolean';
  format?: string;
  width?: string;
  align?: 'left' | 'center' | 'right';
  sortable?: boolean;
}

export interface TableData {
  [key: string]: any;
}

export interface TableProps {
  title?: string;
  description?: string;
  data: TableData[];
  columns?: TableColumn[];
  sortable?: boolean;
  paginated?: boolean;
  page_size?: number;
  stripe?: boolean;
  bordered?: boolean;
  compact?: boolean;
  highlight_column?: string;
  highlight_color?: string;
  max_rows?: number;
  show_index?: boolean;
  index_label?: string;
}

export interface TableState {
  state: 'loading' | 'success' | 'error';
  data?: TableProps;
  error?: string;
}

/**
 * 格式化单元格值
 */
const formatCellValue = (value: any, column: TableColumn): string => {
  if (value === null || value === undefined) {
    return '-';
  }

  const { type = 'text', format } = column;

  switch (type) {
    case 'number':
      if (format) {
        try {
          return format.replace('{}', String(value)).replace('{:.2f}', String(value.toFixed(2)));
        } catch {
          return String(value);
        }
      }
      return typeof value === 'number' ? value.toLocaleString() : String(value);

    case 'percentage':
      const percentageValue = typeof value === 'number' ? value : parseFloat(value);
      if (isNaN(percentageValue)) return '-';
      if (format) {
        try {
          return format.replace('{}', String(percentageValue)).replace('{:.2%}', String(percentageValue.toFixed(2)));
        } catch {
          return `${(percentageValue * 100).toFixed(2)}%`;
        }
      }
      return `${(percentageValue * 100).toFixed(2)}%`;

    case 'currency':
      const currencyValue = typeof value === 'number' ? value : parseFloat(value);
      if (isNaN(currencyValue)) return '-';
      if (format) {
        try {
          return format.replace('{}', String(currencyValue)).replace('{:.2f}', String(currencyValue.toFixed(2)));
        } catch {
          return `¥${currencyValue.toFixed(2)}`;
        }
      }
      return `¥${currencyValue.toFixed(2)}`;

    case 'date':
      if (value instanceof Date) {
        return value.toLocaleDateString('zh-CN');
      }
      const dateValue = new Date(value);
      if (isNaN(dateValue.getTime())) return String(value);
      return dateValue.toLocaleDateString('zh-CN');

    case 'boolean':
      return value ? '✓' : '✗';

    default:
      return String(value);
  }
};

/**
 * 表格组件 - 成功状态
 */
export const Table: React.FC<TableProps> = ({
  title,
  description,
  data,
  columns,
  sortable = true,
  paginated = false,
  page_size = 10,
  stripe = true,
  bordered = true,
  compact = false,
  highlight_column,
  highlight_color = '#fef3c7',
  max_rows,
  show_index = false,
  index_label = '序号',
}) => {
  // 状态管理
  const [sortColumn, setSortColumn] = useState<string>('');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);

  // 自动推断列配置
  const inferredColumns = useMemo(() => {
    if (columns && columns.length > 0) {
      return columns;
    }

    if (!data || data.length === 0) {
      return [];
    }

    // 收集所有字段
    const allKeys = new Set<string>();
    data.slice(0, 10).forEach(item => {
      if (typeof item === 'object' && item !== null) {
        Object.keys(item).forEach(key => allKeys.add(key));
      }
    });

    // 推断列类型
    return Array.from(allKeys).map(key => {
      const sampleValues = data
        .slice(0, 20)
        .map(item => item[key])
        .filter(v => v !== null && v !== undefined);

      let type: TableColumn['type'] = 'text';
      if (sampleValues.length > 0) {
        const firstVal = sampleValues[0];
        if (typeof firstVal === 'boolean') {
          type = 'boolean';
        } else if (typeof firstVal === 'number') {
          type = 'number';
        }
      }

      return {
        key,
        label: key.replace(/_/g, ' ').replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        type,
        align: type === 'text' ? 'left' : 'right',
      };
    });
  }, [columns, data]);

  // 排序和分页处理
  const processedData = useMemo(() => {
    let result = [...data];

    // 排序
    if (sortColumn && sortable) {
      result.sort((a, b) => {
        const aVal = a[sortColumn];
        const bVal = b[sortColumn];

        if (aVal === bVal) return 0;
        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        if (typeof aVal === 'number' && typeof bVal === 'number') {
          return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
        }

        const aStr = String(aVal);
        const bStr = String(bVal);
        return sortDirection === 'asc'
          ? aStr.localeCompare(bStr)
          : bStr.localeCompare(aStr);
      });
    }

    // 分页
    if (paginated) {
      const startIndex = (currentPage - 1) * page_size;
      const endIndex = startIndex + page_size;
      result = result.slice(startIndex, endIndex);
    }

    // 限制行数
    if (max_rows && !paginated) {
      result = result.slice(0, max_rows);
    }

    return result;
  }, [data, sortColumn, sortDirection, sortable, paginated, currentPage, page_size, max_rows]);

  // 处理排序
  const handleSort = (columnKey: string) => {
    if (!sortable) return;

    if (sortColumn === columnKey) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(columnKey);
      setSortDirection('asc');
    }
  };

  // 分页信息
  const totalPages = paginated ? Math.ceil(data.length / page_size) : 1;

  // 空数据处理
  if (!data || data.length === 0) {
    return (
      <div className="my-4 p-6 max-w-4xl bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3 mb-4">
          <ShadcnTable className="w-6 h-6 text-gray-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              {title || '表格'}
            </h3>
            {description && (
              <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center justify-center h-48 text-gray-400">
          <Alert className="border-dashed">
            <Inbox className="h-4 w-4" />
            <AlertDescription className="text-center">
              暂无数据
            </AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  return (
    <div className="my-4 p-6 max-w-full bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 transition-all hover:shadow-md">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
            <ShadcnTable className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              {title || '数据表格'}
            </h3>
            {description && (
              <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <ShadcnTable className="w-4 h-4" />
          <span>{data.length} 行数据</span>
          {stripe && <Badge variant="outline" className="text-xs">斑马纹</Badge>}
          {compact && <Badge variant="outline" className="text-xs">紧凑</Badge>}
        </div>
      </div>

      {/* 表格区域 */}
      <div className="overflow-x-auto">
        <table className={`w-full ${bordered ? 'border-collapse' : ''}`}>
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
              {show_index && (
                <th className={`px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider ${
                  compact ? 'text-xs' : 'text-sm'
                }`}>
                  {index_label}
                </th>
              )}
              {inferredColumns.map((column) => (
                <th
                  key={column.key}
                  className={`px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ${
                    compact ? 'text-xs' : 'text-sm'
                  } ${
                    column.align === 'right' ? 'text-right' : column.align === 'center' ? 'text-center' : 'text-left'
                  }`}
                  style={{ width: column.width }}
                  onClick={() => sortable && column.sortable !== false && handleSort(column.key)}
                >
                  <div className="flex items-center gap-2">
                    <span>{column.label}</span>
                    {sortable && column.sortable !== false && (
                      <span className="text-gray-400">
                        {sortColumn === column.key ? (
                          sortDirection === 'asc' ? (
                            <ArrowUp className="w-3 h-3" />
                          ) : (
                            <ArrowDown className="w-3 h-3" />
                          )
                        ) : (
                          <ArrowUpDown className="w-3 h-3" />
                        )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className={stripe ? 'divide-y divide-gray-200 dark:divide-gray-700' : ''}>
            {processedData.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className={`${
                  stripe && rowIndex % 2 === 0
                    ? 'bg-white dark:bg-gray-800'
                    : 'bg-gray-50 dark:bg-gray-900'
                } hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors ${
                  bordered ? 'border-b border-gray-200 dark:border-gray-700' : ''
                } ${compact ? 'text-xs' : ''}`}
              >
                {show_index && (
                  <td className={`px-4 py-3 text-sm text-gray-500 dark:text-gray-400 ${
                    compact ? 'text-xs' : ''
                  }`}>
                    {paginated ? (currentPage - 1) * page_size + rowIndex + 1 : rowIndex + 1}
                  </td>
                )}
                {inferredColumns.map((column) => {
                  const value = row[column.key];
                  const isHighlighted = column.key === highlight_column;

                  return (
                    <td
                      key={column.key}
                      className={`px-4 py-3 text-sm text-gray-700 dark:text-gray-200 ${
                        compact ? 'text-xs py-2' : ''
                      } ${
                        column.align === 'right' ? 'text-right' : column.align === 'center' ? 'text-center' : 'text-left'
                      } ${
                        column.type === 'number' || column.type === 'currency' || column.type === 'percentage'
                          ? 'font-mono'
                          : ''
                      }`}
                      style={{
                        backgroundColor: isHighlighted ? highlight_color : undefined,
                      }}
                    >
                      {formatCellValue(value, column)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 分页控件 */}
      {paginated && totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            显示 {(currentPage - 1) * page_size + 1} - {Math.min(currentPage * page_size, data.length)} 条，共 {data.length} 条
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
            >
              上一页
            </Button>
            <span className="flex items-center px-3 text-sm text-gray-500 dark:text-gray-400">
              第 {currentPage} / {totalPages} 页
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
            >
              下一页
            </Button>
          </div>
        </div>
      )}

      {/* 数据统计 */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
          <span>总行数: {data.length}</span>
          <span>列数: {inferredColumns.length}</span>
          {max_rows && !paginated && data.length > max_rows && (
            <span className="text-amber-600 dark:text-amber-400">
              仅显示前 {max_rows} 行数据
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * 表格加载状态组件
 */
export const TableSkeleton: React.FC = () => {
  return (
    <div className="my-4 p-6 max-w-full bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 animate-pulse">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
        <div className="flex-1">
          <div className="h-6 w-32 bg-gray-300 dark:bg-gray-600 rounded mb-2"></div>
          <div className="h-4 w-48 bg-gray-300 dark:bg-gray-600 rounded"></div>
        </div>
      </div>

      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
        ))}
      </div>
    </div>
  );
};

/**
 * 表格错误状态组件
 */
export const TableError: React.FC<{ error: string; title?: string }> = ({
  error,
  title,
}) => {
  return (
    <div className="my-4 p-6 max-w-full bg-red-50 dark:bg-red-900/20 rounded-lg shadow-sm border border-red-200 dark:border-red-800">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
          <ShadcnTable className="w-6 h-6 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
            {title || '表格生成失败'}
          </h3>
        </div>
      </div>
      <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
    </div>
  );
};
