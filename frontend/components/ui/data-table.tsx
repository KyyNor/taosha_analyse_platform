'use client'

import * as React from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  ChevronDown,
  ChevronUp,
  Settings,
  Search,
  MoreHorizontal
} from 'lucide-react'

// 数据列定义
export interface Column<T> {
  key: string
  title: string
  dataIndex: keyof T
  width?: string | number
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  searchable?: boolean
  render?: (value: any, record: T, index: number) => React.ReactNode
  className?: string
}

// DataTable Props
interface DataTableProps<T> {
  data: T[]
  columns: Column<T>[]
  loading?: boolean
  error?: string
  title?: string
  subtitle?: string
  showHeader?: boolean
  searchable?: boolean
  searchPlaceholder?: string
  pagination?: {
    current: number
    pageSize: number
    total: number
    onChange: (page: number, pageSize: number) => void
    showSizeChanger?: boolean
    showQuickJumper?: boolean
  }
  rowSelection?: {
    selectedRowKeys?: React.Key[]
    onChange?: (selectedRowKeys: React.Key[], selectedRows: T[]) => void
  }
  scroll?: {
    x?: number | string
    y?: number | string
  }
  size?: 'small' | 'middle' | 'large'
  bordered?: boolean
  striped?: boolean
  hoverable?: boolean
  compact?: boolean
  className?: string
  actions?: React.ReactNode
  onRow?: (record: T, index: number) => {
    onClick?: (event: React.MouseEvent) => void
    onDoubleClick?: (event: React.MouseEvent) => void
    onMouseEnter?: (event: React.MouseEvent) => void
    onMouseLeave?: (event: React.MouseEvent) => void
    className?: string
  }
}

// 排序状态
interface SortState {
  field: string
  direction: 'asc' | 'desc'
}

// 分页组件
const Pagination = ({
  current,
  pageSize,
  total,
  onChange,
  showSizeChanger = true,
  showQuickJumper = true,
}: NonNullable<DataTableProps<any>['pagination']>) => {
  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="flex items-center justify-between px-2 py-4">
      <div className="text-sm text-muted-foreground">
        显示第 {((current - 1) * pageSize) + 1} 至 {Math.min(current * pageSize, total)} 条，共 {total} 条
      </div>

      <div className="flex items-center gap-2">
        {/* 上一页 */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange(current - 1, pageSize)}
          disabled={current <= 1}
        >
          上一页
        </Button>

        {/* 页码 */}
        <div className="flex items-center gap-1">
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            const pageNum = i + 1
            return (
              <Button
                key={pageNum}
                variant={current === pageNum ? "default" : "outline"}
                size="sm"
                onClick={() => onChange(pageNum, pageSize)}
                className="w-8 h-8 p-0"
              >
                {pageNum}
              </Button>
            )
          })}
        </div>

        {/* 下一页 */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange(current + 1, pageSize)}
          disabled={current >= totalPages}
        >
          下一页
        </Button>

        {/* 每页显示数量 */}
        {showSizeChanger && (
          <select
            value={pageSize}
            onChange={(e) => onChange(1, Number(e.target.value))}
            className="ml-4 h-8 rounded border border-input bg-background px-3 py-1 text-sm"
          >
            <option value={10}>10 条/页</option>
            <option value={20}>20 条/页</option>
            <option value={50}>50 条/页</option>
            <option value={100}>100 条/页</option>
          </select>
        )}
      </div>
    </div>
  )
}

