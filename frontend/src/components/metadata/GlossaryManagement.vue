<template>
  <div class="space-y-6">
    <!-- Add Term Section -->
    <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
      <div class="flex items-center space-x-2 mb-4">
        <PlusIcon class="w-5 h-5 text-blue-600" aria-label="添加图标" />
        <h3 class="text-lg font-semibold text-slate-800">添加新术语</h3>
      </div>
      
      <form @submit.prevent="addTerm" class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">术语名称</label>
            <input
              v-model="newTerm.term"
              type="text"
              required
              placeholder="输入术语名称"
              class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">分类</label>
            <input
              v-model="newTerm.category"
              type="text"
              placeholder="输入分类"
              class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">术语定义</label>
          <textarea
            v-model="newTerm.definition"
            rows="3"
            required
            placeholder="输入术语的定义"
            class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          ></textarea>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">SQL表达式</label>
          <textarea
            v-model="newTerm.sqlExpression"
            rows="3"
            placeholder="输入相关的SQL表达式"
            class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
          ></textarea>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">别名（用逗号分隔）</label>
          <input
            v-model="newTerm.aliasesStr"
            type="text"
            placeholder="别名1, 别名2, 别名3"
            class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        
        <button
          type="submit"
          :disabled="!newTerm.term || !newTerm.definition || isAdding"
          class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 hover:scale-105 hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
        >
          {{ isAdding ? '添加中...' : '添加术语' }}
        </button>
      </form>
    </div>

    <!-- Terms List -->
    <div class="bg-white rounded-lg border border-slate-200 shadow-sm">
      <div class="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <BookOpenIcon class="w-5 h-5 text-blue-600" aria-label="书本图标" />
          <h3 class="text-lg font-semibold text-slate-800">术语表管理</h3>
        </div>
        <button
          @click="refreshTerms"
          :disabled="isRefreshing"
          class="px-3 py-1 text-sm bg-slate-100 text-slate-600 rounded hover:bg-slate-200 transition-colors duration-200 disabled:opacity-50"
        >
          <ArrowPathIcon class="w-4 h-4 mr-1" aria-label="刷新图标" />
          <span>{{ isRefreshing ? '刷新中...' : '刷新' }}</span>
        </button>
      </div>

      <div class="p-6">
        <div v-if="isLoading" class="text-center py-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <div class="text-slate-500 mt-2">加载中...</div>
        </div>

        <div v-else-if="terms.length === 0" class="text-center py-8">
          <div class="text-slate-500">暂无术语数据</div>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="term in terms"
            :key="term.id"
            class="border border-slate-200 rounded-lg overflow-hidden"
          >
            <!-- Term Header -->
            <div class="bg-slate-50 px-4 py-3 flex items-center justify-between">
              <div class="flex items-center space-x-3">
                <div class="flex items-center space-x-2">
                  <PencilIcon class="w-4 h-4 text-blue-600" aria-label="编辑图标" />
                  <h4 class="font-medium text-slate-800">{{ term.term }}</h4>
                </div>
                <span v-if="term.category" class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                  {{ term.category }}
                </span>
              </div>
              
              <div class="flex items-center space-x-2">
                <button
                  @click="toggleTermExpansion(term.id!)"
                  class="p-1 hover:bg-slate-200 rounded transition-colors duration-200"
                >
                  <ChevronDownIcon 
                    :class="['w-4 h-4 text-slate-500 transition-transform duration-200', 
                             expandedTerms.has(term.id!) ? 'rotate-180' : '']" 
                  />
                </button>
              </div>
            </div>

            <!-- Term Details -->
            <div v-if="expandedTerms.has(term.id!)" class="p-4 space-y-4">
              <!-- Display Mode -->
              <div v-if="editingTermId !== term.id" class="space-y-3">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">定义</label>
                  <p class="text-slate-600">{{ term.definition || '无定义' }}</p>
                </div>
                
                <div v-if="term.sql_expression">
                  <label class="block text-sm font-medium text-slate-700 mb-1">SQL表达式</label>
                  <pre class="bg-slate-900 text-green-400 p-3 rounded text-sm font-mono overflow-x-auto">{{ term.sql_expression }}</pre>
                </div>
                
                <div v-if="term.aliases && term.aliases.length > 0">
                  <label class="block text-sm font-medium text-slate-700 mb-1">别名</label>
                  <div class="flex flex-wrap gap-1">
                    <span
                      v-for="alias in term.aliases"
                      :key="alias"
                      class="px-2 py-1 text-xs bg-slate-100 text-slate-700 rounded"
                    >
                      {{ alias }}
                    </span>
                  </div>
                </div>
                
                <div class="flex space-x-2 pt-2">
                  <button
                    @click="startEditTerm(term)"
                    class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors duration-200"
                  >
                    <PencilIcon class="w-4 h-4 mr-1" aria-label="编辑图标" />
                    <span>编辑</span>
                  </button>
                  <button
                    @click="confirmDeleteTerm(term.id!, term.term)"
                    class="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600 transition-colors duration-200"
                  >
                    <TrashIcon class="w-4 h-4 mr-1" aria-label="删除图标" />
                    <span>删除</span>
                  </button>
                </div>
              </div>

              <!-- Edit Mode -->
              <div v-else class="space-y-4">
                <TermForm
                  :term="term"
                  :is-editing="true"
                  @term-updated="handleTermUpdated"
                  @cancel="cancelEdit"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ChevronDownIcon, PlusIcon, BookOpenIcon, ArrowPathIcon, PencilIcon, TrashIcon } from '@heroicons/vue/24/outline'
