# 金盾护苗 · 青少年关爱帮扶信息管理平台

面向学校的心理健康风险筛查与干预管理平台。支持平台监管、学校管理、教师辅导、学生答题四类角色，覆盖问卷编制→任务下发→学生作答→自动评分→风险预警→干预记录→数据看板全流程。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite 8 + Ant Design 5 + ECharts 6 + Zustand + React Router 6 |
| 后端 | FastAPI 0.115 + SQLAlchemy 2 + Alembic + Pydantic 2 + Python 3.11+ |
| 数据库 | MySQL 8（生产）/ SQLite（开发） |
| 部署 | Nginx 反代 + systemd 托管后端，域名 `a.annanyun.com`（HTTPS） |

**代码规模**：161 个源文件，约 31,600 行代码（Python 16,252 行 + TypeScript 15,363 行）

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
│   │   ├── models/                 SQLAlchemy ORM 模型（9 个模块）
│   │   │   ├── user.py             用户、学校、班级、年级、教师班级关联
│   │   │   ├── questionnaire.py    问卷、题目、选项、维度、矛盾组
│   │   │   ├── task.py             答题任务、答卷、答题记录
│   │   │   ├── risk.py             风险记录、干预、评分结果、质量评估
│   │   │   ├── audit.py            操作日志、登录日志
│   │   │   ├── external.py         外部日志（短信、AI）
│   │   │   ├── system_config.py    系统配置 KV 表
│   │   │   └── notification.py     站内消息通知
│   │   ├── routers/                18 个路由模块
│   │   │   ├── auth.py             登录、验证码、密码重置
│   │   │   ├── users.py            用户 CRUD（学生/教师）
│   │   │   ├── classes.py          班级管理
│   │   │   ├── questionnaires.py   问卷 CRUD + 导入导出
│   │   │   ├── tasks.py            任务创建、答题、评分、打回、删除
│   │   │   ├── risks.py            风险列表、详情
│   │   │   ├── interventions.py    干预记录
│   │   │   ├── dashboard.py        数据看板（学校/教师/学生）
│   │   │   ├── reports.py          报表（学校总览、风险汇总、学生纵向追踪）
│   │   │   ├── platform.py         平台监管端（含问卷管理、任务管理、导入导出）
│   │   │   ├── ai_analysis.py      AI 分析
│   │   │   ├── sms.py              短信通知
│   │   │   ├── student.py          学生端（待答/已完成、答题、提交）
│   │   │   ├── quality.py          答题质量检测
│   │   │   ├── system.py           系统设置
│   │   │   ├── notifications.py    站内消息通知 API
│   │   │   ├── common.py           通用接口（字典数据）
│   │   │   └── exports.py          数据导出
│   │   ├── schemas/                Pydantic 请求/响应模型（5 个模块）
│   │   ├── services/               业务逻辑层（12 个服务）
│   │   │   ├── scoring_service.py  评分 + 质量检测 + 风险判定（禁止修改）
│   │   │   ├── questionnaire_service.py      问卷 CRUD
│   │   │   ├── questionnaire_import_service.py   Excel 导入导出
│   │   │   ├── auth_service.py     认证、JWT、验证码
│   │   │   ├── user_service.py     用户导入导出
│   │   │   ├── notification_service.py   消息通知创建
│   │   │   ├── sms_service.py      短信发送
│   │   │   ├── stats_service.py    统计数据
│   │   │   └── ...                 其他服务
│   │   ├── questionnaire_bank/     内置问卷定义（39 套）
│   │   │   └── builtin_questionnaires.py
│   │   └── utils/                  JWT、密码哈希、校验、响应封装、访问控制
│   ├── alembic/                    数据库迁移
│   │   └── versions/               6 个迁移文件（单 head: 202606010005）
│   ├── scripts/                    数据初始化脚本（8 个）
│   ├── tests/                      7 个测试模块（66 测试用例）
│   ├── requirements.txt
│   ├── .env.example                环境变量模板
│   ├── .env.production             生产配置（gitignored）
│   └── alembic.ini
│
├── frontend/                       React 前端
│   ├── src/
│   │   ├── api/                    Axios API 封装（8 个模块）
│   │   │   ├── client.ts           axios 实例（baseURL=/api/v1, JWT Bearer）
│   │   │   ├── auth.ts             认证 API
│   │   │   ├── questionnaires.ts   问卷 API（含导入导出）
│   │   │   ├── users.ts            用户 API
│   │   │   └── ...
│   │   ├── components/
│   │   │   ├── layout/             MainLayout（管理端）、StudentLayout（学生端）
│   │   │   ├── screen/             数据大屏公共组件（7 个）
│   │   │   ├── common/             NotificationBell、StudentSelect
│   │   │   ├── ai/                 AI 分析弹窗
│   │   │   └── answer/             答卷详情
│   │   ├── pages/
│   │   │   ├── platform/           公安监管端（14 个页面）
│   │   │   │   ├── Dashboard.tsx           数据看板
│   │   │   │   ├── SchoolManagement.tsx    学校管理
│   │   │   │   ├── QuestionnaireManagement.tsx  问卷管理（含导入导出）
│   │   │   │   ├── TaskSupervision.tsx     任务监管（含发布任务）
│   │   │   │   ├── RiskCenter.tsx          风险中心（含完整质量检测、AI分析）
│   │   │   │   ├── KeyStudents.tsx         重点关注学生
│   │   │   │   ├── StudentManagement.tsx   学生管理（含档案入口）
│   │   │   │   ├── InterventionSupervision.tsx  干预督办
│   │   │   │   ├── AIAnalysis.tsx          AI 分析
│   │   │   │   ├── Notifications.tsx       短信通知
│   │   │   │   ├── AuditLogs.tsx           操作日志
│   │   │   │   ├── Settings.tsx            系统设置
│   │   │   │   └── Screen.tsx              数据大屏
│   │   │   ├── school-admin/       学校管理端（15 个页面）
│   │   │   │   ├── Dashboard.tsx           数据看板
│   │   │   │   ├── StudentManagement.tsx   学生管理（含批量导入）
│   │   │   │   ├── StudentProfile.tsx      一生一档心理档案（含趋势图）
│   │   │   │   ├── TeacherManagement.tsx   教师管理
│   │   │   │   ├── ClassManagement.tsx     班级管理
│   │   │   │   ├── QuestionnaireLibrary.tsx    问卷库（含导入导出）
│   │   │   │   ├── QuestionnaireEditor.tsx     问卷编辑器/预览
│   │   │   │   ├── TaskManagement.tsx      任务管理（含进度监控、打回）
│   │   │   │   ├── RiskWarning.tsx         风险预警
│   │   │   │   ├── RiskDetail.tsx          风险详情
│   │   │   │   ├── InterventionRecords.tsx 干预记录
│   │   │   │   ├── DataReports.tsx         数据报表（5 个标签页）
│   │   │   │   ├── DataScreen.tsx          数据大屏
│   │   │   │   ├── AuditLogs.tsx           操作日志
│   │   │   │   └── SystemSettings.tsx      系统设置（7 个标签页）
│   │   │   ├── teacher/            教师端（8 个页面）
│   │   │   │   ├── TeacherDashboard.tsx    教师看板
│   │   │   │   ├── MyClasses.tsx           我的班级
│   │   │   │   ├── TeacherTasks.tsx        任务管理
│   │   │   │   ├── MyQuestionnaires.tsx    我的问卷
│   │   │   │   ├── RiskStudents.tsx        风险学生
│   │   │   │   ├── TeacherInterventions.tsx 干预记录
│   │   │   │   ├── ClassReport.tsx         班级报告
│   │   │   │   └── CompletionStatus.tsx    完成状态
│   │   │   ├── student/            学生端（6 个页面）
│   │   │   │   ├── StudentHome.tsx         学生首页
│   │   │   │   ├── AnswerPage.tsx          答题页（自动跳转、进度保存）
│   │   │   │   ├── PendingQuestionnaires.tsx   待答问卷
│   │   │   │   ├── CompletedQuestionnaires.tsx 已完成问卷
│   │   │   │   ├── HealthTips.tsx          心理健康科普
│   │   │   │   └── Profile.tsx             个人信息
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
├── CLAUDE.md                       AI 开发上下文
├── README.md                       本文件
├── OPS.md                          运维文档（内部）
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

