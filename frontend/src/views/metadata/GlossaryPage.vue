<template>
  <div class="space-y-6">
    <!-- Filters -->
    <div class="flex flex-wrap gap-4 items-center bg-base-200 p-4 rounded-lg shadow-md">
      <div class="form-control flex-1 min-w-64">
        <label class="label">
          <span class="label-text">搜索</span>
        </label>
        <input
          v-model="filters.search"
          type="text"
          placeholder="搜索术语名称..."
          class="input input-bordered input-sm"
          @input="debouncedSearch"
        >
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text">术语类型</span>
        </label>
        <select
          v-model="filters.type"
          class="select select-bordered select-sm"
          @change="loadTerms"
        >
          <option value="">
            全部
          </option>
          <option value="concept">
            概念解释
          </option>
          <option value="sql_qa">
            SQL问答
          </option>
          <option value="dict_mapping">
            字典转换
          </option>
        </select>
      </div>

      <button
        class="btn btn-primary"
        @click="openAddTerm"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 4v16m8-8H4"
          />
        </svg>
        添加术语
      </button>
    </div>

    <!-- Terms Table -->
    <div class="overflow-x-auto bg-base-100 rounded-lg shadow-md">
      <DataTable
        :data="filteredTerms"
        :columns="termColumns"
        :loading="loading"
        :searchable="false"
        :paginated="true"
        :page-size="20"
        empty-state-type="no-data"
        row-key="id"
        :show-header="true"
        :column-settings="true"
      >
        <template #cell-name="{ value }">
          <div class="font-medium">
            {{ value }}
          </div>
        </template>

        <template #cell-type="{ value }">
          <div class="badge badge-ghost badge-sm">
            {{ getTypeLabel(value) }}
          </div>
        </template>

        <template #cell-content="{ value, record }">
          <div class="max-w-xs">
            <div v-if="record.type === 'concept'">
              {{ value.content || '-' }}
            </div>
            <div v-else-if="record.type === 'sql_qa'">
              <div class="text-sm">
                <div class="font-semibold">
                  问题: {{ value.question || '-' }}
                </div>
                <div class="text-base-content/60">
                  答案: {{ value.answer || '-' }}
                </div>
              </div>
            </div>
            <div v-else-if="record.type === 'dict_mapping'">
              <div class="text-sm">
                <div class="font-semibold">
                  字段: {{ value.col_name || '-' }}
                </div>
                <div class="text-base-content/60">
                  映射: {{ value.dict_map?.length || 0 }} 项
                </div>
              </div>
            </div>
          </div>
        </template>

        <template #cell-creator="{ value }">
          <div class="text-sm">
            {{ value || '-' }}
          </div>
        </template>

        <template #actions="{ record }">
          <div class="flex gap-1">
            <button
              class="btn btn-ghost btn-xs"
              title="编辑"
              @click="openEditTerm(record)"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-3 w-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
            </button>
            <button
              class="btn btn-ghost btn-xs text-error"
              title="删除"
              @click="confirmDeleteTerm(record)"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-3 w-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          </div>
        </template>
      </DataTable>
    </div>

    <!-- Term Form Modal -->
    <div
      v-if="showFormModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeFormModal"
    >
      <div class="bg-base-100 rounded-lg w-11/12 max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <!-- Header -->
        <div class="p-6 border-b border-base-300 flex justify-between items-center flex-shrink-0">
          <h3 class="font-bold text-lg">
            {{ isEditMode ? '编辑术语' : '添加术语' }}
          </h3>
          <button
            class="btn btn-ghost btn-sm"
            @click="closeFormModal"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto p-6">
          <form class="space-y-6">
            <!-- Basic Info -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="form-control">
                <label class="label">
                  <span class="label-text">术语名称 *</span>
                </label>
                <input
                  v-model="termForm.name"
                  type="text"
                  placeholder="请输入术语名称"
                  class="input input-bordered"
                  required
                >
              </div>

              <div class="form-control">
                <label class="label">
                  <span class="label-text">术语类型 *</span>
                </label>
                <select
                  v-model="termForm.type"
                  class="select select-bordered"
                  :disabled="isEditMode"
                  required
                >
                  <option value="">
                    请选择类型
                  </option>
                  <option value="concept">
                    概念解释
                  </option>
                  <option value="sql_qa">
                    SQL问答
                  </option>
                  <option value="dict_mapping">
                    字典转换
                  </option>
                </select>
              </div>
            </div>

            <!-- 创建人字段隐藏，默认为 api_user -->

            <!-- Type-specific content -->
            <div class="form-control w-full">
              <label class="label">
                <span class="label-text font-semibold text-base">
                  {{ getContentLabel() }}
                </span>
              </label>

              <!-- 概念解释 -->
              <div
                v-if="termForm.type === 'concept'"
                class="w-full"
              >
                <div class="form-control">
                  <textarea
                    v-model="termForm.content.content"
                    placeholder="请输入概念解释内容，支持多行文本"
                    class="textarea textarea-bordered textarea-primary w-full h-24 resize-none text-sm leading-relaxed"
                  />
                </div>
              </div>

              <!-- SQL问答 -->
              <div
                v-else-if="termForm.type === 'sql_qa'"
                class="space-y-4 w-full"
              >
                <div class="w-full">
                  <label class="label">
                    <span class="label-text text-sm font-medium">问题</span>
                  </label>
                  <div class="form-control">
                    <input
                      v-model="termForm.content.question"
                      type="text"
                      placeholder="请输入问题，例如：如何查看用户信息？"
                      class="input input-bordered input-primary w-full"
                    >
                  </div>
                </div>
                <div class="w-full">
                  <label class="label">
                    <span class="label-text text-sm font-medium">答案</span>
                  </label>
                  <div class="form-control">
                    <textarea
                      v-model="termForm.content.answer"
                      placeholder="请输入答案，支持SQL语句和详细说明"
                      class="textarea textarea-bordered textarea-primary w-full h-20 resize-none text-sm font-mono leading-relaxed"
                    />
                  </div>
                </div>
                <div class="w-full">
                  <label class="label">
                    <span class="label-text text-sm font-medium">备注</span>
                  </label>
                  <div class="form-control">
                    <input
                      v-model="termForm.content.remark"
                      type="text"
                      placeholder="请输入备注信息（可选）"
                      class="input input-bordered input-primary w-full"
                    >
                  </div>
                </div>
              </div>

              <!-- 字典转换 -->
              <div
                v-else-if="termForm.type === 'dict_mapping'"
                class="space-y-4 w-full"
              >
                <div class="w-full">
                  <label class="label">
                    <span class="label-text text-sm font-medium">字段名</span>
                    <span class="label-text-alt text-base-content/60">多个字段用逗号分隔</span>
                  </label>
                  <div class="form-control">
                    <input
                      v-model="termForm.content.col_name"
                      type="text"
                      placeholder="例如: status,type,level"
                      class="input input-bordered input-primary w-full"
                    >
                  </div>
                </div>
                <div class="w-full">
                  <label class="label">
                    <span class="label-text text-sm font-medium">键值映射</span>
                    <span class="label-text-alt text-base-content/60">配置字段值的映射关系</span>
                  </label>
                  <div class="bg-base-200 rounded-lg p-4">
                    <div class="space-y-3 max-h-48 overflow-y-auto">
                      <div
                        v-for="(mapping, index) in termForm.content.dict_map"
                        :key="index"
                        class="flex gap-3 items-center"
                      >
                        <div class="form-control flex-1">
                          <input
                            v-model="termForm.content.dict_map[index].key"
                            type="text"
                            placeholder="原值"
                            class="input input-bordered input-sm flex-1 font-mono"
                          >
                        </div>
                        <div class="text-base-content/60">
                          →
                        </div>
                        <div class="form-control flex-1">
                          <input
                            v-model="termForm.content.dict_map[index].value"
                            type="text"
                            placeholder="映射值"
                            class="input input-bordered input-sm flex-1 font-mono"
                          >
                        </div>
                        <button
                          type="button"
                          class="btn btn-ghost btn-xs text-error hover:bg-error/10"
                          @click="removeMapping(index)"
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            class="h-3 w-3"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                        </button>
                      </div>
                    </div>
                    <div class="mt-3 pt-3 border-t border-base-300">
                      <button
                        type="button"
                        class="btn btn-outline btn-sm w-full"
                        @click="addMapping"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          class="h-3 w-3 mr-1"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M12 4v16m8-8H4"
                          />
                        </svg>
                        添加映射项
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 未选择类型时的提示 -->
              <div
                v-else
                class="text-center py-8 text-base-content/60 bg-base-200 rounded-lg"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-12 w-12 mx-auto mb-3 opacity-50"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <p class="text-sm">
                  请先选择术语类型以显示对应的输入表单
                </p>
              </div>
            </div>
          </form>
        </div>

        <!-- Actions -->
        <div class="p-6 border-t border-base-300 flex justify-end gap-2 flex-shrink-0">
          <button
            type="button"
            class="btn btn-ghost"
            @click="closeFormModal"
          >
            取消
          </button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="saving || !isFormValid"
            @click="saveTerm"
          >
            <span
              v-if="saving"
              class="loading loading-spinner loading-sm"
            />
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useToast } from '@/composables/useToast'
import { metadataService } from '@services/api'
import DataTable from '@/components/common/DataTable.vue'

