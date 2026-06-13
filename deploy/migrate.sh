#!/bin/bash
# ============================================================
# 青少年风险防范测评管理系统 — 一键迁移脚本
# 适用系统: Ubuntu 20.04 / 22.04 / 24.04
# 用法: sudo bash migrate.sh
# ============================================================

set -e

# ==================== 配置区 ====================
APP_NAME="qingshaonian"
APP_DIR="/www/wwwroot/${APP_NAME}"
BACKEND_DIR="${APP_DIR}/backend"
FRONTEND_DIR="${APP_DIR}/frontend"
VENV_DIR="${BACKEND_DIR}/.venv"
SERVICE_NAME="${APP_NAME}"

# 数据库配置（根据实际情况修改）
DB_NAME="qingshaonian"
DB_USER="qingshaonian"
DB_PASS="Qs@$(openssl rand -hex 4)"  # 自动生成随机密码
DB_HOST="localhost"

# 应用配置（从旧服务器 .env 复制或手动填写）
APP_SECRET_KEY="$(openssl rand -hex 32)"
JWT_SECRET="$(openssl rand -hex 32)"
ADMIN_PASSWORD="Admin@2026!"
PLATFORM_ADMIN_PASSWORD="Admin@2026!"

# ==================== 颜色输出 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ==================== 检查 root 权限 ====================
if [ "$EUID" -ne 0 ]; then
    error "请使用 sudo 运行此脚本: sudo bash migrate.sh"
fi

info "=========================================="
info "  青少年风险防范测评管理系统 — 迁移脚本"
info "=========================================="

# ==================== 1. 系统更新 ====================
info "1/10 更新系统包..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx mysql-server curl wget > /dev/null

# ==================== 2. 安装 Node.js（用于前端构建） ====================
info "2/10 安装 Node.js..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - > /dev/null
    apt-get install -y -qq nodejs > /dev/null
fi
info "  Node.js $(node -v) 已安装"

# ==================== 3. 配置 MySQL ====================
info "3/10 配置 MySQL..."
systemctl enable mysql
systemctl start mysql

# 创建数据库和用户
mysql -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'${DB_HOST}' IDENTIFIED BY '${DB_PASS}';"
mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'${DB_HOST}';"
mysql -e "FLUSH PRIVILEGES;"
info "  数据库 ${DB_NAME} 创建成功"

# ==================== 4. 创建应用目录 ====================
info "4/10 创建应用目录..."
mkdir -p ${APP_DIR}
mkdir -p ${BACKEND_DIR}
mkdir -p ${FRONTEND_DIR}
mkdir -p ${BACKEND_DIR}/uploads/interventions

# ==================== 5. 部署后端代码 ====================
info "5/10 部署后端代码..."
# 假设代码已上传到 /tmp/qingshaonian_backend.tar.gz
if [ -f /tmp/qingshaonian_backend.tar.gz ]; then
    tar -xzf /tmp/qingshaonian_backend.tar.gz -C ${BACKEND_DIR}
    info "  后端代码解压完成"
else
    warn "  请先上传后端代码: scp -r backend/ root@<IP>:/tmp/qingshaonian_backend/"
fi

# ==================== 6. 创建 Python 虚拟环境 ====================
info "6/10 创建 Python 虚拟环境..."
python3 -m venv ${VENV_DIR}
source ${VENV_DIR}/bin/activate
pip install --upgrade pip -q
pip install -r ${BACKEND_DIR}/requirements.txt -q
info "  Python 依赖安装完成"

# ==================== 7. 配置 .env ====================
info "7/10 生成配置文件..."
cat > ${BACKEND_DIR}/.env << EOF
# === 数据库 ===
DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PASS}@${DB_HOST}:3306/${DB_NAME}

# === JWT ===
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480

# === 管理员 ===
ADMIN_USERNAME=admin
ADMIN_PASSWORD=${ADMIN_PASSWORD}
PLATFORM_ADMIN_USERNAME=padm
PLATFORM_ADMIN_PASSWORD=${PLATFORM_ADMIN_PASSWORD}

# === 安全 ===
SECRET_KEY=${APP_SECRET_KEY}
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# === 调试 ===
DEBUG=false
EOF
info "  .env 配置完成"

# ==================== 8. 运行数据库迁移 ====================
info "8/10 运行数据库迁移..."
cd ${BACKEND_DIR}
${VENV_DIR}/bin/python -m alembic upgrade head
info "  数据库迁移完成"

# ==================== 9. 配置 systemd 服务 ====================
info "9/10 配置系统服务..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=青少年风险防范测评管理系统
After=network.target mysql.service

[Service]
User=root
WorkingDirectory=${BACKEND_DIR}
ExecStart=${VENV_DIR}/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment="PATH=${VENV_DIR}/bin"

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}
info "  服务启动成功"

# ==================== 10. 部署前端 ====================
info "10/10 部署前端..."
if [ -f /tmp/qingshaonian_frontend.tar.gz ]; then
    tar -xzf /tmp/qingshaonian_frontend.tar.gz -C ${FRONTEND_DIR}
    info "  前端文件解压完成"
fi

# 配置 Nginx
cat > /etc/nginx/conf.d/${APP_NAME}.conf << 'NGINX'
server {
    listen 80;
    server_name _;

    # 前端静态文件
    location / {
        root /www/wwwroot/qingshaonian/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    # FastAPI 文档
    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
    }
}
NGINX

nginx -t && systemctl reload nginx
info "  Nginx 配置完成"

# ==================== 完成 ====================
echo ""
info "=========================================="
info "  迁移完成！"
info "=========================================="
echo ""
echo "  访问地址: http://<服务器IP>"
echo "  管理员账号: admin / ${ADMIN_PASSWORD}"
echo "  平台管理员: padm / ${PLATFORM_ADMIN_PASSWORD}"
echo "  数据库密码: ${DB_PASS}"
echo ""
echo "  请保存以上信息！"
echo ""
