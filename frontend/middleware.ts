/**
 * Next.js 权限中间件
 * 实现路由级权限检查和token验证
 */

import { NextRequest, NextResponse } from 'next/server'

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
 * 调用后端API验证token并检查权限
 */
async function checkTokenAndPermission(token: string, pagePath: string): Promise<{
  valid: boolean
  isAdmin?: boolean
  hasPageAccess?: boolean
  userInfo?: any
  reason?: string
}> {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:50020'
    
    // 首先验证token并获取用户信息
    const userResponse = await fetch(`${backendUrl}/api/taosha/v1/login-records/current/info`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })
    
    if (!userResponse.ok) {
      if (userResponse.status === 401) {
        return { valid: false, reason: 'expired_token' }
      } else if (userResponse.status === 403) {
        return { valid: false, reason: 'no_permission' }
      } else {
        return { valid: false, reason: 'invalid_token' }
      }
    }
    
    const userInfo = await userResponse.json()
    
    // 检查是否为管理员
    const isAdmin = userInfo.role_id_list?.includes('ADMIN') || 
                   userInfo.role_id_list?.includes('淘沙管理员') || 
                   userInfo.role_id_list?.includes('taosha_admin')
    
    // 如果是管理员路径，直接检查管理员权限
    if (isAdminPath(pagePath)) {
      return {
        valid: true,
        isAdmin,
        hasPageAccess: isAdmin,
        userInfo,
        reason: isAdmin ? undefined : 'no_permission'
      }
    }
    
    // 对于其他路径，假设有权限（具体权限检查在页面组件中进行）
    return {
      valid: true,
      isAdmin,
      hasPageAccess: true,
      userInfo
    }
    
  } catch (error) {
    console.error('Token validation error:', error)
    return { valid: false, reason: 'invalid_token' }
  }
}

/**
 * 创建重定向到Info页面的响应
 */
function createInfoRedirect(request: NextRequest, reason: string, userInfo?: any): NextResponse {
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || ''
  const url = new URL(`${basePath}/info`, request.url)
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
  
  // 获取token
  const token = getTokenFromCookies(request)
  if (!token) {
    return createInfoRedirect(request, 'no_token')
  }
  
  // 验证token并检查权限
  const result = await checkTokenAndPermission(token, pathname)
  
  if (!result.valid) {
    return createInfoRedirect(request, result.reason!, result.userInfo)
  }
  
  // 如果是管理员路径但用户不是管理员
  if (isAdminPath(pathname) && !result.hasPageAccess) {
    return createInfoRedirect(request, 'no_permission', result.userInfo)
  }
  
  // 权限检查通过，继续处理请求
  const response = NextResponse.next()
  
  // 在响应头中添加用户信息（可选，供页面组件使用）
  if (result.userInfo) {
    response.headers.set('X-User-ID', result.userInfo.user_id)
    response.headers.set('X-User-Name', encodeURIComponent(result.userInfo.user_name))
    response.headers.set('X-Branch-Name', encodeURIComponent(result.userInfo.branch_name))
    response.headers.set('X-Is-Admin', result.isAdmin ? 'true' : 'false')
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