const { success, error } = useToast()

// State
const terms = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showFormModal = ref(false)
const isEditMode = ref(false)
const editingTerm = ref<any | null>(null)

// Filters
const filters = reactive({
  search: '',
  type: ''
})

// Form
interface DictMapping {
  key: string
  value: string
}

interface TermFormContent {
  content: string
  question: string
  answer: string
  remark: string
  col_name: string
  dict_map: DictMapping[]
}

interface TermForm {
  name: string
  type: string
  creator: string
  content: TermFormContent
}

const termForm = reactive<TermForm>({
  name: '',
  type: '',
  creator: '',
  content: {
    content: '',
    question: '',
    answer: '',
    remark: '',
    col_name: '',
    dict_map: []
  }
})

// Table columns
const termColumns = [
  {
    key: 'name',
    title: '术语名称',
    sortable: true,
    visible: true
  },
  {
    key: 'type',
    title: '类型',
    sortable: true,
    visible: true
  },
  {
    key: 'content',
    title: '内容',
    sortable: false,
    visible: true
  },
  {
    key: 'creator',
    title: '创建人',
    sortable: true,
    visible: true
  }
]

// Computed
const filteredTerms = computed(() => {
  let result = terms.value

  // Apply type filter
  if (filters.type) {
    result = result.filter(term => term.type === filters.type)
  }

  return result
})

