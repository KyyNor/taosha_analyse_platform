<template>
  <div class="glossary-search-page">
    <div class="page-header">
      <h1 class="page-title">术语表搜索</h1>
      <p class="page-description">搜索和查找业务术语定义</p>
    </div>

    <!-- 搜索框 -->
    <el-card class="search-card">
      <el-input
        v-model="searchQuery"
        size="large"
        placeholder="输入要搜索的术语或别名，例如：销售额、收入"
        clearable
        @input="handleSearch"
      >
        <template #prepend>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </el-card>

    <!-- 搜索结果提示 -->
    <div v-if="searchQuery && filteredTerms.length !== allTerms.length" class="search-info">
      <el-alert
        :title="`找到 ${filteredTerms.length} 个匹配的术语`"
        type="info"
        :closable="false"
        show-icon
      />
    </div>

    <!-- 术语列表 -->
    <el-card class="terms-card">
      <template #header>
        <div class="card-header">
          <span>{{ searchQuery ? '搜索结果' : '所有术语' }} ({{ filteredTerms.length }})</span>
          <el-button size="small" @click="refreshTerms">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <div v-if="loading" class="loading">
        <el-skeleton :rows="3" animated />
      </div>
      
      <div v-else-if="filteredTerms.length === 0" class="empty-state">
        <el-empty :description="searchQuery ? '未找到匹配的术语' : '暂无术语数据'" />
      </div>
      
      <div v-else class="terms-list">
        <el-row :gutter="16">
          <el-col 
            v-for="term in filteredTerms" 
            :key="term.id"
            :span="12"
            class="term-col"
          >
            <el-card class="term-card" shadow="hover">
              <template #header>
                <div class="term-header">
                  <span class="term-name">{{ term.term }}</span>
                  <el-tag v-if="term.category" size="small">
                    {{ term.category }}
                  </el-tag>
                </div>
              </template>
              
              <div class="term-content">
                <div v-if="term.definition" class="term-definition">
                  <h4>定义</h4>
                  <p>{{ term.definition }}</p>
                </div>
                
                <div v-if="term.sql_expression" class="term-sql">
                  <h4>SQL表达式</h4>
                  <el-input
                    :value="term.sql_expression"
                    type="textarea"
                    :rows="3"
                    readonly
                    class="sql-textarea"
                  />
                </div>
                
                <div v-if="term.aliases && term.aliases.length > 0" class="term-aliases">
                  <h4>别名</h4>
                  <div class="aliases-list">
                    <el-tag
                      v-for="alias in term.aliases"
                      :key="alias"
                      size="small"
                      class="alias-tag"
                    >
                      {{ alias }}
                    </el-tag>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { apiClient } from '@/api'
import type { GlossaryTerm } from '@/types'

const loading = ref(false)
const searchQuery = ref('')
const allTerms = ref<GlossaryTerm[]>([])

// 过滤后的术语
const filteredTerms = computed(() => {
  if (!searchQuery.value.trim()) {
    return allTerms.value
  }
  
  const query = searchQuery.value.toLowerCase()
  return allTerms.value.filter(term => {
    // 搜索术语名称
    if (term.term.toLowerCase().includes(query)) {
      return true
    }
    
    // 搜索定义
    if (term.definition && term.definition.toLowerCase().includes(query)) {
      return true
    }
    
    // 搜索分类
    if (term.category && term.category.toLowerCase().includes(query)) {
      return true
    }
    
    // 搜索别名
    if (term.aliases && term.aliases.some(alias => 
      alias.toLowerCase().includes(query)
    )) {
      return true
    }
    
    return false
  })
})

// 获取术语列表
const fetchTerms = async () => {
  try {
    loading.value = true
    const response = await apiClient.glossary.getTerms()
    allTerms.value = response.data || []
  } catch (error: any) {
    ElMessage.error(`获取术语失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  // 实时搜索，通过computed自动过滤
}

// 刷新术语
const refreshTerms = () => {
  fetchTerms()
}

onMounted(() => {
  fetchTerms()
})
</script>

<style scoped lang="scss">
.glossary-search-page {
  max-width: 1200px;
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

.search-card {
  margin-bottom: 24px;
}

.search-info {
  margin-bottom: 16px;
}

.terms-card {
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
  
  .terms-list {
    .term-col {
      margin-bottom: 16px;
    }
    
    .term-card {
      height: 100%;
      
      .term-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        
        .term-name {
          font-size: 16px;
          font-weight: 600;
          color: #303133;
        }
      }
      
      .term-content {
        h4 {
          margin: 0 0 8px 0;
          font-size: 14px;
          color: #409eff;
        }
        
        .term-definition {
          margin-bottom: 16px;
          
          p {
            margin: 0;
            color: #606266;
            line-height: 1.5;
          }
        }
        
        .term-sql {
          margin-bottom: 16px;
          
          .sql-textarea {
            :deep(.el-textarea__inner) {
              font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
              font-size: 12px;
              background: #f8f9fa;
            }
          }
        }
        
        .term-aliases {
          .aliases-list {
            .alias-tag {
              margin-right: 8px;
              margin-bottom: 4px;
            }
          }
        }
      }
    }
  }
}
</style>