<template>
  <div class="space-y-6">
    <!-- 搜索和操作栏 -->
    <div class="card bg-base-100 shadow-md">
      <div class="card-body">
        <div class="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <!-- 搜索区域 -->
          <div class="flex flex-col sm:flex-row gap-2 flex-1">
            <div class="form-control">
              <div class="input-group">
                <input 
                  v-model="searchParams.keyword"
                  type="text" 
                  placeholder="搜索表名..." 
                  class="input input-bordered w-full max-w-xs"
                  @keyup.enter="loadTables"
                />
                <button @click="loadTables" class="btn btn-square">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                  </svg>
                </button>
              </div>
            </div>
            
            <select v-model="searchParams.data_source" @change="loadTables" class="select select-bordered">
              <option value="">所有数据源</option>
              <option value="main_db">主数据库</option>
              <option value="warehouse">数据仓库</option>
              <option value="analytics">分析库</option>
            </select>
            
            <select v-model="searchParams.is_active" @change="loadTables" class="select select-bordered">
              <option value="">所有状态</option>
              <option :value="true">启用</option>
              <option :value="false">禁用</option>
            </select>
          </div>

          <!-- 操作按钮 -->
          <div class="flex gap-2">
            <button @click="showCreateDialog = true" class="btn btn-primary">
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
              </svg>
              新增表
            </button>
            <button @click="importTables" class="btn btn-outline">
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"></path>
              </svg>
              导入
            </button>
            <button @click="syncTables" class="btn btn-outline">
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
              </svg>
              同步结构
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 表格区域 -->
    <div class="card bg-base-100 shadow-md">
      <div class="card-body">
        <div class="overflow-x-auto">
          <table class="table table-zebra table-hover w-full">
            <thead>
              <tr>
                <th>中文名称</th>
                <th>英文名称</th>
                <th>数据源</th>
                <th>更新方式</th>
                <th>字段数</th>
                <th>主题</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="table in tables" :key="table.id">
                <td>
                  <div class="font-semibold">{{ table.table_name_cn }}</div>
                  <div class="text-sm text-base-content text-opacity-70">
                    {{ table.table_description }}
                  </div>
                </td>
                <td>
                  <code class="text-sm bg-base-200 px-2 py-1 rounded">{{ table.table_name_en }}</code>
                </td>
                <td>
                  <span class="badge badge-outline">{{ table.data_source || '未设置' }}</span>
                </td>
                <td>
                  <span class="badge" :class="getUpdateMethodClass(table.update_method)">
                    {{ getUpdateMethodText(table.update_method) }}
                  </span>
                </td>
                <td>
                  <span class="text-sm">{{ table.field_count || 0 }} 个</span>
                </td>
                <td>
                  <div class="flex flex-wrap gap-1">
                    <span 
                      v-for="theme in table.themes" 
                      :key="theme.id"
                      class="badge badge-sm"
                      :class="theme.is_public ? 'badge-success' : 'badge-info'"
                    >
                      {{ theme.theme_name }}
                    </span>
                  </div>
                </td>
                <td>
                  <div class="form-control">
                    <label class="cursor-pointer label">
                      <input 
                        :checked="table.is_active"
                        @change="toggleTableStatus(table)"
                        type="checkbox" 
                        class="toggle toggle-success toggle-sm"
                      />
                    </label>
                  </div>
                </td>
                <td class="text-sm">{{ formatDate(table.created_at) }}</td>
                <td>
                  <div class="dropdown dropdown-end">
                    <label tabindex="0" class="btn btn-ghost btn-sm">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"></path>
                      </svg>
                    </label>
                    <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52">
                      <li><a @click="viewTable(table)">查看详情</a></li>
                      <li><a @click="editTable(table)">编辑</a></li>
                      <li><a @click="manageFields(table)">管理字段</a></li>
                      <li><a @click="viewRelations(table)">查看关联</a></li>
                      <li><hr class="my-1"></li>
                      <li><a @click="deleteTable(table)" class="text-error">删除</a></li>
                    </ul>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          
          <!-- 空状态 -->
          <div v-if="tables.length === 0 && !loading" class="text-center py-12">
            <svg class="w-12 h-12 mx-auto text-base-content text-opacity-30 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
            </svg>
            <p class="text-base-content text-opacity-50">暂无数据表</p>
            <button @click="showCreateDialog = true" class="btn btn-primary btn-sm mt-4">创建第一个表</button>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="pagination.total > 0" class="flex justify-between items-center mt-6">
          <div class="text-sm text-base-content text-opacity-70">
            共 {{ pagination.total }} 条记录，第 {{ pagination.page }} / {{ pagination.pages }} 页
          </div>
          <div class="btn-group">
            <button 
              @click="changePage(pagination.page - 1)"
              :disabled="pagination.page <= 1"
              class="btn btn-sm"
            >
              上一页
            </button>
            <button class="btn btn-sm btn-active">{{ pagination.page }}</button>
            <button 
              @click="changePage(pagination.page + 1)"
              :disabled="pagination.page >= pagination.pages"
              class="btn btn-sm"
            >
              下一页
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑表对话框 -->
    <dialog :class="{ 'modal-open': showCreateDialog || showEditDialog }" class="modal">
      <div class="modal-box w-11/12 max-w-2xl">
        <h3 class="font-bold text-lg mb-4">
          {{ editingTable ? '编辑表' : '新增表' }}
        </h3>
        
        <form @submit.prevent="saveTable" class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="form-control">
              <label class="label">
                <span class="label-text">中文名称 *</span>
              </label>
              <input 
                v-model="tableForm.table_name_cn"
                type="text" 
                class="input input-bordered" 
                required
              />
            </div>
            
            <div class="form-control">
              <label class="label">
                <span class="label-text">英文名称 *</span>
              </label>
              <input 
                v-model="tableForm.table_name_en"
                type="text" 
                class="input input-bordered" 
                required
              />
            </div>
            
            <div class="form-control">
              <label class="label">
                <span class="label-text">数据源</span>
              </label>
              <select v-model="tableForm.data_source" class="select select-bordered">
                <option value="">请选择...</option>
                <option value="main_db">主数据库</option>
                <option value="warehouse">数据仓库</option>
                <option value="analytics">分析库</option>
              </select>
            </div>
            
            <div class="form-control">
              <label class="label">
                <span class="label-text">更新方式</span>
              </label>
              <select v-model="tableForm.update_method" class="select select-bordered">
                <option value="real_time">实时</option>
                <option value="daily">天级</option>
                <option value="weekly">周级</option>
                <option value="monthly">月级</option>
                <option value="manual">手动</option>
              </select>
            </div>
          </div>
          
          <div class="form-control">
            <label class="label">
              <span class="label-text">表描述</span>
            </label>
            <textarea 
              v-model="tableForm.table_description"
              class="textarea textarea-bordered h-20"
              placeholder="描述这个表的用途和内容..."
            ></textarea>
          </div>
          
          <div class="form-control">
            <label class="label">
              <span class="label-text">关联主题</span>
            </label>
            <div class="flex flex-wrap gap-2">
              <label 
                v-for="theme in availableThemes" 
                :key="theme.id"
                class="cursor-pointer label"
              >
                <input 
                  v-model="tableForm.theme_ids" 
                  :value="theme.id" 
                  type="checkbox" 
                  class="checkbox checkbox-primary checkbox-sm"
                />
                <span class="label-text ml-2">{{ theme.theme_name }}</span>
              </label>
            </div>
          </div>
          
          <div class="modal-action">
            <button type="button" @click="closeDialog" class="btn btn-ghost">取消</button>
            <button type="submit" class="btn btn-primary">保存</button>
          </div>
        </form>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="closeDialog">关闭</button>
      </form>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useNotificationStore } from '@/stores/notification'

