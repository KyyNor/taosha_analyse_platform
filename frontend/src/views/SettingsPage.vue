<template>
  <div class="space-y-6">
    <div class="text-center py-12">
      <div class="mt-8">
        <EmptyState
          type="custom"
          title="功能开发中"
          description="系统设置功能正在开发中，敬请期待。"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
</script>
