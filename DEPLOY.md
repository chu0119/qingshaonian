# 宝塔部署操作步骤

## 一、上传项目

在宝塔「文件」面板中，进入 `/www/wwwroot/`，
将本地 `qingshaonian` 整个目录上传（或通过 git clone）。

## 二、配置并初始化后端

SSH 连接服务器，逐条执行：

```bash
cd /www/wwwroot/qingshaonian/backend

# 1. 用生产配置覆盖 .env
cp .env.production .env

# 2. 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 执行数据库迁移（创建所有表 + 内置问卷）
alembic upgrade head

# 4. 初始化学校和管理员（production 模式不自动创建）
python setup_production.py
```

## 三、启动后端（PM2 守护）

```bash
cd /www/wwwroot/qingshaonian/backend
source .venv/bin/activate

pm2 start "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000" \
  --name qingshaonian \
  --interpreter $(which python)

pm2 save
pm2 startup
```

验证：`curl http://127.0.0.1:8000/api/v1/health`

## 四、配置 Nginx

宝塔「网站」→ 添加站点：

- **域名**：a.annanyun.com
- **根目录**：/www/wwwroot/qingshaonian/frontend/dist

站点「配置文件」改为：

```nginx
server {
    listen 80;
    server_name a.annanyun.com;
    root /www/wwwroot/qingshaonian/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

保存后申请 SSL 证书，勾选「强制 HTTPS」。

## 五、账号信息

| 角色 | 账号 | 密码 |
|------|------|------|
| 平台管理员 | padm | Padm@2026 |
| 学校管理员 | admin | Admin@2026 |

## 六、后续更新

```bash
cd /www/wwwroot/qingshaonian
git pull origin master
cd backend && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
cd ../frontend && npm install && npm run build
pm2 restart qingshaonian
```
