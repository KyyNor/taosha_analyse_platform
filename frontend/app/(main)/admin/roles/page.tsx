/**
 * 角色管理页面
 * 只允许淘沙管理员访问
 */

'use client'

import { useState, useEffect } from 'react'
import { Plus, Edit, Trash2, Users, Search, RefreshCw, Shield } from 'lucide-react'
import { useRequireAdmin } from '@/hooks/useAuth'
import { entityApi, ApiError } from '@/lib/api'

// 角色接口
interface Role {
  id: string
  code: string
  name: string
  type: 'role'
  description?: string
  created_at: string
  updated_at: string
}

// 表单数据接口
interface RoleFormData {
  code: string
  name: string
  description: string
}

export default function RolesPage() {
  // 权限检查
  const { isAuthenticated, isLoading: authLoading, isAdmin } = useRequireAdmin()
  
  // 状态管理
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  
  // 模态框状态
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [selectedRole, setSelectedRole] = useState<Role | null>(null)
  
  // 表单状态
  const [formData, setFormData] = useState<RoleFormData>({
    code: '',
    name: '',
    description: ''
  })
  const [formLoading, setFormLoading] = useState(false)
  
  // 加载角色列表
  const loadRoles = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await entityApi.getEntities('role')
      setRoles(response.entities || [])
    } catch (err) {
      const error = err as ApiError
      setError(error.message || '加载角色列表失败')
    } finally {
      setLoading(false)
    }
  }
  
  // 初始加载
  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      loadRoles()
    }
  }, [isAuthenticated, isAdmin])
  
  // 过滤角色
  const filteredRoles = roles.filter(role =>
    role.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    role.code.toLowerCase().includes(searchTerm.toLowerCase())
  )
  
  // 检查是否为系统关键角色
  const isSystemRole = (roleCode: string) => {
    return roleCode === '淘沙管理员' || roleCode === 'taosha_admin'
  }
  
  // 重置表单
  const resetForm = () => {
    setFormData({ code: '', name: '', description: '' })
  }
  
  // 打开创建模态框
  const handleCreate = () => {
    resetForm()
    setShowCreateModal(true)
  }
  
  // 打开编辑模态框
  const handleEdit = (role: Role) => {
    setSelectedRole(role)
    setFormData({
      code: role.code,
      name: role.name,
      description: role.description || ''
    })
    setShowEditModal(true)
  }
  
  // 打开删除确认模态框
  const handleDelete = (role: Role) => {
    setSelectedRole(role)
    setShowDeleteModal(true)
  }
  
  // 提交创建
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      setFormLoading(true)
      await entityApi.createEntity({
        code: formData.code,
        name: formData.name,
        type: 'role',
        description: formData.description || null
      })
      
      setShowCreateModal(false)
      resetForm()
      await loadRoles()
    } catch (err) {
      const error = err as ApiError
      setError(error.message || '创建角色失败')
    } finally {
      setFormLoading(false)
    }
  }
  
  // 提交编辑
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!selectedRole) return
    
    try {
      setFormLoading(true)
      await entityApi.updateEntity(selectedRole.id, {
        name: formData.name,
        description: formData.description || null
      })
      
      setShowEditModal(false)
      setSelectedRole(null)
      resetForm()
      await loadRoles()
    } catch (err) {
      const error = err as ApiError
      setError(error.message || '更新角色失败')
    } finally {
      setFormLoading(false)
    }
  }
  
  // 确认删除
  const handleDeleteConfirm = async () => {
    if (!selectedRole) return
    
    try {
      setFormLoading(true)
      await entityApi.deleteEntity(selectedRole.id)
      
      setShowDeleteModal(false)
      setSelectedRole(null)
      await loadRoles()
    } catch (err) {
      const error = err as ApiError
      setError(error.message || '删除角色失败')
    } finally {
      setFormLoading(false)
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
      <div className="max-w-7xl mx-auto">
        {/* 页面标题 */}
        <div className="mb-8">
          <div className="flex items-center space-x-3 mb-2">
            <Users className="h-8 w-8 text-green-600" />
            <h1 className="text-3xl font-bold text-gray-900">角色管理</h1>
          </div>
          <p className="text-gray-600">管理系统中的角色信息和权限分配</p>
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
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
            {/* 搜索框 */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="搜索角色名称或编码..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
              />
            </div>
            
            {/* 操作按钮 */}
            <div className="flex space-x-3">
              <button
                onClick={loadRoles}
                disabled={loading}
                className="flex items-center px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-green-500 disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                刷新
              </button>
              
              <button
                onClick={handleCreate}
                className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 focus:ring-2 focus:ring-green-500"
              >
                <Plus className="h-4 w-4 mr-2" />
                新建角色
              </button>
            </div>
          </div>
        </div>
        
        {/* 角色列表 */}
        <div className="bg-white rounded-lg shadow-sm border">
          {loading ? (
            <div className="p-8 text-center">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-green-600" />
              <p className="text-gray-600">加载中...</p>
            </div>
          ) : filteredRoles.length === 0 ? (
            <div className="p-8 text-center">
              <Users className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-gray-600">
                {searchTerm ? '没有找到匹配的角色' : '暂无角色数据'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      角色信息
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      描述
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      类型
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      创建时间
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredRoles.map((role) => (
                    <tr key={role.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          {isSystemRole(role.code) && (
                            <div title="系统角色">
                              <Shield className="h-4 w-4 text-amber-500 mr-2" />
                            </div>
                          )}
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {role.name}
                            </div>
                            <div className="text-sm text-gray-500">
                              编码: {role.code}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900">
                          {role.description || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          isSystemRole(role.code)
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-green-100 text-green-800'
                        }`}>
                          {isSystemRole(role.code) ? '系统角色' : '自定义角色'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900">
                          {new Date(role.created_at).toLocaleDateString('zh-CN')}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => handleEdit(role)}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                            title="编辑"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(role)}
                            disabled={isSystemRole(role.code)}
                            className={`p-2 rounded-lg ${
                              isSystemRole(role.code)
                                ? 'text-gray-400 cursor-not-allowed'
                                : 'text-red-600 hover:bg-red-50'
                            }`}
                            title={isSystemRole(role.code) ? '系统角色不可删除' : '删除'}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
      
      {/* 创建角色模态框 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-semibold mb-4">新建角色</h3>
            
            <form onSubmit={handleCreateSubmit}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    角色编码 *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="请输入角色编码"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    建议使用英文或拼音，如：data_analyst
                  </p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    角色名称 *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="请输入角色名称"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    描述
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="请输入角色描述"
                  />
                </div>
              </div>
              
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {formLoading ? '创建中...' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      
      {/* 编辑角色模态框 */}
      {showEditModal && selectedRole && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-semibold mb-4">编辑角色</h3>
            
            <form onSubmit={handleEditSubmit}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    角色编码
                  </label>
                  <input
                    type="text"
                    value={formData.code}
                    disabled
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">角色编码不可修改</p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    角色名称 *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    disabled={isSystemRole(selectedRole.code)}
                    className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent ${
                      isSystemRole(selectedRole.code) ? 'bg-gray-50 text-gray-500' : ''
                    }`}
                    placeholder="请输入角色名称"
                  />
                  {isSystemRole(selectedRole.code) && (
                    <p className="text-xs text-amber-600 mt-1">系统角色名称不可修改</p>
                  )}
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    描述
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="请输入角色描述"
                  />
                </div>
              </div>
              
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {formLoading ? '保存中...' : '保存'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      
      {/* 删除确认模态框 */}
      {showDeleteModal && selectedRole && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-semibold mb-4 text-red-600">确认删除</h3>
            
            {isSystemRole(selectedRole.code) ? (
              <div>
                <p className="text-gray-700 mb-4">
                  <strong>{selectedRole.name}</strong> 是系统关键角色，不能删除。
                </p>
                <p className="text-sm text-amber-600 mb-6">
                  系统角色对平台正常运行至关重要，请勿删除。
                </p>
                <div className="flex justify-end">
                  <button
                    onClick={() => setShowDeleteModal(false)}
                    className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                  >
                    关闭
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <p className="text-gray-700 mb-4">
                  您确定要删除角色 <strong>{selectedRole.name}</strong> 吗？
                </p>
                
                <p className="text-sm text-gray-500 mb-6">
                  删除角色将同时删除该角色的所有权限配置，此操作不可撤销。
                </p>
                
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => setShowDeleteModal(false)}
                    className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleDeleteConfirm}
                    disabled={formLoading}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                  >
                    {formLoading ? '删除中...' : '确认删除'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}