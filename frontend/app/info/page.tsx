/**
 * 统一信息提示页面
 * 根据不同情况显示相应的提示信息
 */

'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { AlertCircle, Lock, Clock, User, RefreshCw, Home } from 'lucide-react'

// 定义信息类型
type InfoReason = 'no_token' | 'invalid_token' | 'expired_token' | 'no_permission'

// 信息配置
const INFO_CONFIG = {
  no_token: {
    icon: User,
    title: '请先登录系统',
    message: '您还未登录系统，请通过外部系统跳转进入。',
    description: '本系统需要通过外部系统的身份验证才能访问。',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    showRefresh: false,
    showUserInfo: false
  },
  invalid_token: {
    icon: AlertCircle,
    title: 'Token无效',
    message: '您的登录凭证无效，请重新登录。',
    description: '可能是由于登录凭证格式错误或已被篡改，请通过外部系统重新登录。',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    showRefresh: true,
    showUserInfo: false
  },
  expired_token: {
    icon: Clock,
    title: '登录已过期',
    message: '您的登录凭证已过期，请重新登录。',
    description: '为了保障系统安全，登录凭证有一定的有效期，请通过外部系统重新登录。',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    showRefresh: true,
    showUserInfo: true
  },
  no_permission: {
    icon: Lock,
    title: '无权限访问',
    message: '您没有权限访问此页面。',
    description: '请联系系统管理员为您分配相应的页面访问权限。',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    showRefresh: false,
    showUserInfo: true
  }
}

export default function InfoPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  
  // 获取URL参数
  const reason = (searchParams.get('reason') as InfoReason) || 'no_token'
  const userName = searchParams.get('user_name')
  const userId = searchParams.get('user_id')
  
  // 获取配置
  const config = INFO_CONFIG[reason] || INFO_CONFIG.no_token
  const IconComponent = config.icon
  
  useEffect(() => {
    setMounted(true)
  }, [])
  
  // 刷新页面
  const handleRefresh = () => {
    window.location.reload()
  }
  
  // 返回首页
  const handleGoHome = () => {
    router.push('/')
  }
  
  // 清除token并刷新
  const handleClearTokenAndRefresh = () => {
    // 清除可能的token cookie
    document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
    
    // 清除localStorage中的token
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user_info')
    }
    
    // 刷新页面
    window.location.reload()
  }
  
  if (!mounted) {
    return null // 避免服务端渲染不一致
  }
  
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* 主要信息卡片 */}
        <div className={`${config.bgColor} ${config.borderColor} border rounded-lg p-6 shadow-sm`}>
          <div className="flex items-center space-x-3 mb-4">
            <IconComponent className={`h-8 w-8 ${config.color}`} />
            <h1 className={`text-xl font-semibold ${config.color}`}>
              {config.title}
            </h1>
          </div>
          
          <p className="text-gray-700 mb-3">
            {config.message}
          </p>
          
          <p className="text-gray-600 text-sm">
            {config.description}
          </p>
          
          {/* 用户信息显示 */}
          {config.showUserInfo && (userName || userId) && (
            <div className="mt-4 p-3 bg-white rounded border border-gray-200">
              <h3 className="text-sm font-medium text-gray-700 mb-2">当前用户信息</h3>
              {userName && (
                <p className="text-sm text-gray-600">
                  <span className="font-medium">用户姓名：</span>{userName}
                </p>
              )}
              {userId && (
                <p className="text-sm text-gray-600">
                  <span className="font-medium">用户ID：</span>{userId}
                </p>
              )}
            </div>
          )}
        </div>
        
        {/* 操作按钮 */}
        <div className="space-y-3">
          {config.showRefresh && (
            <button
              onClick={handleRefresh}
              className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              刷新页面
            </button>
          )}
          
          {(reason === 'invalid_token' || reason === 'expired_token') && (
            <button
              onClick={handleClearTokenAndRefresh}
              className="w-full flex items-center justify-center px-4 py-2 border border-red-300 rounded-md shadow-sm bg-red-50 text-sm font-medium text-red-700 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
            >
              <AlertCircle className="h-4 w-4 mr-2" />
              清除登录信息并刷新
            </button>
          )}
          
          <button
            onClick={handleGoHome}
            className="w-full flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm bg-blue-600 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            <Home className="h-4 w-4 mr-2" />
            返回首页
          </button>
        </div>
        
        {/* 帮助信息 */}
        <div className="text-center">
          <p className="text-xs text-gray-500">
            如果问题持续存在，请联系系统管理员
          </p>
          {reason === 'no_permission' && (
            <p className="text-xs text-gray-500 mt-1">
              管理员邮箱: admin@example.com
            </p>
          )}
        </div>
        
        {/* 调试信息（仅在开发环境显示） */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-6 p-3 bg-gray-100 rounded text-xs text-gray-600">
            <h4 className="font-medium mb-1">调试信息:</h4>
            <p>Reason: {reason}</p>
            <p>User Name: {userName || 'N/A'}</p>
            <p>User ID: {userId || 'N/A'}</p>
            <p>Timestamp: {new Date().toISOString()}</p>
          </div>
        )}
      </div>
    </div>
  )
}