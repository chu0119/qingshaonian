from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import os
from .database import init_db, seed_all, SessionLocal
from .config import settings, validate_production_settings

MAX_PAGE_SIZE = 200


class PageSizeClampMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Clamp page_size query param to MAX_PAGE_SIZE
        ps = request.query_params.get("page_size")
        if ps is not None:
            try:
                val = int(ps)
                if val > MAX_PAGE_SIZE:
                    # Replace in scope query string
                    qs = str(request.scope.get("query_string", b"").decode())
                    qs = qs.replace(f"page_size={ps}", f"page_size={MAX_PAGE_SIZE}")
                    request.scope["query_string"] = qs.encode()
            except (ValueError, TypeError):
                pass
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_production_settings()
    init_db()
    db = SessionLocal()
    try:
        seed_all(db)
        from .services.seed_service import initialize_seed_data
        initialize_seed_data(db, settings)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(PageSizeClampMiddleware)

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()] or ["http://localhost:5173", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routers import auth, common
from .routers import dashboard as dashboard_router
from .routers import classes as classes_router
from .routers import users as users_router
from .routers import questionnaires as questionnaire_router
from .routers import tasks as tasks_router
from .routers import student as student_router
from .routers import risks as risks_router
from .routers import quality as quality_router
from .routers import interventions as interventions_router
from .routers import reports as reports_router
from .routers import exports as exports_router
from .routers import system as system_router
from .routers import ai_analysis as ai_router
from .routers import platform as platform_router
from .routers import sms as sms_router
from .routers import notifications as notifications_router

app.include_router(auth.router)
app.include_router(common.router)
app.include_router(dashboard_router.router)
app.include_router(classes_router.router)
app.include_router(users_router.router)
app.include_router(questionnaire_router.router)
app.include_router(tasks_router.router)
app.include_router(student_router.router)
app.include_router(risks_router.router)
app.include_router(quality_router.router)
app.include_router(interventions_router.router)
app.include_router(reports_router.router)
app.include_router(exports_router.router)
app.include_router(system_router.router)
app.include_router(ai_router.router)
app.include_router(platform_router.router)
app.include_router(sms_router.router)
app.include_router(notifications_router.router)


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
