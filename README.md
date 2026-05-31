# 青少年风险防范测评管理系统

面向学校的心理健康风险筛查与干预管理平台。支持平台监管、学校管理、教师辅导、学生答题四类角色，覆盖问卷编制→任务下发→学生作答→自动评分→风险预警→干预记录→数据看板全流程。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite 8 + Ant Design 5 + ECharts 6 + Zustand + React Router 6 |
| 后端 | FastAPI 0.115 + SQLAlchemy 2 + Alembic + Pydantic 2 + Python 3.11+ |
| 数据库 | MySQL 8（生产）/ SQLite（开发） |
| 部署 | Nginx 反代 + systemd 托管后端，域名 `a.annanyun.com`（HTTPS） |

## 项目结构

```
qingshaonian/
├── backend/                        FastAPI 后端
│   ├── app/
│   │   ├── main.py                 应用入口、CORS、路由挂载
│   │   ├── config.py               环境变量读取、生产校验
│   │   ├── database.py             SQLAlchemy 引擎、Session 工厂
│   │   ├── dependencies.py         get_current_user、require_role 依赖注入
│   │   ├── middleware/             请求日志中间件
│   │   ├── models/                 SQLAlchemy ORM 模型（8 个模块）
│   │   │   ├── user.py             用户、学校、班级
│   │   │   ├── questionnaire.py    问卷、题目、选项、维度
│   │   │   ├── task.py             答题任务、答卷
│   │   │   ├── risk.py             风险记录、干预
│   │   │   ├── audit.py            操作日志
│   │   │   ├── external.py         外部日志（短信、AI）
│   │   │   └── system_config.py    系统配置 KV 表
│   │   ├── routers/                16 个路由模块
│   │   │   ├── auth.py             登录、验证码、密码重置
│   │   │   ├── users.py            用户 CRUD
│   │   │   ├── classes.py          班级管理
│   │   │   ├── questionnaires.py   问卷 CRUD + 导入导出
│   │   │   ├── tasks.py            任务创建、答题、评分
│   │   │   ├── risks.py            风险列表、详情
│   │   │   ├── interventions.py    干预记录
│   │   │   ├── dashboard.py        数据看板
│   │   │   ├── reports.py          报表导出
│   │   │   ├── platform.py         平台监管端（含问卷管理、导入导出）
│   │   │   ├── ai_analysis.py      AI 分析
│   │   │   ├── sms.py              短信通知
│   │   │   ├── student.py          学生端接口
│   │   │   ├── quality.py          答题质量检测
│   │   │   ├── system.py           系统设置
│   │   │   └── common.py           通用接口（字典、验证码）
│   │   ├── schemas/                Pydantic 请求/响应模型
│   │   ├── services/               业务逻辑层
│   │   │   ├── scoring_service.py  评分 + 风险判定（禁止修改）
│   │   │   ├── questionnaire_service.py
│   │   │   ├── questionnaire_import_service.py   Excel 导入导出
│   │   │   ├── auth_service.py     认证、JWT、验证码
│   │   │   ├── user_service.py     用户导入导出
│   │   │   └── ...                 其他服务
│   │   ├── questionnaire_bank/     内置问卷定义（38 套）
│   │   └── utils/                  JWT、密码哈希、校验、响应封装
│   ├── alembic/                    数据库迁移
│   │   └── versions/               5 个迁移文件（单 head: 202605260004）
│   ├── scripts/                    数据初始化脚本
│   ├── tests/                      6 个测试模块（66 测试用例）
│   ├── requirements.txt
│   ├── .env.example                环境变量模板
│   ├── .env.production             生产配置（gitignored）
│   └── alembic.ini
│
├── frontend/                       React 前端
│   ├── src/
│   │   ├── api/                    Axios API 封装（auth/questionnaires/users 等）
│   │   ├── components/
│   │   │   ├── layout/             MainLayout（管理端）、StudentLayout（学生端）
│   │   │   ├── screen/             数据大屏公共组件
│   │   │   ├── ai/                 AI 分析弹窗
│   │   │   ├── answer/             答卷详情
│   │   │   └── common/             通用组件
│   │   ├── pages/
│   │   │   ├── platform/           公安监管端（12 个页面）
│   │   │   ├── school-admin/       学校管理端（13 个页面）
│   │   │   ├── teacher/            教师端（8 个页面）
│   │   │   ├── student/            学生端（6 个页面）
│   │   │   ├── LoginPage.tsx       登录页（含验证码）
│   │   │   ├── ForceChangePassword.tsx
│   │   │   ├── 403.tsx / 404.tsx
│   │   │   └── ...
│   │   ├── routes/                 路由表 + ProtectedRoute 角色鉴权
│   │   ├── stores/                 Zustand authStore（token/role 持久化）
│   │   ├── styles/                 全局样式、主题
│   │   ├── types/                  TypeScript 类型定义
│   │   └── utils/                  常量、工具函数
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── docs/
│   ├── 金盾护苗平台操作手册.docx    操作手册 v1
│   ├── 金盾护苗平台操作手册_v2.docx  操作手册 v2
│   └── generate_manual.py          手册生成脚本
│
├── CLAUDE.md                       AI 开发上下文（已 checkout）
├── README.md                       本文件
├── OPS.md                          运维文档
└── 启动系统.bat                    Windows 一键启动脚本
```

## 角色体系

