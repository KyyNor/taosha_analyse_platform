import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  // State
  const isLoading = ref(false)
  const sidebarCollapsed = ref(false)
  const notifications = ref<Array<{
    id: string
    type: 'success' | 'error' | 'warning' | 'info'
    title?: string
    message: string
    duration?: number
    timestamp: number
  }>>([])

  // Getters
  const hasUnreadNotifications = computed(() =>
    notifications.value.length > 0
  )

  const recentNotifications = computed(() =>
    notifications.value.slice(0, 5)
  )

  // Actions
  const setLoading = (loading: boolean) => {
    isLoading.value = loading
  }

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
    // Save to localStorage
    localStorage.setItem('sidebar_collapsed', String(sidebarCollapsed.value))
  }

  const setSidebarCollapsed = (collapsed: boolean) => {
    sidebarCollapsed.value = collapsed
    localStorage.setItem('sidebar_collapsed', String(collapsed))
  }

  const addNotification = (notification: {
    type: 'success' | 'error' | 'warning' | 'info'
    title?: string
    message: string
    duration?: number
  }) => {
    const id = Date.now().toString()
    const newNotification = {
      id,
      timestamp: Date.now(),
      duration: 5000,
      ...notification
    }

    notifications.value.unshift(newNotification)

    // Auto remove after duration
    if (newNotification.duration && newNotification.duration > 0) {
      setTimeout(() => {
        removeNotification(id)
      }, newNotification.duration)
    }

    return id
  }

  const removeNotification = (id: string) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  const clearNotifications = () => {
    notifications.value = []
  }

  // Initialize
  const init = () => {
    // Restore sidebar state
    const savedCollapsed = localStorage.getItem('sidebar_collapsed')
    if (savedCollapsed !== null) {
      sidebarCollapsed.value = savedCollapsed === 'true'
    }
  }

  // Auto-initialize
  init()

  return {
    // State
    isLoading,
    sidebarCollapsed,
    notifications,

    // Getters
    hasUnreadNotifications,
    recentNotifications,

    // Actions
    setLoading,
    toggleSidebar,
    setSidebarCollapsed,
    addNotification,
    removeNotification,
    clearNotifications
  }
})
