/**
 * 权限分配页面
 * 只允许淘沙管理员访问
 */

'use client'

import { useState, useEffect } from 'react'
import { Shield, Users, FileText, Search, RefreshCw, Save, Copy, Eye } from 'lucide-react'
import { useRequireAdmin } from '@/hooks/useAuth'
import { permissionApi, entityApi, ApiError } from '@/lib/api'

// 实体接口
interface Entity {
  id: string
  code: string
  name: string
  type: 'department' | 'role'
}

// 页面接口
interface Page {
  id: string
  path: string
  name: string
  description?: string
}

// 权限矩阵接口
interface PermissionMatrix {
  entities: Array<{
    id: string
    code: string
    name: string
    type: string
  }>
  pages: Array<{
    id: string
    path: string
    name: string
  }>
  matrix: Record<string, Record<string, boolean>>
}

export default function PermissionsPage() {
  // 权限检查
  const { isAuthenticated, isLoading: authLoading, isAdmin } = useRequireAdmin()
  
  // 状态管理
  const [entities, setEntities] = useState<Entity[]>([])
  const [pages, setPages] = useState<Page[]>([])
  const [matrix, setMatrix] = useState<Record<string, Record<string, boolean>>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  
  // 过滤状态
  const [entityFilter, setEntityFilter] = useState('')
  const [pageFilter, setPageFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState<'all' | 'department' | 'role'>('all')
  
  // 选择状态
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null)
  const [showCopyModal, setShowCopyModal] = useState(false)
  const [copySource, setCopySource] = useState<string | null>(null)
  const [copyTarget, setCopyTarget] = useState<string | null>(null)
  
  // 加载数据
  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // 并行加载数据
      const [entitiesResponse, pagesResponse, matrixResponse] = await Promise.all([
        entityApi.getEntities(),
        permissionApi.getPages(),
        permissionApi.getPermissionMatrix()
      ])
      
      setEntities(entitiesResponse.entities || [])
      setPages(pagesResponse.pages || [])
      setMatrix(matrixResponse.matrix || {})
      
    } catch (err) {
      const error = err as ApiError
      setError(error.message || '加载权限数据失败')
    } finally {
      setLoading(false)
    }
  }
  
  // 初始加载
  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      loadData()
    }
  }, [isAuthenticated, isAdmin])
  
  // 过滤实体
  const filteredEntities = entities.filter(entity => {
    const matchesName = entity.name.toLowerCase().includes(entityFilter.toLowerCase()) ||
                       entity.code.toLowerCase().includes(entityFilter.toLowerCase())
    const matchesType = typeFilter === 'all' || entity.type === typeFilter
    return matchesName && matchesType
  })
  
  // 过滤页面
  const filteredPages = pages.filter(page =>
    page.name.toLowerCase().includes(pageFilter.toLowerCase()) ||
    page.path.toLowerCase().includes(pageFilter.toLowerCase())
  )
  
  // 切换权限
  const togglePermission = (entityId: string, pageId: string) => {
    setMatrix(prev => ({
      ...prev,
      [entityId]: {
        ...prev[entityId],
        [pageId]: !prev[entityId]?.[pageId]
      }
    }))
  }
  
  // 保存权限更改
  const savePermissions = async () => {
    try {
      setSaving(true)
      setError(null)
      
      // 构建批量分配请求
      const assignments = Object.entries(matrix).map(([entityId, pagePermissions]) => ({
        entity_id: entityId,
        page_ids: Object.entries(pagePermissions)
          .filter(([_, hasPermission]) => hasPermission)
          .map(([pageId]) => pageId)
      }))
      
      await permissionApi.assignPermissions(assignments[0]?.entity_id || '', assignments[0]?.page_ids || [])
      
      // 重新加载数据以确保同步
      await loadData()
      
    } catch (err) {
      const error = err as ApiError
      setError(error.message || '保存权限失败')
    } finally {
      setSaving(false)
    }
  }
  
  // 复制权限
  const handleCopyPermissions = async () => {
    if (!copySource || !copyTarget) return
    
    try {
      setSaving(true)
      setError(null)
      
      // 调用复制权限API
      await permissionApi.copyPermissions(copySource, copyTarget)
      
      setShowCopyModal(false)
      setCopySource(null)
      setCopyTarget(null)
      
      // 重新加载数据
      await loadData()
      
    } catch (err) {
      const error = err as ApiError
      setError(error.message || '复制权限失败')
    } finally {
      setSaving(false)
    }
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
      <div className="max-w-full mx-auto">
        {/* 页面标题 */}
        <div className="mb-8">
          <div className="flex items-center space-x-3 mb-2">
            <Shield className="h-8 w-8 text-purple-600" />
            <h1 className="text-3xl font-bold text-gray-900">权限分配</h1>
          </div>
          <p className="text-gray-600">为部门和角色分配页面访问权限</p>
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
        
        {/* 操作栏 */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
            {/* 过滤器 */}
            <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索实体..."
                  value={entityFilter}
                  onChange={(e) => setEntityFilter(e.target.value)}
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>
              
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索页面..."
                  value={pageFilter}
                  onChange={(e) => setPageFilter(e.target.value)}
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>
              
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value as any)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="all">所有类型</option>
                <option value="department">部门</option>
                <option value="role">角色</option>
              </select>
            </div>
            
            {/* 操作按钮 */}
            <div className="flex space-x-3">
              <button
                onClick={() => setShowCopyModal(true)}
                className="flex items-center px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-purple-500"
              >
                <Copy className="h-4 w-4 mr-2" />
                复制权限
              </button>
              
              <button
                onClick={loadData}
                disabled={loading}
                className="flex items-center px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                刷新
              </button>
              
              <button
                onClick={savePermissions}
                disabled={saving}
                className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
              >
                <Save className="h-4 w-4 mr-2" />
                {saving ? '保存中...' : '保存更改'}
              </button>
            </div>
          </div>
        </div>
        
        {/* 权限矩阵 */}
        <div className="bg-white rounded-lg shadow-sm border">
          {loading ? (
            <div className="p-8 text-center">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-purple-600" />
              <p className="text-gray-600">加载权限矩阵中...</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-0 bg-gray-50 z-10">
                      实体
                    </th>
                    {filteredPages.map((page) => (
                      <th
                        key={page.id}
                        className="px-2 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider min-w-[120px]"
                        title={page.path}
                      >
                        <div className="truncate">
                          {page.name}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredEntities.map((entity) => (
                    <tr
                      key={entity.id}
                      className={`hover:bg-gray-50 ${
                        selectedEntity === entity.id ? 'bg-blue-50' : ''
                      }`}
                    >
                      <td className="px-4 py-4 sticky left-0 bg-white z-10 border-r">
                        <div className="flex items-center space-x-2">
                          {entity.type === 'department' ? (
                            <Users className="h-4 w-4 text-blue-500" />
                          ) : (
                            <Shield className="h-4 w-4 text-green-500" />
                          )}
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {entity.name}
                            </div>
                            <div className="text-xs text-gray-500">
                              {entity.code}
                            </div>
                          </div>
                        </div>
                      </td>
                      {filteredPages.map((page) => (
                        <td key={page.id} className="px-2 py-4 text-center">
                          <input
                            type="checkbox"
                            checked={matrix[entity.id]?.[page.id] || false}
                            onChange={() => togglePermission(entity.id, page.id)}
                            className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {filteredEntities.length === 0 && (
                <div className="p-8 text-center">
                  <Users className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-gray-600">没有找到匹配的实体</p>
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* 统计信息 */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow-sm border p-4">
            <div className="flex items-center">
              <Users className="h-8 w-8 text-blue-500" />
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500">总实体数</p>
                <p className="text-2xl font-semibold text-gray-900">{entities.length}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border p-4">
            <div className="flex items-center">
              <FileText className="h-8 w-8 text-green-500" />
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500">总页面数</p>
                <p className="text-2xl font-semibold text-gray-900">{pages.length}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border p-4">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-purple-500" />
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500">权限总数</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {Object.values(matrix).reduce((total, entityPerms) => 
                    total + Object.values(entityPerms).filter(Boolean).length, 0
                  )}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border p-4">
            <div className="flex items-center">
              <Eye className="h-8 w-8 text-amber-500" />
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500">覆盖率</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {entities.length > 0 && pages.length > 0 
                    ? Math.round((Object.values(matrix).reduce((total, entityPerms) => 
                        total + Object.values(entityPerms).filter(Boolean).length, 0
                      ) / (entities.length * pages.length)) * 100)
                    : 0}%
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* 复制权限模态框 */}
      {showCopyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-semibold mb-4">复制权限</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  源实体（复制自）
                </label>
                <select
                  value={copySource || ''}
                  onChange={(e) => setCopySource(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  <option value="">请选择源实体</option>
                  {entities.map((entity) => (
                    <option key={entity.id} value={entity.id}>
                      {entity.name} ({entity.type === 'department' ? '部门' : '角色'})
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  目标实体（复制到）
                </label>
                <select
                  value={copyTarget || ''}
                  onChange={(e) => setCopyTarget(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  <option value="">请选择目标实体</option>
                  {entities
                    .filter(entity => entity.id !== copySource)
                    .map((entity) => (
                      <option key={entity.id} value={entity.id}>
                        {entity.name} ({entity.type === 'department' ? '部门' : '角色'})
                      </option>
                    ))}
                </select>
              </div>
              
              {copySource && copyTarget && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-sm text-blue-700">
                    将复制 <strong>{entities.find(e => e.id === copySource)?.name}</strong> 的所有权限到 
                    <strong>{entities.find(e => e.id === copyTarget)?.name}</strong>
                  </p>
                  <p className="text-xs text-blue-600 mt-1">
                    目标实体的现有权限将被覆盖
                  </p>
                </div>
              )}
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => {
                  setShowCopyModal(false)
                  setCopySource(null)
                  setCopyTarget(null)
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleCopyPermissions}
                disabled={!copySource || !copyTarget || saving}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
              >
                {saving ? '复制中...' : '确认复制'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}