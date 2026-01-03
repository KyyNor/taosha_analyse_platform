'use client'

import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'

export default function TestTokenPage() {
  const { isAuthenticated, user, token, login } = useAuth()
  const [testToken, setTestToken] = useState('')

  const handleTestLogin = async () => {
    if (testToken) {
      const success = await login(testToken)
      if (success) {
        alert('Token设置成功！')
      } else {
        alert('Token无效！')
      }
    }
  }

  const handleClearToken = () => {
    // 清除cookie
    document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
    // 清除localStorage
    localStorage.removeItem('auth_token')
    window.location.reload()
  }

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">Token测试页面</h1>
      
      <div className="space-y-6">
        {/* 当前状态 */}
        <div className="bg-gray-100 p-4 rounded">
          <h2 className="text-lg font-semibold mb-2">当前状态</h2>
          <p>认证状态: {isAuthenticated ? '已认证' : '未认证'}</p>
          {user && (
            <div className="mt-2">
              <p>用户ID: {user.user_id}</p>
              <p>用户名: {user.user_name}</p>
              <p>部门: {user.branch_name}</p>
              <p>角色: {user.role_name_list?.join(', ')}</p>
            </div>
          )}
          {token && (
            <div className="mt-2">
              <p>Token: {token.substring(0, 50)}...</p>
            </div>
          )}
        </div>

        {/* 测试Token输入 */}
        <div className="bg-blue-50 p-4 rounded">
          <h2 className="text-lg font-semibold mb-2">测试Token</h2>
          <div className="space-y-2">
            <textarea
              value={testToken}
              onChange={(e) => setTestToken(e.target.value)}
              placeholder="粘贴生成的token..."
              className="w-full p-2 border rounded h-32"
            />
            <div className="space-x-2">
              <button
                onClick={handleTestLogin}
                className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
              >
                设置Token
              </button>
              <button
                onClick={handleClearToken}
                className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
              >
                清除Token
              </button>
            </div>
          </div>
        </div>

        {/* URL参数测试说明 */}
        <div className="bg-green-50 p-4 rounded">
          <h2 className="text-lg font-semibold mb-2">URL参数测试</h2>
          <p className="mb-2">你也可以通过URL参数传递token：</p>
          <code className="bg-gray-200 p-2 rounded block">
            {window.location.origin}/taosha/test-token?token=你的token字符串
          </code>
          <p className="mt-2 text-sm text-gray-600">
            系统会自动将token保存到cookie中，然后重定向到当前页面
          </p>
        </div>

        {/* 权限测试链接 */}
        <div className="bg-yellow-50 p-4 rounded">
          <h2 className="text-lg font-semibold mb-2">权限测试链接</h2>
          <div className="space-y-2">
            <div>
              <a href="/taosha/agent" className="text-blue-600 hover:underline">
                普通页面 (/agent)
              </a>
            </div>
            <div>
              <a href="/taosha/admin/departments" className="text-blue-600 hover:underline">
                管理员页面 (/admin/departments) - 需要管理员权限
              </a>
            </div>
            <div>
              <a href="/taosha/metadata/tables" className="text-blue-600 hover:underline">
                元数据页面 (/metadata/tables)
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}