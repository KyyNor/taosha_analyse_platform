<template>
  <MainLayout>
    <div class="space-y-6">
      <div class="text-center py-12">
        <h1 class="text-2xl font-bold mb-4">系统设置</h1>
        <p class="text-base-content/60">配置系统参数和个人偏好</p>
        <div class="mt-8">
          <EmptyState
            type="custom"
            title="功能开发中"
            description="系统设置功能正在开发中，敬请期待。"
          />
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup lang="ts">
import MainLayout from '@/components/layout/MainLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
</script>