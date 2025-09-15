<template>
  <div class="data-query-page">
    <div class="page-header">
      <h1 class="page-title">淘沙数据分析助手</h1>
      <p class="page-description">使用自然语言查询您的数据，获得即时的分析结果</p>
    </div>

    <!-- 查询输入区域 -->
    <el-card class="query-card">
      <div class="query-input-area">
        <el-row :gutter="16">
          <el-col :span="18">
            <el-input
              v-model="queryInput"
              placeholder="例如：显示北京地区本月的销售额，最近一周电子产品销量统计"
              size="large"
              clearable
              @keyup.enter="handleQuery"
            >
              <template #prepend>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="3">
            <el-select v-model="maxRetries" placeholder="重试次数" size="large">
              <el-option label="0次" :value="0" />
              <el-option label="1次" :value="1" />
              <el-option label="2次" :value="2" />
              <el-option label="3次" :value="3" />
            </el-select>
          </el-col>
          <el-col :span="3">
            <el-button
              type="primary"
              size="large"
              :loading="querying"
              @click="handleQuery"
              style="width: 100%"
            >
              查询
            </el-button>
          </el-col>
        </el-row>
      </div>
    </el-card>

    <!-- 示例查询 -->
    <el-card class="examples-card">
      <template #header>
        <span>示例查询</span>
      </template>
      <div class="examples-grid">
        <el-tag
          v-for="example in exampleQueries"
          :key="example"
          class="example-tag"
          @click="queryInput = example"
        >
          {{ example }}
        </el-tag>
      </div>
    </el-card>

    <!-- 输入清晰度提示 -->
    <ClarityCheck
      v-if="clarityDetails && !clarityDetails.is_clear"
      :details="clarityDetails"
      @suggestion-selected="handleSuggestionSelected"
    />

    <!-- 查询结果 -->
    <div v-if="queryResult" class="result-section">
      <ResultDisplay :result="queryResult" />
    </div>

    <!-- 查询历史 -->
    <el-card v-if="appStore.chatHistory.length > 0" class="history-card">
      <template #header>
        <div class="card-header">
          <span>查询历史</span>
          <el-button size="small" text @click="appStore.clearChatHistory">
            清空历史
          </el-button>
        </div>
      </template>
      <div class="history-list">
        <div
          v-for="(entry, index) in appStore.chatHistory.slice().reverse()"
          :key="index"
          class="history-item"
        >
          <el-row :gutter="16" align="middle">
            <el-col :span="12">
              <div class="history-query">
                <el-icon v-if="entry.success" color="#67c23a"><CircleCheck /></el-icon>
                <el-icon v-else color="#f56c6c"><CircleClose /></el-icon>
                <span class="query-text">{{ entry.query }}</span>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="history-time">
                {{ formatTime(entry.timestamp) }}
              </div>
            </el-col>
            <el-col :span="6">
              <div class="history-actions">
                <el-button size="small" @click="queryInput = entry.query">
                  重新查询
                </el-button>
              </div>
            </el-col>
          </el-row>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'
import { apiClient } from '@/api'
import type { QueryResult, ClearCheckDetails } from '@/types'
import ResultDisplay from '@/components/ResultDisplay.vue'
import ClarityCheck from '@/components/ClarityCheck.vue'

const appStore = useAppStore()

// 响应式数据
const queryInput = ref('')
const maxRetries = ref(2)
const querying = ref(false)
const queryResult = ref<QueryResult | null>(null)
const clarityDetails = ref<ClearCheckDetails | null>(null)

// 示例查询
const exampleQueries = [
  '显示所有销售数据',
  '北京地区的销售额是多少？',
  '按产品类别统计销售量',
  '哪个客户购买最多？',
  '今年的总销售额',
  '电子产品的平均价格'
]

// 处理查询
const handleQuery = async () => {
  if (!queryInput.value.trim()) {
    ElMessage.warning('请输入查询内容')
    return
  }

  querying.value = true
  queryResult.value = null
  clarityDetails.value = null

  try {
    const startTime = Date.now()
    const result = await apiClient.query({
      query: queryInput.value,
      max_retries: maxRetries.value
    })
    const endTime = Date.now()

    queryResult.value = result
    clarityDetails.value = result.clear_check_details || null

    // 添加到历史记录
    appStore.addChatHistory({
      query: queryInput.value,
      timestamp: Date.now(),
      success: result.success,
      sql: result.sql_query || '',
      data_count: result.data?.length || 0
    })

    if (result.success) {
      ElMessage.success(`查询成功！耗时: ${((endTime - startTime) / 1000).toFixed(2)}秒`)
    } else {
      ElMessage.error(`查询失败: ${result.error}`)
    }
  } catch (error: any) {
    ElMessage.error(`查询失败: ${error.message}`)
  } finally {
    querying.value = false
  }
}

// 处理建议选择
const handleSuggestionSelected = (suggestion: string) => {
  queryInput.value = suggestion
  clarityDetails.value = null
}

// 格式化时间
const formatTime = (timestamp: number) => {
  return new Date(timestamp).toLocaleTimeString()
}
</script>

<style scoped lang="scss">
.data-query-page {
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

.query-card {
  margin-bottom: 24px;
  
  .query-input-area {
    .el-input {
      :deep(.el-input-group__prepend) {
        background: #f5f7fa;
        border-color: #dcdfe6;
      }
    }
  }
}

.examples-card {
  margin-bottom: 24px;
  
  .examples-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    
    .example-tag {
      cursor: pointer;
      padding: 8px 16px;
      border-radius: 16px;
      transition: all 0.2s;
      
      &:hover {
        background: #409eff;
        color: white;
      }
    }
  }
}

.result-section {
  margin-bottom: 24px;
}

.history-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .history-list {
    .history-item {
      padding: 12px 0;
      border-bottom: 1px solid #f0f2f5;
      
      &:last-child {
        border-bottom: none;
      }
      
      .history-query {
        display: flex;
        align-items: center;
        gap: 8px;
        
        .query-text {
          flex: 1;
          color: #303133;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
      
      .history-time {
        color: #909399;
        font-size: 12px;
      }
      
      .history-actions {
        text-align: right;
      }
    }
  }
}
</style>