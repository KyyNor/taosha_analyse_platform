"use client";

import { useState, useMemo } from "react";
import { Input } from "./input";
import { Button } from "./button";
import { Badge } from "./badge";
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
  ChevronRight
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

interface ColumnConfig {
  key: string;
  label: string;
  type?: 'text' | 'datetime' | 'boolean' | 'object' | 'number';
  maxLength?: number;
  width?: string;
  sortable?: boolean;
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
  pagination?: {
    pageSize: number;
    currentPage: number;
    total: number;
    onPageChange: (page: number) => void;
  };
  emptyText?: string;
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
  pagination,
  emptyText = "暂无数据"
}: MetadataTableProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<{ item: any; index: number } | null>(null);

  // 过滤数据
  const filteredData = useMemo(() => {
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
  }, [data, columns, searchQuery]);

  // 分页数据
  const paginatedData = useMemo(() => {
    if (!pagination) return filteredData;

    const startIndex = (pagination.currentPage - 1) * pagination.pageSize;
    const endIndex = startIndex + pagination.pageSize;
    return filteredData.slice(startIndex, endIndex);
  }, [filteredData, pagination]);

  // 格式化单元格值
  const formatCellValue = (value: any, column: ColumnConfig) => {
    const type = column.type || 'text';
    const maxLength = column.maxLength;

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
      default:
        return maxLength
          ? truncateText(safeString(value), maxLength)
          : safeString(value);
    }
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
            onChange={(e) => setSearchQuery(e.target.value)}
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
      <div className="rounded-md border">
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
              {paginatedData.map((row, index) => (
                <TableRow key={index}>
                  {columns.map((column) => (
                    <TableCell
                      key={column.key}
                      className="px-3 py-2"
                    >
                      {formatCellValue(row[column.key], column)}
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
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}

        {/* 空状态 */}
        {!loading && paginatedData.length === 0 && (
          <div className="p-8 text-center text-sm text-muted-foreground">
            {emptyText}
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