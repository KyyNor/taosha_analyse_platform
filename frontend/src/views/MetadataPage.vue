<template>
  <div class="space-y-6">
    <!-- Tab Navigation -->
    <div class="tabs tabs-boxed bg-base-100">
      <a
        v-for="tab in tabs"
        :key="tab.key"
        class="tab"
        :class="{ 'tab-active': activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <component
          :is="tab.icon"
          class="w-4 h-4 mr-2"
        />
        {{ tab.label }}
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
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { metadataService } from '@services/api'

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
    icon: TableIcon
  },
  {
    key: 'columns',
    label: '字段配置',
    icon: ColumnsIcon
  },
  {
    key: 'relations',
    label: '关联配置',
    icon: RelationsIcon
  },
  {
    key: 'glossary',
    label: '业务术语',
    icon: GlossaryIcon
  },
  {
    key: 'themes',
    label: '数据主题',
    icon: ThemesIcon
  }
])

// Initialize
onMounted(() => {
})
</script>
