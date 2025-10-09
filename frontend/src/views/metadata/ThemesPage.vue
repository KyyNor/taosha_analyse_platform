<template>
  <div class="space-y-6">
    <div class="text-center py-12">
      <h2 class="text-xl font-semibold mb-4">
        数据主题管理
      </h2>
      <p class="text-base-content/60">
        管理数据主题分类和表的主题归属
      </p>
      <div class="mt-8">
        <EmptyState
          type="custom"
          title="功能开发中"
          description="数据主题管理功能正在开发中，敬请期待。"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
</script>
