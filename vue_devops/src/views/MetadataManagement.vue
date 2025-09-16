<template>
  <div class="min-h-screen bg-slate-50">
    <!-- Page Header -->
    <section class="bg-white border-b border-slate-200 py-8">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center">
          <h1 class="text-3xl font-bold text-slate-800 mb-4">
            🛠️ 元数据管理
          </h1>
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

    <!-- Features Overview -->
    <section class="py-16 bg-white">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-12">
          <h2 class="text-3xl font-bold text-slate-800 mb-4">
            元数据管理功能
          </h2>
          <p class="text-xl text-slate-600 max-w-3xl mx-auto">
            完善的元数据管理体系，为数据分析和查询提供强大支撑
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div 
            v-for="feature in features"
            :key="feature.title"
            class="bg-slate-50 rounded-xl p-8 border border-slate-200 hover:-translate-y-1 transition-all duration-300 hover:shadow-md"
          >
            <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-6">
              <component :is="feature.icon" class="w-6 h-6 text-blue-600" />
            </div>
            <h3 class="text-xl font-semibold text-slate-800 mb-3">{{ feature.title }}</h3>
            <p class="text-slate-600 leading-relaxed mb-4">{{ feature.description }}</p>
            <ul class="text-sm text-slate-500 space-y-1">
              <li v-for="item in feature.items" :key="item" class="flex items-start space-x-2">
                <CheckIcon class="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span>{{ item }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- Quick Stats -->
    <section class="py-8 bg-slate-100">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h3 class="text-lg font-semibold text-slate-800 mb-4 text-center">📊 数据概览</h3>
          
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
  CheckIcon,
  CubeIcon,
  DocumentTextIcon,
  CogIcon
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

// 功能特性
const features = [
  {
    title: '表结构管理',
    description: '完整的数据表和字段元数据管理，支持业务类型和关联关系配置',
    icon: CubeIcon,
    items: [
      '表和列的基本信息维护',
      '业务类型字段分类',
      '字段可用性状态管理',
      '关联ID配置支持'
    ]
  },
  {
    title: '术语字典',
    description: '统一的业务术语定义和管理，建立标准化的数据语言',
    icon: DocumentTextIcon,
    items: [
      '术语定义和分类',
      'SQL表达式关联',
      '别名和同义词支持',
      '术语搜索和检索'
    ]
  },
  {
    title: '关联配置',
    description: '灵活的字段关联配置，支持复杂的数据关系映射',
    icon: CogIcon,
    items: [
      '关联族和子族管理',
      '关联ID自动生成',
      '配置使用统计',
      '关联关系可视化'
    ]
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