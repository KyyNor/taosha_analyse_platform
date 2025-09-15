<template>
  <div class="app-container">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="280px" class="sidebar">
        <div class="sidebar-header">
          <h2 class="app-title">淘沙分析平台</h2>
        </div>
        
        <!-- 导航菜单 -->
        <el-menu
          :default-active="$route.path"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/query">
            <el-icon><Search /></el-icon>
            <span>数据查询</span>
          </el-menu-item>
          <el-menu-item index="/metadata">
            <el-icon><Setting /></el-icon>
            <span>元数据管理</span>
          </el-menu-item>
          <el-menu-item index="/glossary">
            <el-icon><Document /></el-icon>
            <span>术语搜索</span>
          </el-menu-item>
        </el-menu>
        
        <!-- 系统状态 -->
        <div class="system-status">
          <el-divider />
          
          <!-- 健康状态 -->
          <div class="status-item">
            <el-tag 
              :type="appStore.isBackendHealthy ? 'success' : 'danger'"
              size="small"
            >
              {{ appStore.isBackendHealthy ? '后端服务正常' : '后端服务异常' }}
            </el-tag>
          </div>
          
          <!-- 系统信息 -->
          <el-collapse v-if="appStore.systemStatus" accordion>
            <el-collapse-item name="system" title="系统状态">
              <div class="status-details">
                <p><strong>应用:</strong> {{ appStore.systemStatus.app_name }}</p>
                <p><strong>版本:</strong> {{ appStore.systemStatus.version }}</p>
                <p><strong>数据库类型:</strong> {{ appStore.systemStatus.database?.database_type }}</p>
                <p><strong>表数量:</strong> {{ appStore.systemStatus.database?.total_tables }}</p>
              </div>
            </el-collapse-item>
          </el-collapse>
          
          <!-- 数据表信息 -->
          <el-collapse v-if="appStore.hasData" accordion>
            <el-collapse-item name="tables" title="数据表">
              <div class="tables-list">
                <div
                  v-for="table in appStore.tables"
                  :key="table.table_name"
                  class="table-item"
                >
                  <p class="table-name">{{ table.table_name }}</p>
                  <p v-if="table.comment" class="table-comment">{{ table.comment }}</p>
                  <p class="table-rows">行数: {{ table.row_count }}</p>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-aside>
      
      <!-- 主内容区 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { Search, Setting, Document } from '@element-plus/icons-vue'

const appStore = useAppStore()

onMounted(() => {
  appStore.init()
})
</script>

<style scoped lang="scss">
.app-container {
  min-height: 100vh;
}

.sidebar {
  background: #ffffff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  
  .sidebar-header {
    padding: 24px 20px;
    border-bottom: 1px solid #e4e7ed;
    
    .app-title {
      font-size: 20px;
      font-weight: 600;
      color: #303133;
      margin: 0;
    }
  }
  
  .sidebar-menu {
    border: none;
    flex: 1;
    
    .el-menu-item {
      height: 50px;
      line-height: 50px;
      margin: 4px 16px;
      border-radius: 8px;
      
      &.is-active {
        background-color: #ecf5ff;
        color: #409eff;
        
        &::before {
          display: none;
        }
      }
      
      &:hover {
        background-color: #f5f7fa;
      }
    }
  }
  
  .system-status {
    padding: 16px;
    margin-top: auto;
    
    .status-item {
      margin-bottom: 12px;
    }
    
    .status-details {
      font-size: 12px;
      color: #606266;
      
      p {
        margin: 8px 0;
      }
    }
    
    .tables-list {
      max-height: 200px;
      overflow-y: auto;
      
      .table-item {
        padding: 8px;
        margin-bottom: 8px;
        background: #f5f7fa;
        border-radius: 6px;
        
        .table-name {
          font-weight: 600;
          font-size: 13px;
          color: #303133;
          margin: 0 0 4px 0;
        }
        
        .table-comment {
          font-size: 12px;
          color: #909399;
          font-style: italic;
          margin: 0 0 4px 0;
        }
        
        .table-rows {
          font-size: 12px;
          color: #606266;
          margin: 0;
        }
      }
    }
  }
}

.main-content {
  padding: 24px;
  background: #f5f7fa;
}

:deep(.el-collapse) {
  border: none;
  
  .el-collapse-item__header {
    height: 40px;
    line-height: 40px;
    font-size: 13px;
    background: transparent;
    border: none;
    padding-left: 0;
  }
  
  .el-collapse-item__content {
    padding-bottom: 12px;
  }
  
  .el-collapse-item__wrap {
    border: none;
  }
}
</style>