<template>
  <div class="min-h-screen bg-slate-50">
    <!-- Page Header -->
    <section class="bg-white border-b border-slate-200 py-8">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center">
          <div class="flex items-center justify-center space-x-3 mb-4">
            <WrenchScrewdriverIcon class="w-8 h-8 text-blue-600" aria-label="工具图标" />
            <h1 class="text-3xl font-bold text-slate-800">
              元数据管理
            </h1>
          </div>
          <p class="text-xl text-slate-600 max-w-3xl mx-auto">
            管理数据表和列的元数据信息、业务术语表以及关联字段配置
          </p>
        </div>
      </div>
    </section>

    <!-- Main Content -->
    <section class="py-8">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <!-- Tab Navigation -->
        <div class="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
          <!-- Tab Headers -->
          <div class="border-b border-slate-200">
            <nav class="flex space-x-1 p-1">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                @click="activeTab = tab.id"
                :class="[
                  'flex-1 px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200',
                  activeTab === tab.id
                    ? 'bg-blue-500 text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'
                ]"
              >
                <div class="flex items-center justify-center space-x-2">
                  <component :is="tab.icon" class="w-5 h-5" />
                  <span>{{ tab.title }}</span>
                </div>
              </button>
            </nav>
          </div>

          <!-- Tab Content -->
          <div class="p-6">
            <!-- Tab 1: Table Metadata -->
            <div v-if="activeTab === 'tables'" class="space-y-6">
              <div class="text-center mb-6">
                <h2 class="text-2xl font-semibold text-slate-800 mb-2">表元数据管理</h2>
                <p class="text-slate-600">管理数据表的基本信息和列字段元数据</p>
              </div>
              <TableMetadata />
            </div>

            <!-- Tab 2: Glossary Management -->
            <div v-if="activeTab === 'glossary'" class="space-y-6">
              <div class="text-center mb-6">
                <h2 class="text-2xl font-semibold text-slate-800 mb-2">业务术语表管理</h2>
                <p class="text-slate-600">定义和管理业务术语，建立统一的数据字典</p>
              </div>
              <GlossaryManagement />
            </div>

            <!-- Tab 3: Relation Configuration -->
            <div v-if="activeTab === 'relations'" class="space-y-6">
              <div class="text-center mb-6">
                <h2 class="text-2xl font-semibold text-slate-800 mb-2">关联字段配置</h2>
                <p class="text-slate-600">配置字段关联ID，用于字段业务关联分类</p>
              </div>
              <RelationConfig />
            </div>
          </div>
        </div>
      </div>
    </section>


    <!-- Quick Stats -->
    <section class="py-8 bg-slate-100">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <div class="flex items-center justify-center space-x-2 mb-4">
            <ChartBarIcon class="w-6 h-6 text-blue-600" aria-label="图表图标" />
            <h3 class="text-lg font-semibold text-slate-800">数据概览</h3>
          </div>
          
          <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div class="text-center">
              <div class="text-2xl font-bold text-blue-600 mb-1" :class="{ 'animate-pulse': isLoadingStats }">
                {{ stats.tables }}
              </div>
              <div class="text-sm text-slate-500">数据表</div>
            </div>
            
            <div class="text-center">
              <div class="text-2xl font-bold text-green-600 mb-1" :class="{ 'animate-pulse': isLoadingStats }">
                {{ stats.columns }}
              </div>
              <div class="text-sm text-slate-500">字段列</div>
            </div>
            
            <div class="text-center">
              <div class="text-2xl font-bold text-purple-600 mb-1" :class="{ 'animate-pulse': isLoadingStats }">
                {{ stats.terms }}
              </div>
              <div class="text-sm text-slate-500">业务术语</div>
            </div>
            
            <div class="text-center">
              <div class="text-2xl font-bold text-orange-600 mb-1" :class="{ 'animate-pulse': isLoadingStats }">
                {{ stats.relations }}
              </div>
              <div class="text-sm text-slate-500">关联配置</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { 
  TableCellsIcon, 
  BookOpenIcon, 
  LinkIcon,
  WrenchScrewdriverIcon,
  ChartBarIcon
} from '@heroicons/vue/24/outline'
import { apiClient } from '@/api'
import TableMetadata from '@/components/metadata/TableMetadata.vue'
import GlossaryManagement from '@/components/metadata/GlossaryManagement.vue'
import RelationConfig from '@/components/metadata/RelationConfig.vue'

// 响应式数据
const activeTab = ref('tables')
const isLoadingStats = ref(false)

// 统计数据
const stats = ref({
  tables: 0,
  columns: 0,
  terms: 0,
  relations: 0
})

// Tab 配置
const tabs = [
  {
    id: 'tables',
    title: '表元数据',
    icon: TableCellsIcon
  },
  {
    id: 'glossary',
    title: '术语表',
    icon: BookOpenIcon
  },
  {
    id: 'relations',
    title: '关联配置',
    icon: LinkIcon
  }
]


// 加载统计数据
const loadStats = async () => {
  isLoadingStats.value = true
  
  try {
    const [tablesData, termsData, relationsData] = await Promise.all([
      apiClient.getAllMetadataTables(),
      apiClient.getAllTerms(),
      apiClient.getAllRelationConfigs()
    ])

    stats.value.tables = tablesData.length
    stats.value.columns = tablesData.reduce((total, table) => {
      return total + (table.columns?.length || 0)
    }, 0)
    stats.value.terms = termsData.length
    stats.value.relations = relationsData.length
  } catch (error) {
    console.error('加载统计数据失败:', error)
  } finally {
    isLoadingStats.value = false
  }
}

// 初始化
onMounted(() => {
  loadStats()
  
  // 监听页面可见性变化，重新加载统计数据
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      loadStats()
    }
  })
})
</script>

<style scoped>
/* Tab transition animations */
.tab-enter-active,
.tab-leave-active {
  transition: all 0.3s ease;
}

.tab-enter-from,
.tab-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

/* Custom animations */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-up {
  animation: fadeInUp 0.6s ease-out;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .grid.grid-cols-2.md\\:grid-cols-4 {
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }
}
</style>