import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  // State
  const theme = ref<'light' | 'dark'>('light')
  const systemPreference = ref<'light' | 'dark'>('light')
  const autoSwitch = ref(false)

  // Getters
  const isDark = computed(() => theme.value === 'dark')
  const isLight = computed(() => theme.value === 'light')
  const currentTheme = computed(() => theme.value)

  // Actions
  const setTheme = (newTheme: 'light' | 'dark') => {
    theme.value = newTheme
    applyTheme(newTheme)
    saveThemePreference(newTheme)
  }

  const toggleTheme = () => {
    const newTheme = theme.value === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
  }

  const initTheme = async () => {
    // Get saved preference
    const saved = getSavedTheme()

    // Get system preference
    systemPreference.value = getSystemPreference()

    // Determine initial theme
    if (saved) {
      theme.value = saved
    } else if (autoSwitch.value) {
      theme.value = systemPreference.value
    } else {
      theme.value = 'light'
    }

    // Apply theme
    applyTheme(theme.value)

    // Listen for system theme changes if auto-switch is enabled
    if (autoSwitch.value) {
      listenForSystemThemeChanges()
    }
  }

  const setAutoSwitch = (enabled: boolean) => {
    autoSwitch.value = enabled
    if (enabled) {
      systemPreference.value = getSystemPreference()
      setTheme(systemPreference.value)
      listenForSystemThemeChanges()
    } else {
      stopListeningForSystemThemeChanges()
    }
  }

  // Private helpers
  const applyTheme = (themeValue: 'light' | 'dark') => {
    const html = document.documentElement

    if (themeValue === 'dark') {
      html.classList.add('dark')
      html.setAttribute('data-theme', 'dark')
    } else {
      html.classList.remove('dark')
      html.setAttribute('data-theme', 'light')
    }

    // Update meta theme-color for mobile browsers
    const metaThemeColor = document.querySelector('meta[name="theme-color"]')
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', themeValue === 'dark' ? '#1f2937' : '#ffffff')
    }
  }

  const saveThemePreference = (themeValue: 'light' | 'dark') => {
    try {
      localStorage.setItem('theme', themeValue)
    } catch (error) {
      console.warn('Failed to save theme preference:', error)
    }
  }

  const getSavedTheme = (): 'light' | 'dark' | null => {
    try {
      const saved = localStorage.getItem('theme')
      return saved === 'light' || saved === 'dark' ? saved : null
    } catch (error) {
      console.warn('Failed to get saved theme preference:', error)
      return null
    }
  }

  const getSystemPreference = (): 'light' | 'dark' => {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark'
    }
    return 'light'
  }

  let mediaQueryListener: ((event: MediaQueryListEvent) => void) | null = null

  const listenForSystemThemeChanges = () => {
    if (window.matchMedia && !mediaQueryListener) {
      mediaQueryListener = (event: MediaQueryListEvent) => {
        if (autoSwitch.value) {
          systemPreference.value = event.matches ? 'dark' : 'light'
          setTheme(systemPreference.value)
        }
      }

      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaQuery.addEventListener('change', mediaQueryListener)
    }
  }

  const stopListeningForSystemThemeChanges = () => {
    if (mediaQueryListener && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaQuery.removeEventListener('change', mediaQueryListener)
      mediaQueryListener = null
    }
  }

  return {
    // State
    theme,
    systemPreference,
    autoSwitch,

    // Getters
    isDark,
    isLight,
    currentTheme,

    // Actions
    setTheme,
    toggleTheme,
    initTheme,
    setAutoSwitch
  }
})
