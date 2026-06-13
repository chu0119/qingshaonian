# AGENTS.md — 青少年风险防范测评管理系统

## Quick Commands

### Backend
```bash
# Start dev server
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Run tests (66 tests)
cd backend && python -m compileall app -q && python -m pytest tests/ -v

# Database migration
cd backend && alembic upgrade head
```

### Frontend
```bash
# Start dev server
cd frontend && npm run dev  # http://localhost:3000

# Build (typecheck + bundle)
cd frontend && npm run build

# Lint
cd frontend && npm run lint
```

### Windows One-Click
Double-click `启动系统.bat` — starts backend (8000) + frontend (3000).

## Architecture

| Layer | Tech |
|-------|------|
| Frontend | React 18 + TypeScript + Vite + Ant Design 5 + ECharts + Zustand |
| Backend | FastAPI + SQLAlchemy 2 + Alembic + Pydantic 2 |
| Database | MySQL 8 (prod) / SQLite (dev) |
| Deploy | BaoTao panel, domain `hm.annanyun.com`, systemd |

**Scale**: 161 source files, ~31,600 lines (Python 16,252 + TypeScript 15,363)

## Role System

| Role | Route Prefix | Access |
|------|-------------|--------|
| `platform_admin` | `/platform/` | All schools, can enter school context |
| `school_admin` | `/school-admin/` | Own school only |
| `teacher/counselor` | `/teacher/` | Assigned classes |
| `student` | `/student/` | Own questionnaires only |

**Platform admin entering school**: `/api/v1/platform/enter` returns JWT with `school_context_id`, preserving `platform_admin` role.

## Critical Rules (Never Violate)

### Permission Model
1. `get_current_user` sets `user._effective_school_id` from JWT's `school_context_id` — **never** modify ORM `user.school_id`
2. All routes use `(getattr(user, '_effective_school_id', None) or user.school_id)` for school ID
3. `require_role` allows `platform_admin` with `school_context_id` to access school-level routes

### Security
1. School admins can only reset passwords for own school users, not `platform_admin`
2. Teacher creation forces `role=teacher/counselor`, rejects `school_admin`/`platform_admin` injection
3. `selected_display_index` computed backend from `option_orders` — never trust frontend value
4. Sensitive ops (view student details/export/AI analysis/send SMS/enter school) must write `operation_logs`
5. Delete operations must cascade clean (answer sheets/scoring/quality/risk alerts/interventions/teacher-class associations)

### Forbidden Changes
- Do NOT modify scoring rules (`scoring_service.py`) or risk rules
- Do NOT modify AI/SMS sending logic
- Do NOT delete school/teacher/student features
- Do NOT rewrite existing business logic
- Frontend must NOT fabricate data (show "暂无数据" instead)

### Risk Language
Use: "风险提示""关注信号""重点关注""建议跟进"
Forbidden: "问题学生""心理疾病""确诊"

## Code Conventions

### Backend
- **Models**: `backend/app/models/` — 9 modules (user, questionnaire, task, risk, audit, external, system_config, notification)
- **Routers**: `backend/app/routers/` — 18 modules, prefix `/api/v1/`
- **Services**: `backend/app/services/` — 12 modules, business logic layer
- **Schemas**: `backend/app/schemas/` — Pydantic request/response models
- **Built-in questionnaires**: `backend/app/questionnaire_bank/builtin_questionnaires.py` (39 sets)

### Frontend
- **Pages**: `frontend/src/pages/` — platform (14), school-admin (15), teacher (8), student (6)
- **Components**: `frontend/src/components/` — layout (MainLayout, StudentLayout), screen/, ai/, common/
- **API client**: `frontend/src/api/client.ts` — axios instance, baseURL `/api/v1`, JWT Bearer
- **State**: `frontend/src/stores/authStore.ts` — Zustand, token/role persisted to localStorage
- **Routes**: `frontend/src/routes/index.tsx` — role-based routing with `ProtectedRoute`

### Mobile
- Tables: add `scroll={{ x: 'max-content' }}`
- Modals: add `style={{ maxWidth: '95vw' }}`

## Database Migrations

Alembic chain (6 migrations, single head):
```
base → 001(create_all) → 002(phase2) → 003_qrf(规则字段+hash) → 003(历史兼容) → 004(缺失列) → 005(通知表)
```
Current head: `202606010005`

**Adding new migrations**: Be cautious. No model changes without evaluating impact.

## Testing

```bash
# Backend: compile check + unit tests
cd backend && python -m compileall app -q && python -m pytest tests/ -v

# Frontend: typecheck + build
cd frontend && npm run build
```

Current: **66 tests passing**

## Deployment

### Server (current)
- SSH: `ssh ubuntu@119.45.241.31` — password auth
- Backend: systemd `qingshaonian` service on port 8000
- Frontend: Nginx on 443 (HTTPS), proxied to backend

### Deploy Frontend
```bash
cd frontend && npm run build
sshpass -f .deploy_pwd scp -r frontend/dist/* ubuntu@119.45.241.31:/www/wwwroot/qingshaonian/frontend/dist/
```

### Deploy Backend
```bash
# ubuntu user lacks write permission to /www/wwwroot/, use /tmp + sudo
sshpass -f .deploy_pwd scp backend/app/routers/xxx.py ubuntu@119.45.241.31:/tmp/
sshpass -f .deploy_pwd ssh ubuntu@119.45.241.31 "sudo cp /tmp/xxx.py /www/wwwroot/qingshaonian/backend/app/routers/ && sudo systemctl restart qingshaonian"
```

### GitHub Push (requires proxy)
```bash
export https_proxy=http://127.0.0.1:7897; git push origin master
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app entry, CORS, router mounting |
| `backend/app/dependencies.py` | `get_current_user`, `require_role` |
| `backend/app/services/scoring_service.py` | Scoring + quality check + risk rules (DO NOT MODIFY) |
| `backend/app/services/questionnaire_service.py` | Questionnaire CRUD |
| `frontend/src/routes/index.tsx` | All route definitions |
| `frontend/src/stores/authStore.ts` | Auth state management |
| `frontend/src/api/client.ts` | Axios instance config |