const notificationStore = useNotificationStore()

// 响应式数据
const loading = ref(false)
const tables = ref([])
const pagination = ref({
  total: 0,
  page: 1,
  size: 20,
  pages: 0
})

const searchParams = reactive({
  keyword: '',
  data_source: '',
  is_active: ''
})

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingTable = ref(null)

const tableForm = reactive({
  table_name_cn: '',
  table_name_en: '',
  data_source: '',
  update_method: 'daily',
  table_description: '',
  theme_ids: []
})

const availableThemes = ref([
  { id: 1, theme_name: '销售数据' },
  { id: 2, theme_name: '用户数据' },
  { id: 3, theme_name: '公共数据' }
])

// 模拟数据
const mockTables = [
  {
    id: 1,
    table_name_cn: '用户表',
    table_name_en: 'users',
    data_source: 'main_db',
    update_method: 'daily',
    table_description: '系统用户基本信息',
    field_count: 12,
    themes: [{ id: 2, theme_name: '用户数据', is_public: false }],
    is_active: true,
    created_at: '2024-01-15T08:30:00Z'
  },
  {
    id: 2,
    table_name_cn: '订单表',
    table_name_en: 'orders',
    data_source: 'main_db',
    update_method: 'real_time',
    table_description: '用户订单交易记录',
    field_count: 18,
    themes: [{ id: 1, theme_name: '销售数据', is_public: false }],
    is_active: true,
    created_at: '2024-01-20T10:15:00Z'
  }
]

