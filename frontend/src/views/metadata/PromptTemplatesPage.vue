<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-xl font-semibold">
          提示词配置管理
        </h2>
        <p class="text-base-content/60">
          管理系统提示词模板配置
        </p>
      </div>
      <button
        class="btn btn-primary"
        @click="openAddTemplate"
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
        添加提示词模板
      </button>
    </div>

    <!-- Templates Table -->
    <div class="overflow-x-auto bg-base-100 rounded-lg shadow-md">
      <DataTable
        :data="templates"
        :columns="templateColumns"
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

        <template #cell-fields="{ value }">
          <div class="flex flex-wrap gap-1">
            <div
              v-if="!value || value.length === 0"
              class="text-xs text-base-content/50 italic"
            >
              (无参数)
            </div>
            <div
              v-for="field in value"
              :key="field"
              class="badge badge-outline badge-sm"
            >
              {{ field }}
            </div>
          </div>
        </template>

        <template #cell-template="{ value }">
          <div
            class="max-w-xs truncate text-sm"
            :title="value"
          >
            {{ value || '-' }}
          </div>
        </template>

        <template #actions="{ record }">
          <div class="flex gap-1">
            <button
              class="btn btn-ghost btn-xs"
              title="预览"
              @click="openPreviewModal(record)"
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
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
              </svg>
            </button>
            <button
              class="btn btn-ghost btn-xs"
              title="编辑"
              @click="openEditTemplate(record)"
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
          </div>
        </template>
      </DataTable>
    </div>

    <!-- Template Form Modal -->
    <div
      v-if="showFormModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-base-100 rounded-lg w-11/12 max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <!-- Header -->
        <div class="p-6 border-b border-base-300 flex justify-between items-center flex-shrink-0">
          <h3 class="font-bold text-lg">
            {{ isEditMode ? '编辑提示词模板' : '添加提示词模板' }}
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
            <!-- Template Name -->
            <div class="form-control">
              <label class="label">
                <span class="label-text">模板名称 *</span>
              </label>
              <input
                v-model="templateForm.name"
                type="text"
                placeholder="请输入模板名称"
                class="input input-bordered"
                :disabled="isEditMode"
                required
              >
            </div>

            <!-- Fields (only for new templates) -->
            <div
              v-if="!isEditMode"
              class="form-control"
            >
              <label class="label">
                <span class="label-text">字段名 *</span>
              </label>
              <div class="space-y-2">
                <div
                  v-for="(_, index) in templateForm.fields"
                  :key="index"
                  class="flex gap-2 items-center"
                >
                  <input
                    v-model="templateForm.fields[index]"
                    type="text"
                    placeholder="字段名（如：user_input）"
                    class="input input-bordered input-sm flex-1"
                  >
                  <button
                    type="button"
                    class="btn btn-ghost btn-xs text-error"
                    :disabled="templateForm.fields.length <= 1"
                    @click="removeField(index)"
                  >
                    删除
                  </button>
                </div>
                <button
                  type="button"
                  class="btn btn-outline btn-sm"
                  @click="addField"
                >
                  添加字段
                </button>
              </div>
              <label class="label">
                <span class="label-text-alt">字段名将在模板中作为占位符使用，格式：{字段名}。不添加字段表示模板没有参数（固定内容）。</span>
              </label>
            </div>

            <!-- Fields Display (for edit mode) -->
            <div
              v-else
              class="form-control"
            >
              <label class="label">
                <span class="label-text">字段名</span>
              </label>
              <div class="flex flex-wrap gap-2 p-3 bg-base-200 rounded-lg">
                <div
                  v-for="field in templateForm.fields"
                  :key="field"
                  class="badge badge-ghost"
                >
                  {{ field }}
                </div>
              </div>
              <label class="label">
                <span class="label-text-alt">编辑模式下不能修改字段名</span>
              </label>
            </div>

            <!-- Template Content -->
            <div class="form-control">
              <label class="label">
                <span class="label-text">提示词模板 *</span>
              </label>
              <textarea
                v-model="templateForm.template"
                placeholder="请输入提示词模板，使用 {字段名} 作为占位符"
                class="textarea textarea-bordered h-48"
                required
              />
              <label class="label shadow-inner rounded-lg p-4 m-4 bg-base-200">
                <span class="label-text-alt">
                  <span class="text-warning">★ 占位符格式：使用 </span><span class="font-mono bg-warning/20 px-1 py-0.5">{字段名}</span><span class="text-warning"> 标记占位符，使用 </span><span class="font-mono bg-warning/20 px-1 py-0.5">@[模板名称]</span><span class="text-warning"> 标记模板替换</span>
                </span>
              </label>
            </div>

            <!-- Validation Errors -->
            <div
              v-if="validationErrors.length > 0"
              class="alert alert-error"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="stroke-current shrink-0 h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div>
                <h3 class="font-bold">
                  验证错误
                </h3>
                <div class="text-xs">
                  <ul class="list-disc list-inside">
                    <li
                      v-for="error in validationErrors"
                      :key="error"
                    >
                      {{ error }}
                    </li>
                  </ul>
                </div>
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
            :disabled="saving || !isFormValid || validationErrors.length > 0"
            @click="saveTemplate"
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

    <!-- Preview Modal -->
    <div
      v-if="showPreviewModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-base-100 rounded-lg w-11/12 max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <!-- Header -->
        <div class="p-6 border-b border-base-300 flex justify-between items-center flex-shrink-0">
          <h3 class="font-bold text-lg">
            模板预览 - {{ previewTemplate?.name }}
          </h3>
          <button
            class="btn btn-ghost btn-sm"
            @click="closePreviewModal"
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
        <div class="flex-1 overflow-y-auto p-6 space-y-6">
          <!-- Fields -->
          <div>
            <h4 class="font-semibold mb-3">
              字段列表 <span v-if="!previewTemplate?.fields?.filter((f: string) => f.trim()).length" class="text-xs text-base-content/50">(无参数模板)</span>
            </h4>
            <div class="flex flex-wrap gap-2">
              <div
                v-if="!previewTemplate?.fields?.filter((f: string) => f.trim()).length"
                class="text-base-content/60 text-sm italic"
              >
                此模板没有参数，包含固定内容
              </div>
              <div
                v-for="field in previewTemplate?.fields?.filter((f: string) => f.trim())"
                :key="field"
                class="badge badge-outline"
              >
                {{ field }}
              </div>
            </div>
          </div>

          <!-- Template -->
          <div>
            <h4 class="font-semibold mb-3">
              模板内容 <span class="text-xs text-base-content/50">(占位符已高亮)</span>
            </h4>
            <div class="bg-base-200 p-4 rounded-lg">
              <pre class="whitespace-pre-wrap text-sm" v-html="highlightedTemplate" />
            </div>
          </div>

          <!-- Example Usage -->
          <div>
            <h4 class="font-semibold mb-3">
              示例使用
            </h4>
            <div class="bg-base-200 p-4 rounded-lg">
              <div v-if="!previewTemplate?.fields?.filter((f: string) => f.trim()).length" class="text-base-content/60 text-sm italic">
                此模板无参数，直接使用即可（无需输入参数值）
              </div>
              <div v-else class="text-sm space-y-2">
                <div
                  v-for="field in previewTemplate?.fields?.filter((f: string) => f.trim())"
                  :key="field"
                  class="flex items-center gap-2"
                >
                  <span class="font-mono">{field}:</span>
                  <input
                    v-model="exampleValues[field]"
                    type="text"
                    :placeholder="`请输入 ${field} 的值`"
                    class="input input-bordered input-sm flex-1"
                    @input="updateExample"
                  >
                </div>
              </div>
            </div>
          </div>

          <!-- Result -->
          <div v-if="exampleResult">
            <h4 class="font-semibold mb-3">
              生成结果
            </h4>
            <div class="bg-primary/10 p-4 rounded-lg border border-primary/20">
              <pre class="whitespace-pre-wrap text-sm">{{ exampleResult }}</pre>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="p-6 border-t border-base-300 flex justify-end gap-2 flex-shrink-0">
          <button
            type="button"
            class="btn btn-ghost"
            @click="closePreviewModal"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useToast } from '@/composables/useToast'
