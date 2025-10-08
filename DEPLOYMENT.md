# 淘沙分析平台部署指南

本文档提供淘沙分析平台的详细部署说明，包括开发环境和生产环境的配置。

## 📋 系统要求

### 硬件要求
- **CPU**: 4核心以上
- **内存**: 8GB以上 (推荐16GB)
- **存储**: 50GB以上可用空间
- **网络**: 稳定的网络连接

### 软件要求
- **操作系统**: Linux (Ubuntu 20.04+) / macOS / Windows 10+
- **Python**: 3.8+ (推荐3.10+)
- **Node.js**: 16+ (推荐18+)
- **数据库**: MySQL 8.0+ (生产环境)
- **Redis**: 6.0+ (可选，用于缓存)

## 🔧 开发环境部署

### 1. 克隆项目

```bash
git clone <repository-url>
cd taosha_analyse_platform
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或者 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库和API密钥

# 初始化数据库
python scripts/init_permissions.py

# 启动后端服务
python start.py
```

### 3. 前端配置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 或使用启动脚本
chmod +x start.sh
./start.sh
```

### 4. 访问应用

- **前端**: http://localhost:5173
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

默认登录账户：
- 用户名: `admin`
- 密码: `admin123456`

## 🚀 生产环境部署

### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要软件
sudo apt install -y python3 python3-pip nodejs npm nginx mysql-server redis-server
```

### 2. 数据库配置

```bash
# 配置MySQL
sudo mysql_secure_installation

# 创建数据库和用户
sudo mysql -u root -p
```

```sql
CREATE DATABASE taosha_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'taosha'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON taosha_db.* TO 'taosha'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 3. 应用部署

```bash
# 创建应用目录
sudo mkdir -p /opt/taosha
sudo chown $USER:$USER /opt/taosha
cd /opt/taosha

# 部署代码
git clone <repository-url> .

# 后端部署
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 配置生产环境变量
cp .env.example .env
# 编辑 .env 文件，配置生产数据库连接

# 初始化数据库
python scripts/init_permissions.py

# 前端构建
cd ../frontend
npm install
npm run build
```

### 4. Nginx配置

创建 `/etc/nginx/sites-available/taosha`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /opt/taosha/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket代理
    location /api/v1/ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/taosha /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Systemd服务配置

创建 `/etc/systemd/system/taosha-backend.service`:

```ini
[Unit]
Description=Taosha Backend Service
After=network.target mysql.service redis.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/taosha/backend
Environment=PATH=/opt/taosha/backend/venv/bin
ExecStart=/opt/taosha/backend/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable taosha-backend
sudo systemctl start taosha-backend
sudo systemctl status taosha-backend
```

### 6. SSL证书配置 (推荐)

使用Let's Encrypt免费SSL证书：

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 🔒 安全配置

### 1. 防火墙配置

```bash
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 2. 数据库安全

- 定期备份数据库
- 使用强密码
- 限制数据库访问IP
- 定期更新MySQL版本

### 3. 应用安全

- 修改默认管理员密码
- 配置强JWT密钥
- 启用HTTPS
- 定期更新依赖包

## 📊 监控和日志

### 1. 日志配置

应用日志位置：
- 后端日志: `/opt/taosha/backend/logs/`
- Nginx日志: `/var/log/nginx/`
- 系统日志: `/var/log/syslog`

### 2. 监控指标

建议监控以下指标：
- CPU和内存使用率
- 磁盘空间
- 数据库连接数
- API响应时间
- 错误率

## 🔄 备份和恢复

### 1. 数据库备份

```bash
# 创建备份脚本
cat > /opt/taosha/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/taosha/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 备份数据库
mysqldump -u taosha -p taosha_db > $BACKUP_DIR/taosha_db_$DATE.sql

# 备份ChromaDB
tar -czf $BACKUP_DIR/chroma_db_$DATE.tar.gz -C /opt/taosha/backend chroma_db

# 清理7天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x /opt/taosha/backup.sh

# 添加到定时任务
crontab -e
# 添加: 0 2 * * * /opt/taosha/backup.sh
```

### 2. 恢复数据

```bash
# 恢复数据库
mysql -u taosha -p taosha_db < backup_file.sql

# 恢复ChromaDB
tar -xzf chroma_db_backup.tar.gz -C /opt/taosha/backend/
```

## 🐛 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务状态
   - 验证连接字符串
   - 检查防火墙设置

2. **API访问失败**
   - 检查后端服务状态
   - 查看应用日志
   - 验证Nginx配置

3. **前端资源加载失败**
   - 检查静态文件路径
   - 验证Nginx配置
   - 清除浏览器缓存

### 日志查看

```bash
# 查看后端服务状态
sudo systemctl status taosha-backend

# 查看应用日志
tail -f /opt/taosha/backend/logs/app.log

# 查看Nginx日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## 📞 技术支持

如遇到部署问题，请：

1. 查看相关日志文件
2. 检查系统资源使用情况
3. 验证配置文件
4. 联系技术支持团队

---

✅ 部署完成后，请及时修改默认密码并做好安全配置！