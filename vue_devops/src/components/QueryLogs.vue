<template>
  <el-card class="query-logs-card">
    <template #header>
      <div class="card-header">
        <span>查询执行日志</span>
        <el-button size="small" text @click="expanded = !expanded">
          {{ expanded ? '收起' : '展开' }}
        </el-button>
      </div>
    </template>
    
    <el-collapse v-model="activeNames" v-show="expanded">
      <el-collapse-item
        v-for="(log, index) in logs"
        :key="index"
        :name="index.toString()"
      >
        <template #title>
          <div class="log-title">
            <el-icon v-if="log.success" color="#67c23a"><CircleCheck /></el-icon>
            <el-icon v-else color="#f56c6c"><CircleClose /></el-icon>
            <span class="step-name">{{ index + 1 }}. {{ log.step }}</span>
            <span v-if="log.timestamp" class="timestamp">{{ log.timestamp }}</span>
          </div>
        </template>
        
        <div class="log-content">
          <el-row :gutter="16">
            <el-col :span="12" v-if="log.input_data">
              <h4>输入数据</h4>
              <el-input
                v-model="log.input_data"
                type="textarea"
                :rows="5"
                readonly
                class="log-textarea"
              />
            </el-col>
            
            <el-col :span="12" v-if="log.model_output">
              <h4>模型输出</h4>
              <el-input
                v-model="log.model_output"
                type="textarea"
                :rows="5"
                readonly
                class="log-textarea"
              />
            </el-col>
            
            <el-col :span="24" v-if="log.error">
              <el-alert
                :title="`错误: ${log.error}`"
                type="error"
                :closable="false"
                show-icon
              />
            </el-col>
            
            <el-col :span="24" v-if="log.prompt">
              <el-collapse>
                <el-collapse-item :title="`查看提示词 - ${log.step}`">
                  <div class="prompt-content">
                    <pre>{{ log.prompt }}</pre>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </el-col>
          </el-row>
        </div>
      </el-collapse-item>
    </el-collapse>
  </el-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { CircleCheck, CircleClose } from '@element-plus/icons-vue'
import type { QueryLog } from '@/types'

interface Props {
  logs: QueryLog[]
}

const props = defineProps<Props>()

const expanded = ref(false)
const activeNames = ref<string[]>([])
</script>

<style scoped lang="scss">
.query-logs-card {
  margin-top: 24px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .log-title {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    
    .step-name {
      font-weight: 500;
      color: #303133;
    }
    
    .timestamp {
      margin-left: auto;
      font-size: 12px;
      color: #909399;
    }
  }
  
  .log-content {
    h4 {
      margin: 0 0 12px 0;
      font-size: 14px;
      color: #303133;
    }
    
    .log-textarea {
      margin-bottom: 16px;
      
      :deep(.el-textarea__inner) {
        font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
        font-size: 12px;
        line-height: 1.4;
        background: #f8f9fa;
      }
    }
    
    .prompt-content {
      pre {
        font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
        font-size: 12px;
        line-height: 1.4;
        background: #f8f9fa;
        padding: 16px;
        border-radius: 6px;
        overflow-x: auto;
        white-space: pre-wrap;
        word-wrap: break-word;
      }
    }
  }
}

:deep(.el-collapse-item__content) {
  padding-bottom: 16px;
}
</style>