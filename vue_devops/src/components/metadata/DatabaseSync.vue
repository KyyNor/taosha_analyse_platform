<template>
  <div class="database-sync">
    <el-row :gutter="24">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>同步功能说明</span>
          </template>
          
          <div class="sync-info">
            <h4>同步功能说明：</h4>
            <ul>
              <li>自动扫描数据库中的所有表</li>
              <li>为不存在的表创建基础元数据</li>
              <li>自动添加列信息（名称、类型、是否可空）</li>
              <li>不会覆盖已有的描述信息</li>
            </ul>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>执行同步</span>
          </template>
          
          <div class="sync-action">
            <el-button
              type="primary"
              size="large"
              @click="handleSync"
              :loading="syncing"
              style="width: 100%"
            >
              <el-icon v-if="!syncing"><Refresh /></el-icon>
              {{ syncing ? '正在同步数据库元数据...' : '从数据库同步元数据' }}
            </el-button>
          </div>
          
          <!-- 同步结果 -->
          <div v-if="syncResult" class="sync-result">
            <el-divider />
            
            <div v-if="syncResult.success" class="success-result">
              <el-alert
                :title="`同步完成！${syncResult.message || ''}`"
                type="success"
                :closable="false"
                show-icon
              />
              
              <div v-if="syncResult.synced_tables && syncResult.synced_tables.length > 0" class="synced-tables">
                <h4>同步的表：</h4>
                <ul>
                  <li v-for="table in syncResult.synced_tables" :key="table">
                    {{ table }}
                  </li>
                </ul>
              </div>
            </div>
            
            <div v-else class="error-result">
              <el-alert
                :title="`同步失败：${syncResult.error || '未知错误'}`"
                type="error"
                :closable="false"
                show-icon
              />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { apiClient } from '@/api'

const syncing = ref(false)
const syncResult = ref<any>(null)

// 处理同步
const handleSync = async () => {
  try {
    syncing.value = true
    syncResult.value = null
    
    const result = await apiClient.metadata.syncFromDatabase()
    syncResult.value = result
    
    if (result.success) {
      ElMessage.success('数据库同步完成！')
      // 可以发射事件通知其他组件刷新数据
    } else {
      ElMessage.error(`同步失败：${result.error}`)
    }
  } catch (error: any) {
    ElMessage.error(`同步失败：${error.message}`)
    syncResult.value = {
      success: false,
      error: error.message
    }
  } finally {
    syncing.value = false
  }
}
</script>

<style scoped lang="scss">
.database-sync {
  .sync-info {
    h4 {
      margin: 0 0 12px 0;
      color: #303133;
    }
    
    ul {
      margin: 0;
      padding-left: 20px;
      
      li {
        margin-bottom: 8px;
        color: #606266;
        line-height: 1.5;
      }
    }
  }
  
  .sync-action {
    margin-bottom: 20px;
  }
  
  .sync-result {
    .success-result {
      .synced-tables {
        margin-top: 16px;
        
        h4 {
          margin: 0 0 12px 0;
          color: #303133;
        }
        
        ul {
          margin: 0;
          padding-left: 20px;
          
          li {
            margin-bottom: 4px;
            color: #606266;
          }
        }
      }
    }
  }
}
</style>