import { apiClient } from '@/api'
import type { Term } from '@/types'
import TermForm from './TermForm.vue'

// 响应式数据
const terms = ref<Term[]>([])
const isLoading = ref(false)
const isRefreshing = ref(false)
const isAdding = ref(false)
const expandedTerms = ref<Set<number>>(new Set())
const editingTermId = ref<number | null>(null)

// 新术语表单
const newTerm = ref({
  term: '',
  definition: '',
  sqlExpression: '',
  category: '',
  aliasesStr: ''
})

// 加载术语数据
const loadTerms = async () => {
  isLoading.value = true
  try {
    terms.value = await apiClient.getAllTerms()
  } catch (error) {
    console.error('加载术语数据失败:', error)
  } finally {
    isLoading.value = false
  }
}

// 刷新术语数据
const refreshTerms = async () => {
  isRefreshing.value = true
  try {
    terms.value = await apiClient.getAllTerms()
  } catch (error) {
    console.error('刷新术语数据失败:', error)
  } finally {
    isRefreshing.value = false
  }
}

// 添加术语
const addTerm = async () => {
  if (!newTerm.value.term || !newTerm.value.definition) return
  
  isAdding.value = true
  try {
    const aliases = newTerm.value.aliasesStr
      .split(',')
      .map(alias => alias.trim())
      .filter(alias => alias)

    const success = await apiClient.addTerm(
      newTerm.value.term,
      newTerm.value.definition,
      newTerm.value.sqlExpression,
      newTerm.value.category,
      aliases
    )
    
    if (success) {
      // 重置表单
      newTerm.value = {
        term: '',
        definition: '',
        sqlExpression: '',
        category: '',
        aliasesStr: ''
      }
      
      // 刷新列表
      await refreshTerms()
    }
  } catch (error) {
    console.error('添加术语失败:', error)
  } finally {
    isAdding.value = false
  }
}

// 切换术语展开状态
const toggleTermExpansion = (termId: number) => {
  if (expandedTerms.value.has(termId)) {
    expandedTerms.value.delete(termId)
  } else {
    expandedTerms.value.add(termId)
  }
}

// 开始编辑术语
const startEditTerm = (term: Term) => {
  editingTermId.value = term.id!
}

// 取消编辑
const cancelEdit = () => {
  editingTermId.value = null
}

// 处理术语更新
const handleTermUpdated = () => {
  editingTermId.value = null
  refreshTerms()
}

// 删除术语确认
const confirmDeleteTerm = (termId: number, termName: string) => {
  if (confirm(`确定要删除术语 "${termName}" 吗？此操作不可恢复。`)) {
    deleteTerm(termId)
  }
}

// 删除术语
const deleteTerm = async (termId: number) => {
  try {
    const success = await apiClient.deleteTerm(termId)
    
    if (success) {
      await refreshTerms()
    }
  } catch (error) {
    console.error('删除术语失败:', error)
  }
}

// 初始化
onMounted(() => {
  loadTerms()
})
</script>