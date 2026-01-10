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
 * 从多个来源获取token（优先级：SearchParam > Cookie > Header）
 */
function getTokenFromRequest(request: NextRequest): { token: string | null, fromSearchParam: boolean } {
  // 1. 优先从URL参数获取token（首次跳转）
  const searchParams = request.nextUrl.searchParams
  const tokenFromParam = searchParams.get('token')
  if (tokenFromParam) {
    return { token: tokenFromParam, fromSearchParam: true }
  }
  
  // 2. 从cookie获取token（后续访问）
  const authToken = request.cookies.get('auth_token')?.value
  if (authToken) {
    return { token: authToken, fromSearchParam: false }
  }
  
  // 3. 从Authorization header获取token（API调用）
  const authHeader = request.headers.get('authorization')
  if (authHeader && authHeader.startsWith('Bearer ')) {
    return { token: authHeader.substring(7), fromSearchParam: false }
  }
  
  return { token: null, fromSearchParam: false }
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
    // 中间件运行在服务器端，直接调用后端API（不通过Next.js代理）
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:50020'

    // 1. 首先验证token并获取用户信息
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

    // 2. 检查是否为管理员（完全依赖后端返回的 is_admin 字段）
    // 后端会根据实体的 is_admin 字段进行判断，不再硬编码角色名称
    const isAdmin = userInfo.is_admin === true

    // 3. 如果是管理员路径，直接检查管理员权限
    if (isAdminPath(pagePath)) {
      return {
        valid: true,
        isAdmin,
        hasPageAccess: isAdmin,
        userInfo,
        reason: isAdmin ? undefined : 'no_permission'
      }
    }

    // 4. 对于其他路径，调用权限检查API
    try {
      const permissionResponse = await fetch(`${backendUrl}/api/taosha/v1/permissions/check-access`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ page_path: pagePath })
      })

      if (!permissionResponse.ok) {
        console.error(`Permission check failed: ${permissionResponse.status}`)
        // 权限检查API失败时，采用安全优先策略：拒绝访问
        return {
          valid: true,
          isAdmin,
          hasPageAccess: false,
          userInfo,
          reason: 'no_permission'  // 统一使用标准code
        }
      }

      const permissionData = await permissionResponse.json()

      // 统一reason为标准code，确保info页面能正确显示提示
      // 优先使用后端返回的reason，如果没有则使用默认值
      let finalReason: string | undefined
      if (permissionData.has_access) {
        finalReason = undefined
      } else {
        // 后端应该返回标准reason code: 'no_permission' | 'page_not_found'
        // 如果后端返回了中文reason，映射为标准code
        finalReason = permissionData.reason || 'no_permission'
      }

      return {
        valid: true,
        isAdmin: permissionData.is_admin || isAdmin,
        hasPageAccess: permissionData.has_access,
        userInfo,
        reason: finalReason
      }

    } catch (error) {
      console.error('Permission check API error:', error)
      // API调用失败时，采用安全优先策略：拒绝访问
      return {
        valid: true,
        isAdmin,
        hasPageAccess: false,
        userInfo,
        reason: 'no_permission'  // 统一使用标准code
      }
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
  const url = new URL(request.url)
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || ''
  url.pathname = `${basePath}/info`
  url.search = '' // 清除现有的查询参数
  url.searchParams.set('reason', reason)
  
  if (userInfo) {
    url.searchParams.set('user_name', userInfo.user_name)
    url.searchParams.set('user_id', userInfo.user_id)
  }
  
  return NextResponse.redirect(url)
}

/**
 * 创建带token cookie的重定向响应
 */
function createRedirectWithTokenCookie(request: NextRequest, token: string, targetPath?: string): NextResponse {
  // 构建重定向URL，保持basePath
  const url = new URL(request.url)
  
  // 如果指定了目标路径，使用目标路径；否则使用当前路径
  if (targetPath) {
    url.pathname = targetPath
  }
  // 如果没有指定目标路径，保持当前路径不变（已经包含basePath）
  
  // 移除token参数
  url.searchParams.delete('token')
  
  // 创建重定向响应
  const response = NextResponse.redirect(url)
  
  // 设置token到cookie（7天过期）
  const expires = new Date()
  expires.setDate(expires.getDate() + 7)
  
  response.cookies.set('auth_token', token, {
    expires: expires,
    path: '/',
    httpOnly: false, // 允许前端JavaScript访问
    secure: process.env.NODE_ENV === 'production', // 生产环境使用HTTPS
    sameSite: 'lax'
  })
  
  return response
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

  // 获取token（支持SearchParam、Cookie、Header）
  const { token, fromSearchParam } = getTokenFromRequest(request)

  // 如果没有token，重定向到info页面
  if (!token) {
    return createInfoRedirect(request, 'no_token')
  }

  // 如果token来自SearchParam，先验证token，然后设置cookie并重定向
  if (fromSearchParam) {
    // 验证token
    const result = await checkTokenAndPermission(token, pathname)

    if (!result.valid) {
      return createInfoRedirect(request, result.reason!, result.userInfo)
    }

    // token有效，设置cookie并重定向到当前页面（去掉token参数）
    return createRedirectWithTokenCookie(request, token)
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

  // 对于所有路径（包括管理员路径和普通页面），检查页面访问权限
  if (result.hasPageAccess === false) {
    return createInfoRedirect(request, result.reason || 'no_permission', result.userInfo)
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