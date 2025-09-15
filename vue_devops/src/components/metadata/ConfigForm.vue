<template>
  <div class="config-form">
    <div class="form-info">
      <el-alert
        title="关联ID格式：关联族|关联子族"
        type="info"
        :closable="false"
        show-icon
      />
    </div>
    
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="关联族" prop="relation_family">
        <el-input
          v-model="form.relation_family"
          placeholder="如：cust_no"
          clearable
        />
      </el-form-item>
      
      <el-form-item label="关联子族" prop="relation_subfamily">
        <el-input
          v-model="form.relation_subfamily"
          placeholder="如：17"
          clearable
        />
      </el-form-item>
      
      <el-form-item label="描述">
        <el-input
          v-model="form.relation_desc"
          type="textarea"
          :rows="3"
          placeholder="请输入关联字段的描述..."
        />
      </el-form-item>
      
      <!-- 预览关联ID -->
      <div v-if="previewId" class="preview-section">
        <el-alert
          :title="`预览关联ID: ${previewId}`"
          type="success"
          :closable="false"
          show-icon
        />
      </div>
      
      <el-form-item>
        <el-button type="primary" @click="handleSubmit" :loading="loading">
          {{ isEditing ? '更新配置' : '添加配置' }}
        </el-button>
        <el-button @click="handleCancel">
          {{ isEditing ? '取消' : '重置' }}
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { apiClient } from '@/api'
import type { RelationConfig } from '@/types'

interface Props {
  config?: RelationConfig | null
}

interface Emits {
  (e: 'saved'): void
  (e: 'cancel'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const formRef = ref<FormInstance>()
const loading = ref(false)

const isEditing = computed(() => !!props.config)

const form = reactive({
  relation_family: '',
  relation_subfamily: '',
  relation_desc: ''
})

const rules: FormRules = {
  relation_family: [
    { required: true, message: '请输入关联族', trigger: 'blur' }
  ],
  relation_subfamily: [
    { required: true, message: '请输入关联子族', trigger: 'blur' }
  ]
}

// 预览关联ID
const previewId = computed(() => {
  if (form.relation_family && form.relation_subfamily) {
    return `${form.relation_family}|${form.relation_subfamily}`
  }
  return ''
})

// 监听传入的配置数据
watch(() => props.config, (newConfig) => {
  if (newConfig) {
    Object.assign(form, {
      relation_family: newConfig.relation_family || '',
      relation_subfamily: newConfig.relation_subfamily || '',
      relation_desc: newConfig.relation_desc || ''
    })
  } else {
    resetForm()
  }
}, { immediate: true })

const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    loading.value = true
    
    if (isEditing.value && props.config) {
      // 更新配置
      await apiClient.relationConfig.update(props.config.relation_id, {
        relation_family: form.relation_family,
        relation_subfamily: form.relation_subfamily,
        relation_desc: form.relation_desc
      })
      
      ElMessage.success(`关联配置已更新: ${props.config.relation_id} -> ${previewId.value}`)
    } else {
      // 添加配置
      await apiClient.relationConfig.add({
        relation_family: form.relation_family,
        relation_subfamily: form.relation_subfamily,
        relation_desc: form.relation_desc
      })
      
      ElMessage.success(`关联配置 ${previewId.value} 已添加`)
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
    relation_family: '',
    relation_subfamily: '',
    relation_desc: ''
  })
}
</script>

<style scoped lang="scss">
.config-form {
  .form-info {
    margin-bottom: 16px;
  }
  
  .preview-section {
    margin-bottom: 16px;
  }
}
</style>