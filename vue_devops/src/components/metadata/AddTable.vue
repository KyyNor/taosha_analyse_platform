<template>
  <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
    <el-form-item label="表名" prop="name">
      <el-input
        v-model="form.name"
        placeholder="请输入表名"
        clearable
      />
    </el-form-item>
    
    <el-form-item label="表描述" prop="comment">
      <el-input
        v-model="form.comment"
        type="textarea"
        :rows="3"
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
      <el-button type="primary" @click="handleSubmit" :loading="loading">
        添加表
      </el-button>
      <el-button @click="resetForm">重置</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { apiClient } from '@/api'

interface Emits {
  (e: 'added'): void
}

const emit = defineEmits<Emits>()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  name: '',
  comment: '',
  is_available: 0
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入表名', trigger: 'blur' }
  ]
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    loading.value = true
    
    await apiClient.metadata.addTable({
      name: form.name,
      comment: form.comment,
      is_available: form.is_available
    })
    
    ElMessage.success(`表 ${form.name} 元数据已添加`)
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
    comment: '',
    is_available: 0
  })
}
</script>