import { metadataService } from '@services/api'
import DataTable from '@/components/common/DataTable.vue'

const { success, error } = useToast()

// State
const templates = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showFormModal = ref(false)
const showPreviewModal = ref(false)
const isEditMode = ref(false)
const editingTemplate = ref<any | null>(null)
const previewTemplate = ref<any | null>(null)

// Form
const templateForm = reactive({
  name: '',
  fields: [''],
  template: ''
})

// Preview example values
const exampleValues = ref<Record<string, string>>({})
const exampleResult = ref('')

// Table columns
const templateColumns = [
  {
    key: 'name',
    title: '模板名称',
    sortable: true,
    visible: true
  },
  {
    key: 'fields',
    title: '字段',
    sortable: false,
    visible: true
  },
  {
    key: 'template',
    title: '模板内容',
    sortable: false,
    visible: true
  }
]

// Computed
const isFormValid = computed(() => {
  return templateForm.name.trim() !== '' &&
         templateForm.template.trim() !== ''
  // 字段可以为空（表示模板没有参数）
})

const validationErrors = computed(() => {
  const errors: string[] = []

  if (!templateForm.template) return errors

  // Extract placeholders from template - 严格匹配 {字段名} 格式（不匹配 {{}} 格式）
  // 使用负向后视来避免匹配 {{}} 或 JSON 格式 {"key": "value"}
  const placeholderRegex = /(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})/g
  const placeholders = new Set<string>()
  let match
  while ((match = placeholderRegex.exec(templateForm.template)) !== null) {
    placeholders.add(match[1])
  }

  // Get defined fields（过滤空白字段）
  const definedFields = new Set(templateForm.fields.filter(f => f.trim()))

  // 如果字段列表为空，则不检查字段匹配（模板可以没有参数）
  if (definedFields.size === 0 && placeholders.size === 0) {
    // 无参数模板，完全有效
    return errors
  }

  // Check for missing fields
  const missingFields = Array.from(placeholders).filter(p => !definedFields.has(p))
  if (missingFields.length > 0) {
    errors.push(`模板中使用了未定义的字段: ${missingFields.join(', ')}`)
  }

  // Check for unused fields
  const unusedFields = Array.from(definedFields).filter(f => !placeholders.has(f))
  if (unusedFields.length > 0) {
    errors.push(`字段列表中有未使用的字段: ${unusedFields.join(', ')}`)
  }

  return errors
})

