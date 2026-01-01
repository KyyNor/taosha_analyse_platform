/**
 * 部门管理页面
 * 只允许淘沙管理员访问
 */

'use client'

import { useState, useEffect } from 'react'
import { Plus, Edit, Trash2, Building, Search, RefreshCw } from 'lucide-react'
import { useRequireAdmin } from '@/hooks/useAuth'
import { entityApi, ApiError } from '@/lib/api'

// 部门接口
interface Department {
  id: string
  code: string
  name: string
  type: 'department'
  description?: string
  created_at: string
  updated_at: string
}

// 表单数据接口
interface DepartmentFormData {
  code: string
  name: string
  description: string
}

export default function DepartmentsPage() {
  // 权限检查
  const { isAuthenticated, isLoading: authLoading, isAdmin } = useRequireAdmin()
  
  // 状态管理
  const [departments, setDepartments] = useState<Department[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  
  // 模态框状态
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [selectedDepartment, setSelectedDepartment] = useState<Department | null>(null)
  
  // 表单状态
  const [formData, setFormData] = useState<DepartmentFormData>({
    code: '',
    name: '',
    description: ''
  })
  const [formLoading, setFormLoading] = useState(false)
  
  // 加载部门列表
  const loadDepartments = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await entityApi.getEntities('department')
      setDepartments(response.entities || [])
    } catch (err) {
      const error = err as ApiError
      setError(error.message || '加载部门列表失败')
    } finally {
      setLoading(false)
    }
  }
  
  // 初始加载
  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      loadDepartments()
    }
  }, [isAuthenticated, isAdmin])
  
  // 过滤部门
  const filteredDepartments = departments.filter(dept =>
    dept.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    dept.code.toLowerCase().includes(searchTerm.toLowerCase())
  )
  
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
  const handleEdit = (department: Department) => {
    setSelectedDepartment(department)
    setFormData({
      code: department.code,
      name: department.name,
      description: department.description || ''
    })
    setShowEditModal(true)
  }
  
  // 打开删除确认模态框
  const handleDelete = (department: Department) => {
    setSelectedDepartment(department)
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
        type: 'department',
        description: formData.description || null
      })
      
      setShowCreateModal(false)
      resetForm()
      await loadDepartments()
    } catch (err) {
      const error = err as ApiError
      setError(error.message || '创建部门失败')
    } finally {
      setFormLoading(false)
    }
  }
  
  // 提交编辑
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!selectedDepartment) return
    
    try {
      setFormLoading(true)
      await entityApi.updateEntity(selectedDepartment.id, {
        name: formData.name,
        description: formData.description || null
      })
      
      setShowEditModal(false)
      setSelectedDepartment(null)
      resetForm()
      await loadDepartments()
    } catch (err) {
      const error = err as ApiError
      setError(error.message || '更新部门失败')
    } finally {
      setFormLoading(false)
    }
  }
  
  // 确认删除
  const handleDeleteConfirm = async () => {
    if (!selectedDepartment) return
    
    try {
      setFormLoading(true)
      await entityApi.deleteEntity(selectedDepartment.id)
      
      setShowDeleteModal(false)
      setSelectedDepartment(null)
      await loadDepartments()
    } catch (err) {
      const error = err as ApiError
      setError(error.message || '删除部门失败')
    } finally {
      setFormLoading(false)
    }
  }
  
  // 权限检查中
  if (authLoading) {
    return (
      <div className=\"min-h-screen flex items-center justify-center\">
        <div className=\"text-center\">
          <RefreshCw className=\"h-8 w-8 animate-spin mx-auto mb-4 text-blue-600\" />
          <p className=\"text-gray-600\">验证权限中...</p>
        </div>
      </div>
    )
  }
  
  // 无权限访问
  if (!isAuthenticated || !isAdmin) {
    return null // 会被useRequireAdmin重定向
  }
  
  return (
    <div className=\"min-h-screen bg-gray-50 p-6\">
      <div className=\"max-w-7xl mx-auto\">
        {/* 页面标题 */}
        <div className=\"mb-8\">
          <div className=\"flex items-center space-x-3 mb-2\">
            <Building className=\"h-8 w-8 text-blue-600\" />
            <h1 className=\"text-3xl font-bold text-gray-900\">部门管理</h1>
          </div>
          <p className=\"text-gray-600\">管理系统中的部门信息和权限分配</p>
        </div>
        
        {/* 错误提示 */}
        {error && (
          <div className=\"mb-6 bg-red-50 border border-red-200 rounded-lg p-4\">
            <p className=\"text-red-700\">{error}</p>
            <button
              onClick={() => setError(null)}
              className=\"mt-2 text-sm text-red-600 hover:text-red-800\"
            >
              关闭
            </button>
          </div>
        )}
        
        {/* 操作栏 */}
        <div className=\"bg-white rounded-lg shadow-sm border p-6 mb-6\">
          <div className=\"flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0\">
            {/* 搜索框 */}
            <div className=\"relative flex-1 max-w-md\">
              <Search className=\"absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400\" />
              <input
                type=\"text\"
                placeholder=\"搜索部门名称或编码...\"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className=\"pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent\"
              />
            </div>
            
            {/* 操作按钮 */}
            <div className=\"flex space-x-3\">
              <button
                onClick={loadDepartments}
                disabled={loading}
                className=\"flex items-center px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 disabled:opacity-50\"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                刷新
              </button>
              
              <button
                onClick={handleCreate}
                className=\"flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500\"
              >
                <Plus className=\"h-4 w-4 mr-2\" />
                新建部门
              </button>
            </div>
          </div>
        </div>
        
        {/* 部门列表 */}
        <div className=\"bg-white rounded-lg shadow-sm border\">
          {loading ? (
            <div className=\"p-8 text-center\">
              <RefreshCw className=\"h-8 w-8 animate-spin mx-auto mb-4 text-blue-600\" />
              <p className=\"text-gray-600\">加载中...</p>
            </div>
          ) : filteredDepartments.length === 0 ? (
            <div className=\"p-8 text-center\">
              <Building className=\"h-12 w-12 mx-auto mb-4 text-gray-400\" />
              <p className=\"text-gray-600\">
                {searchTerm ? '没有找到匹配的部门' : '暂无部门数据'}
              </p>
            </div>
          ) : (
            <div className=\"overflow-x-auto\">
              <table className=\"w-full\">
                <thead className=\"bg-gray-50 border-b\">
                  <tr>
                    <th className=\"px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider\">
                      部门信息
                    </th>
                    <th className=\"px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider\">
                      描述
                    </th>
                    <th className=\"px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider\">
                      创建时间
                    </th>
                    <th className=\"px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider\">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className=\"divide-y divide-gray-200\">
                  {filteredDepartments.map((department) => (
                    <tr key={department.id} className=\"hover:bg-gray-50\">
                      <td className=\"px-6 py-4\">
                        <div>
                          <div className=\"text-sm font-medium text-gray-900\">
                            {department.name}
                          </div>
                          <div className=\"text-sm text-gray-500\">
                            编码: {department.code}
                          </div>
                        </div>
                      </td>
                      <td className=\"px-6 py-4\">
                        <div className=\"text-sm text-gray-900\">
                          {department.description || '-'}
                        </div>
                      </td>
                      <td className=\"px-6 py-4\">
                        <div className=\"text-sm text-gray-900\">
                          {new Date(department.created_at).toLocaleDateString('zh-CN')}
                        </div>
                      </td>
                      <td className=\"px-6 py-4 text-right\">
                        <div className=\"flex items-center justify-end space-x-2\">
                          <button
                            onClick={() => handleEdit(department)}
                            className=\"p-2 text-blue-600 hover:bg-blue-50 rounded-lg\"
                            title=\"编辑\"
                          >
                            <Edit className=\"h-4 w-4\" />
                          </button>
                          <button
                            onClick={() => handleDelete(department)}
                            className=\"p-2 text-red-600 hover:bg-red-50 rounded-lg\"
                            title=\"删除\"
                          >
                            <Trash2 className=\"h-4 w-4\" />
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
      
      {/* 创建部门模态框 */}
      {showCreateModal && (
        <div className=\"fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50\">
          <div className=\"bg-white rounded-lg max-w-md w-full p-6\">
            <h3 className=\"text-lg font-semibold mb-4\">新建部门</h3>
            
            <form onSubmit={handleCreateSubmit}>
              <div className=\"space-y-4\">
                <div>
                  <label className=\"block text-sm font-medium text-gray-700 mb-1\">
                    部门编码 *
                  </label>
                  <input
                    type=\"text\"
                    required
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                    className=\"w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent\"
                    placeholder=\"请输入部门编码\"
                  />
                </div>
                
                <div>
                  <label className=\"block text-sm font-medium text-gray-700 mb-1\">
                    部门名称 *
                  </label>
                  <input
                    type=\"text\"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className=\"w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent\"
                    placeholder=\"请输入部门名称\"
                  />
                </div>
                
                <div>
                  <label className=\"block text-sm font-medium text-gray-700 mb-1\">
                    描述
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                    className=\"w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent\"
                    placeholder=\"请输入部门描述\"
                  />
                </div>
              </div>
              
              <div className=\"flex justify-end space-x-3 mt-6\">
                <button
                  type=\"button\"
                  onClick={() => setShowCreateModal(false)}
                  className=\"px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50\"
                >
                  取消
                </button>
                <button
                  type=\"submit\"
                  disabled={formLoading}
                  className=\"px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50\"
                >
                  {formLoading ? '创建中...' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      
      {/* 编辑部门模态框 */}
      {showEditModal && selectedDepartment && (
        <div className=\"fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50\">
          <div className=\"bg-white rounded-lg max-w-md w-full p-6\">
            <h3 className=\"text-lg font-semibold mb-4\">编辑部门</h3>
            
            <form onSubmit={handleEditSubmit}>
              <div className=\"space-y-4\">
                <div>
                  <label className=\"block text-sm font-medium text-gray-700 mb-1\">
                    部门编码
                  </label>
                  <input
                    type=\"text\"
                    value={formData.code}
                    disabled
                    className=\"w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500\"
                  />
                  <p className=\"text-xs text-gray-500 mt-1\">部门编码不可修改</p>
                </div>
                
                <div>
                  <label className=\"block text-sm font-medium text-gray-700 mb-1\">
                    部门名称 *
                  </label>
                  <input
                    type=\"text\"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className=\"w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent\"
                    placeholder=\"请输入部门名称\"
                  />
                </div>
                
                <div>
                  <label className=\"block text-sm font-medium text-gray-700 mb-1\">
                    描述
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                    className=\"w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent\"
                    placeholder=\"请输入部门描述\"
                  />
                </div>
              </div>
              
              <div className=\"flex justify-end space-x-3 mt-6\">
                <button
                  type=\"button\"
                  onClick={() => setShowEditModal(false)}
                  className=\"px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50\"
                >
                  取消
                </button>
                <button
                  type=\"submit\"
                  disabled={formLoading}
                  className=\"px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50\"
                >
                  {formLoading ? '保存中...' : '保存'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      
      {/* 删除确认模态框 */}
      {showDeleteModal && selectedDepartment && (
        <div className=\"fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50\">
          <div className=\"bg-white rounded-lg max-w-md w-full p-6\">
            <h3 className=\"text-lg font-semibold mb-4 text-red-600\">确认删除</h3>
            
            <p className=\"text-gray-700 mb-4\">
              您确定要删除部门 <strong>{selectedDepartment.name}</strong> 吗？
            </p>
            
            <p className=\"text-sm text-gray-500 mb-6\">
              删除部门将同时删除该部门的所有权限配置，此操作不可撤销。
            </p>
            
            <div className=\"flex justify-end space-x-3\">
              <button
                onClick={() => setShowDeleteModal(false)}
                className=\"px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50\"
              >
                取消
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={formLoading}
                className=\"px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50\"
              >
                {formLoading ? '删除中...' : '确认删除'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}