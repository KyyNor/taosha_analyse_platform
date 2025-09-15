<template>
  <div class="metadata-management-page">
    <div class="page-header">
      <h1 class="page-title">元数据管理</h1>
      <p class="page-description">管理数据表和列的元数据信息，以及业务术语表</p>
    </div>

    <el-tabs v-model="activeTab" class="main-tabs">
      <!-- 表元数据 -->
      <el-tab-pane label="表元数据" name="tables">
        <TableMetadata />
      </el-tab-pane>
      
      <!-- 术语表 -->
      <el-tab-pane label="术语表" name="glossary">
        <GlossaryManagement />
      </el-tab-pane>
      
      <!-- 关联配置 -->
      <el-tab-pane label="关联配置" name="relations">
        <RelationConfig />
      </el-tab-pane>
      
      <!-- 数据库同步 -->
      <el-tab-pane label="数据库同步" name="sync">
        <DatabaseSync />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import TableMetadata from '@/components/metadata/TableMetadata.vue'
import GlossaryManagement from '@/components/metadata/GlossaryManagement.vue'
import RelationConfig from '@/components/metadata/RelationConfig.vue'
import DatabaseSync from '@/components/metadata/DatabaseSync.vue'

const activeTab = ref('tables')
</script>

<style scoped lang="scss">
.metadata-management-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 32px;
  text-align: center;
  
  .page-title {
    font-size: 28px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 8px 0;
  }
  
  .page-description {
    font-size: 16px;
    color: #606266;
    margin: 0;
  }
}

.main-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 24px;
  }
  
  :deep(.el-tabs__item) {
    font-size: 16px;
    padding: 0 24px;
  }
}
</style>