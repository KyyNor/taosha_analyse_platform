import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/query'
    },
    {
      path: '/query',
      name: 'DataQuery',
      component: () => import('@/views/DataQuery.vue'),
      meta: { title: '数据查询' }
    },
    {
      path: '/metadata',
      name: 'MetadataManagement', 
      component: () => import('@/views/MetadataManagement.vue'),
      meta: { title: '元数据管理' }
    },
    {
      path: '/glossary',
      name: 'GlossarySearch',
      component: () => import('@/views/GlossarySearch.vue'),
      meta: { title: '术语搜索' }
    }
  ]
})

export default router