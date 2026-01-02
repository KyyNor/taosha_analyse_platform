/**
 * 登录记录查看页面
 * 只允许淘沙管理员访问
 */

'use client'

import { useState, useEffect } from 'react'
import { Clock, Users, Search, RefreshCw, Calendar, TrendingUp, Building, UserCheck } from 'lucide-react'
import { useRequireAdmin } from '@/hooks/useAuth'
import { loginRecordApi, ApiError } from '@/lib/api'

// 登录记录接口
interface LoginRecord {
  user_id: string
  user_name: string
  branch_no: string
  branch_name: string
  role_id_list: string[]
  role_name_list: string[]
  last_login_time: string
  created_at: string
  updated_at: string
}

// 登录统计接口
interface LoginSummary {
  total_users: number
  active_users_today: number
  active_users_week: number
  active_users_month: number
  latest_login_time?: string
  most_active_department?: string
  most_active_role?: string
}

export default function LoginRecordsPage() {
  // 权限检查
  const { isAuthenticated, isLoading: authLoading, isAdmin } = useRequireAdmin()
  
  // 状态管理
  const [records, setRecords] = useState<LoginRecord[]>([])
  const [summary, setSummary] = useState<LoginSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // 分页状态
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(20)
  const [totalRecords, setTotalRecords] = useState(0)
  
  // 过滤状态
  const [userIdFilter, setUserIdFilter] = useState('')
  const [branchFilter, setBranchFilter] = useState('')
  
  // 加载登录记录
  const loadRecords = async (page: number = 1) => {
    try {
      setLoading(true)
      setError(null)
      
      const params: any = {
        page,
        page_size: pageSize
      }
      
      if (userIdFilter) {
        params.user_id = userIdFilter
      }
      
      if (branchFilter) {
        params.branch_no = branchFilter
      }
      
      const response = await loginRecordApi.getLoginRecords(params)
      
      setRecords(response.records || [])
      setTotalRecords(response.total || 0)
      setCurrentPage(response.page || 1)
      
    } catch (err) {
      const error = err as ApiError
      setError(error.message || '加载登录记录失败')
    } finally {
      setLoading(false)
    }
  }
  
  // 加载统计信息
  const loadSummary = async () => {
    try {
      const summaryData = await loginRecordApi.getLoginSummary()
      setSummary(summaryData)
    } catch (err) {
      console.error('加载统计信息失败:', err)
    }
  }
  
  // 初始加载
  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      loadRecords()
      loadSummary()
    }
  }, [isAuthenticated, isAdmin])
  
  // 搜索处理
  const handleSearch = () => {
    setCurrentPage(1)
    loadRecords(1)
  }
  
  // 重置搜索
  const handleReset = () => {
    setUserIdFilter('')
    setBranchFilter('')
    setCurrentPage(1)
    loadRecords(1)
  }
  
  // 分页处理
  const totalPages = Math.ceil(totalRecords / pageSize)
  
  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      loadRecords(page)
    }
  }
  
  // 格式化时间
  const formatTime = (timeString: string) => {
    return new Date(timeString).toLocaleString('zh-CN')
  }
  
  // 权限检查中
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-gray-600">验证权限中...</p>
        </div>
      </div>
    )
  }
  
  // 无权限访问
  if (!isAuthenticated || !isAdmin) {
    return null // 会被useRequireAdmin重定向
  }
  
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 页面标题 */}
        <div className="mb-8">
          <div className="flex items-center space-x-3 mb-2">
            <Clock className="h-8 w-8 text-indigo-600" />
            <h1 className="text-3xl font-bold text-gray-900">登录记录</h1>
          </div>
          <p className="text-gray-600">查看用户登录历史和活跃度统计</p>
        </div>
        
        {/* 错误提示 */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700">{error}</p>
            <button
              onClick={() => setError(null)}
              className="mt-2 text-sm text-red-600 hover:text-red-800"
            >
              关闭
            </button>
          </div>
        )}
        
        {/* 统计卡片 */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center">
                <Users className="h-8 w-8 text-blue-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">总用户数</p>
                  <p className="text-2xl font-semibold text-gray-900">{summary.total_users}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center">
                <UserCheck className="h-8 w-8 text-green-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">今日活跃</p>
                  <p className="text-2xl font-semibold text-gray-900">{summary.active_users_today}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center">
                <TrendingUp className="h-8 w-8 text-purple-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">本周活跃</p>
                  <p className="text-2xl font-semibold text-gray-900">{summary.active_users_week}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center">
                <Calendar className="h-8 w-8 text-amber-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">本月活跃</p>
                  <p className="text-2xl font-semibold text-gray-900">{summary.active_users_month}</p>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* 搜索和操作栏 */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
            {/* 搜索框 */}
            <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索用户ID..."
                  value={userIdFilter}
                  onChange={(e) => setUserIdFilter(e.target.value)}
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              
              <div className="relative">
                <Building className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索部门编号..."
                  value={branchFilter}
                  onChange={(e) => setBranchFilter(e.target.value)}
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
            </div>
            
            {/* 操作按钮 */}
            <div className="flex space-x-3">
              <button
                onClick={handleReset}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-indigo-500"
              >
                重置
              </button>
              
              <button
                onClick={handleSearch}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500"
              >
                搜索
              </button>
              
              <button
                onClick={() => loadRecords(currentPage)}
                disabled={loading}
                className="flex items-center px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                刷新
              </button>
            </div>
          </div>
        </div>
        
        {/* 登录记录表格 */}
        <div className="bg-white rounded-lg shadow-sm border">
          {loading ? (
            <div className="p-8 text-center">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-indigo-600" />
              <p className="text-gray-600">加载中...</p>
            </div>
          ) : records.length === 0 ? (
            <div className="p-8 text-center">
              <Clock className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-gray-600">
                {userIdFilter || branchFilter ? '没有找到匹配的登录记录' : '暂无登录记录'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      用户信息
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      部门信息
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      角色信息
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      最后登录时间
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      首次记录时间
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {records.map((record) => (
                    <tr key={record.user_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {record.user_name}
                          </div>
                          <div className="text-sm text-gray-500">
                            ID: {record.user_id}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {record.branch_name}
                          </div>
                          <div className="text-sm text-gray-500">
                            编号: {record.branch_no}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1">
                          {record.role_name_list.map((roleName, index) => (
                            <span
                              key={index}
                              className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800"
                            >
                              {roleName}
                            </span>
                          ))}
                          {record.role_name_list.length === 0 && (
                            <span className="text-sm text-gray-500">无角色</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900">
                          {formatTime(record.last_login_time)}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900">
                          {formatTime(record.created_at)}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          
          {/* 分页 */}
          {totalRecords > 0 && (
            <div className="bg-white px-4 py-3 border-t border-gray-200 sm:px-6">
              <div className="flex items-center justify-between">
                <div className="flex-1 flex justify-between sm:hidden">
                  <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage <= 1}
                    className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                  >
                    上一页
                  </button>
                  <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage >= totalPages}
                    className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                  >
                    下一页
                  </button>
                </div>
                <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm text-gray-700">
                      显示第 <span className="font-medium">{(currentPage - 1) * pageSize + 1}</span> 到{' '}
                      <span className="font-medium">
                        {Math.min(currentPage * pageSize, totalRecords)}
                      </span>{' '}
                      条，共 <span className="font-medium">{totalRecords}</span> 条记录
                    </p>
                  </div>
                  <div>
                    <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                      <button
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage <= 1}
                        className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                      >
                        上一页
                      </button>
                      
                      {/* 页码按钮 */}
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        let pageNum
                        if (totalPages <= 5) {
                          pageNum = i + 1
                        } else if (currentPage <= 3) {
                          pageNum = i + 1
                        } else if (currentPage >= totalPages - 2) {
                          pageNum = totalPages - 4 + i
                        } else {
                          pageNum = currentPage - 2 + i
                        }
                        
                        return (
                          <button
                            key={pageNum}
                            onClick={() => handlePageChange(pageNum)}
                            className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                              pageNum === currentPage
                                ? 'z-10 bg-indigo-50 border-indigo-500 text-indigo-600'
                                : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                            }`}
                          >
                            {pageNum}
                          </button>
                        )
                      })}
                      
                      <button
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={currentPage >= totalPages}
                        className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                      >
                        下一页
                      </button>
                    </nav>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
        
        {/* 额外信息 */}
        {summary && (
          <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">系统活跃度</h3>
              <div className="space-y-3">
                {summary.latest_login_time && (
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500">最新登录时间:</span>
                    <span className="text-sm font-medium text-gray-900">
                      {formatTime(summary.latest_login_time)}
                    </span>
                  </div>
                )}
                {summary.most_active_department && (
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500">最活跃部门:</span>
                    <span className="text-sm font-medium text-gray-900">
                      {summary.most_active_department}
                    </span>
                  </div>
                )}
                {summary.most_active_role && (
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-500">最活跃角色:</span>
                    <span className="text-sm font-medium text-gray-900">
                      {summary.most_active_role}
                    </span>
                  </div>
                )}
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">使用说明</h3>
              <div className="text-sm text-gray-600 space-y-2">
                <p>• 登录记录显示用户最后一次登录的信息</p>
                <p>• 可以按用户ID或部门编号进行搜索</p>
                <p>• 角色信息显示用户当前拥有的所有角色</p>
                <p>• 统计数据每次页面加载时更新</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}