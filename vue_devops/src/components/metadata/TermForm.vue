<template>
  <form @submit.prevent="submitForm" class="space-y-4">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Term Name -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">术语名称</label>
        <input
          v-model="formData.term"
          type="text"
          required
          placeholder="输入术语名称"
          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <!-- Category -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">分类</label>
        <input
          v-model="formData.category"
          type="text"
          placeholder="输入分类"
          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
    </div>

    <!-- Definition -->
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-2">术语定义</label>
      <textarea
        v-model="formData.definition"
        rows="3"
        required
        placeholder="输入术语的定义"
        class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      ></textarea>
    </div>

    <!-- SQL Expression -->
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-2">SQL表达式</label>
      <textarea
        v-model="formData.sql_expression"
        rows="4"
        placeholder="输入相关的SQL表达式（可选）"
        class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
      ></textarea>
      <div class="text-xs text-slate-500 mt-1">
        💡 提示：可以输入与此术语相关的SQL查询示例
      </div>
    </div>

    <!-- Aliases -->
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-2">别名（用逗号分隔）</label>
      <input
        v-model="aliasesInput"
        type="text"
        placeholder="别名1, 别名2, 别名3"
        class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      />
      <div class="text-xs text-slate-500 mt-1">
        输入该术语的其他名称或同义词，用逗号分隔
      </div>
      
      <!-- Alias Preview -->
      <div v-if="aliasesPreview.length > 0" class="mt-2">
        <div class="text-xs text-slate-600 mb-1">别名预览：</div>
        <div class="flex flex-wrap gap-1">
          <span
            v-for="alias in aliasesPreview"
            :key="alias"
            class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded"
          >
            {{ alias }}
          </span>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="flex space-x-3">
      <button
        type="submit"
        :disabled="!isFormValid || isSubmitting"
        class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 hover:scale-105 hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
      >
        {{ isSubmitting ? (isEditing ? '更新中...' : '添加中...') : (isEditing ? '📝 更新术语' : '➕ 添加术语') }}
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
      <h4 class="text-sm font-medium text-blue-800 mb-2">💡 填写建议</h4>
      <ul class="text-sm text-blue-700 space-y-1">
        <li>• 术语定义应该清晰、准确，便于理解</li>
        <li>• SQL表达式可以帮助技术人员理解术语的计算逻辑</li>
        <li>• 别名有助于用户用不同表达方式查询同一概念</li>
        <li>• 合理的分类有助于术语的组织和检索</li>
      </ul>
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { apiClient } from '@/api'
import type { Term } from '@/types'

// 定义组件属性
interface Props {
  term?: Term
  isEditing?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isEditing: false
})

// 定义事件
const emit = defineEmits<{
  termAdded: []
  termUpdated: []
  cancel: []
}>()

// 响应式数据
const formData = ref({
  term: '',
  definition: '',
  sql_expression: '',
  category: ''
})

const aliasesInput = ref('')
const isSubmitting = ref(false)

// 计算属性
const isFormValid = computed(() => {
  return formData.value.term.trim() && formData.value.definition.trim()
})

const aliasesPreview = computed(() => {
  return aliasesInput.value
    .split(',')
    .map(alias => alias.trim())
    .filter(alias => alias)
})

// 初始化表单数据
const initializeForm = () => {
  if (props.term && props.isEditing) {
    formData.value = {
      term: props.term.term || '',
      definition: props.term.definition || '',
      sql_expression: props.term.sql_expression || '',
      category: props.term.category || ''
    }
    
    aliasesInput.value = props.term.aliases ? props.term.aliases.join(', ') : ''
  } else {
    resetForm()
  }
}

// 重置表单
const resetForm = () => {
  formData.value = {
    term: '',
    definition: '',
    sql_expression: '',
    category: ''
  }
  aliasesInput.value = ''
}

// 提交表单
const submitForm = async () => {
  if (!isFormValid.value || isSubmitting.value) return

  isSubmitting.value = true
  
  try {
    const aliases = aliasesPreview.value
    let success = false

    if (props.isEditing && props.term?.id) {
      // 更新术语
      success = await apiClient.updateTerm(props.term.id, {
        term: formData.value.term,
        definition: formData.value.definition,
        sql_expression: formData.value.sql_expression,
        category: formData.value.category,
        aliases: aliases
      })
      
      if (success) {
        emit('termUpdated')
      }
    } else {
      // 添加术语
      success = await apiClient.addTerm(
        formData.value.term,
        formData.value.definition,
        formData.value.sql_expression,
        formData.value.category,
        aliases
      )
      
      if (success) {
        resetForm()
        emit('termAdded')
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

// 监听术语数据变化
watch(() => props.term, () => {
  initializeForm()
}, { immediate: true, deep: true })

// 初始化
onMounted(() => {
  initializeForm()
})
</script>