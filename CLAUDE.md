# CLAUDE.md — 青少年风险防范测评管理系统

## 架构概览
- **前端**: React 18 + TypeScript + Vite + Ant Design 5 + ECharts + Zustand + React Router 6
- **后端**: FastAPI + SQLAlchemy 2 + Alembic + Pydantic 2
- **数据库**: MySQL (生产) / SQLite (开发)
- **部署**: 宝塔面板, 域名 a.annanyun.com, systemd 托管后端

## 项目结构
```
frontend/src/
  api/         — axios 客户端 (baseURL=/api/v1), 各模块 API
  components/  — layout/MainLayout(管理员), layout/StudentLayout(学生), ai/, common/, screen/(大屏公共组件)
  pages/       — platform/(公安监管端), school-admin/, teacher/, student/, LoginPage
  routes/      — ProtectedRoute(角色鉴权), 全局路由表
  stores/      — zustand authStore (token/role 持久化到 localStorage)
  styles/      — global.css

backend/
  app/
    main.py / config.py / database.py / dependencies.py
    routers/   — 18 个路由模块
    services/  — scoring_service(评分+质量检测), questionnaire_service, seed_service 等
    models/    — user, questionnaire, task, risk, audit, external, system_config, notification
    schemas/   — Pydantic 请求/响应模型
    questionnaire_bank/ — 39 套内置问卷
    alembic/   — 6 个迁移 (001→002→003_qrf→003→004→005, 单 head)
    tests/     — 7 个测试模块
```

## 角色体系
| 角色 | 路由前缀 | 权限范围 |
|------|---------|---------|
| platform_admin | /platform/ | 公安监管端, 14 项菜单, 可进入学校后台 |
| school_admin | /school-admin/ | 本校完整管理 |
| teacher/counselor | /teacher/ | 所负责班级 |
| student | /student/ | 本人问卷 |

## 关键规则（不可违反）

### 权限
1. `get_current_user` 通过 JWT 中的 `school_context_id` 设置 `user._effective_school_id`, **绝不**修改 ORM `user.school_id`
2. 所有路由使用 `(getattr(user, '_effective_school_id', None) or user.school_id)` 获取有效学校 ID
3. `require_role` 允许 platform_admin 带 school_context_id 访问学校级路由
4. 平台管理员进入学校后台: `/enter` 签发含 `school_context_id` 的 JWT, 保留 platform_admin 身份

### 安全
1. 学校管理员只能重置本校用户密码, 不能重置 platform_admin
2. 教师创建强制 role=teacher/counselor, 拒绝 school_admin/platform_admin 注入
3. `selected_display_index` 后端根据 `option_orders` 计算, 不信任前端传值
4. 敏感操作(查看学生详情/导出/AI分析/发送短信/进入学校)必须写 `operation_logs`
5. 删除操作必须级联清理关联数据(答卷/评分/质检/风险预警/干预/教师班级关联)

### 兼容
1. 新增 Alembic 迁移需谨慎(当前 6 个, head: 202606010005)
2. 不修改数据库模型需评估影响
3. 不修改问卷评分规则(`scoring_service.py`)和风险规则
4. 不修改 AI/短信发送逻辑

## 开发规则
- 不可删除学校端/教师端/学生端功能
- 不可重写已有业务逻辑
- 前端不编造假数据（显示"暂无数据"）
- 风险文案: "风险提示""关注信号""重点关注""建议跟进", 禁止"问题学生""心理疾病""确诊"
- 移动端表格加 `scroll={{ x: 'max-content' }}`, Modal 加 `style={{ maxWidth: '95vw' }}`

## Alembic 迁移链
```
base → 001(create_all) → 002(phase2) → 003_qrf(规则字段+hash) → 003(历史兼容) → 004(缺失列) → 005(通知表)
```
- 单 head: `202606010005`

## 测试
- 后端: `cd backend && python -m compileall app -q && python -m pytest tests/ -v`
- 前端: `cd frontend && npm run build`
- 当前 66 测试通过

## 服务器（参见 memory/baota-server-connection.md）
- SSH: `ssh -i ~/.ssh/baota_key root@106.53.174.3`
- 部署: `scp -i ~/.ssh/baota_key -r frontend/dist/ root@106.53.174.3:/www/wwwroot/qingshaonian/frontend/`
- GitHub push 需设置代理: `export https_proxy=http://127.0.0.1:7897; git push origin master`

## 大屏组件 (frontend/src/components/screen/)
- ScreenShell: 统一外壳(标题/时钟/全屏按钮/确定性星空背景)
- ScreenCard: 卡片容器(省略标题/移动端缩小 padding)
- ScreenKpiCard: KPI 卡片(fmtNumber 万级/无 emoji)
- ScreenChart: ECharts 包装(resize 适配/空状态)
- RankingList/LatestList: 排名/最新列表
- 大屏**不强制全屏**, 不自动 navigate(-1)
