'use client'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { DataTable, Column } from '@/components/ui/data-table'
import { EmptyState } from '@/components/ui/empty-state'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { useTables, useCreateTable, useUpdateTable, useDeleteTable } from '@/hooks/use-metadata'
import { useMetadataStore } from '@/store'
import { useTableForm } from '@/hooks/use-table-form'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Checkbox } from '@/components/ui/checkbox'
import { Textarea } from '@/components/ui/textarea'
import { Plus, Database, Search, Filter } from 'lucide-react'
import type { TableMetadata } from '@/types/index'

// 表格列定义
const tableColumns: Column<TableMetadata>[] = [
  {
    key: 'name',
    title: '表名',
    dataIndex: 'name',
    sortable: true,
    searchable: true,
    width: 200,
    render: (value: TableMetadata[keyof TableMetadata]) => (
      <div className="flex items-center gap-2">
        <Database className="h-4 w-4 text-muted-foreground" />
        <span className="font-medium">{String(value)}</span>
      </div>
    )
  },
  {
    key: 'comment',
    title: '表注释',
    dataIndex: 'comment',
    searchable: true,
    render: (value: TableMetadata[keyof TableMetadata]) => value ? String(value) : <span className="text-muted-foreground">-</span>
  },
  {
    key: 'dataSource',
    title: '数据源',
    dataIndex: 'dataSource',
    width: 120,
    render: (value: TableMetadata[keyof TableMetadata]) => value ? <Badge variant="secondary">{String(value)}</Badge> : <span className="text-muted-foreground">-</span>
  },
  {
    key: 'updateMethod',
    title: '更新方式',
    dataIndex: 'updateMethod',
    width: 120,
    render: (value: TableMetadata[keyof TableMetadata]) => value ? <Badge variant="outline">{String(value)}</Badge> : <span className="text-muted-foreground">-</span>
  },
  {
    key: 'isAvailable',
    title: '状态',
    dataIndex: 'isAvailable',
    width: 80,
    sortable: true,
    render: (value: TableMetadata[keyof TableMetadata]) => (
      <Badge variant={value === true ? 'default' : 'secondary'}>
        {value === true ? '启用' : '禁用'}
      </Badge>
    )
  },
  {
    key: 'createdAt',
    title: '创建时间',
    dataIndex: 'createdAt',
    width: 160,
    sortable: true,
    render: (value: TableMetadata[keyof TableMetadata]) => value ? new Date(String(value)).toLocaleString('zh-CN') : '-'
  },
  {
    key: 'updatedAt',
    title: '更新时间',
    dataIndex: 'updatedAt',
    width: 160,
    sortable: true,
    render: (value: TableMetadata[keyof TableMetadata]) => value ? new Date(String(value)).toLocaleString('zh-CN') : '-'
  }
]

// 表单组件
function TableFormDialog() {
  const { form, handleSubmit, handleCancel, isEditing, isLoading } = useTableForm()
  const editingTable = useMetadataStore(state => state.editingTable)

  return (
    <Dialog open={!!editingTable} onOpenChange={(open) => !open && handleCancel()}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? '编辑表配置' : '新增表配置'}</DialogTitle>
          <DialogDescription>
            {isEditing ? '修改表的基本信息和配置' : '添加新的表配置'}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>表名 *</FormLabel>
                  <FormControl>
                    <Input placeholder="请输入表名" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="comment"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>表注释</FormLabel>
                  <FormControl>
                    <Textarea placeholder="请输入表注释" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="remark"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>备注</FormLabel>
                  <FormControl>
                    <Textarea placeholder="请输入备注信息" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="dataSource"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>数据源</FormLabel>
                  <FormControl>
                    <Input placeholder="请输入数据源" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="updateMethod"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>更新方式</FormLabel>
                  <FormControl>
                    <Input placeholder="请输入更新方式" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="isAvailable"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                  <FormControl>
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                  <div className="space-y-1 leading-none">
                    <FormLabel>启用状态</FormLabel>
                    <FormDescription>
                      是否启用此表配置
                    </FormDescription>
                  </div>
                </FormItem>
              )}
            />

            <div className="flex justify-end space-x-2 pt-4">
              <Button type="button" variant="outline" onClick={handleCancel}>
                取消
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading && <LoadingSpinner size="sm" className="mr-2" />}
                {isEditing ? '更新' : '创建'}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

// 主页面组件
export default function TablesPage() {
  const { data: tables = [], isLoading, error } = useTables()
  const _createTableMutation = useCreateTable()
  const _updateTableMutation = useUpdateTable()
  const _deleteTableMutation = useDeleteTable()

  const {
    searchQuery,
    setSearchQuery,
    setEditingTable,
    filters,
    setFilters
  } = useMetadataStore()

  // 操作处理
  const handleCreate = () => {
    setEditingTable({} as TableMetadata)
  }

  const handleEdit = (record: TableMetadata) => {
    setEditingTable(record)
  }

  // 过滤器组件
  const FilterControls = () => (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-medium">筛选:</span>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索表名或注释..."
            value={searchQuery || ''}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 w-64"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant={filters.isAvailable === true ? "default" : "outline"}
          size="sm"
          onClick={() => setFilters({ isAvailable: filters.isAvailable === true ? undefined : true })}
        >
          启用
        </Button>
        <Button
          variant={filters.isAvailable === false ? "default" : "outline"}
          size="sm"
          onClick={() => setFilters({ isAvailable: filters.isAvailable === false ? undefined : false })}
        >
          禁用
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setFilters({ isAvailable: undefined })}
        >
          全部
        </Button>
      </div>
    </div>
  )

  if (error) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardContent className="py-12">
            <EmptyState
              title="加载失败"
              description={typeof error === 'string' ? error : error?.message || '未知错误'}
              action={{
                label: '重试',
                onClick: () => window.location.reload()
              }}
            />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">表配置管理</h1>
          <p className="text-muted-foreground">
            管理数据库表的基础配置和元数据信息
          </p>
        </div>
        <Button onClick={handleCreate}>
          <Plus className="h-4 w-4 mr-2" />
          新增表
        </Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总表数</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tables.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">启用表</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {tables.filter(t => t.isAvailable).length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">禁用表</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {tables.filter(t => !t.isAvailable).length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">有数据源</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {tables.filter(t => t.dataSource).length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 表格 */}
      <Card>
        <CardHeader>
          <CardTitle>表列表</CardTitle>
          <CardDescription>
            所有数据库表的基础配置信息
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-12">
              <LoadingSpinner text="加载中..." />
            </div>
          ) : tables.length === 0 ? (
            <EmptyState
              icon={<Database className="h-12 w-12 text-muted-foreground" />}
              title="暂无表配置"
              description="还没有添加任何表配置，点击上方按钮创建第一个表配置"
              action={{
                label: '新增表',
                onClick: handleCreate
              }}
            />
          ) : (
            <DataTable
              columns={tableColumns}
              data={tables}
              loading={isLoading}
              searchable={true}
              searchPlaceholder="搜索表名、注释或数据源..."
              onRow={(record) => ({
                className: 'cursor-pointer',
                onDoubleClick: () => handleEdit(record)
              })}
              actions={<FilterControls />}
            />
          )}
        </CardContent>
      </Card>

      {/* 表单弹窗 */}
      <TableFormDialog />
    </div>
  )
}