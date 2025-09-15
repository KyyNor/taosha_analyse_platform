<template>
  <div class="add-column">
    <h4>添加列元数据</h4>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" size="small">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="列名" prop="name">
            <el-input
              v-model="form.name"
              placeholder="请输入列名"
              clearable
            />
          </el-form-item>
          
          <el-form-item label="存储类型" prop="type">
            <el-select v-model="form.type" style="width: 100%">
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
      </el-row>
      
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="状态">
            <el-select v-model="form.is_available" style="width: 100%">
              <el-option label="可用" :value="0" />
              <el-option label="不可用" :value="1" />
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col :span="12">
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
        </el-col>
      </el-row>
      
      <el-form-item>
        <el-button type="primary" size="small" @click="handleSubmit" :loading="loading">
          添加列
        </el-button>
        <el-button size="small" @click="resetForm">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { apiClient } from '@/api'
import type { MetadataTable } from '@/types'

interface Props {
  table: MetadataTable
}

interface Emits {
  (e: 'added'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const formRef = ref<FormInstance>()
const loading = ref(false)
const relationIds = ref<string[]>([])

const form = reactive({
  name: '',
  type: 'VARCHAR',
  comment: '',
  is_available: 0,
  business_type: 'VARCHAR',
  relation_id: ''
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入列名', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择存储类型', trigger: 'change' }
  ]
}

// 获取关联ID列表
const fetchRelationIds = async () => {
  try {
    const response = await apiClient.relationConfig.getIds()
    relationIds.value = response.data || []
  } catch (error: any) {
    console.error('获取关联ID失败:', error.message)
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    loading.value = true
    
    await apiClient.metadata.addColumn({
      table_name: props.table.name,
      name: form.name,
      type: form.type,
      comment: form.comment,
      is_available: form.is_available,
      business_type: form.business_type,
      relation_id: form.relation_id
    })
    
    ElMessage.success(`列 ${form.name} 已添加到表 ${props.table.name}`)
    resetForm()
    emit('added')
  } catch (error: any) {
    if (error.errors) {
      // 表单验证错误
      return
    }
    ElMessage.error(`添加失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  formRef.value?.resetFields()
  Object.assign(form, {
    name: '',
    type: 'VARCHAR',
    comment: '',
    is_available: 0,
    business_type: 'VARCHAR',
    relation_id: ''
  })
}

onMounted(() => {
  fetchRelationIds()
})
</script>

<style scoped lang="scss">
.add-column {
  h4 {
    margin: 0 0 16px 0;
    color: #303133;
    font-size: 14px;
  }
}
</style>