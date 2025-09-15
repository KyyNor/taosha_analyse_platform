<template>
  <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
    <el-form-item label="术语名称" prop="term">
      <el-input
        v-model="form.term"
        placeholder="请输入术语名称"
        clearable
      />
    </el-form-item>
    
    <el-form-item label="术语定义" prop="definition">
      <el-input
        v-model="form.definition"
        type="textarea"
        :rows="3"
        placeholder="请输入术语定义"
      />
    </el-form-item>
    
    <el-form-item label="SQL表达式">
      <el-input
        v-model="form.sql_expression"
        type="textarea"
        :rows="3"
        placeholder="请输入SQL表达式"
      />
    </el-form-item>
    
    <el-form-item label="分类">
      <el-input
        v-model="form.category"
        placeholder="请输入分类"
        clearable
      />
    </el-form-item>
    
    <el-form-item label="别名">
      <el-input
        v-model="aliasesText"
        placeholder="请输入别名，用逗号分隔"
        clearable
      />
    </el-form-item>
    
    <el-form-item>
      <el-button type="primary" @click="handleSubmit" :loading="loading">
        {{ isEditing ? '更新术语' : '添加术语' }}
      </el-button>
      <el-button @click="handleCancel">
        {{ isEditing ? '取消' : '重置' }}
      </el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { apiClient } from '@/api'
import type { GlossaryTerm } from '@/types'

interface Props {
  term?: GlossaryTerm | null
}

interface Emits {
  (e: 'saved'): void
  (e: 'cancel'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const formRef = ref<FormInstance>()
const loading = ref(false)
const aliasesText = ref('')

const isEditing = computed(() => !!props.term)

const form = reactive({
  term: '',
  definition: '',
  sql_expression: '',
  category: ''
})

const rules: FormRules = {
  term: [
    { required: true, message: '请输入术语名称', trigger: 'blur' }
  ]
}

// 监听传入的术语数据
watch(() => props.term, (newTerm) => {
  if (newTerm) {
    Object.assign(form, {
      term: newTerm.term || '',
      definition: newTerm.definition || '',
      sql_expression: newTerm.sql_expression || '',
      category: newTerm.category || ''
    })
    aliasesText.value = newTerm.aliases?.join(', ') || ''
  } else {
    resetForm()
  }
}, { immediate: true })

const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    loading.value = true
    
    const aliases = aliasesText.value
      .split(',')
      .map(alias => alias.trim())
      .filter(alias => alias.length > 0)
    
    if (isEditing.value && props.term) {
      // 更新术语
      await apiClient.glossary.updateTerm(props.term.id, {
        term: form.term,
        definition: form.definition,
        sql_expression: form.sql_expression,
        category: form.category
      })
      
      ElMessage.success(`术语 ${form.term} 已更新`)
    } else {
      // 添加术语
      await apiClient.glossary.addTerm({
        term: form.term,
        definition: form.definition,
        sql_expression: form.sql_expression,
        category: form.category,
        aliases
      })
      
      ElMessage.success(`术语 ${form.term} 已添加`)
    }
    
    emit('saved')
  } catch (error: any) {
    if (error.errors) {
      // 表单验证错误
      return
    }
    ElMessage.error(`${isEditing.value ? '更新' : '添加'}失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  if (isEditing.value) {
    emit('cancel')
  } else {
    resetForm()
  }
}

const resetForm = () => {
  formRef.value?.resetFields()
  Object.assign(form, {
    term: '',
    definition: '',
    sql_expression: '',
    category: ''
  })
  aliasesText.value = ''
}
</script>