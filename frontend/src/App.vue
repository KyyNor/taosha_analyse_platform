<template>
  <div
    id="app"
    class="min-h-screen bg-base-100"
  >
    <!-- 路由视图 -->
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useThemeStore } from '@stores/theme'
const themeStore = useThemeStore()

// Initialize app
onMounted(async () => {
  // Initialize theme
  await themeStore.initTheme()
})
</script>

<style>
/* Global styles */
#app {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Loading state for router transitions */
.loading {
  opacity: 0.6;
  pointer-events: none;
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: hsl(var(--b2));
}

::-webkit-scrollbar-thumb {
  background: hsl(var(--bc) / 0.3);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--bc) / 0.5);
}

/* Focus styles */
.focus-visible:focus {
  outline: 2px solid hsl(var(--p));
  outline-offset: 2px;
}

/* Print styles */
@media print {
  .no-print {
    display: none !important;
  }
}
</style>
