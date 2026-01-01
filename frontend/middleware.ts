/**
 * Next.js 权限中间件
 * 实现路由级权限检查和token验证
 */

import { NextRequest, NextResponse } from 'next/server'
import { jwtDecode } from 'jwt-decode'

// 定义用户信息接口
interface UserInfo {
  user_id: string
  user_name: string
  branch_no: string
  branch_name: string
  role_id_list: string[]
  access_time: string
  exp: number
  iat: number
}

// 定义权限检查结果接口
interface PermissionCheckResult {
  hasAccess: boolean
  reason?: 'no_token' | 'invalid_token' | 'expired_token' | 'no_permission'
  userInfo?: UserInfo
}

// 不需要权限检查的公共路径
const PUBLIC_PATHS = [
  '/info',
  '/api/health',
  '/_next',
  '/favicon.ico',
  '/static',
  '/images',
  '/fonts'
]

// 管理员专用路径
const ADMIN_PATHS = [
  '/admin/departments',
  '/admin/roles', 
  '/admin/permissions',
  '/admin/login-records'
]

/**
 * 检查路径是否为公共路径
 */
function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some(path => pathname.startsWith(path))
}

/**
 * 检查路径是否需要管理员权限
 */
function isAdminPath(pathname: string): boolean {
  return ADMIN_PATHS.some(path => pathname.startsWith(path))
}

/**
 * 从cookie中获取token
 */
function getTokenFromCookies(request: NextRequest): string | null {
  const authToken = request.cookies.get('auth_token')?.value
  if (authToken) {
    return authToken
  }
  
  // 也尝试从Authorization header获取
  const authHeader = request.headers.get('authorization')
  if (authHeader && authHeader.startsWith('Bearer ')) {
    return authHeader.substring(7)
  }
  
  return null
}

/**
 * 验证JWT token并解析用户信息
 */
function validateToken(token: string): { valid: boolean; userInfo?: UserInfo; reason?: string } {
  try {
    const decoded = jwtDecode<UserInfo>(token)
    
    // 检查token是否过期
    const now = Math.floor(Date.now() / 1000)
    if (decoded.exp && decoded.exp < now) {
      return { valid: false, reason: 'expired_token' }
    }
    
    // 检查必要字段
    if (!decoded.user_id || !decoded.user_name || !decoded.branch_no || !decoded.role_id_list) {
      return { valid: false, reason: 'invalid_token' }
    }
    
    return { valid: true, userInfo: decoded }
    
  } catch (error) {
    console.error('Token validation error:', error)
    return { valid: false, reason: 'invalid_token' }
  }
}

/**
 * 检查用户是否为管理员
 */
function isAdminUser(userInfo: UserInfo): boolean {
  return userInfo.role_id_list.includes('淘沙管理员') || 
         userInfo.role_id_list.includes('taosha_admin')
}

/**
 * 调用后端API检查页面访问权限
 */
async function checkPageAccess(token: string, pagePath: string): Promise<boolean> {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
    
    const response = await fetch(`${backendUrl}/api/permissions/check-access`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ page_path: pagePath })
    })
    
    if (response.ok) {
      const result = await response.json()
      return result.has_access === true
    }
    
    // 如果API调用失败，默认拒绝访问
    return false
    
  } catch (error) {
    console.error('Page access check error:', error)
    // API调用失败时，默认拒绝访问
    return false
  }
}

/**
 * 执行权限检查
 */
async function performPermissionCheck(request: NextRequest): Promise<PermissionCheckResult> {
  const pathname = request.nextUrl.pathname
  
  // 1. 获取token
  const token = getTokenFromCookies(request)
  if (!token) {
    return { hasAccess: false, reason: 'no_token' }
  }
  
  // 2. 验证token
  const tokenValidation = validateToken(token)
  if (!tokenValidation.valid) {
    return { 
      hasAccess: false, 
      reason: tokenValidation.reason as 'invalid_token' | 'expired_token'
    }
  }
  
  const userInfo = tokenValidation.userInfo!
  
  // 3. 检查管理员路径
  if (isAdminPath(pathname)) {
    if (!isAdminUser(userInfo)) {
      return { hasAccess: false, reason: 'no_permission', userInfo }
    }
    // 管理员用户访问管理员路径，直接允许
    return { hasAccess: true, userInfo }
  }
  
  // 4. 对于其他路径，调用后端API检查权限
  try {
    const hasAccess = await checkPageAccess(token, pathname)
    return { 
      hasAccess, 
      reason: hasAccess ? undefined : 'no_permission',
      userInfo 
    }
  } catch (error) {
    console.error('Permission check failed:', error)
    return { hasAccess: false, reason: 'no_permission', userInfo }
  }
}

/**
 * 创建重定向到Info页面的响应
 */
function createInfoRedirect(request: NextRequest, reason: string, userInfo?: UserInfo): NextResponse {
  const url = new URL('/info', request.url)
  url.searchParams.set('reason', reason)
  
  if (userInfo) {
    url.searchParams.set('user_name', userInfo.user_name)
    url.searchParams.set('user_id', userInfo.user_id)
  }
  
  return NextResponse.redirect(url)
}

/**
 * Next.js 中间件主函数
 */
export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname
  
  // 跳过公共路径
  if (isPublicPath(pathname)) {
    return NextResponse.next()
  }
  
  // 执行权限检查
  const permissionResult = await performPermissionCheck(request)
  
  if (!permissionResult.hasAccess) {
    // 根据不同的原因重定向到Info页面
    return createInfoRedirect(request, permissionResult.reason!, permissionResult.userInfo)
  }
  
  // 权限检查通过，继续处理请求
  const response = NextResponse.next()
  
  // 在响应头中添加用户信息（可选，供页面组件使用）
  if (permissionResult.userInfo) {
    response.headers.set('X-User-ID', permissionResult.userInfo.user_id)
    response.headers.set('X-User-Name', encodeURIComponent(permissionResult.userInfo.user_name))
    response.headers.set('X-Branch-Name', encodeURIComponent(permissionResult.userInfo.branch_name))
  }
  
  return response
}

/**
 * 中间件配置
 * 定义哪些路径需要经过中间件处理
 */
export const config = {
  matcher: [
    /*
     * 匹配所有路径，除了：
     * - api routes (以 /api/ 开头)
     * - _next/static (静态文件)
     * - _next/image (图片优化)
     * - favicon.ico (网站图标)
     * - public文件夹中的文件
     */
    '/((?!api|_next/static|_next/image|favicon.ico|static|images|fonts).*)',
  ],
}