// 方法
const loadTables = async () => {
  loading.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    tables.value = mockTables
    pagination.value = {
      total: mockTables.length,
      page: 1,
      size: 20,
      pages: 1
    }
  } catch (error) {
    notificationStore.error('加载表列表失败')
  } finally {
    loading.value = false
  }
}

const changePage = (page: number) => {
  pagination.value.page = page
  loadTables()
}

const getUpdateMethodText = (method: string) => {
  const map = {
    'real_time': '实时',
    'daily': '天级',
    'weekly': '周级', 
    'monthly': '月级',
    'manual': '手动'
  }
  return map[method] || method
}

const getUpdateMethodClass = (method: string) => {
  const map = {
    'real_time': 'badge-success',
    'daily': 'badge-primary',
    'weekly': 'badge-info',
    'monthly': 'badge-warning',
    'manual': 'badge-ghost'
  }
  return map[method] || 'badge-ghost'
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const editTable = (table: any) => {
  editingTable.value = table
  Object.assign(tableForm, {
    table_name_cn: table.table_name_cn,
    table_name_en: table.table_name_en,
    data_source: table.data_source,
    update_method: table.update_method,
    table_description: table.table_description,
    theme_ids: table.themes.map(t => t.id)
  })
  showEditDialog.value = true
}

const deleteTable = (table: any) => {
  if (confirm(`确定要删除表 "${table.table_name_cn}" 吗？`)) {
    notificationStore.success('表删除成功')
    loadTables()
  }
}

const toggleTableStatus = (table: any) => {
  table.is_active = !table.is_active
  notificationStore.success(`表状态已${table.is_active ? '启用' : '禁用'}`)
}

const saveTable = async () => {
  try {
    // 模拟保存
    await new Promise(resolve => setTimeout(resolve, 500))
    notificationStore.success(editingTable.value ? '表更新成功' : '表创建成功')
    closeDialog()
    loadTables()
  } catch (error) {
    notificationStore.error('保存失败')
  }
}

const closeDialog = () => {
  showCreateDialog.value = false
  showEditDialog.value = false
  editingTable.value = null
  Object.assign(tableForm, {
    table_name_cn: '',
    table_name_en: '',
    data_source: '',
    update_method: 'daily',
    table_description: '',
    theme_ids: []
  })
}

const viewTable = (table: any) => {
  notificationStore.info('查看详情功能开发中...')
}

const manageFields = (table: any) => {
  notificationStore.info('字段管理功能开发中...')
}

const viewRelations = (table: any) => {
  notificationStore.info('关联关系功能开发中...')
}

const importTables = () => {
  notificationStore.info('导入功能开发中...')
}

const syncTables = () => {
  notificationStore.info('同步结构功能开发中...')
}

onMounted(() => {
  loadTables()
})
</script>