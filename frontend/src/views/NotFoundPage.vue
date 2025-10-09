<template>
  <div class="min-h-screen flex items-center justify-center bg-base-200">
    <div class="text-center">
      <div class="mb-8">
        <h1 class="text-9xl font-bold text-primary">404</h1>
      </div>
      <div class="space-y-4">
        <h2 class="text-2xl font-bold">页面未找到</h2>
        <p class="text-base-content/60 max-w-md mx-auto">
          抱歉，您访问的页面不存在或已被移除。
        </p>
        <div class="flex gap-4 justify-center">
          <router-link to="/" class="btn btn-primary">
            返回首页
          </router-link>
          <router-link to="/query" class="btn btn-ghost">
            开始查询
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 404 页面组件
</script>