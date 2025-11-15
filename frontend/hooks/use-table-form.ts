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
      if (editingTable?.id) {
        // 更新现有表
        await updateTableMutation.mutateAsync({
          id: editingTable.id,
          data
        })
      } else {
        // 创建新表
        await createTableMutation.mutateAsync(data)
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