import { defineStore } from 'pinia'
import { ref } from 'vue'

// 通知类型
export type NotificationType = 'info' | 'success' | 'warning' | 'error'

// 通知项接口
export interface Notification {
  id: string
  type: NotificationType
  title?: string
  message: string
  duration?: number
  persistent?: boolean
  timestamp: number
  actions?: NotificationAction[]
}

// 通知操作接口
export interface NotificationAction {
  label: string
  handler: () => void
  style?: 'primary' | 'secondary' | 'ghost'
}

// 通知选项接口
export interface NotificationOptions {
  title?: string
  duration?: number
  persistent?: boolean
  actions?: NotificationAction[]
}

export const useNotificationStore = defineStore('notification', () => {
  // 状态
  const notifications = ref<Notification[]>([])
  const maxNotifications = ref(5) // 最大显示数量

  // 生成唯一 ID
  function generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2)
  }

  // 添加通知
  function addNotification(
    type: NotificationType,
    message: string,
    options: NotificationOptions = {}
  ): string {
    const id = generateId()
    const notification: Notification = {
      id,
      type,
      title: options.title,
      message,
      duration: options.duration ?? getDefaultDuration(type),
      persistent: options.persistent ?? false,
      timestamp: Date.now(),
      actions: options.actions
    }

    notifications.value.unshift(notification)

    // 限制通知数量
    if (notifications.value.length > maxNotifications.value) {
      notifications.value = notifications.value.slice(0, maxNotifications.value)
    }

    // 自动移除（非持久化通知）
    if (!notification.persistent && notification.duration && notification.duration > 0) {
      setTimeout(() => {
        removeNotification(id)
      }, notification.duration)
    }

    return id
  }

  // 获取默认持续时间
  function getDefaultDuration(type: NotificationType): number {
    switch (type) {
      case 'error':
        return 6000 // 错误消息显示更久
      case 'warning':
        return 5000
      case 'success':
        return 4000
      case 'info':
      default:
        return 3000
    }
  }

  // 移除通知
  function removeNotification(id: string) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  // 清除所有通知
  function clearAll() {
    notifications.value = []
  }

  // 清除指定类型的通知
  function clearByType(type: NotificationType) {
    notifications.value = notifications.value.filter(n => n.type !== type)
  }

  // 便捷方法：信息通知
  function info(message: string, options?: NotificationOptions): string {
    return addNotification('info', message, options)
  }

  // 便捷方法：成功通知
  function success(message: string, options?: NotificationOptions): string {
    return addNotification('success', message, options)
  }

  // 便捷方法：警告通知
  function warning(message: string, options?: NotificationOptions): string {
    return addNotification('warning', message, options)
  }

  // 便捷方法：错误通知
  function error(message: string, options?: NotificationOptions): string {
    return addNotification('error', message, options)
  }

  // 获取通知的图标
  function getIcon(type: NotificationType): string {
    switch (type) {
      case 'info':
        return 'ℹ️'
      case 'success':
        return '✅'
      case 'warning':
        return '⚠️'
      case 'error':
        return '❌'
      default:
        return 'ℹ️'
    }
  }

  // 获取通知的样式类
  function getAlertClass(type: NotificationType): string {
    switch (type) {
      case 'info':
        return 'alert-info'
      case 'success':
        return 'alert-success'
      case 'warning':
        return 'alert-warning'
      case 'error':
        return 'alert-error'
      default:
        return 'alert-info'
    }
  }

  // 获取未读通知数量
  function getUnreadCount(): number {
    return notifications.value.length
  }

  // 判断是否有指定类型的通知
  function hasNotificationType(type: NotificationType): boolean {
    return notifications.value.some(n => n.type === type)
  }

  // 获取最新的通知
  function getLatestNotification(): Notification | null {
    return notifications.value[0] || null
  }

  return {
    // 状态
    notifications,
    maxNotifications,

    // 方法
    addNotification,
    removeNotification,
    clearAll,
    clearByType,
    
    // 便捷方法
    info,
    success,
    warning,
    error,
    
    // 工具方法
    getIcon,
    getAlertClass,
    getUnreadCount,
    hasNotificationType,
    getLatestNotification
  }
})