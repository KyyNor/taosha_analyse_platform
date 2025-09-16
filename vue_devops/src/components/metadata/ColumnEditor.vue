<template>
  <form @submit.prevent="submitForm" class="space-y-4">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Column Name -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">列名</label>
        <input
          v-model="formData.name"
          type="text"
          :disabled="isEditing"
          required
          placeholder="输入列名"
          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-slate-100 disabled:text-slate-500"
        />
      </div>

      <!-- Storage Type -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">存储类型</label>
        <select
          v-model="formData.type"
          required
          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">请选择类型</option>
          <option value="VARCHAR">VARCHAR</option>
          <option value="INTEGER">INTEGER</option>
          <option value="DECIMAL">DECIMAL</option>
          <option value="DATE">DATE</option>
          <option value="BOOLEAN">BOOLEAN</option>
          <option value="TEXT">TEXT</option>
        </select>
      </div>

      <!-- Business Type -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">业务类型</label>
        <select
          v-model="formData.business_type"
          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">请选择业务类型</option>
          <option value="VARCHAR">VARCHAR</option>
          <option value="INTEGER">INTEGER</option>
          <option value="DECIMAL">DECIMAL</option>
          <option value="DATE">DATE</option>
          <option value="BOOLEAN">BOOLEAN</option>
          <option value="TEXT">TEXT</option>
        </select>
      </div>

      <!-- Status -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">状态</label>
        <select
          v-model="formData.is_available"
          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option :value="0">可用</option>
          <option :value="1">不可用</option>
        </select>
      </div>
    </div>

    <!-- Relation ID -->
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-2">关联ID</label>
      <select
        v-model="formData.relation_id"
        class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      >
        <option value="">请选择关联ID</option>
        <option
          v-for="relationId in relationIds"
          :key="relationId"
          :value="relationId"
        >
          {{ relationId }}
        </option>
      </select>
    </div>

    <!-- Comment -->
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-2">描述</label>
      <textarea
        v-model="formData.comment"
        rows="3"
        placeholder="输入列的描述信息"
        class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      ></textarea>
    </div>

    <!-- Action Buttons -->
    <div class="flex space-x-3">
      <button
        type="submit"
        :disabled="!isFormValid || isSubmitting"
        class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 hover:scale-105 hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
      >
        {{ isSubmitting ? (isEditing ? '更新中...' : '添加中...') : (isEditing ? '📝 更新列' : '➕ 添加列') }}
      </button>
      
      <button
        v-if="isEditing"
        type="button"
        @click="cancel"
        class="px-4 py-2 bg-slate-500 text-white rounded-lg hover:bg-slate-600 transition-colors duration-200"
      >
        取消
      </button>
      
      <button
        v-if="!isEditing"
        type="button"
        @click="resetForm"
        class="px-4 py-2 bg-slate-500 text-white rounded-lg hover:bg-slate-600 transition-colors duration-200"
      >
        重置
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { apiClient } from '@/api'
import type { ColumnMetadata } from '@/types'

// 定义组件属性
interface Props {
  tableName: string
  column?: ColumnMetadata
  isEditing?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isEditing: false
})

// 定义事件
const emit = defineEmits<{
  columnAdded: []
  columnUpdated: []
  cancel: []
}>()

// 响应式数据
const formData = ref({
  name: '',
  type: '',
  business_type: '',
  is_available: 0,
  relation_id: '',
  comment: ''
})

const relationIds = ref<string[]>([])
const isSubmitting = ref(false)

// 计算属性
const isFormValid = computed(() => {
  return formData.value.name.trim() && formData.value.type
})

// 初始化表单数据
const initializeForm = () => {
  if (props.column && props.isEditing) {
    formData.value = {
      name: props.column.name || '',
      type: props.column.type || '',
      business_type: props.column.business_type || '',
      is_available: props.column.is_available ?? 0,
      relation_id: props.column.relation_id || '',
      comment: props.column.comment || ''
    }
  } else {
    resetForm()
  }
}

// 重置表单
const resetForm = () => {
  formData.value = {
    name: '',
    type: '',
    business_type: '',
    is_available: 0,
    relation_id: '',
    comment: ''
  }
}

// 提交表单
const submitForm = async () => {
  if (!isFormValid.value || isSubmitting.value) return

  isSubmitting.value = true
  
  try {
    let success = false

    if (props.isEditing) {
      // 更新列
      success = await apiClient.updateColumnMetadata(
        props.tableName,
        formData.value.name,
        {
          type: formData.value.type,
          comment: formData.value.comment,
          is_available: formData.value.is_available,
          business_type: formData.value.business_type,
          relation_id: formData.value.relation_id
        }
      )
      
      if (success) {
        emit('columnUpdated')
      }
    } else {
      // 添加列
      success = await apiClient.addColumnMetadata(
        props.tableName,
        formData.value.name,
        formData.value.type,
        formData.value.comment,
        formData.value.is_available,
        formData.value.business_type,
        formData.value.relation_id
      )
      
      if (success) {
        resetForm()
        emit('columnAdded')
      }
    }
  } catch (error) {
    console.error('提交表单失败:', error)
  } finally {
    isSubmitting.value = false
  }
}

// 取消操作
const cancel = () => {
  emit('cancel')
}

// 加载关联ID列表
const loadRelationIds = async () => {
  try {
    relationIds.value = await apiClient.getRelationIds()
  } catch (error) {
    console.error('加载关联ID列表失败:', error)
  }
}

// 监听列数据变化
watch(() => props.column, () => {
  initializeForm()
}, { immediate: true, deep: true })

// 初始化
onMounted(() => {
  loadRelationIds()
  initializeForm()
})
</script>