复制 `backend/.env.example` 为 `backend/.env`，关键配置（共 26 个）：

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

系统内置 39 套问卷，涵盖心理健康、行为风险、家庭环境等维度。启动时自动注入数据库（`INIT_BUILTIN_QUESTIONNAIRES=true`）。

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

## 学生答题流程

1. 学生登录 → 查看待答任务列表
2. 点击开始 → 阅读知情同意书并勾选同意
3. 逐题作答（单选/判断题选中后自动跳转下一题）
4. 自动保存（每 30 秒）+ 手动保存
5. 提交 → 服务端校验必填题（未答则跳转到对应题目）
6. 自动评分 → 风险判定 → 质量检测 → 生成风险预警

## 风险评分体系

### 分数阈值（以综合问卷为例，100 题 × 1-4 分）

| 等级 | 分数范围 | 每题均分 | 预期占比 |
|------|---------|---------|---------|
| 低风险（关注） | 100-180 | 1.0-1.8 | 60-70% |
| 中风险（预警） | 181-240 | 1.8-2.4 | 15-25% |
| 高风险（警告） | 241-310 | 2.4-3.1 | 5-12% |
| 紧急风险（危急） | 311-400 | 3.1-4.0 | 1-3% |

### 风险判定逻辑

```
最终风险等级 = MAX(
    分数等级,           # 来自 total_score_ranges
    维度提升等级,        # 来自 dimension_pct_rules
    风险标签提升等级     # 来自 risk_tag_rules（需达到 min_count）
)
```

