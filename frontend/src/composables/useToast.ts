import { ref } from 'vue'

interface ToastOptions {
  title?: string
  message?: string
  duration?: number
  persistent?: boolean
}

interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title?: string
  message?: string
  duration?: number
  persistent?: boolean
}

const toasts = ref<Toast[]>([])

export function useToast() {
  const addToast = (type: Toast['type'], options: ToastOptions = {}) => {
    const id = Date.now().toString()
    const toast: Toast = {
      id,
      type,
      duration: 5000,
      ...options
    }

    toasts.value.push(toast)

    // Auto remove after duration
    if (!toast.persistent && toast.duration && toast.duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, toast.duration)
    }

    return id
  }

  const removeToast = (id: string) => {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  const clearAll = () => {
    toasts.value = []
  }

  const success = (message: string, options?: Omit<ToastOptions, 'message'>) => {
    return addToast('success', { message, ...options })
  }

  const error = (message: string, options?: Omit<ToastOptions, 'message'>) => {
    return addToast('error', { message, duration: 8000, ...options })
  }

  const warning = (message: string, options?: Omit<ToastOptions, 'message'>) => {
    return addToast('warning', { message, ...options })
  }

  const info = (message: string, options?: Omit<ToastOptions, 'message'>) => {
    return addToast('info', { message, ...options })
  }

  return {
    toasts,
    success,
    error,
    warning,
    info,
    removeToast,
    clearAll,
    addToast
  }
}

// Global toast instance for use outside of components
let globalToast: ReturnType<typeof useToast> | null = null

export const initGlobalToast = () => {
  if (!globalToast) {
    globalToast = useToast()
  }
  return globalToast
}

// Make toast available globally
declare global {
  interface Window {
    $toast: ReturnType<typeof useToast>
  }
}
