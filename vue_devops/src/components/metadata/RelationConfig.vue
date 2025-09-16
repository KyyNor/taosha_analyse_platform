<template>
  <div class="space-y-6">
    <!-- Add Relation Config Section -->
    <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
      <div class="flex items-center space-x-2 mb-4">
        <PlusIcon class="w-5 h-5 text-blue-600" aria-label="添加图标" />
        <h3 class="text-lg font-semibold text-slate-800">添加关联配置</h3>
      </div>
      <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
        <div class="flex items-start space-x-2">
          <InformationCircleIcon class="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div class="text-sm text-blue-800">
            <strong>关联ID格式：</strong>关联族|关联子族<br />
            <strong>示例：</strong>cust_no|17 表示客户编号的第17种变体
          </div>
        </div>
      </div>
      
      <form @submit.prevent="addRelationConfig" class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">关联族</label>
            <input
              v-model="newConfig.family"
              type="text"
              required
              placeholder="如：cust_no"
              class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">关联子族</label>
            <input
              v-model="newConfig.subfamily"
              type="text"
              required
              placeholder="如：17"
              class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
        
        <!-- Preview -->
        <div v-if="newConfig.family && newConfig.subfamily" class="bg-green-50 border border-green-200 rounded-lg p-3">
          <div class="text-sm text-green-800">
            <strong>预览关联ID：</strong>
            <span class="font-mono">{{ newConfig.family }}|{{ newConfig.subfamily }}</span>
          </div>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">描述</label>
          <textarea
            v-model="newConfig.desc"
            rows="3"
            placeholder="请输入关联字段的描述..."
            class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          ></textarea>
        </div>
        
        <button
          type="submit"
          :disabled="!newConfig.family || !newConfig.subfamily || isAdding"
          class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 hover:scale-105 hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
        >
          {{ isAdding ? '添加中...' : '添加关联配置' }}
        </button>
      </form>
    </div>

    <!-- Relation Configs List -->
    <div class="bg-white rounded-lg border border-slate-200 shadow-sm">
      <div class="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <LinkIcon class="w-5 h-5 text-blue-600" aria-label="链接图标" />
          <h3 class="text-lg font-semibold text-slate-800">关联配置管理</h3>
        </div>
        <button
          @click="refreshConfigs"
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

        <div v-else-if="configs.length === 0" class="text-center py-8">
          <div class="text-slate-500">暂无关联配置</div>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="config in configs"
            :key="config.relation_id"
            class="border border-slate-200 rounded-lg overflow-hidden"
          >
            <!-- Config Header -->
            <div class="bg-slate-50 px-4 py-3 flex items-center justify-between">
              <div class="flex items-center space-x-3">
                <div class="flex items-center space-x-2">
                  <LinkIcon class="w-4 h-4 text-blue-600" aria-label="链接图标" />
                  <h4 class="font-medium text-slate-800 font-mono">{{ config.relation_id }}</h4>
                </div>
              </div>
              
              <div class="flex items-center space-x-2">
                <button
                  @click="toggleConfigExpansion(config.relation_id)"
                  class="p-1 hover:bg-slate-200 rounded transition-colors duration-200"
                >
                  <ChevronDownIcon 
                    :class="['w-4 h-4 text-slate-500 transition-transform duration-200', 
                             expandedConfigs.has(config.relation_id) ? 'rotate-180' : '']" 
                  />
                </button>
              </div>
            </div>

            <!-- Config Details -->
            <div v-if="expandedConfigs.has(config.relation_id)" class="p-4 space-y-4">
              <!-- Display Mode -->
              <div v-if="editingConfigId !== config.relation_id" class="space-y-3">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">关联族</label>
                    <p class="text-slate-600 font-mono">{{ config.relation_family }}</p>
                  </div>
                  
                  <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">关联子族</label>
                    <p class="text-slate-600 font-mono">{{ config.relation_subfamily }}</p>
                  </div>
                  
                  <div>
                    <label class="block text-sm font-medium text-slate-700 mb-1">完整关联ID</label>
                    <p class="text-slate-600 font-mono">{{ config.relation_id }}</p>
                  </div>
                </div>
                
                <div v-if="config.relation_desc">
                  <label class="block text-sm font-medium text-slate-700 mb-1">描述</label>
                  <p class="text-slate-600">{{ config.relation_desc }}</p>
                </div>
                
                <div class="flex space-x-2 pt-2">
                  <button
                    @click="startEditConfig(config)"
                    class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors duration-200"
                  >
                    <PencilIcon class="w-4 h-4 mr-1" aria-label="编辑图标" />
                    <span>编辑</span>
                  </button>
                  <button
                    @click="confirmDeleteConfig(config.relation_id)"
                    class="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600 transition-colors duration-200"
                  >
                    <TrashIcon class="w-4 h-4 mr-1" aria-label="删除图标" />
                    <span>删除</span>
                  </button>
                </div>
              </div>

              <!-- Edit Mode -->
              <div v-else class="space-y-4">
                <RelationConfigForm
                  :config="config"
                  :is-editing="true"
                  @config-updated="handleConfigUpdated"
                  @cancel="cancelEdit"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Usage Statistics -->
    <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
      <div class="flex items-center space-x-2 mb-4">
        <ChartBarIcon class="w-5 h-5 text-blue-600" aria-label="图表图标" />
        <h3 class="text-lg font-semibold text-slate-800">使用统计</h3>
      </div>
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-blue-50 rounded-lg p-4">
          <div class="text-2xl font-bold text-blue-600">{{ configs.length }}</div>
          <div class="text-sm text-blue-700">总关联配置数</div>
        </div>
        
        <div class="bg-green-50 rounded-lg p-4">
          <div class="text-2xl font-bold text-green-600">{{ uniqueFamilies.length }}</div>
          <div class="text-sm text-green-700">不同关联族数</div>
        </div>
        
        <div class="bg-purple-50 rounded-lg p-4">
          <div class="text-2xl font-bold text-purple-600">{{ relationIdList.length }}</div>
          <div class="text-sm text-purple-700">可用关联ID数</div>
        </div>
      </div>

      <!-- Family Distribution -->
      <div class="mt-6">
        <h4 class="font-medium text-slate-800 mb-3">关联族分布</h4>
        <div class="space-y-2">
          <div
            v-for="(count, family) in familyDistribution"
            :key="family"
            class="flex items-center justify-between py-2 px-3 bg-slate-50 rounded"
          >
            <span class="font-mono text-slate-700">{{ family }}</span>
            <span class="text-slate-600">{{ count }} 个配置</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ChevronDownIcon, InformationCircleIcon, PlusIcon, LinkIcon, ArrowPathIcon, ChartBarIcon, PencilIcon, TrashIcon } from '@heroicons/vue/24/outline'
