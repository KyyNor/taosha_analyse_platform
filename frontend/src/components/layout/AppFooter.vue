<template>
  <footer class="footer bg-base-200 text-base-content p-4 mt-auto">
    <div class="container mx-auto">
      <div class="flex flex-col md:flex-row items-center justify-between gap-4">
        <!-- Copyright Info -->
        <div class="flex items-center gap-2 text-sm text-base-content/60">
          <span>© 2024 淘沙分析平台</span>
          <span class="hidden md:inline">•</span>
          <span class="hidden md:inline">基于 AI 的自然语言转 SQL 分析平台</span>
        </div>

        <!-- Footer Links -->
        <div class="flex items-center gap-6 text-sm">
          <a
            href="#"
            class="link link-hover text-base-content/60 hover:text-primary transition-colors"
          >
            隐私政策
          </a>
          <a
            href="#"
            class="link link-hover text-base-content/60 hover:text-primary transition-colors"
          >
            使用条款
          </a>
          <a
            href="#"
            class="link link-hover text-base-content/60 hover:text-primary transition-colors"
          >
            关于我们
          </a>
          <a
            href="#"
            class="link link-hover text-base-content/60 hover:text-primary transition-colors"
          >
            联系支持
          </a>
        </div>

        <!-- Version Info -->
        <div class="flex items-center gap-2 text-sm text-base-content/40">
          <span>v{{ version }}</span>
          <span class="badge badge-xs badge-success" v-if="isProduction">
            生产环境
          </span>
          <span class="badge badge-xs badge-warning" v-else>
            开发环境
          </span>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const version = ref('1.0.0')
const isProduction = import.meta.env.PROD
</script>