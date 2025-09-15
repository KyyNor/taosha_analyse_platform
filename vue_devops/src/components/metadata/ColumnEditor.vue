<template>
  <div class="column-editor">
    <el-select
      v-model="selectedColumnName"
      placeholder="选择要编辑的列"
      style="width: 100%; margin-bottom: 16px;"
    >
      <el-option
        v-for="column in availableColumns"
        :key="column.name"
        :label="column.name"
        :value="column.name"
      />
    </el-select>

    <div v-if="selectedColumn" class="edit-form">
      <h4>编辑列: {{ selectedColumnName }}</h4>
      
      <el-form ref="formRef" :model="form" label-width="80px" size="small">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="存储类型">
              <el-select v-model="form.type" style="width: 100%">
                <el-option label="VARCHAR" value="VARCHAR" />
                <el-option label="INTEGER" value="INTEGER" />
                <el-option label="DECIMAL" value="DECIMAL" />
                <el-option label="DATE" value="DATE" />
                <el-option label="BOOLEAN" value="BOOLEAN" />
                <el-option label="TEXT" value="TEXT" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="业务类型">
              <el-select v-model="form.business_type" style="width: 100%">
                <el-option label="VARCHAR" value="VARCHAR" />
                <el-option label="INTEGER" value="INTEGER" />
                <el-option label="DECIMAL" value="DECIMAL" />
                <el-option label="DATE" value="DATE" />
                <el-option label="BOOLEAN" value="BOOLEAN" />
                <el-option label="TEXT" value="TEXT" />
              </el-select>
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="列描述">
              <el-input
                v-model="form.comment"
                type="textarea"
                :rows="2"
                placeholder="请输入列描述"
              />
            </el-form-item>
            
            <el-form-item label="状态">
              <el-select v-model="form.is_available" style="width: 100%">
                <el-option label="可用" :value="0" />
                <el-option label="不可用" :value="1" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="关联ID">
          <el-select v-model="form.relation_id" clearable style="width: 100%">
            <el-option
              v-for="relationId in relationIds"
              :key="relationId"
              :label="relationId"
              :value="relationId"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" size="small" @click="handleUpdate" :loading="updating">
            更新列
          </el-button>
          <el-button size="small" @click="handleDelete" :loading="deleting">
            删除列
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
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
const selectedColumnName = ref('')
const updating = ref(false)
const deleting = ref(false)
const relationIds = ref<string[]>([])

const form = reactive({
  type: '',
  business_type: '',
  comment: '',
  is_available: 0,
  relation_id: ''
})

// 可用的列
const availableColumns = computed(() => {
  return props.table.columns || []
})

// 选中的列
const selectedColumn = computed(() => {
  return availableColumns.value.find(col => col.name === selectedColumnName.value)
})

// 监听选中列的变化
watch(selectedColumn, (newColumn) => {
  if (newColumn) {
    Object.assign(form, {
      type: newColumn.type || '',
      business_type: newColumn.business_type || newColumn.type || '',
      comment: newColumn.comment || '',
      is_available: newColumn.is_available || 0,
      relation_id: newColumn.relation_id || ''
    })
  }
}, { immediate: true })

// 获取关联ID列表
const fetchRelationIds = async () => {
  try {
    const response = await apiClient.relationConfig.getIds()
    relationIds.value = ['', ...(response.data || [])]
  } catch (error: any) {
    console.error('获取关联ID失败:', error.message)
  }
}

// 更新列
const handleUpdate = async () => {
  if (!selectedColumn.value) return
  
  try {
    updating.value = true
    
    await apiClient.metadata.updateColumn(
      props.table.name,
      selectedColumn.value.name,
      {
        type: form.type,
        comment: form.comment,
        is_available: form.is_available,
        business_type: form.business_type,
        relation_id: form.relation_id
      }
    )
    
    ElMessage.success(`列 ${selectedColumn.value.name} 元数据已更新`)
    emit('updated')
  } catch (error: any) {
    ElMessage.error(`更新失败: ${error.message}`)
  } finally {
    updating.value = false
  }
}

// 删除列
const handleDelete = async () => {
  if (!selectedColumn.value) return
  
  try {
    await ElMessageBox.confirm(
      `确定要删除列 "${selectedColumn.value.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )
    
    deleting.value = true
    
    await apiClient.metadata.deleteColumn(
      props.table.name,
      selectedColumn.value.name
    )
    
    ElMessage.success(`列 ${selectedColumn.value.name} 已删除`)
    selectedColumnName.value = ''
    emit('updated')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(`删除失败: ${error.message}`)
    }
  } finally {
    deleting.value = false
  }
}

// 初始化
fetchRelationIds()
</script>

<style scoped lang="scss">
.column-editor {
  .edit-form {
    h4 {
      margin: 0 0 16px 0;
      color: #303133;
      font-size: 14px;
    }
  }
}
</style>