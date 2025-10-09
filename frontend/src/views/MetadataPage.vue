<template>
  <MainLayout>
    <div class="space-y-6">
      <!-- Page Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold">元数据配置</h1>
          <p class="text-base-content/60 mt-1">管理数据表、字段、业务术语和关联配置</p>
        </div>
        <div class="flex gap-2">
          <button
            @click="handleSyncFromDatabase"
            class="btn btn-primary"
            :disabled="syncLoading"
          >
            <span v-if="syncLoading" class="loading loading-spinner loading-sm"></span>
            {{ syncLoading ? '同步中...' : '从数据库同步' }}
          </button>
          <div class="dropdown dropdown-end">
            <label tabindex="0" class="btn btn-ghost">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              导入/导出
            </label>
            <ul tabindex="0" class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-48">
              <li><a @click="handleExport('json')">导出 JSON</a></li>
              <li><a @click="handleExport('xlsx')">导出 Excel</a></li>
              <li><a @click="showImportModal = true">导入元数据</a></li>
              <li><a @click="downloadTemplate('tables')">表配置模板</a></li>
              <li><a @click="downloadTemplate('columns')">字段配置模板</a></li>
              <li><a @click="downloadTemplate('glossary')">术语表模板</a></li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Statistics Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="stat bg-base-100 rounded-lg shadow">
          <div class="stat-figure text-primary">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
            </svg>
          </div>
          <div class="stat-title">数据表</div>
          <div class="stat-value text-primary">{{ statistics.totalTables || 0 }}</div>
          <div class="stat-desc">个活跃表</div>
        </div>

        <div class="stat bg-base-100 rounded-lg shadow">
          <div class="stat-figure text-secondary">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <div class="stat-title">字段</div>
          <div class="stat-value text-secondary">{{ statistics.totalColumns || 0 }}</div>
          <div class="stat-desc">个字段</div>
        </div>

        <div class="stat bg-base-100 rounded-lg shadow">
          <div class="stat-figure text-accent">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div class="stat-title">业务术语</div>
          <div class="stat-value text-accent">{{ statistics.totalTerms || 0 }}</div>
          <div class="stat-desc">个术语</div>
        </div>

        <div class="stat bg-base-100 rounded-lg shadow">
          <div class="stat-figure text-warning">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
          </div>
          <div class="stat-title">关联配置</div>
          <div class="stat-value text-warning">{{ statistics.totalRelations || 0 }}</div>
          <div class="stat-desc">个关联</div>
        </div>
      </div>

      <!-- Tab Navigation -->
      <div class="tabs tabs-boxed bg-base-100">
        <a
          v-for="tab in tabs"
          :key="tab.key"
          @click="activeTab = tab.key"
          class="tab"
          :class="{ 'tab-active': activeTab === tab.key }"
        >
          <component :is="tab.icon" class="w-4 h-4 mr-2" />
          {{ tab.label }}
          <span v-if="tab.count" class="badge badge-sm ml-2">{{ tab.count }}</span>
        </a>
      </div>

      <!-- Tab Content -->
      <div class="bg-base-100 rounded-lg shadow p-6">
        <!-- Tables Tab -->
        <TablesPage v-if="activeTab === 'tables'" />

        <!-- Columns Tab -->
        <ColumnsPage v-if="activeTab === 'columns'" />

        <!-- Relations Tab -->
        <RelationsPage v-if="activeTab === 'relations'" />

        <!-- Glossary Tab -->
        <GlossaryPage v-if="activeTab === 'glossary'" />

        <!-- Themes Tab -->
        <ThemesPage v-if="activeTab === 'themes'" />
      </div>
    </div>

    <!-- Import Modal -->
    <dialog ref="importModal" class="modal" :open="showImportModal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">导入元数据</h3>
        <div class="form-control mt-4">
          <label class="label">
            <span class="label-text">选择文件类型</span>
          </label>
          <select v-model="importType" class="select select-bordered">
            <option value="tables">表配置</option>
            <option value="columns">字段配置</option>
            <option value="glossary">业务术语</option>
          </select>
        </div>
        <div class="form-control mt-4">
          <label class="label">
            <span class="label-text">选择文件</span>
          </label>
          <input
            type="file"
            accept=".json,.xlsx,.xls"
            @change="handleFileSelect"
            class="file-input file-input-bordered"
          />
        </div>
        <div class="modal-action">
          <button @click="showImportModal = false" class="btn btn-ghost">取消</button>
          <button
            @click="handleImport"
            class="btn btn-primary"
            :disabled="!selectedFile || importLoading"
          >
            <span v-if="importLoading" class="loading loading-spinner loading-sm"></span>
            {{ importLoading ? '导入中...' : '导入' }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showImportModal = false">close</button>
      </form>
    </dialog>
  </MainLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { metadataService } from '@services/api'
import MainLayout from '@/components/layout/MainLayout.vue'

// Import tab components (will be created later)
import TablesPage from '@/views/metadata/TablesPage.vue'
import ColumnsPage from '@/views/metadata/ColumnsPage.vue'
import RelationsPage from '@/views/metadata/RelationsPage.vue'
import GlossaryPage from '@/views/metadata/GlossaryPage.vue'
import ThemesPage from '@/views/metadata/ThemesPage.vue'

const router = useRouter()
const { success, error, info } = useToast()

// State
const activeTab = ref('tables')
const statistics = ref({
  totalTables: 0,
  totalColumns: 0,
  totalTerms: 0,
  totalRelations: 0
})

// Import/Export state
const showImportModal = ref(false)
const importType = ref<'tables' | 'columns' | 'glossary'>('tables')
const selectedFile = ref<File | null>(null)
const importLoading = ref(false)
const syncLoading = ref(false)

// Icon components
const TableIcon = () => h('svg', {
  xmlns: 'http://www.w3.org/2000/svg',
  class: 'h-5 w-5',
  fill: 'none',
  viewBox: '0 0 24 24',
  stroke: 'currentColor'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4'
  })
])