| 角色 | 路由前缀 | 权限范围 |
|------|---------|---------|
| `platform_admin` | `/platform/` | 公安监管端，可查看所有学校数据，可代入学校后台 |
| `school_admin` | `/school-admin/` | 本校完整管理：问卷、任务、教师、学生、报表 |
| `teacher` / `counselor` | `/teacher/` | 所负责班级的学生和任务 |
| `student` | `/student/` | 仅本人问卷和答题记录 |

**平台管理员代入学校**：通过 `/api/v1/platform/enter` 接口获取含 `school_context_id` 的 JWT，保留 `platform_admin` 身份同时拥有学校级访问权限。

## 快速开始

### 后端

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # 开发用默认配置（SQLite）
alembic upgrade head          # 创建数据库表 + 内置问卷
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

访问 API 文档：`http://localhost:8000/docs`

### 前端

```bash
cd frontend
npm install
npm run dev                   # 开发服务器 http://localhost:3000
```

### Windows 一键启动

双击根目录 `启动系统.bat`，自动清理旧进程 → 启动后端(8000) → 启动前端(3000)。

## 环境变量

复制 `backend/.env.example` 为 `backend/.env`，关键配置：

| 变量 | 说明 | 开发默认值 |
|------|------|-----------|
| `APP_ENV` | 运行环境 | `demo` |
| `DEBUG` | 调试模式 | `true` |
| `DB_TYPE` | 数据库类型 | `sqlite` |
| `DB_HOST` / `DB_PORT` / `DB_NAME` | MySQL 连接 | — |
| `DB_USER` / `DB_PASSWORD` | MySQL 凭证 | — |
| `JWT_SECRET_KEY` | JWT 签名密钥 | 占位符（生产必须更换） |
| `JWT_EXPIRE_MINUTES` | Token 有效期 | `480` |
| `PLATFORM_ADMIN_USERNAME` / `_PASSWORD` | 平台管理员 | `padm` / `padm123` |
| `ADMIN_USERNAME` / `_PASSWORD` | 学校管理员 | `admin` / `admin123` |
| `INIT_BUILTIN_QUESTIONNAIRES` | 启动时注入内置问卷 | `true` |
| `SMS_ENABLED` | 短信通知 | `false` |
| `AI_ENABLED` | AI 分析 | `false` |
| `CORS_ORIGINS` | 跨域白名单 | `localhost:3000,localhost:5173` |

> 生产环境必须：`DEBUG=false`、`DB_TYPE=mysql`、强随机 `JWT_SECRET_KEY`（≥32 字符）、强密码（≥10 字符）。

## 问卷管理

### 内置问卷

系统内置 38 套问卷，涵盖心理健康、行为风险、家庭环境等维度。启动时自动注入数据库（`INIT_BUILTIN_QUESTIONNAIRES=true`）。

### Excel 模板导入导出

平台管理员和学校管理员均支持：

1. **下载模板** — 生成包含 3 个 Sheet 的 Excel 文件
   - Sheet「题目」：每行一道题，含题号、内容、类型、维度、选项（最多 6 个）、分值、风险标记
   - Sheet「问卷设置」：标题、分类、年级、维度定义、风险判定规则
   - Sheet「填写说明」：各字段的详细说明和可选值
2. **导入问卷** — 上传填写好的 Excel 文件，系统自动校验并创建问卷（默认草稿状态）
3. **导出问卷** — 将已有问卷导出为 Excel 文件
4. **批量导出** — 多选问卷打包为 ZIP 下载（仅平台端）

### 题目类型

`单选` / `多选` / `判断` / `量表` / `填空` / `简答`

## 数据库迁移

```bash
cd backend
alembic upgrade head          # 执行迁移
alembic current               # 查看当前版本
alembic history               # 查看迁移链
```

迁移链（5 个，单 head）：
```
base → 001(create_all) → 002(phase2) → 003_qrf(规则字段) → 003(历史兼容) → 004(缺失列)
当前 head: 202605260004
```

## 测试

```bash
# 后端（编译检查 + 单元测试）
cd backend
python -m compileall app -q
python -m pytest tests/ -v

# 前端（类型检查 + 构建）
cd frontend
npm run build
```

当前测试状态：**66 通过**

## 风险文案规范

系统中所有风险相关表述必须使用以下措辞，禁止出现"问题学生""心理疾病""确诊"等词：

| 级别 | 提示语 |
|------|--------|
| 低风险 | "性格内核健康" / "无明显风险信号" |
| 中风险 | "存在明显的关注信号" / "建议跟进" |
| 高风险 | "重点关注" / "建议学校安排专业辅导" |
| 紧急风险 | "风险提示" / "建议立即启动干预" |

## API 文档

后端启动后访问：
- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`

生产环境：`https://a.annanyun.com/docs`

## 安全规则

- 所有敏感操作（查看学生详情、导出、AI 分析、发送短信）写入 `operation_logs` 表
- `selected_display_index` 由后端根据 `option_orders` 计算，不信任前端
- 学校管理员只能重置本校用户密码，不能操作 `platform_admin`
- 教师创建时强制 `role=teacher/counselor`，拒绝越权注入
- `.env`、`.env.production` 已被 `.gitignore` 排除，禁止提交密钥

## 部署

详见 [OPS.md](OPS.md)

## 许可证

内部项目，未公开授权。
