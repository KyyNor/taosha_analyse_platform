import { createRouter, createWebHistory } from 'vue-router'
import DataQuery from '@/views/DataQuery.vue'
import MetadataManagement from '@/views/MetadataManagement.vue'
import OperationLogs from '@/views/OperationLogs.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'DataQuery',
      component: DataQuery,
      meta: {
        title: '数据查询'
      }
    },
    {
      path: '/metadata',
      name: 'MetadataManagement',
      component: MetadataManagement,
      meta: {
        title: '元数据管理'
      }
    },
    {
      path: '/logs',
      name: 'OperationLogs',
      component: OperationLogs,
      meta: {
        title: '操作日志'
      }
    }
  ]
})

export default router