// Highlight placeholders in template
const highlightedTemplate = computed(() => {
  if (!previewTemplate.value) return ''

  let template = previewTemplate.value.template

  // 匹配 {字段名} 格式并高亮（避免匹配 {{}} 或 JSON）
  return template.replace(
    /(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})/g,
    '<span class="bg-warning/50 font-semibold px-1 rounded">{$1}</span>'
  )
})

// Watch for template changes to update example
watch(() => templateForm.template, () => {
  if (showPreviewModal.value) {
    updateExample()
  }
})

// Methods
const addField = () => {
  templateForm.fields.push('')
}

const removeField = (index: number) => {
  if (templateForm.fields.length > 1) {
    templateForm.fields.splice(index, 1)
  }
}

const resetForm = () => {
  Object.assign(templateForm, {
    name: '',
    fields: [''],
    template: ''
  })
}

const openAddTemplate = () => {
  isEditMode.value = false
  editingTemplate.value = null
  resetForm()
  showFormModal.value = true
}

const openEditTemplate = (template: any) => {
  isEditMode.value = true
  editingTemplate.value = template

  Object.assign(templateForm, {
    name: template.name,
    fields: [...template.fields],
    template: template.template
  })

  showFormModal.value = true
}

const closeFormModal = () => {
  showFormModal.value = false
  editingTemplate.value = null
  isEditMode.value = false
  resetForm()
}

const saveTemplate = async () => {
  try {
    saving.value = true

    // 过滤掉空白字段（允许完全没有字段）
    const fieldsArray = templateForm.fields.filter(f => f.trim())

    const data = {
      name: templateForm.name,
      fields: fieldsArray,  // 可以为空数组
      template: templateForm.template
    }

    if (isEditMode.value) {
      await metadataService.updatePromptTemplate(editingTemplate.value.id, data)
      success('提示词模板已更新')
    } else {
      await metadataService.createPromptTemplate(data)
      success('提示词模板已创建')
    }

    closeFormModal()
    await loadTemplates()
  } catch (err) {
    error(isEditMode.value ? '更新提示词模板失败' : '创建提示词模板失败')
  } finally {
    saving.value = false
  }
}


const openPreviewModal = (template: any) => {
  previewTemplate.value = template

  // Initialize example values（过滤空字段）
  exampleValues.value = {}
  template.fields
    .filter((field: string) => field.trim())
    .forEach((field: string) => {
      exampleValues.value[field] = `示例${field}`
    })

  updateExample()
  showPreviewModal.value = true
}

const closePreviewModal = () => {
  showPreviewModal.value = false
  previewTemplate.value = null
  exampleValues.value = {}
  exampleResult.value = ''
}

const updateExample = () => {
  if (!previewTemplate.value) return

  let result = previewTemplate.value.template

  // Replace placeholders with example values - 严格匹配 {字段名} 格式
  Object.entries(exampleValues.value).forEach(([field, value]) => {
    // 使用负向后视/前视避免匹配 {{}} 或其他格式
    const regex = new RegExp(`(?<!\\{)\\{${field}\\}(?!\\})`, 'g')
    result = result.replace(regex, value || `{${field}}`)
  })

  exampleResult.value = result
}

const loadTemplates = async () => {
  try {
    loading.value = true
    templates.value = await metadataService.getPromptTemplates()
  } catch (err) {
    error('加载提示词模板列表失败')
  } finally {
    loading.value = false
  }
}

// Initialize
onMounted(() => {
  loadTemplates()
})
</script>
