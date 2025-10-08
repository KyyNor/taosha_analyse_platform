<template>
  <div class="min-h-screen flex items-center justify-center bg-base-200">
    <div class="card w-96 bg-base-100 shadow-xl">
      <div class="card-body">
        <!-- Logo和标题 -->
        <div class="text-center mb-6">
          <h1 class="text-2xl font-bold text-primary mb-2">淘沙分析平台</h1>
          <p class="text-base-content text-opacity-60">基于自然语言的企业数据分析平台</p>
        </div>

        <!-- 登录表单 -->
        <form @submit.prevent="handleLogin" class="space-y-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">用户名</span>
            </label>
            <input 
              v-model="loginForm.username"
              type="text" 
              placeholder="请输入用户名" 
              class="input input-bordered w-full"
              :class="{ 'input-error': errors.username }"
              required
            />
            <label v-if="errors.username" class="label">
              <span class="label-text-alt text-error">{{ errors.username }}</span>
            </label>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">密码</span>
            </label>
            <input 
              v-model="loginForm.password"
              :type="showPassword ? 'text' : 'password'" 
              placeholder="请输入密码" 
              class="input input-bordered w-full"
              :class="{ 'input-error': errors.password }"
              required
            />
            <label class="label">
              <button 
                type="button"
                @click="showPassword = !showPassword"
                class="label-text-alt link link-hover"
              >
                {{ showPassword ? '隐藏密码' : '显示密码' }}
              </button>
            </label>
            <label v-if="errors.password" class="label">
              <span class="label-text-alt text-error">{{ errors.password }}</span>
            </label>
          </div>

          <div class="form-control">
            <label class="cursor-pointer label">
              <span class="label-text">记住登录状态</span>
              <input v-model="rememberMe" type="checkbox" class="checkbox checkbox-primary" />
            </label>
          </div>

          <div class="form-control mt-6">
            <button 
              type="submit" 
              class="btn btn-primary w-full"
              :class="{ 'loading': authStore.loading }"
              :disabled="authStore.loading"
            >
              <span v-if="!authStore.loading">登录</span>
              <span v-else>登录中...</span>
            </button>
          </div>
        </form>

        <!-- 演示账户提示 -->
        <div class="divider">演示账户</div>
        <div class="bg-base-200 p-4 rounded-lg text-sm">
          <p class="mb-2 font-semibold">可使用以下账户登录：</p>
          <div class="space-y-1">
            <p><span class="font-mono">admin</span> / <span class="font-mono">admin123</span> - 管理员账户</p>
            <p><span class="font-mono">user</span> / <span class="font-mono">user123</span> - 普通用户</p>
          </div>
        </div>

        <!-- 快速登录按钮 -->
        <div class="flex gap-2 mt-4">
          <button 
            @click="quickLogin('admin', 'admin123')"
            class="btn btn-outline btn-sm flex-1"
            :disabled="authStore.loading"
          >
            管理员登录
          </button>
          <button 
            @click="quickLogin('user', 'user123')"
            class="btn btn-outline btn-sm flex-1"
            :disabled="authStore.loading"
          >
            用户登录
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notification'
import type { LoginRequest } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const notificationStore = useNotificationStore()

// 表单数据
const loginForm = reactive<LoginRequest>({
  username: '',
  password: ''
})

const showPassword = ref(false)
const rememberMe = ref(false)

// 表单验证错误
const errors = reactive({
  username: '',
  password: ''
})

// 验证表单
const validateForm = (): boolean => {
  errors.username = ''
  errors.password = ''

  if (!loginForm.username.trim()) {
    errors.username = '请输入用户名'
    return false
  }

  if (!loginForm.password.trim()) {
    errors.password = '请输入密码'
    return false
  }

  if (loginForm.password.length < 6) {
    errors.password = '密码长度至少6位'
    return false
  }

  return true
}

// 处理登录
const handleLogin = async () => {
  if (!validateForm()) {
    return
  }

  try {
    await authStore.login(loginForm)
    
    notificationStore.success('登录成功！')
    
    // 重定向到目标页面或首页
    const redirect = route.query.redirect as string || '/'
    router.push(redirect)
    
  } catch (error: any) {
    notificationStore.error(error.message || '登录失败，请检查用户名和密码')
  }
}

// 快速登录
const quickLogin = (username: string, password: string) => {
  loginForm.username = username
  loginForm.password = password
  handleLogin()
}
</script>

<style scoped>
.card {
  backdrop-filter: blur(10px);
}

@media (max-width: 640px) {
  .card {
    @apply w-full max-w-sm mx-4;
  }
}
</style>