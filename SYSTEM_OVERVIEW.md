# Token权限管理系统概览

## 🎯 系统目标

本系统实现了基于JWT token的权限管理，替代了原有的前端传递user_id的认证方式，提供了更安全、更标准的权限控制机制。

## 🏗️ 系统架构

### 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Database      │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│ (PostgreSQL)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
    ┌────▼────┐             ┌────▼────┐             ┌────▼────┐
    │权限中间件│             │JWT验证  │             │权限数据 │
    │路由保护 │             │API认证  │             │用户记录 │
    │管理界面 │             │权限计算 │             │实体关系 │
    └─────────┘             └─────────┘             └─────────┘
```

### 核心组件

#### 1. 认证层 (Authentication)
- **JWT Token服务**: 生成、验证、解析JWT token
- **认证中间件**: FastAPI依赖注入，验证API请求
- **前端中间件**: Next.js路由级权限检查

#### 2. 授权层 (Authorization)  
- **权限服务**: 计算用户权限（部门权限 ∪ 角色权限）
- **页面访问控制**: 检查用户是否有访问特定页面的权限
- **管理员权限**: 特殊角色拥有所有权限

#### 3. 数据层 (Data)
- **实体管理**: 部门和角色的CRUD操作
- **权限分配**: 为实体分配页面访问权限
- **登录记录**: 记录用户登录信息和状态

#### 4. 管理层 (Management)
- **部门管理**: 创建、编辑、删除部门
- **角色管理**: 创建、编辑、删除角色
- **权限分配**: 为部门和角色分配页面权限
- **登录记录**: 查看用户登录历史

## 🔐 安全机制

### JWT Token安全
- **标准JWT格式**: 使用HS256算法签名
- **过期控制**: 24小时自动过期
- **签名验证**: 防止token篡改
- **传输安全**: 仅通过HTTPS传输

### 权限控制
- **最小权限原则**: 用户仅获得必要的权限
- **权限继承**: 管理员拥有所有权限
- **实时验证**: 每次请求都验证权限
- **页面级控制**: 前端路由级权限检查

### 数据安全
- **数据隔离**: 不同部门数据相互隔离
- **审计日志**: 记录所有权限变更操作
- **输入验证**: 防止SQL注入和XSS攻击
- **错误处理**: 不泄露敏感信息

## 📊 数据模型

### 核心表结构

```sql
-- 系统实体表（部门和角色）
system_entities
├── id (主键)
├── code (唯一标识)
├── name (显示名称)
├── type (department/role)
├── description (描述)
└── created_at (创建时间)

-- 系统页面表
system_pages  
├── id (主键)
├── path (页面路径)
├── name (页面名称)
├── description (描述)
└── created_at (创建时间)

-- 系统权限表（实体-页面关联）
system_permissions
├── id (主键)
├── entity_id (实体ID)
├── page_id (页面ID)
└── created_at (创建时间)

-- 系统登录记录表
system_login_records
├── user_id (主键)
├── user_name (用户名)
├── branch_no (部门编号)
├── branch_name (部门名称)
├── role_id_list (角色列表)
├── role_name_list (角色名称列表)
└── last_login_time (最后登录时间)
```

## 🔄 权限计算流程

### 用户权限计算
```
用户权限 = 部门权限 ∪ 角色权限

1. 根据用户的branch_no查询部门权限
2. 根据用户的role_id_list查询所有角色权限  
3. 计算两者的并集作为最终权限
4. 管理员角色拥有所有页面权限
```

### 页面访问验证
```
页面访问验证流程:

1. 检查页面是否存在
   ├── 不存在 → 拒绝访问
   └── 存在 → 继续

2. 检查用户是否为管理员
   ├── 是管理员 → 允许访问
   └── 非管理员 → 继续

3. 检查用户是否有页面权限
   ├── 有权限 → 允许访问
   └── 无权限 → 拒绝访问
```

## 🚀 API接口改造

### 改造前后对比

**改造前**:
```python
@router.post("/api/create")
async def create_item(request: CreateRequest, user_id: str = Query(...)):
    # 使用前端传递的user_id
    service.create_item(request, created_by=user_id)
```

**改造后**:
```python
@router.post("/api/create")  
async def create_item(
    request: CreateRequest, 
    current_user: UserInfo = Depends(get_current_user)
):
    # 从JWT token获取用户信息
    service.create_item(request, created_by=current_user.user_id)
```

### 改造统计
- **总计改造接口**: 12个
- **Agent相关**: 3个接口
- **FraudHunter相关**: 8个接口
- **元数据管理**: 1个接口

## 🎨 前端权限控制

### 路由级权限控制
```typescript
// middleware.ts
export function middleware(request: NextRequest) {
  // 验证token有效性
  // 检查页面访问权限
  // 重定向到相应页面
}
```

### 组件级权限控制
```typescript
// useAuth Hook
const { isAuthenticated, isAdmin, hasPagePermission } = useAuth();

// 权限检查Hook
const hasPermission = usePagePermission('/admin/departments');
```

### 统一错误处理
```typescript
// Info页面统一处理
- 未登录 → 显示登录提示
- Token失效 → 显示重新登录提示  
- 无权限 → 显示权限不足提示
- 页面不存在 → 显示404提示
```

## 📈 系统优势

### 安全性提升
- ✅ 标准JWT认证，防止token伪造
- ✅ 服务端权限验证，防止绕过
- ✅ 最小权限原则，降低安全风险
- ✅ 审计日志完整，便于追踪

### 可维护性
- ✅ 统一认证机制，代码简洁
- ✅ 权限配置灵活，易于管理
- ✅ 前后端分离，职责清晰
- ✅ 测试覆盖完整，质量保证

### 用户体验
- ✅ 单点登录体验，无需重复认证
- ✅ 权限实时生效，无需重启
- ✅ 错误提示友好，便于理解
- ✅ 管理界面直观，操作简单

### 扩展性
- ✅ 支持多种实体类型扩展
- ✅ 支持细粒度权限控制
- ✅ 支持权限继承和组合
- ✅ 支持多租户架构扩展

## 🧪 测试覆盖

### 集成测试
- ✅ 数据库连接和表创建
- ✅ JWT Token生成和验证
- ✅ 页面同步功能
- ✅ 权限服务操作
- ✅ 登录记录管理
- ✅ API路由导入

### 安全性测试
- ✅ Token安全性（无效、过期、篡改）
- ✅ 管理员权限控制
- ✅ 页面访问权限控制
- ✅ API接口权限验证
- ✅ 数据隔离性

## 📚 相关文档

- [部署指南](DEPLOYMENT_GUIDE.md) - 详细的部署步骤和配置
- [安全检查清单](SECURITY_CHECKLIST.md) - 安全配置和检查项
- [API改造分析](backend/api_migration_analysis.md) - 接口改造详情
- [需求文档](.kiro/specs/token-based-permission-management/requirements.md) - 系统需求
- [设计文档](.kiro/specs/token-based-permission-management/design.md) - 系统设计
- [任务清单](.kiro/specs/token-based-permission-management/tasks.md) - 实现任务

---

**系统状态**: ✅ 开发完成，测试通过，可部署上线