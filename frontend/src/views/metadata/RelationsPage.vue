<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-xl font-semibold">关联配置管理</h2>
        <p class="text-base-content/60">
          管理表之间的关联关系配置
        </p>
      </div>
      <button
        class="btn btn-primary"
        @click="openAddRelation"
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
        添加关联配置
      </button>
    </div>

    <!-- Relations Table -->
    <div class="overflow-x-auto bg-base-100 rounded-lg shadow-md">
      <DataTable
        :data="relations"
        :columns="relationColumns"
        :loading="loading"
        :searchable="false"
        :paginated="true"
        :page-size="20"
        empty-state-type="no-data"
        row-key="relation_id"
        :show-header="true"
        :column-settings="true"
      >
        <template #cell-relation_id="{ value }">
          <div class="font-mono text-sm">
            {{ value }}
          </div>
        </template>

        <template #cell-relation_family="{ value }">
          <div class="badge badge-ghost badge-sm">
            {{ value }}
          </div>
        </template>

        <template #cell-relation_subfamily="{ value }">
          <div class="badge badge-ghost badge-sm">
            {{ value }}
          </div>
        </template>

        <template #cell-relation_desc="{ value }">
          <div
            class="max-w-xs truncate"
            :title="value"
          >
            {{ value || '-' }}
          </div>
        </template>

        <template #actions="{ record }">
          <div class="flex gap-1">
            <button
              class="btn btn-ghost btn-xs"
              title="编辑"
              @click="openEditRelation(record)"
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
              @click="confirmDeleteRelation(record)"
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

    <!-- Relation Form Modal -->
    <div
      v-if="showFormModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeFormModal"
    >
      <div class="bg-base-100 rounded-lg w-11/12 max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <!-- Header -->
        <div class="p-6 border-b border-base-300 flex justify-between items-center flex-shrink-0">
          <h3 class="font-bold text-lg">
            {{ isEditMode ? '编辑关联配置' : '添加关联配置' }}
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
            <!-- Relation Family -->
            <div class="form-control">
              <label class="label">
                <span class="label-text">关系家族 *</span>
              </label>
              <input
                v-model="relationForm.relation_family"
                type="text"
                placeholder="请输入关系家族"
                class="input input-bordered"
                required
              >
              <label class="label">
                <span class="label-text-alt">例如：时间、地理位置、用户行为等</span>
              </label>
            </div>

            <!-- Relation Subfamily -->
            <div class="form-control">
              <label class="label">
                <span class="label-text">关系子家族 *</span>
              </label>
              <input
                v-model="relationForm.relation_subfamily"
                type="text"
                placeholder="请输入关系子家族"
                class="input input-bordered"
                required
              >
              <label class="label">
                <span class="label-text-alt">例如：年月日、省市县、注册登录等</span>
              </label>
            </div>

            <!-- Relation Description -->
            <div class="form-control">
              <label class="label">
                <span class="label-text">关系描述</span>
              </label>
              <textarea
                v-model="relationForm.relation_desc"
                placeholder="请输入关系描述"
                class="textarea textarea-bordered h-24"
              />
              <label class="label">
                <span class="label-text-alt">详细描述这种关系的用途和含义</span>
              </label>
            </div>

            <!-- Generated Relation ID (Read-only) -->
            <div class="form-control">
              <label class="label">
                <span class="label-text">关联ID（自动生成）</span>
              </label>
              <input
                :value="generatedRelationId"
                type="text"
                class="input input-bordered"
                readonly
                disabled
              >
              <label class="label">
                <span class="label-text-alt">格式：家族|子家族</span>
              </label>
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
            @click="saveRelation"
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
const relations = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showFormModal = ref(false)
const isEditMode = ref(false)
const editingRelation = ref<any | null>(null)

// Form
const relationForm = reactive({
  relation_family: '',
  relation_subfamily: '',
  relation_desc: ''
})

// Table columns
const relationColumns = [
  {
    key: 'relation_id',
    title: '关联ID',
    sortable: true,
    visible: true
  },
  {
    key: 'relation_family',
    title: '关系家族',
    sortable: true,
    visible: true
  },
  {
    key: 'relation_subfamily',
    title: '关系子家族',
    sortable: true,
    visible: true
  },
  {
    key: 'relation_desc',
    title: '关系描述',
    sortable: false,
    visible: true
  }
]

// Computed
const generatedRelationId = computed(() => {
  if (relationForm.relation_family && relationForm.relation_subfamily) {
    return `${relationForm.relation_family}|${relationForm.relation_subfamily}`
  }
  return ''
})

const isFormValid = computed(() => {
  return relationForm.relation_family.trim() !== '' &&
         relationForm.relation_subfamily.trim() !== ''
})

// Methods
const resetForm = () => {
  Object.assign(relationForm, {
    relation_family: '',
    relation_subfamily: '',
    relation_desc: ''
  })
}

const openAddRelation = () => {
  isEditMode.value = false
  editingRelation.value = null
  resetForm()
  showFormModal.value = true
}

const openEditRelation = (relation: any) => {
  isEditMode.value = true
  editingRelation.value = relation

  Object.assign(relationForm, {
    relation_family: relation.relation_family,
    relation_subfamily: relation.relation_subfamily,
    relation_desc: relation.relation_desc || ''
  })

  showFormModal.value = true
}

const closeFormModal = () => {
  showFormModal.value = false
  editingRelation.value = null
  isEditMode.value = false
  resetForm()
}

const saveRelation = async () => {
  try {
    saving.value = true

    const data = {
      relation_family: relationForm.relation_family,
      relation_subfamily: relationForm.relation_subfamily,
      relation_desc: relationForm.relation_desc
    }

    if (isEditMode.value) {
      await metadataService.updateRelationConfig(editingRelation.value.relation_id, data)
      success('关联配置已更新')
    } else {
      await metadataService.createRelationConfig(data)
      success('关联配置已创建')
    }

    closeFormModal()
    await loadRelations()
  } catch (err) {
    error(isEditMode.value ? '更新关联配置失败' : '创建关联配置失败')
  } finally {
    saving.value = false
  }
}

const confirmDeleteRelation = (relation: any) => {
  if (confirm(`确定要删除关联配置 "${relation.relation_id}" 吗？此操作不可恢复。`)) {
    deleteRelation(relation)
  }
}

const deleteRelation = async (relation: any) => {
  try {
    await metadataService.deleteRelationConfig(relation.relation_id)
    success('关联配置已删除')
    await loadRelations()
  } catch (err) {
    error('删除关联配置失败')
  }
}

const loadRelations = async () => {
  try {
    loading.value = true
    relations.value = await metadataService.getRelationConfigs()
  } catch (err) {
    error('加载关联配置列表失败')
  } finally {
    loading.value = false
  }
}

// Initialize
onMounted(() => {
  loadRelations()
})
</script>