### 质量检测

- 快速作答检测（按题型阈值）
- 连续同选项检测
- 注意力检测题验证
- 矛盾题检测
- 规律作答检测（ABAB、ABCDABCD）
- 综合质量评分（0-100）

## 数据库迁移

```bash
cd backend
alembic upgrade head          # 执行迁移
alembic current               # 查看当前版本
alembic history               # 查看迁移链
```

迁移链（6 个，单 head）：
```
base → 001(create_all) → 002(phase2) → 003_qrf(规则字段) → 003(历史兼容) → 004(缺失列) → 005(通知表)
当前 head: 202606010005
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

## API 路由总览

| 路由 | 前缀 | 说明 |
|------|------|------|
| `auth.py` | `/api/v1/auth` | 登录、验证码、密码重置 |
| `users.py` | `/api/v1/users` | 学生/教师 CRUD、批量导入 |
| `classes.py` | `/api/v1/classes` | 班级管理 |
| `questionnaires.py` | `/api/v1/questionnaires` | 问卷 CRUD、题目管理、导入导出 |
| `tasks.py` | `/api/v1/tasks` | 任务 CRUD、完成状态、打回、延期 |
| `student.py` | `/api/v1/student` | 学生端答题流程 |
| `risks.py` | `/api/v1/risks` | 风险预警列表、详情 |
| `interventions.py` | `/api/v1/interventions` | 干预记录 CRUD |
| `dashboard.py` | `/api/v1/dashboard` | 数据看板（学校/教师/学生） |
| `reports.py` | `/api/v1/reports` | 报表（总览、风险、质量、纵向追踪） |
| `quality.py` | `/api/v1/quality` | 答题质量检测 |
| `ai_analysis.py` | `/api/v1/ai` | AI 分析（学生风险、班级报告） |
| `sms.py` | `/api/v1/sms` | 短信发送、模板、日志 |
| `notifications.py` | `/api/v1/notifications` | 站内消息通知 |
| `system.py` | `/api/v1/system` | 系统设置 |
| `exports.py` | `/api/v1/exports` | 数据导出 |
| `common.py` | `/api/v1/common` | 字典数据 |
| `platform.py` | `/api/v1/platform` | 平台监管端全部功能 |

## 风险文案规范

系统中所有风险相关表述必须使用以下措辞，禁止出现"问题学生""心理疾病""确诊"等词：

| 级别 | 提示语 |
|------|--------|
| 低风险 | "综合评估未发现明显风险信号" / "建议保持常规关注" |
| 中风险 | "存在明显的关注信号" / "建议班主任加强日常观察和沟通" |
| 高风险 | "多个维度存在明显风险信号" / "建议安排专业评估" |
| 紧急风险 | "存在高风险信号" / "建议立即启动干预流程" |

## 安全规则

- 所有敏感操作（查看学生详情、导出、AI 分析、发送短信）写入 `operation_logs` 表
- `selected_display_index` 由后端根据 `option_orders` 计算，不信任前端
- 学校管理员只能重置本校用户密码，不能操作 `platform_admin`
- 教师创建时强制 `role=teacher/counselor`，拒绝越权注入
- 删除操作级联清理所有关联数据（答卷、评分、质检、风险预警、干预记录）
- `.env`、`.env.production` 已被 `.gitignore` 排除，禁止提交密钥

## API 文档

后端启动后访问：
- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`

生产环境：`https://hm.annanyun.com/docs`

## 部署

详见 [OPS.md](OPS.md)

## 许可证

内部项目，未公开授权。
