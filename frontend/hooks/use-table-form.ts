import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMetadataStore } from '@/store/use-metadata-store'
import { useCreateTable, useUpdateTable } from '@/hooks/use-metadata'
import type { TableFormData } from '@/types/index'

const tableSchema = z.object({
  name: z.string().min(1, '表名不能为空'),
  comment: z.string().optional(),
  remark: z.string().optional(),
  isAvailable: z.boolean(),
  dataSource: z.string().optional(),
  updateMethod: z.string().optional(),
})

export function useTableForm(defaultValues?: Partial<TableFormData>) {
  const editingTable = useMetadataStore(state => state.editingTable)
  const setEditingTable = useMetadataStore(state => state.setEditingTable)
  const createTableMutation = useCreateTable()
  const updateTableMutation = useUpdateTable()

  const form = useForm<TableFormData>({
    resolver: zodResolver(tableSchema),
    defaultValues: {
      name: '',
      comment: '',
      remark: '',
      isAvailable: true,
      dataSource: '',
      updateMethod: '',
      ...editingTable,
      ...defaultValues,
    },
  })

  const handleSubmit = form.handleSubmit(async (data) => {
    try {
      // 转换数据以匹配API期望的格式
      const apiData = {
        name: data.name,
        comment: data.comment || '',
        remark: data.remark || '',
        isAvailable: data.isAvailable,
        dataSource: data.dataSource,
        updateMethod: data.updateMethod,
      }

      if (editingTable?.id) {
        // 更新现有表
        await updateTableMutation.mutateAsync({
          id: editingTable.id,
          data: apiData
        })
      } else {
        // 创建新表
        await createTableMutation.mutateAsync(apiData)
      }
      setEditingTable(null)
      form.reset()
    } catch (error) {
      // 错误处理在 mutation 中统一处理
    }
  })

  const handleCancel = () => {
    setEditingTable(null)
    form.reset()
  }

  return {
    form,
    handleSubmit,
    handleCancel,
    isEditing: !!editingTable?.id,
    isLoading: createTableMutation.isPending || updateTableMutation.isPending
  }
}