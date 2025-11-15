import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type { Notification, User } from '@/types/index'

interface AppState {
  // 主题相关
  theme: 'light' | 'dark'

  // UI状态
  sidebarOpen: boolean
  loading: boolean

  // 通知系统
  notifications: Notification[]

  // 用户信息
  user: User | null

  // 操作方法
  setTheme: (theme: 'light' | 'dark') => void
  toggleSidebar: () => void
  setLoading: (loading: boolean) => void
  addNotification: (notification: Notification) => void
  removeNotification: (id: string) => void
  setUser: (user: User | null) => void
}

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        theme: 'light',
        sidebarOpen: true,
        loading: false,
        notifications: [],
        user: null,

        setTheme: (theme) => set({ theme }),
        toggleSidebar: () => set((state) => ({
          sidebarOpen: !state.sidebarOpen
        })),
        setLoading: (loading) => set({ loading }),

        addNotification: (notification) => set((state) => ({
          notifications: [...state.notifications, notification]
        })),

        removeNotification: (id) => set((state) => ({
          notifications: state.notifications.filter(n => n.id !== id)
        })),

        setUser: (user) => set({ user }),
      }),
      {
        name: 'app-store',
        partialize: (state) => ({
          theme: state.theme,
          user: state.user
        }),
      }
    )
  )
)