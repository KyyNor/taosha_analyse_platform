<template>
  <div class="table-editor">
    <h4>编辑表元数据</h4>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="60px" size="small">
      <el-form-item label="描述" prop="comment">
        <el-input
          v-model="form.comment"
          type="textarea"
          :rows="2"
          placeholder="请输入表描述"
        />
      </el-form-item>
      
      <el-form-item label="状态" prop="is_available">
        <el-select v-model="form.is_available" style="width: 100%">
          <el-option label="可用" :value="0" />
          <el-option label="不可用" :value="1" />
        </el-select>
      </el-form-item>
      
      <el-form-item>
        <el-button type="primary" size="small" @click="handleUpdate" :loading="loading">
          更新表元数据
        </el-button>
        <el-button size="small" @click="handleDelete" :loading="deleting">
          删除表
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { apiClient } from '@/api'
import type { MetadataTable } from '@/types'

interface Props {
  table: MetadataTable
}

interface Emits {
  (e: 'updated'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const formRef = ref<FormInstance>()
const loading = ref(false)
const deleting = ref(false)

const form = reactive({
  comment: props.table.comment || '',
  is_available: props.table.is_available
})

const rules = {}

// 监听表数据变化
watch(() => props.table, (newTable) => {
  form.comment = newTable.comment || ''
  form.is_available = newTable.is_available
}, { deep: true })

// 更新表元数据
const handleUpdate = async () => {
  try {
    loading.value = true
    
    await apiClient.metadata.updateTable(props.table.name, {
      comment: form.comment,
      is_available: form.is_available
    })
    
    ElMessage.success(`表 ${props.table.name} 元数据已更新`)
    emit('updated')
  } catch (error: any) {
    ElMessage.error(`更新失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

// 删除表
const handleDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除表 "${props.table.name}" 的元数据吗？此操作不可恢复。`,
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )
    
    deleting.value = true
    
    await apiClient.metadata.deleteTable(props.table.name)
    
    ElMessage.success(`表 ${props.table.name} 元数据已删除`)
    emit('updated')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(`删除失败: ${error.message}`)
    }
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped lang="scss">
.table-editor {
  h4 {
    margin: 0 0 12px 0;
    color: #303133;
    font-size: 14px;
  }
}
</style>