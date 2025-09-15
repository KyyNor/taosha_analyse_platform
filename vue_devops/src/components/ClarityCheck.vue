<template>
  <el-alert
    title="您的问题可能不够清晰"
    type="warning"
    :closable="false"
    class="clarity-alert"
  >
    <div class="clarity-content">
      <p v-if="details.reason" class="reason">
        <strong>原因:</strong> {{ details.reason }}
      </p>
      
      <div v-if="details.suggestions && details.suggestions.length > 0" class="suggestions">
        <h4>改进建议</h4>
        <p>请选择以下建议之一来完善您的查询：</p>
        
        <div class="suggestions-grid">
          <el-button
            v-for="(suggestion, index) in details.suggestions"
            :key="index"
            @click="handleSuggestionClick(suggestion)"
            class="suggestion-button"
            size="small"
          >
            {{ suggestion }}
          </el-button>
        </div>
        
        <!-- 建议内容展示 -->
        <el-collapse v-model="activeCollapse" class="suggestions-collapse">
          <el-collapse-item name="copy" title="复制建议内容">
            <div class="suggestion-list">
              <div
                v-for="(suggestion, index) in details.suggestions"
                :key="index"
                class="suggestion-item"
              >
                <span class="suggestion-number">{{ index + 1 }}.</span>
                <span class="suggestion-text">{{ suggestion }}</span>
                <el-button
                  size="small"
                  text
                  @click="copyToClipboard(suggestion)"
                >
                  复制
                </el-button>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </el-alert>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { ClearCheckDetails } from '@/types'

interface Props {
  details: ClearCheckDetails
}

interface Emits {
  (e: 'suggestion-selected', suggestion: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const activeCollapse = ref<string[]>([])

// 处理建议点击
const handleSuggestionClick = (suggestion: string) => {
  emit('suggestion-selected', suggestion)
}

// 复制到剪贴板
const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    // 降级方案
    const textArea = document.createElement('textarea')
    textArea.value = text
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    ElMessage.success('已复制到剪贴板')
  }
}
</script>

<style scoped lang="scss">
.clarity-alert {
  margin-bottom: 24px;
  
  .clarity-content {
    .reason {
      margin: 0 0 16px 0;
      color: #606266;
    }
    
    .suggestions {
      h4 {
        margin: 0 0 8px 0;
        font-size: 16px;
        color: #303133;
      }
      
      p {
        margin: 0 0 16px 0;
        color: #606266;
      }
      
      .suggestions-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 16px;
        
        .suggestion-button {
          flex: 1;
          min-width: 200px;
          max-width: 400px;
          text-align: left;
          white-space: normal;
          height: auto;
          padding: 12px 16px;
          line-height: 1.4;
        }
      }
      
      .suggestions-collapse {
        .suggestion-list {
          .suggestion-item {
            display: flex;
            align-items: flex-start;
            gap: 8px;
            padding: 8px 0;
            border-bottom: 1px solid #f0f2f5;
            
            &:last-child {
              border-bottom: none;
            }
            
            .suggestion-number {
              font-weight: 600;
              color: #409eff;
              min-width: 20px;
            }
            
            .suggestion-text {
              flex: 1;
              line-height: 1.5;
              color: #303133;
            }
          }
        }
      }
    }
  }
}

:deep(.el-collapse) {
  border: none;
  
  .el-collapse-item__header {
    background: transparent;
    border: none;
    font-size: 14px;
  }
  
  .el-collapse-item__content {
    padding-bottom: 0;
  }
  
  .el-collapse-item__wrap {
    border: none;
  }
}
</style>