<template>
  <div class="text-center py-20">
    <svg 
      class="w-24 h-24 mx-auto text-base-content text-opacity-20 mb-8" 
      fill="none" 
      stroke="currentColor" 
      viewBox="0 0 24 24"
    >
      <path 
        stroke-linecap="round" 
        stroke-linejoin="round" 
        stroke-width="2" 
        d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-2.34 0-4.29-1.175-5.5-2.926L3.227 6.213a.5.5 0 01.154-.51A7.93 7.93 0 0112 2a7.93 7.93 0 018.619 3.703.5.5 0 01.154.51L17.5 12.074A7.962 7.962 0 0112 15z"
      />
    </svg>
    
    <h1 class="text-4xl font-bold text-base-content mb-4">404</h1>
    <h2 class="text-xl text-base-content text-opacity-70 mb-6">页面未找到</h2>
    <p class="text-base-content text-opacity-50 mb-8 max-w-md mx-auto">
      抱歉，您访问的页面不存在。可能是页面已被删除，或者您输入的地址有误。
    </p>
    
    <div class="space-x-4">
      <button @click="goBack" class="btn btn-outline">
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        返回上页
      </button>
      
      <RouterLink to="/" class="btn btn-primary">
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
        回到首页
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, useRouter } from 'vue-router'

const router = useRouter()

const goBack = () => {
  if (window.history.length > 1) {
    router.go(-1)
  } else {
    router.push('/')
  }
}
</script>