# Token权限管理系统部署指南

## 📋 系统概述

本系统实现了基于JWT token的权限管理，包括：
- JWT token认证和授权
- 部门和角色管理
- 页面级权限控制
- 用户登录记录
- 管理员界面

## 🏗️ 系统架构

```
Frontend (Next.js)  ←→  Backend (FastAPI)  ←→  Database (PostgreSQL)
     ↓                        ↓                      ↓
- 权限中间件           - JWT token验证         - 权限数据存储
- 管理界面             - API接口认证           - 用户登录记录
- 权限Hook             - 权限计算服务          - 实体和权限关系
```

## 🚀 部署前准备

### 1. 环境要求

**后端环境：**
- Python 3.9+
- PostgreSQL 12+
- Redis 6+ (可选，用于缓存)

**前端环境：**
- Node.js 18+
- npm 或 yarn

### 2. 数据库准备

```sql
-- 创建数据库
CREATE DATABASE taosha_production;

-- 创建用户（可选）
CREATE USER taosha_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE taosha_production TO taosha_user;
```

## 🔧 后端部署

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制并修改生产环境配置：
```bash
cp .env.production .env
```

**重要配置项：**
- `DATABASE_URL`: 数据库连接字符串
- `TOKEN_SECRET_KEY`: JWT签名密钥（必须修改！）
- `ALLOWED_HOSTS`: 允许的域名
- `CORS_ORIGINS`: 前端域名

### 3. 初始化数据库

```bash
# 创建数据库表
python -c "from models.db_base import create_tables; create_tables()"

# 同步页面配置
python -c "
from models.db_base import get_db_session
from services.page_discovery_service import PageDiscoveryService
with get_db_session() as db:
    service = PageDiscoveryService(db)
    count = service.sync_pages_from_config()
    print(f'同步了 {count} 个页面')
"
```

### 4. 创建管理员实体

```bash
python -c "
from models.db_base import get_db_session
from services.permission_service import EntityService
from models.permission_models import EntityType
with get_db_session() as db:
    service = EntityService(db)
    # 创建管理员角色
    admin_role = service.create_entity(
        code='淘沙管理员',
        name='淘沙管理员',
        entity_type=EntityType.ROLE,
        description='系统管理员角色'
    )
    print(f'创建管理员角色: {admin_role.name}')
"
```

### 5. 运行测试

```bash
# 运行集成测试
python test_integration.py

# 运行安全性测试
python test_security.py
```

### 6. 启动服务

```bash
# 开发模式
uvicorn main:app --host 0.0.0.0 --port 8000

# 生产模式（使用gunicorn）
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🌐 前端部署

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置环境变量

创建 `.env.production.local`:
```bash
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com
NEXT_PUBLIC_APP_ENV=production
```

### 3. 构建和部署

```bash
# 构建生产版本
npm run build

# 启动生产服务
npm start

# 或使用PM2
pm2 start npm --name "taosha-frontend" -- start
```

## 🔒 安全配置

### 1. JWT Token安全

- **密钥管理**: 使用强随机密钥，定期轮换
- **过期时间**: 建议设置为24小时或更短
- **传输安全**: 仅通过HTTPS传输token

### 2. 数据库安全

- 使用专用数据库用户，限制权限
- 启用SSL连接
- 定期备份数据

### 3. 网络安全

- 配置防火墙，仅开放必要端口
- 使用HTTPS/TLS加密
- 配置CORS策略

## 📊 监控和维护

### 1. 日志监控

系统日志位置：
- 应用日志: `backend/logs/`
- 访问日志: Web服务器日志
- 错误日志: 应用错误日志

### 2. 性能监控

关键指标：
- API响应时间
- 数据库连接数
- 内存使用率
- Token验证成功率

### 3. 定期维护

- 清理过期的登录记录
- 检查权限配置
- 更新依赖包
- 备份数据库

## 🚨 故障排除

### 常见问题

1. **Token验证失败**
   - 检查密钥配置
   - 确认时间同步
   - 验证token格式

2. **权限访问被拒绝**
   - 检查用户角色配置
   - 验证页面权限分配
   - 确认管理员角色

3. **数据库连接失败**
   - 检查连接字符串
   - 验证数据库服务状态
   - 确认网络连通性

### 调试命令

```bash
# 生成测试token
python scripts/generate_token.py

# 检查数据库连接
python -c "from models.db_base import get_db_session; print('数据库连接正常' if get_db_session() else '连接失败')"

# 验证权限配置
python test_security.py
```

## 📞 技术支持

如遇到部署问题，请检查：
1. 系统日志文件
2. 环境变量配置
3. 网络连接状态
4. 依赖包版本

---

**部署完成后，请务必：**
1. 修改默认密钥和密码
2. 配置HTTPS证书
3. 设置定期备份
4. 建立监控告警