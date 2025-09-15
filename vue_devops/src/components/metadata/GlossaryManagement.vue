<template>
  <div class="glossary-management">
    <el-row :gutter="24">
      <el-col :span="16">
        <!-- 现有术语 -->
        <el-card>
          <template #header>
            <div class="card-header">
              <span>现有术语</span>
              <el-button size="small" @click="refreshTerms">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          
          <div v-if="loading" class="loading">
            <el-skeleton :rows="3" animated />
          </div>
          
          <div v-else-if="terms.length === 0" class="empty-state">
            <el-empty description="暂无业务术语，可从右侧添加" />
          </div>
          
          <div v-else class="terms-list">
            <div
              v-for="term in terms"
              :key="term.id"
              class="term-item"
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
                  <p><strong>定义:</strong> {{ term.definition || '无定义' }}</p>
                  <p v-if="term.sql_expression"><strong>SQL表达式:</strong> {{ term.sql_expression }}</p>
                  <p v-if="term.aliases && term.aliases.length > 0">
                    <strong>别名:</strong> {{ term.aliases.join(', ') }}
                  </p>
                  
                  <!-- 编辑区域 -->
                  <div class="term-actions">
                    <el-button size="small" @click="editTerm(term)">编辑</el-button>
                    <el-button size="small" type="danger" @click="deleteTerm(term)">删除</el-button>
                  </div>
                </div>
              </el-card>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <!-- 添加新术语 -->
        <el-card>
          <template #header>
            <span>{{ editingTerm ? '编辑术语' : '添加新术语' }}</span>
          </template>
          <TermForm
            :term="editingTerm"
            @saved="handleTermSaved"
            @cancel="editingTerm = null"
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
import type { GlossaryTerm } from '@/types'
import TermForm from './TermForm.vue'

const loading = ref(false)
const terms = ref<GlossaryTerm[]>([])
const editingTerm = ref<GlossaryTerm | null>(null)

// 获取术语列表
const fetchTerms = async () => {
  try {
    loading.value = true
    const response = await apiClient.glossary.getTerms()
    terms.value = response.data || []
  } catch (error: any) {
    ElMessage.error(`获取术语失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

// 刷新术语
const refreshTerms = () => {
  fetchTerms()
}

// 编辑术语
const editTerm = (term: GlossaryTerm) => {
  editingTerm.value = { ...term }
}

// 删除术语
const deleteTerm = async (term: GlossaryTerm) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除术语 "${term.term}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )
    
    await apiClient.glossary.deleteTerm(term.id)
    ElMessage.success(`术语 ${term.term} 已删除`)
    fetchTerms()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(`删除失败: ${error.message}`)
    }
  }
}

// 处理术语保存
const handleTermSaved = () => {
  editingTerm.value = null
  fetchTerms()
}

onMounted(() => {
  fetchTerms()
})
</script>

<style scoped lang="scss">
.glossary-management {
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
    .term-item {
      margin-bottom: 16px;
      
      .term-card {
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
          p {
            margin: 8px 0;
            color: #606266;
            line-height: 1.5;
          }
          
          .term-actions {
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