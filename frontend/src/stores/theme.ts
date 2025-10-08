import { defineStore } from 'pinia'
import { ref } from 'vue'

// 主题类型
export type Theme = 'light' | 'dark'

// 主题配置
export interface ThemeConfig {
  name: Theme
  displayName: string
  colors: {
    primary: string
    secondary: string
    accent: string
    neutral: string
    'base-100': string
    'base-200': string
    'base-300': string
    info: string
    success: string
    warning: string
    error: string
  }
}

// 内置主题配置
const themes: Record<Theme, ThemeConfig> = {
  light: {
    name: 'light',
    displayName: '浅色主题',
    colors: {
      primary: '#3B82F6',
      secondary: '#8B5CF6',
      accent: '#10B981',
      neutral: '#374151',
      'base-100': '#FFFFFF',
      'base-200': '#F3F4F6',
      'base-300': '#E5E7EB',
      info: '#3ABFF8',
      success: '#36D399',
      warning: '#FBBD23',
      error: '#F87272'
    }
  },
  dark: {
    name: 'dark',
    displayName: '深色主题',
    colors: {
      primary: '#60A5FA',
      secondary: '#A78BFA',
      accent: '#34D399',
      neutral: '#1F2937',
      'base-100': '#111827',
      'base-200': '#1F2937',
      'base-300': '#374151',
      info: '#7DD3FC',
      success: '#4ADE80',
      warning: '#FCD34D',
      error: '#F87171'
    }
  }
}

export const useThemeStore = defineStore('theme', () => {
  // 状态
  const currentTheme = ref<Theme>('light')
  const systemTheme = ref<Theme>('light')
  const followSystem = ref(false)

  // 初始化主题
  function initTheme() {
    // 检测系统主题
    detectSystemTheme()
    
    // 从 localStorage 恢复主题设置
    const savedTheme = localStorage.getItem('taosha_theme') as Theme
    const savedFollowSystem = localStorage.getItem('taosha_follow_system') === 'true'
    
    followSystem.value = savedFollowSystem
    
    if (savedFollowSystem) {
      setTheme(systemTheme.value)
    } else if (savedTheme && themes[savedTheme]) {
      setTheme(savedTheme)
    } else {
      setTheme('light')
    }
    
    // 监听系统主题变化
    watchSystemTheme()
  }

  // 检测系统主题
  function detectSystemTheme() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      systemTheme.value = 'dark'
    } else {
      systemTheme.value = 'light'
    }
  }

  // 监听系统主题变化
  function watchSystemTheme() {
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      
      mediaQuery.addEventListener('change', (e) => {
        systemTheme.value = e.matches ? 'dark' : 'light'
        
        // 如果设置为跟随系统，自动切换主题
        if (followSystem.value) {
          setTheme(systemTheme.value)
        }
      })
    }
  }

  // 设置主题
  function setTheme(theme: Theme) {
    if (!themes[theme]) {
      console.warn(`主题 ${theme} 不存在，使用默认主题`)
      theme = 'light'
    }

    currentTheme.value = theme
    
    // 应用主题到 DOM
    applyTheme(theme)
    
    // 保存到 localStorage
    localStorage.setItem('taosha_theme', theme)
  }

  // 应用主题到 DOM
  function applyTheme(theme: Theme) {
    const html = document.documentElement
    
    // 设置 data-theme 属性（DaisyUI 使用）
    html.setAttribute('data-theme', theme)
    
    // 设置主题类名
    html.className = html.className.replace(/theme-\w+/g, '')
    html.classList.add(`theme-${theme}`)
    
    // 设置 CSS 变量（可选，用于自定义样式）
    const themeConfig = themes[theme]
    const root = document.documentElement.style
    
    Object.entries(themeConfig.colors).forEach(([key, value]) => {
      root.setProperty(`--color-${key}`, value)
    })
  }

  // 切换主题
  function toggleTheme() {
    const newTheme = currentTheme.value === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
    followSystem.value = false
    localStorage.setItem('taosha_follow_system', 'false')
  }

  // 设置是否跟随系统主题
  function setFollowSystem(follow: boolean) {
    followSystem.value = follow
    localStorage.setItem('taosha_follow_system', follow.toString())
    
    if (follow) {
      setTheme(systemTheme.value)
    }
  }

  // 获取当前主题配置
  function getCurrentThemeConfig(): ThemeConfig {
    return themes[currentTheme.value]
  }

  // 获取所有可用主题
  function getAvailableThemes(): ThemeConfig[] {
    return Object.values(themes)
  }

  // 判断是否为深色主题
  function isDarkTheme(): boolean {
    return currentTheme.value === 'dark'
  }

  // 获取主题对应的图标
  function getThemeIcon(theme?: Theme): string {
    const targetTheme = theme || currentTheme.value
    return targetTheme === 'dark' ? '🌙' : '☀️'
  }

  return {
    // 状态
    currentTheme,
    systemTheme,
    followSystem,
    
    // 方法
    initTheme,
    setTheme,
    toggleTheme,
    setFollowSystem,
    getCurrentThemeConfig,
    getAvailableThemes,
    isDarkTheme,
    getThemeIcon
  }
})