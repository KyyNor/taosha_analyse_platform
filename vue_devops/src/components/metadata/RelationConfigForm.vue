<template>
  <form @submit.prevent="submitForm" class="space-y-4">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Relation Family -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">关联族</label>
        <input
          v-model="formData.relation_family"
          type="text"
          required
          placeholder="如：cust_no"
          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
        />
      </div>

      <!-- Relation Subfamily -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">关联子族</label>
        <input
          v-model="formData.relation_subfamily"
          type="text"
          required
          placeholder="如：17"
          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
        />
      </div>
    </div>

    <!-- Preview New Relation ID -->
    <div v-if="newRelationId && newRelationId !== originalRelationId" class="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
      <div class="flex items-start space-x-2">
        <ExclamationTriangleIcon class="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
        <div class="text-sm">
          <div class="text-yellow-800 font-medium">关联ID将发生变化</div>
          <div class="text-yellow-700 mt-1">
            <span class="font-mono">{{ originalRelationId }}</span> → <span class="font-mono font-semibold">{{ newRelationId }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Current Relation ID Preview -->
    <div v-else-if="newRelationId" class="bg-blue-50 border border-blue-200 rounded-lg p-3">
      <div class="text-sm text-blue-800">
        <strong>当前关联ID：</strong>
        <span class="font-mono">{{ newRelationId }}</span>
      </div>
    </div>

    <!-- Description -->
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-2">描述</label>
      <textarea
        v-model="formData.relation_desc"
        rows="3"
        placeholder="请输入关联字段的描述..."
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
        {{ isSubmitting ? (isEditing ? '更新中...' : '添加中...') : (isEditing ? '📝 更新配置' : '➕ 添加配置') }}
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

    <!-- Form Tips -->
    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <h4 class="text-sm font-medium text-blue-800 mb-2">💡 配置说明</h4>
      <ul class="text-sm text-blue-700 space-y-1">
        <li>• <strong>关联族：</strong>表示同一类业务字段的标识，如 customer_no、cust_id 都可归为 cust_no 族</li>
        <li>• <strong>关联子族：</strong>同一族中的不同变体编号，如不同系统中的客户编号格式</li>
        <li>• <strong>关联ID格式：</strong>关联族|关联子族，系统会自动生成如 cust_no|17</li>
        <li>• <strong>描述信息：</strong>说明该关联配置的具体含义和使用场景</li>
      </ul>
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { apiClient } from '@/api'
import type { RelationConfig } from '@/types'

// 定义组件属性
interface Props {
  config?: RelationConfig
  isEditing?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isEditing: false
})

// 定义事件
const emit = defineEmits<{
  configAdded: []
  configUpdated: []
  cancel: []
}>()

// 响应式数据
const formData = ref({
  relation_family: '',
  relation_subfamily: '',
  relation_desc: ''
})

const isSubmitting = ref(false)
const originalRelationId = ref('')

// 计算属性
const isFormValid = computed(() => {
  return formData.value.relation_family.trim() && formData.value.relation_subfamily.trim()
})

const newRelationId = computed(() => {
  if (formData.value.relation_family && formData.value.relation_subfamily) {
    return `${formData.value.relation_family}|${formData.value.relation_subfamily}`
  }
  return ''
})

// 初始化表单数据
const initializeForm = () => {
  if (props.config && props.isEditing) {
    formData.value = {
      relation_family: props.config.relation_family || '',
      relation_subfamily: props.config.relation_subfamily || '',
      relation_desc: props.config.relation_desc || ''
    }
    originalRelationId.value = props.config.relation_id
  } else {
    resetForm()
  }
}

// 重置表单
const resetForm = () => {
  formData.value = {
    relation_family: '',
    relation_subfamily: '',
    relation_desc: ''
  }
  originalRelationId.value = ''
}

// 提交表单
const submitForm = async () => {
  if (!isFormValid.value || isSubmitting.value) return

  isSubmitting.value = true
  
  try {
    let success = false

    if (props.isEditing && props.config?.relation_id) {
      // 更新关联配置
      success = await apiClient.updateRelationConfig(props.config.relation_id, {
        relation_family: formData.value.relation_family,
        relation_subfamily: formData.value.relation_subfamily,
        relation_desc: formData.value.relation_desc
      })
      
      if (success) {
        emit('configUpdated')
      }
    } else {
      // 添加关联配置
      success = await apiClient.addRelationConfig(
        formData.value.relation_family,
        formData.value.relation_subfamily,
        formData.value.relation_desc
      )
      
      if (success) {
        resetForm()
        emit('configAdded')
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

// 监听配置数据变化
watch(() => props.config, () => {
  initializeForm()
}, { immediate: true, deep: true })

// 初始化
onMounted(() => {
  initializeForm()
})
</script>