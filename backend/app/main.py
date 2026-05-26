from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .database import init_db, seed_all, SessionLocal
from .config import settings, validate_production_settings


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