import { apiClient } from '@/api'
import type { RelationConfig } from '@/types'
import RelationConfigForm from './RelationConfigForm.vue'

// 响应式数据
const configs = ref<RelationConfig[]>([])
const relationIdList = ref<string[]>([])
const isLoading = ref(false)
const isRefreshing = ref(false)
const isAdding = ref(false)
const expandedConfigs = ref<Set<string>>(new Set())
const editingConfigId = ref<string | null>(null)

// 新配置表单
const newConfig = ref({
  family: '',
  subfamily: '',
  desc: ''
})

// 计算属性
const uniqueFamilies = computed(() => {
  const families = new Set(configs.value.map(config => config.relation_family))
  return Array.from(families)
})

const familyDistribution = computed(() => {
  const distribution: Record<string, number> = {}
  configs.value.forEach(config => {
    const family = config.relation_family
    distribution[family] = (distribution[family] || 0) + 1
  })
  return distribution
})

// 加载配置数据
const loadConfigs = async () => {
  isLoading.value = true
  try {
    const [configsData, relationIds] = await Promise.all([
      apiClient.getAllRelationConfigs(),
      apiClient.getRelationIds()
    ])
    
    configs.value = configsData
    relationIdList.value = relationIds
  } catch (error) {
    console.error('加载关联配置数据失败:', error)
  } finally {
    isLoading.value = false
  }
}

// 刷新配置数据
const refreshConfigs = async () => {
  isRefreshing.value = true
  try {
    const [configsData, relationIds] = await Promise.all([
      apiClient.getAllRelationConfigs(),
      apiClient.getRelationIds()
    ])
    
    configs.value = configsData
    relationIdList.value = relationIds
  } catch (error) {
    console.error('刷新关联配置数据失败:', error)
  } finally {
    isRefreshing.value = false
  }
}

// 添加关联配置
const addRelationConfig = async () => {
  if (!newConfig.value.family || !newConfig.value.subfamily) return
  
  isAdding.value = true
  try {
    const success = await apiClient.addRelationConfig(
      newConfig.value.family,
      newConfig.value.subfamily,
      newConfig.value.desc
    )
    
    if (success) {
      // 重置表单
      newConfig.value = {
        family: '',
        subfamily: '',
        desc: ''
      }
      
      // 刷新列表
      await refreshConfigs()
    }
  } catch (error) {
    console.error('添加关联配置失败:', error)
  } finally {
    isAdding.value = false
  }
}

// 切换配置展开状态
const toggleConfigExpansion = (configId: string) => {
  if (expandedConfigs.value.has(configId)) {
    expandedConfigs.value.delete(configId)
  } else {
    expandedConfigs.value.add(configId)
  }
}

// 开始编辑配置
const startEditConfig = (config: RelationConfig) => {
  editingConfigId.value = config.relation_id
}

// 取消编辑
const cancelEdit = () => {
  editingConfigId.value = null
}

// 处理配置更新
const handleConfigUpdated = () => {
  editingConfigId.value = null
  refreshConfigs()
}

// 删除配置确认
const confirmDeleteConfig = (configId: string) => {
  if (confirm(`确定要删除关联配置 "${configId}" 吗？此操作不可恢复。`)) {
    deleteConfig(configId)
  }
}

// 删除配置
const deleteConfig = async (configId: string) => {
  try {
    const success = await apiClient.deleteRelationConfig(configId)
    
    if (success) {
      await refreshConfigs()
    }
  } catch (error) {
    console.error('删除关联配置失败:', error)
  }
}

// 初始化
onMounted(() => {
  loadConfigs()
})
</script>