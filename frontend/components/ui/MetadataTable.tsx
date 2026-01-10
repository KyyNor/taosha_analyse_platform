"use client";

import { useState, useMemo } from "react";
import { Input } from "./input";
import { Button } from "./button";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell
} from "./table";
import {
  Eye,
  Edit,
  Trash2,
  Plus,
  ChevronFirst,
  ChevronLast,
  ChevronLeft,
  ChevronRight,
  Inbox
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./dialog";
import {
  formatDateTime,
  formatObjectInline,
  truncateText,
  formatBoolean,
  safeString
} from "@/lib/utils/formatUtils";
import { Alert, AlertDescription } from "./alert";
import { Badge } from "./badge";

interface BadgeConfig {
  [key: string]: {
    variant?: "default" | "secondary" | "destructive" | "outline";
    label?: string;
  };
}

interface ColumnConfig {
  key: string;
  label: string;
  type?: 'text' | 'datetime' | 'boolean' | 'object' | 'number' | 'badge' | 'custom';
  maxLength?: number;
  width?: string;
  sortable?: boolean;
  render?: (value: any, row: any) => React.ReactNode;
  // 标签配置，当type为'badge'时使用
  badgeConfig?: BadgeConfig;
}

interface MetadataTableProps {
  data: any[];
  columns: ColumnConfig[];
  loading?: boolean;
  onRefresh?: () => void;
  onAdd?: () => void;
  onView?: (item: any, index: number) => void;
  onEdit?: (item: any, index: number) => void;
  onDelete?: (item: any, index: number) => void;
  searchPlaceholder?: string;
  showActions?: boolean;
  customActions?: (item: any, index: number) => React.ReactNode;
  pagination?: {
    pageSize: number;
    currentPage: number;
    total: number;
    onPageChange: (page: number) => void;
  };
  emptyText?: string;
  // 受控搜索模式（支持服务端搜索）
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
  // 自定义行样式
  getRowClassName?: (item: any, index: number) => string;
}

export function MetadataTable({
  data,
  columns,
  loading = false,
  onRefresh,
  onAdd,
  onView,
  onEdit,
  onDelete,
  searchPlaceholder = "搜索...",
  showActions = true,
  customActions,
  pagination,
  emptyText = "暂无数据",
  searchQuery: controlledSearchQuery,
  onSearchChange,
  getRowClassName
}: MetadataTableProps) {
  // 支持受控和非受控两种模式
  const [localSearchQuery, setLocalSearchQuery] = useState("");
  const isControlled = controlledSearchQuery !== undefined;
  const searchQuery = isControlled ? controlledSearchQuery : localSearchQuery;

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<{ item: any; index: number } | null>(null);

  // 处理搜索变化
  const handleSearchChange = (value: string) => {
    if (isControlled) {
      // 受控模式：通知父组件，由父组件调用 API
      onSearchChange?.(value);
    } else {
      // 非受控模式：使用本地搜索
      setLocalSearchQuery(value);
    }
  };

  // 过滤数据（仅在非受控模式下使用前端搜索）
  const filteredData = useMemo(() => {
    // 受控模式：数据已由服务端过滤，直接使用
    if (isControlled) return data;

    // 非受控模式：前端过滤
    if (!searchQuery.trim()) return data;

    const query = searchQuery.toLowerCase().trim();
    return data.filter((row) => {
      return columns.some((col) => {
        const value = row[col.key];
        if (value === null || value === undefined) return false;

        if (typeof value === 'object') {
          return JSON.stringify(value).toLowerCase().includes(query);
        }

        return String(value).toLowerCase().includes(query);
      });
    });
  }, [data, columns, searchQuery, isControlled]);

  // 服务端分页：直接使用过滤后的数据，不做客户端 slice
  const displayData = filteredData;

  // 格式化单元格值
  const formatCellValue = (value: any, column: ColumnConfig, row: any) => {
    const type = column.type || 'text';
    const maxLength = column.maxLength;

    // 如果有自定义渲染函数，优先使用
    if (type === 'custom' && column.render) {
      return column.render(value, row);
    }

    switch (type) {
      case 'datetime':
        return formatDateTime(value);
      case 'boolean':
        return formatBoolean(value);
      case 'object':
        return maxLength
          ? truncateText(formatObjectInline(value), maxLength)
          : formatObjectInline(value);
      case 'number':
        return value !== null && value !== undefined ? String(value) : '-';
      case 'badge':
        return renderBadge(value, column.badgeConfig);
      default:
        return maxLength
          ? truncateText(safeString(value), maxLength)
          : safeString(value);
    }
  };

  // 渲染标签
  const renderBadge = (value: any, badgeConfig?: BadgeConfig) => {
    // 对于布尔值，即使是 false 也应该渲染
    if (value === null || value === undefined) return '-';

    const stringValue = String(value);
    const config = badgeConfig?.[stringValue] || {};

    return (
      <Badge variant={config.variant || "secondary"}>
        {config.label || stringValue}
      </Badge>
    );
  };

  // 处理删除
  const handleDeleteClick = (item: any, index: number) => {
    setItemToDelete({ item, index });
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (itemToDelete && onDelete) {
      onDelete(itemToDelete.item, itemToDelete.index);
    }
    setDeleteDialogOpen(false);
    setItemToDelete(null);
  };

  // 获取总页数
  const totalPages = pagination ? Math.ceil(pagination.total / pagination.pageSize) : 1;

  return (
    <div className="space-y-4">
      {/* 搜索和操作栏 */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-1">
          <Input
            placeholder={searchPlaceholder}
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="max-w-sm"
          />
          {onRefresh && (
            <Button variant="outline" onClick={onRefresh} disabled={loading}>
              刷新
            </Button>
          )}
        </div>
        {onAdd && (
          <Button onClick={onAdd}>
            <Plus className="h-4 w-4 mr-2" />
            新增
          </Button>
        )}
      </div>

      {/* 表格 */}
      <div className="rounded-lg border bg-white dark:bg-card text-card-foreground shadow-sm overflow-hidden transition-all hover:shadow-md">
        {loading ? (
          <div className="p-8 text-center text-sm text-muted-foreground">
            加载中...
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                {columns.map((column) => (
                  <TableHead
                    key={column.key}
                    className="px-3 py-2 text-left whitespace-nowrap"
                    style={{ width: column.width }}
                  >
                    {column.label}
                  </TableHead>
                ))}
                {showActions && (
                  <TableHead className="px-3 py-2 text-center whitespace-nowrap w-32">
                    操作
                  </TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayData.map((row, index) => (
                <TableRow 
                  key={index}
                  className={getRowClassName ? getRowClassName(row, index) : undefined}
                >
                  {columns.map((column) => (
                    <TableCell
                      key={column.key}
                      className="px-3 py-2"
                    >
                      {formatCellValue(row[column.key], column, row)}
                    </TableCell>
                  ))}
                  {showActions && (
                    <TableCell className="px-3 py-2">
                      <div className="flex items-center justify-center gap-1">
                        {onView && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onView(row, index)}
                            title="查看详情"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        )}
                        {onEdit && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onEdit(row, index)}
                            title="编辑"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                        )}
                        {onDelete && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteClick(row, index)}
                            title="删除"
                            className="text-destructive hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                        {customActions && customActions(row, index)}
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}

        {/* 空状态 */}
        {!loading && displayData.length === 0 && (
          <div className="p-8">
            <Alert className="border-dashed">
              <Inbox className="h-4 w-4" />
              <AlertDescription className="text-center">
                {emptyText}
              </AlertDescription>
            </Alert>
          </div>
        )}
      </div>

      {/* 分页 */}
      {pagination && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            显示第 {((pagination.currentPage - 1) * pagination.pageSize) + 1} -{" "}
            {Math.min(pagination.currentPage * pagination.pageSize, pagination.total)} 条，
            共 {pagination.total} 条
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onPageChange(1)}
              disabled={pagination.currentPage === 1}
            >
              <ChevronFirst className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onPageChange(pagination.currentPage - 1)}
              disabled={pagination.currentPage === 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>

            <span className="px-3 py-1 text-sm">
              {pagination.currentPage} / {totalPages}
            </span>

            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onPageChange(pagination.currentPage + 1)}
              disabled={pagination.currentPage === totalPages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onPageChange(totalPages)}
              disabled={pagination.currentPage === totalPages}
            >
              <ChevronLast className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* 删除确认对话框 */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              此操作不可撤销，确定要删除这条记录吗？
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}