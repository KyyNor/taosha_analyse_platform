<template>
  <div class="relation-config">
    <el-row :gutter="24">
      <el-col :span="16">
        <!-- 现有关联配置 -->
        <el-card>
          <template #header>
            <div class="card-header">
              <span>现有关联配置</span>
              <el-button size="small" @click="refreshConfigs">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          
          <div v-if="loading" class="loading">
            <el-skeleton :rows="3" animated />
          </div>
          
          <div v-else-if="configs.length === 0" class="empty-state">
            <el-empty description="暂无关联配置，可从右侧添加" />
          </div>
          
          <div v-else class="configs-list">
            <div
              v-for="config in configs"
              :key="config.relation_id"
              class="config-item"
            >
              <el-card class="config-card" shadow="hover">
                <template #header>
                  <span class="config-title">{{ config.relation_id }}</span>
                </template>
                
                <div class="config-content">
                  <p><strong>关联族:</strong> {{ config.relation_family }}</p>
                  <p><strong>关联子族:</strong> {{ config.relation_subfamily }}</p>
                  <p><strong>描述:</strong> {{ config.relation_desc || '无描述' }}</p>
                  
                  <!-- 编辑区域 -->
                  <div class="config-actions">
                    <el-button size="small" @click="editConfig(config)">编辑</el-button>
                    <el-button size="small" type="danger" @click="deleteConfig(config)">删除</el-button>
                  </div>
                </div>
              </el-card>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <!-- 添加关联配置 -->
        <el-card>
          <template #header>
            <span>{{ editingConfig ? '编辑关联配置' : '添加关联配置' }}</span>
          </template>
          <ConfigForm
            :config="editingConfig"
            @saved="handleConfigSaved"
            @cancel="editingConfig = null"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { apiClient } from '@/api'
import type { RelationConfig } from '@/types'
import ConfigForm from './ConfigForm.vue'

const loading = ref(false)
const configs = ref<RelationConfig[]>([])
const editingConfig = ref<RelationConfig | null>(null)

// 获取关联配置列表
const fetchConfigs = async () => {
  try {
    loading.value = true
    const response = await apiClient.relationConfig.getAll()
    configs.value = response.data || []
  } catch (error: any) {
    ElMessage.error(`获取关联配置失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

// 刷新配置
const refreshConfigs = () => {
  fetchConfigs()
}

// 编辑配置
const editConfig = (config: RelationConfig) => {
  editingConfig.value = { ...config }
}

// 删除配置
const deleteConfig = async (config: RelationConfig) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除关联配置 "${config.relation_id}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )
    
    await apiClient.relationConfig.delete(config.relation_id)
    ElMessage.success(`关联配置 ${config.relation_id} 已删除`)
    fetchConfigs()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(`删除失败: ${error.message}`)
    }
  }
}

// 处理配置保存
const handleConfigSaved = () => {
  editingConfig.value = null
  fetchConfigs()
}

onMounted(() => {
  fetchConfigs()
})
</script>

<style scoped lang="scss">
.relation-config {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .loading {
    padding: 20px;
  }
  
  .empty-state {
    padding: 40px 20px;
  }
  
  .configs-list {
    .config-item {
      margin-bottom: 16px;
      
      .config-card {
        .config-title {
          font-size: 16px;
          font-weight: 600;
          color: #303133;
        }
        
        .config-content {
          p {
            margin: 8px 0;
            color: #606266;
            line-height: 1.5;
          }
          
          .config-actions {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid #ebeef5;
          }
        }
      }
    }
  }
}
</style>