const ColumnsIcon = () => h('svg', {
  xmlns: 'http://www.w3.org/2000/svg',
  class: 'h-5 w-5',
  fill: 'none',
  viewBox: '0 0 24 24',
  stroke: 'currentColor'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2'
  })
])

const RelationsIcon = () => h('svg', {
  xmlns: 'http://www.w3.org/2000/svg',
  class: 'h-5 w-5',
  fill: 'none',
  viewBox: '0 0 24 24',
  stroke: 'currentColor'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1'
  })
])

const GlossaryIcon = () => h('svg', {
  xmlns: 'http://www.w3.org/2000/svg',
  class: 'h-5 w-5',
  fill: 'none',
  viewBox: '0 0 24 24',
  stroke: 'currentColor'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253'
  })
])

const ThemesIcon = () => h('svg', {
  xmlns: 'http://www.w3.org/2000/svg',
  class: 'h-5 w-5',
  fill: 'none',
  viewBox: '0 0 24 24',
  stroke: 'currentColor'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01'
  })
])

// Tab configuration
const tabs = computed(() => [
  {
    key: 'tables',
    label: '表配置',
    icon: TableIcon,
    count: statistics.value.totalTables
  },
  {
    key: 'columns',
    label: '字段配置',
    icon: ColumnsIcon,
    count: statistics.value.totalColumns
  },
  {
    key: 'relations',
    label: '关联配置',
    icon: RelationsIcon,
    count: statistics.value.totalRelations
  },
  {
    key: 'glossary',
    label: '业务术语',
    icon: GlossaryIcon,
    count: statistics.value.totalTerms
  },
  {
    key: 'themes',
    label: '数据主题',
    icon: ThemesIcon
  }
])

// Load statistics
const loadStatistics = async () => {
  try {
    const stats = await metadataService.getStatistics()
    statistics.value = stats
  } catch (err) {
    console.error('Failed to load statistics:', err)
  }
}

// Handle sync from database
const handleSyncFromDatabase = async () => {
  try {
    syncLoading.value = true
    const result = await metadataService.syncFromDatabase()

    if (result.success) {
      success(result.message || '同步成功')
      await loadStatistics()
    } else {
      error(result.message || '同步失败')
    }
  } catch (err) {
    error('同步失败')
  } finally {
    syncLoading.value = false
  }
}

// Handle export
const handleExport = async (format: 'json' | 'xlsx') => {
  try {
    const blob = await metadataService.exportMetadata(format)

    // Create download link
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `metadata-${new Date().toISOString().split('T')[0]}.${format}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    success(`正在导出 ${format.toUpperCase()} 文件...`)
  } catch (err) {
    error('导出失败')
  }
}

// Download template
const downloadTemplate = async (type: 'tables' | 'columns' | 'glossary') => {
  try {
    const blob = await metadataService.getImportTemplate(type)

    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${type}-template.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    error('下载模板失败')
  }
}

// Handle file selection
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  selectedFile.value = target.files?.[0] || null
}

// Handle import
const handleImport = async () => {
  if (!selectedFile.value) return

  try {
    importLoading.value = true
    const result = await metadataService.importMetadata(selectedFile.value, importType.value)

    if (result.success) {
      success(`导入成功，已导入 ${result.importedCount} 条记录`)
      showImportModal.value = false
      selectedFile.value = null
      await loadStatistics()
    } else {
      error(result.message || '导入失败')
    }
  } catch (err) {
    error('导入失败')
  } finally {
    importLoading.value = false
  }
}

// Initialize
onMounted(() => {
  loadStatistics()
})
</script>