const isFormValid = computed(() => {
  return termForm.name && termForm.type && isContentValid()
})

// Methods
const getTypeLabel = (type: string) => {
  const labels = {
    concept: '概念解释',
    sql_qa: 'SQL问答',
    dict_mapping: '字典转换'
  }
  return labels[type] || type
}

const getContentLabel = () => {
  const labels = {
    concept: '概念解释内容',
    sql_qa: 'SQL问答内容',
    dict_mapping: '字典转换内容'
  }
  return labels[termForm.type] || '内容'
}

const isContentValid = () => {
  switch (termForm.type) {
    case 'concept':
      return termForm.content.content.trim() !== ''
    case 'sql_qa':
      return termForm.content.question.trim() !== '' && termForm.content.answer.trim() !== ''
    case 'dict_mapping':
      return termForm.content.col_name.trim() !== '' && termForm.content.dict_map.length > 0
    default:
      return false
  }
}

const addMapping = () => {
  termForm.content.dict_map.push({ key: '', value: '' })
}

const removeMapping = (index: number) => {
  termForm.content.dict_map.splice(index, 1)
}


const resetForm = () => {
  Object.assign(termForm, {
    name: '',
    type: '',
    creator: '',
    content: {
      content: '',
      question: '',
      answer: '',
      remark: '',
      col_name: '',
      dict_map: []
    }
  })
}

const openAddTerm = () => {
  isEditMode.value = false
  editingTerm.value = null
  resetForm()
  showFormModal.value = true
}

const openEditTerm = (term: any) => {
  isEditMode.value = true
  editingTerm.value = term

  Object.assign(termForm, {
    name: term.name,
    type: term.type,
    creator: term.creator || '',
    content: {
      ...termForm.content,
      ...term.content
    }
  })

  // Ensure dict_map exists for dict_mapping type
  if (term.type === 'dict_mapping' && !termForm.content.dict_map) {
    termForm.content.dict_map = []
  }

  showFormModal.value = true
}

const closeFormModal = () => {
  showFormModal.value = false
  editingTerm.value = null
  isEditMode.value = false
  resetForm()
}

const saveTerm = async () => {
  try {
    saving.value = true

    const data = {
      name: termForm.name,
      type: termForm.type,
      creator: termForm.creator,
      content: { ...termForm.content }
    }

    if (isEditMode.value) {
      await metadataService.updateGlossaryTerm(editingTerm.value.id, data)
      success('术语已更新')
    } else {
      await metadataService.createGlossaryTerm(data)
      success('术语已创建')
    }

    closeFormModal()
    await loadTerms()
  } catch (err) {
    error(isEditMode.value ? '更新术语失败' : '创建术语失败')
  } finally {
    saving.value = false
  }
}

const confirmDeleteTerm = (term: any) => {
  if (confirm(`确定要删除术语 "${term.name}" 吗？此操作不可恢复。`)) {
    deleteTerm(term)
  }
}

const deleteTerm = async (term: any) => {
  try {
    await metadataService.deleteGlossaryTerm(term.id)
    success('术语已删除')
    await loadTerms()
  } catch (err) {
    error('删除术语失败')
  }
}

const loadTerms = async () => {
  try {
    loading.value = true
    terms.value = await metadataService.getGlossaryTerms()
  } catch (err) {
    error('加载术语列表失败')
  } finally {
    loading.value = false
  }
}

// Debounced search
let searchTimeout: number
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    // Search is handled by the computed property
  }, 500)
}

// Initialize
onMounted(() => {
  loadTerms()
})
</script>
