<template>
  <div class="min-h-screen bg-base-100 flex flex-col">
    <!-- Header -->
    <AppHeader />

    <!-- Main Content -->
    <div class="flex-1 flex">
      <!-- Sidebar (Desktop) -->
      <aside class="hidden lg:block">
        <AppSidebar />
      </aside>

      <!-- Main Content Area -->
      <main class="flex-1 overflow-auto">
        <!-- Breadcrumb -->
        <div
          v-if="showBreadcrumb"
          class="bg-base-200 border-b border-base-300 px-6 py-3"
        >
          <div class="flex items-center gap-2 text-sm">
            <router-link
              to="/"
              class="link link-hover text-base-content/60 hover:text-primary"
            >
              首页
            </router-link>
            <span class="text-base-content/40">/</span>
            <template
              v-for="(item, index) in breadcrumbItems"
              :key="index"
            >
              <router-link
                v-if="item.to && index < breadcrumbItems.length - 1"
                :to="item.to"
                class="link link-hover text-base-content/60 hover:text-primary"
              >
                {{ item.label }}
              </router-link>
              <span
                v-else
                :class="{ 'text-base-content': index === breadcrumbItems.length - 1 }"
                class="text-base-content/60"
              >
                {{ item.label }}
              </span>
              <span
                v-if="index < breadcrumbItems.length - 1"
                class="text-base-content/40"
              >/</span>
            </template>
          </div>
        </div>

        <!-- Page Content -->
        <div class="p-6">
          <slot />
        </div>
      </main>
    </div>

    <!-- Footer -->
    <AppFooter />

    <!-- Loading Overlay -->
    <div
      v-if="isLoading"
      class="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center"
    >
      <div class="bg-base-100 p-6 rounded-lg shadow-xl">
        <div class="flex items-center gap-3">
          <span class="loading loading-spinner loading-md text-primary" />
          <span class="text-sm font-medium">加载中...</span>
        </div>
      </div>
    </div>

    <!-- Toast Notification Container -->
    <div class="toast toast-top toast-end z-50">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        :class="[
          'alert',
          'shadow-lg',
          'mb-2',
          {
            'alert-success': notification.type === 'success',
            'alert-error': notification.type === 'error',
            'alert-warning': notification.type === 'warning',
            'alert-info': notification.type === 'info'
          }
        ]"
      >
        <component
          :is="getNotificationIcon(notification.type)"
          class="w-5 h-5"
        />
        <div>
          <h3
            v-if="notification.title"
            class="font-bold"
          >
            {{ notification.title }}
          </h3>
          <div
            v-if="notification.message"
            class="text-xs"
          >
            {{ notification.message }}
          </div>
        </div>
        <button
          class="btn btn-ghost btn-xs"
          @click="removeNotification(notification.id)"
        >
          ✕
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, h } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@stores/app'
import { useToast } from '@/composables/useToast'
import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'
import AppFooter from './AppFooter.vue'

interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title?: string
  message?: string
  duration?: number
}

const route = useRoute()
const appStore = useAppStore()

const notifications = ref<Notification[]>([])
const isLoading = ref(false)

// Breadcrumb
const showBreadcrumb = computed(() => {
  return route.meta.breadcrumb && route.meta.breadcrumb.length > 0
})

const breadcrumbItems = computed(() => {
  return route.meta.breadcrumb || []
})

// Notification icons
const getNotificationIcon = (type: string) => {
  switch (type) {
    case 'success':
      return h('svg', {
        xmlns: 'http://www.w3.org/2000/svg',
        class: 'h-6 w-6 shrink-0 stroke-current',
        fill: 'none',
        viewBox: '0 0 24 24'
      }, [
        h('path', {
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'stroke-width': '2',
          d: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z'
        })
      ])
    case 'error':
      return h('svg', {
        xmlns: 'http://www.w3.org/2000/svg',
        class: 'h-6 w-6 shrink-0 stroke-current',
        fill: 'none',
        viewBox: '0 0 24 24'
      }, [
        h('path', {
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'stroke-width': '2',
          d: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z'
        })
      ])
    case 'warning':
      return h('svg', {
        xmlns: 'http://www.w3.org/2000/svg',
        class: 'h-6 w-6 shrink-0 stroke-current',
        fill: 'none',
        viewBox: '0 0 24 24'
      }, [
        h('path', {
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'stroke-width': '2',
          d: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z'
        })
      ])
    case 'info':
    default:
      return h('svg', {
        xmlns: 'http://www.w3.org/2000/svg',
        class: 'h-6 w-6 shrink-0 stroke-current',
        fill: 'none',
        viewBox: '0 0 24 24'
      }, [
        h('path', {
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'stroke-width': '2',
          d: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
        })
      ])
  }
}

// Add notification
const addNotification = (notification: Omit<Notification, 'id'>) => {
  const id = Date.now().toString()
  const newNotification: Notification = {
    id,
    duration: 5000,
    ...notification
  }

  notifications.value.push(newNotification)

  // Auto remove after duration
  if (newNotification.duration && newNotification.duration > 0) {
    setTimeout(() => {
      removeNotification(id)
    }, newNotification.duration)
  }
}

// Remove notification
const removeNotification = (id: string) => {
  const index = notifications.value.findIndex(n => n.id === id)
  if (index > -1) {
    notifications.value.splice(index, 1)
  }
}

// Show loading
const showLoading = () => {
  isLoading.value = true
}

// Hide loading
const hideLoading = () => {
  isLoading.value = false
}

// Global notification methods
const showSuccess = (message: string, title?: string) => {
  addNotification({ type: 'success', title, message })
}

const showError = (message: string, title?: string) => {
  addNotification({ type: 'error', title, message, duration: 8000 })
}

const showWarning = (message: string, title?: string) => {
  addNotification({ type: 'warning', title, message })
}

const showInfo = (message: string, title?: string) => {
  addNotification({ type: 'info', title, message })
}

// Expose methods globally
onMounted(() => {
  // Make notification methods available globally
  window.$notify = {
    success: showSuccess,
    error: showError,
    warning: showWarning,
    info: showInfo,
    loading: showLoading,
    hideLoading
  }
})
</script>

<style scoped>
/* Custom animations */
.toast {
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
