import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'

// Styles
import './styles/index.css'

// App component
import App from './App.vue'

// Create app instance
const app = createApp(App)

// Use plugins
app.use(createPinia())
app.use(router)

// Global properties
app.config.globalProperties.$appName = '淘沙分析平台'
app.config.globalProperties.$version = import.meta.env.VITE_APP_VERSION || '1.0.0'

// Error handling
app.config.errorHandler = (err, vm, info) => {
  console.error('Vue Error:', err, info)
  // In production, you might want to send this to an error tracking service
}

// Mount app
app.mount('#app')