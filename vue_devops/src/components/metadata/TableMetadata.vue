<template>
  <div class="table-metadata">
    <el-row :gutter="24">
      <el-col :span="16">
        <!-- 现有表元数据 -->
        <el-card>
          <template #header>
            <div class="card-header">
              <span>现有表元数据</span>
              <el-button size="small" @click="refreshData">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          
          <div v-if="loading" class="loading">
            <el-skeleton :rows="3" animated />
          </div>
          
          <div v-else-if="metadataTables.length === 0" class="empty-state">
            <el-empty description="暂无表元数据，可从右侧添加或使用数据库同步功能" />
          </div>
          
          <div v-else class="tables-list">
            <el-collapse>
              <el-collapse-item
                v-for="table in metadataTables"
                :key="table.name"
                :name="table.name"
              >
                <template #title>
                  <div class="table-title">
                    <el-icon v-if="table.is_available === 0" color="#67c23a"><CircleCheck /></el-icon>
                    <el-icon v-else color="#f56c6c"><CircleClose /></el-icon>
                    <span class="table-name">{{ table.name }}</span>
                    <el-tag 
                      :type="table.is_available === 0 ? 'success' : 'danger'"
                      size="small"
                    >
                      {{ table.is_available === 0 ? '可用' : '不可用' }}
                    </el-tag>
                  </div>
                </template>
                
                <div class="table-content">
                  <div class="table-info">
                    <p><strong>描述:</strong> {{ table.comment || '无描述' }}</p>
                  </div>
                  
                  <!-- 列信息 -->
                  <div v-if="table.columns && table.columns.length > 0" class="columns-section">
                    <h4>列信息 ({{ table.columns.length }} 列)</h4>
                    <el-table :data="table.columns" stripe size="small">
                      <el-table-column prop="name" label="列名" width="120" />
                      <el-table-column prop="type" label="存储类型" width="100" />
                      <el-table-column prop="business_type" label="业务类型" width="100" />
                      <el-table-column prop="relation_id" label="关联ID" width="120" />
                      <el-table-column label="状态" width="80">
                        <template #default="{ row }">
                          <el-tag 
                            :type="row.is_available === 0 ? 'success' : 'danger'"
                            size="small"
                          >
                            {{ row.is_available === 0 ? '可用' : '不可用' }}
                          </el-tag>
                        </template>
                      </el-table-column>
                      <el-table-column prop="comment" label="描述" show-overflow-tooltip />
                    </el-table>
                    
                    <!-- 编辑列 -->
                    <el-collapse style="margin-top: 16px;">
                      <el-collapse-item title="编辑列元数据">
                        <ColumnEditor :table="table" @updated="refreshData" />
                      </el-collapse-item>
                    </el-collapse>
                  </div>
                  
                  <div v-else class="no-columns">
                    <el-empty description="该表暂无列元数据" />
                  </div>
                  
                  <!-- 表操作 -->
                  <div class="table-actions">
                    <el-row :gutter="16">
                      <el-col :span="12">
                        <TableEditor :table="table" @updated="refreshData" />
                      </el-col>
                      <el-col :span="12">
                        <AddColumn :table="table" @added="refreshData" />
                      </el-col>
                    </el-row>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <!-- 添加新表 -->
        <el-card>
          <template #header>
            <span>添加新表</span>
          </template>
          <AddTable @added="refreshData" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { apiClient } from '@/api'
import type { MetadataTable } from '@/types'
import TableEditor from './TableEditor.vue'
import ColumnEditor from './ColumnEditor.vue'
import AddTable from './AddTable.vue'
import AddColumn from './AddColumn.vue'

const loading = ref(false)
const metadataTables = ref<MetadataTable[]>([])

// 获取表元数据
const fetchMetadataTables = async () => {
  try {
    loading.value = true
    const response = await apiClient.metadata.getTables()
    metadataTables.value = response.data || []
  } catch (error: any) {
    ElMessage.error(`获取元数据失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

// 刷新数据
const refreshData = () => {
  fetchMetadataTables()
}

onMounted(() => {
  fetchMetadataTables()
})
</script>

<style scoped lang="scss">
.table-metadata {
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
  
  .tables-list {
    .table-title {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      
      .table-name {
        font-weight: 500;
        color: #303133;
        margin-right: auto;
      }
    }
    
    .table-content {
      .table-info {
        margin-bottom: 16px;
        padding: 12px;
        background: #f5f7fa;
        border-radius: 6px;
        
        p {
          margin: 0;
          color: #606266;
        }
      }
      
      .columns-section {
        margin-bottom: 20px;
        
        h4 {
          margin: 0 0 12px 0;
          color: #303133;
        }
      }
      
      .no-columns {
        margin: 20px 0;
      }
      
      .table-actions {
        margin-top: 20px;
        padding-top: 20px;
        border-top: 1px solid #ebeef5;
      }
    }
  }
}

:deep(.el-collapse-item__content) {
  padding-bottom: 16px;
}
</style>