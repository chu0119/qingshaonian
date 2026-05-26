# 青少年风险防范测评管理平台

这是一个通过网页访问的多学校 SaaS 化青少年风险防范测评管理平台。系统支持平台管理员、学校管理员、教师和学生四类角色，覆盖学校开通、组织管理、问卷任务、学生答题、自动评分、风险提示、答题质量检测、干预记录、数据看板、AI 分析和短信通知等核心流程。

## 项目结构

```text
backend/   FastAPI 后端、SQLAlchemy 模型、Alembic 迁移、单元测试
frontend/  React + Vite 前端
```

## 环境要求

- Python 3.11+
- Node.js 18+
- MySQL 8+（生产建议）
- SQLite（演示/开发可用）

## 后端启动

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

接口文档默认地址：

```text
http://localhost:8000/docs
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：

```text
http://localhost:3000
```

## 配置说明

请复制 `backend/.env.example` 为 `backend/.env` 后再填写配置。真实 `.env` 已被 `.gitignore` 排除，禁止提交密钥和生产密码。

关键配置包括：

- `APP_ENV`: `demo` / `development` / `production`
- `DB_TYPE`: `sqlite` / `mysql`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `JWT_SECRET_KEY`
- `SMS_ENABLED`, `SMS_API_URL`, `SMS_APP_KEY`
- `AI_ENABLED`, `AI_API_URL`, `AI_API_KEY`

生产环境必须关闭 `DEBUG`，并配置强随机 `JWT_SECRET_KEY`、数据库账号和强初始密码。

## 常用检查

后端：

```bash
cd backend
python -m compileall app
alembic upgrade head
python -m unittest discover -v
```

前端：

```bash
cd frontend
npm run build
```

## 版本管理约定

当前基线建立后，后续开发在 `phase-p1-productization` 分支继续。每完成一个模块，先运行必要检查，再查看 `git diff`，然后单独提交。

推荐提交前缀：

- `fix:` 修复问题
- `feat:` 新增功能
- `refactor:` 重构
- `test:` 增加测试
- `chore:` 配置和工程化
- `docs:` 文档

## 安全注意事项

- 不提交 `.env`、密钥、短信/AI 凭证
- 不提交 `node_modules/`、`dist/`、`build/`
- 不提交本地数据库文件、日志、导出文件
- 学生端不展示风险等级、答题质量提示等敏感结果
- 学校、教师、学生数据访问必须同时在前端和后端校验权限