// 主组件
export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  loading = false,
  error,
  title,
  subtitle,
  showHeader = true,
  searchable = true,
  searchPlaceholder = "搜索...",
  pagination,
  rowSelection,
  scroll,
  size = 'middle',
  bordered = false,
  striped = false,
  hoverable = true,
  compact = false,
  className,
  actions,
  onRow,
}: DataTableProps<T>) {
  const [searchQuery, setSearchQuery] = React.useState('')
  const [sort, setSort] = React.useState<SortState | null>(null)
  const [visibleColumns, setVisibleColumns] = React.useState<string[]>(
    columns.map(col => col.key)
  )
  const [selectedRows, setSelectedRows] = React.useState<React.Key[]>(
    rowSelection?.selectedRowKeys || []
  )

  // 过滤数据
  const filteredData = React.useMemo(() => {
    if (!searchQuery) return data

    return data.filter((record) => {
      return columns.some(column => {
        if (!column.searchable && !column.sortable) return false

        const value = record[column.dataIndex]
        if (value == null) return false

        const stringValue = String(value)
        return stringValue.toLowerCase().includes(searchQuery.toLowerCase())
      })
    })
  }, [data, columns, searchQuery])

  // 排序数据
  const sortedData = React.useMemo(() => {
    if (!sort) return filteredData

    const column = columns.find(col => col.key === sort.field)
    if (!column || !column.sortable) return filteredData

    return [...filteredData].sort((a, b) => {
      const aValue = a[column.dataIndex]
      const bValue = b[column.dataIndex]

      if (aValue === null || aValue === undefined) return sort.direction === 'asc' ? -1 : 1
      if (bValue === null || bValue === undefined) return sort.direction === 'asc' ? 1 : -1

      let result = 0
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        result = aValue - bValue
      } else {
        result = String(aValue).localeCompare(String(bValue))
      }

      return sort.direction === 'asc' ? result : -result
    })
  }, [filteredData, columns, sort])

  // 分页数据
  const paginatedData = React.useMemo(() => {
    if (!pagination) return sortedData

    const { current, pageSize } = pagination
    const startIndex = (current - 1) * pageSize
    return sortedData.slice(startIndex, startIndex + pageSize)
  }, [sortedData, pagination])

  // 处理排序
  const handleSort = (column: Column<T>) => {
    if (!column.sortable) return

    setSort(prev => {
      if (prev?.field === column.key) {
        return {
          field: column.key,
          direction: prev.direction === 'asc' ? 'desc' : 'asc'
        }
      }
      return {
        field: column.key,
        direction: 'asc'
      }
    })
  }

  // 处理列显示/隐藏
  const toggleColumn = (columnKey: string) => {
    setVisibleColumns(prev =>
      prev.includes(columnKey)
        ? prev.filter(key => key !== columnKey)
        : [...prev, columnKey]
    )
  }

  // 处理行选择
  const handleRowSelect = (record: T, checked: boolean) => {
    const key = record.id || record.key || JSON.stringify(record)

    let newSelectedRows: React.Key[]
    if (checked) {
      newSelectedRows = [...selectedRows, key]
    } else {
      newSelectedRows = selectedRows.filter(rowKey => rowKey !== key)
    }

    setSelectedRows(newSelectedRows)
    rowSelection?.onChange?.(newSelectedRows,
      newSelectedRows.map(rowKey =>
        data.find(item =>
          (item.id || item.key || JSON.stringify(item)) === rowKey
        )!
      )
    )
  }

  // 处理全选
  const handleSelectAll = (checked: boolean) => {
    const keys = paginatedData.map(record =>
      record.id || record.key || JSON.stringify(record)
    )
    setSelectedRows(checked ? keys : [])

    if (checked) {
      rowSelection?.onChange?.(keys, paginatedData)
    } else {
      rowSelection?.onChange?.([], [])
    }
  }

  // 获取可见列
  const visibleColumnsData = columns.filter(col => visibleColumns.includes(col.key))

  // 表格尺寸样式
  const sizeClasses = {
    small: 'text-xs',
    middle: 'text-sm',
    large: 'text-base'
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="text-lg font-semibold text-destructive mb-2">加载失败</div>
        <div className="text-muted-foreground">{error}</div>
      </div>
    )
  }

  return (
    <div className={`w-full space-y-4 ${className}`}>
      {/* 表格头部 */}
      {showHeader && (title || subtitle || searchable || actions) && (
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            {title && <h3 className="text-lg font-semibold">{title}</h3>}
            {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
          </div>

          <div className="flex items-center gap-2">
            {searchable && (
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder={searchPlaceholder}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 w-64"
                />
              </div>
            )}

            {actions}

            {/* 列设置 */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <Settings className="h-4 w-4 mr-2" />
                  列设置
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                {columns.map(column => (
                  <DropdownMenuCheckboxItem
                    key={column.key}
                    checked={visibleColumns.includes(column.key)}
                    onCheckedChange={() => toggleColumn(column.key)}
                  >
                    {column.title}
                  </DropdownMenuCheckboxItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      )}

      {/* 表格容器 */}
      <div
        className={`border rounded-lg ${loading ? 'opacity-50' : ''}`}
        style={{
          maxHeight: scroll?.y,
          overflowY: scroll?.y ? 'auto' : 'visible'
        }}
      >
        <Table>
          <TableHeader>
            <TableRow>
              {/* 选择列 */}
              {rowSelection && (
                <TableHead className="w-12">
                  <input
                    type="checkbox"
                    checked={selectedRows.length > 0 && selectedRows.length === paginatedData.length}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="rounded"
                  />
                </TableHead>
              )}

              {/* 数据列 */}
              {visibleColumnsData.map(column => (
                <TableHead
                  key={column.key}
                  className={`
                    ${column.sortable ? 'cursor-pointer hover:bg-muted/50' : ''}
                    ${column.className || ''}
                  `}
                  style={{ width: column.width }}
                  onClick={() => handleSort(column)}
                >
                  <div className="flex items-center gap-2">
                    <span>{column.title}</span>
                    {column.sortable && sort?.field === column.key && (
                      sort.direction === 'asc' ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )
                    )}
                  </div>
                </TableHead>
              ))}

              {/* 操作列 */}
              {onRow && <TableHead className="w-12" />}
            </TableRow>
          </TableHeader>

          <TableBody>
            {loading ? (
              // 加载状态
              Array.from({ length: 5 }).map((_, index) => (
                <TableRow key={index}>
                  {rowSelection && (
                    <TableCell>
                      <div className="h-4 w-4 bg-muted rounded animate-pulse" />
                    </TableCell>
                  )}
                  {visibleColumnsData.map((column, colIndex) => (
                    <TableCell key={colIndex}>
                      <div className="h-4 bg-muted rounded animate-pulse" />
                    </TableCell>
                  ))}
                  {onRow && <TableCell />}
                </TableRow>
              ))
            ) : paginatedData.length === 0 ? (
              // 空状态
              <TableRow>
                <TableCell
                  colSpan={visibleColumnsData.length + (rowSelection ? 1 : 0) + (onRow ? 1 : 0)}
                  className="text-center py-12"
                >
                  {searchQuery ? '没有找到匹配的数据' : '暂无数据'}
                </TableCell>
              </TableRow>
            ) : (
              // 数据行
              paginatedData.map((record, index) => {
                const rowProps = onRow?.(record, index) || {}
                const isSelected = selectedRows.includes(
                  record.id || record.key || JSON.stringify(record)
                )

                return (
                  <TableRow
                    key={record.id || record.key || index}
                    className={`
                      ${hoverable ? 'hover:bg-muted/50' : ''}
                      ${striped && index % 2 === 1 ? 'bg-muted/25' : ''}
                      ${isSelected ? 'bg-primary/5' : ''}
                      ${rowProps.className || ''}
                    `}
                    {...rowProps}
                  >
                    {/* 选择列 */}
                    {rowSelection && (
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => handleRowSelect(record, e.target.checked)}
                          className="rounded"
                        />
                      </TableCell>
                    )}

                    {/* 数据列 */}
                    {visibleColumnsData.map(column => {
                      const value = record[column.dataIndex]
                      const alignClasses = {
                        left: 'text-left',
                        center: 'text-center',
                        right: 'text-right'
                      }

                      return (
                        <TableCell
                          key={column.key}
                          className={`
                            ${alignClasses[column.align || 'left']}
                            ${column.className || ''}
                            ${sizeClasses[size]}
                          `}
                        >
                          {column.render
                            ? column.render(value, record, index)
                            : value ?? '-'
                          }
                        </TableCell>
                      )
                    })}

                    {/* 操作列 */}
                    {onRow && (
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>编辑</DropdownMenuItem>
                            <DropdownMenuItem>删除</DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    )}
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* 分页 */}
      {pagination && !loading && paginatedData.length > 0 && (
        <Pagination {...pagination} />
      )}
    </div>
  )
}