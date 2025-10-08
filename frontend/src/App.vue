<template>
  <div id="app" class="min-h-screen bg-base-100">
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import { onMounted } from 'vue'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

onMounted(() => {
  // 初始化主题
  themeStore.initTheme()
})
</script>

<style scoped>
#app {
  font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>