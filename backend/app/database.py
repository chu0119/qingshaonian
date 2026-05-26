from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings
from .models.base import Base
from .models.user import School, User, Grade, Class, TeacherClass
from .models.system_config import SystemConfig
from .models.questionnaire import Questionnaire, Question, Option, ContradictionGroup
from .models.task import Task, AnswerSheet, AnswerRecord
from .models.risk import ScoringResult, QualityAssessment, RiskAlert, Intervention
from .models.audit import LoginLog, OperationLog
from .models.external import SMSLog, AIAnalysisLog

_engine_kwargs = {"echo": settings.DEBUG}
if settings.DB_TYPE == "sqlite":
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs.update({"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20})

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)


def create_default_school(db):
    school = db.query(School).filter(School.code == "MINGDE").first()
    if not school:
        school = School(name="明德实验学校", code="MINGDE", address="", phone="")
        db.add(school)
        db.flush()

        # 创建默认年级
        grades_data = [("初一", 1), ("初二", 2), ("初三", 3)]
        grades = {}
        for gname, gsort in grades_data:
            grade = Grade(school_id=school.id, name=gname, sort_order=gsort)
            db.add(grade)
            db.flush()
            grades[gname] = grade

        # 创建默认班级
        classes_data = [
            ("初一(1)班", grades["初一"]), ("初一(2)班", grades["初一"]),
            ("初二(1)班", grades["初二"]), ("初二(2)班", grades["初二"]),
            ("初三(1)班", grades["初三"]), ("初三(2)班", grades["初三"]),
        ]
        for cname, grade in classes_data:
            db.add(Class(school_id=school.id, grade_id=grade.id, name=cname))

        db.flush()

    return school


def create_default_admin(db, school_id: int):
    from .utils.password import hash_password

    if not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
        return None
    user = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
    if not user:
        user = User(
            school_id=school_id,
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            real_name="系统管理员",
            role="school_admin",
            must_change_password=True,
        )
        db.add(user)
        db.flush()

    return user


def create_builtin_dictionaries(db):
    """初始化系统字典数据（风险等级、答题质量等级等）。"""
    from .models.system_config import SystemConfig

    configs = [
        ("risk_levels", '{"low": {"name":"低风险","min_score":0,"max_score":25},"medium":{"name":"中风险","min_score":26,"max_score":50},"high":{"name":"高风险","min_score":51,"max_score":75},"urgent":{"name":"紧急风险","min_score":76,"max_score":100}}', "风险等级配置"),
        ("quality_levels", '{"normal":{"name":"正常","min_score":80},"mild_anomaly":{"name":"轻度异常","min_score":60},"moderate_anomaly":{"name":"中度异常","min_score":40},"severe_anomaly":{"name":"高度异常","min_score":0}}', "答题质量等级配置"),
        ("fast_answer_threshold", '{"total_min_seconds_per_question":2,"consecutive_fast_count":8,"consecutive_fast_seconds":1}', "快速作答检测阈值"),
        ("consecutive_same_threshold", '{"max_consecutive_count":10}', "连续同选项检测阈值"),
    ]

    for key, value, desc in configs:
        existing = (
            db.query(SystemConfig)
            .filter(SystemConfig.config_key == key, SystemConfig.school_id.is_(None))
            .first()
        )
        if not existing:
            db.add(SystemConfig(config_key=key, config_value=value, description=desc))


def seed_all(db):
    from .config import settings as _settings

    env = getattr(_settings, "APP_ENV", "demo").lower()

    # Production: only create the admin account (school/org must be created explicitly).
    if env == "production":
        from .models.user import User
        if _settings.ADMIN_USERNAME and _settings.ADMIN_PASSWORD:
            user = db.query(User).filter(User.username == _settings.ADMIN_USERNAME).first()
            if not user:
                from .utils.password import hash_password
                db.add(User(
                    username=_settings.ADMIN_USERNAME,
                    password_hash=hash_password(_settings.ADMIN_PASSWORD),
                    real_name="系统管理员",
                    role="school_admin",
                    must_change_password=True,
                ))
        if _settings.PLATFORM_ADMIN_USERNAME and _settings.PLATFORM_ADMIN_PASSWORD:
            from .utils.password import hash_password
            from .models.user import User
            platform_admin = db.query(User).filter(User.username == _settings.PLATFORM_ADMIN_USERNAME).first()
            if not platform_admin:
                db.add(User(
                    username=_settings.PLATFORM_ADMIN_USERNAME,
                    password_hash=hash_password(_settings.PLATFORM_ADMIN_PASSWORD),
                    real_name="平台管理员",
                    role="platform_admin",
                    status=True,
                ))
        create_builtin_dictionaries(db)
        db.commit()
        return

    # Demo / development: create default school, admin, and platform admin.
    school = create_default_school(db)
    create_default_admin(db, school.id)
    create_builtin_dictionaries(db)
    if _settings.PLATFORM_ADMIN_USERNAME and _settings.PLATFORM_ADMIN_PASSWORD:
        from .utils.password import hash_password
        from .models.user import User
        platform_admin = db.query(User).filter(User.username == _settings.PLATFORM_ADMIN_USERNAME).first()
        if not platform_admin:
            db.add(User(
                username=_settings.PLATFORM_ADMIN_USERNAME,
                password_hash=hash_password(_settings.PLATFORM_ADMIN_PASSWORD),
                real_name="平台管理员",
                role="platform_admin",
                status=True,
            ))
    db.commit()
