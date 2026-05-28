import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import case, func
from ..database import get_db
from ..models.user import User, School, Grade, Class
from ..models.task import Task, AnswerSheet
from ..models.risk import RiskAlert, Intervention, ScoringResult, QualityAssessment
from ..models.audit import LoginLog, OperationLog
from ..models.questionnaire import Questionnaire
from ..models.external import SMSLog, AIAnalysisLog
from ..dependencies import require_role
from ..utils.response import APIResponse
from ..utils.password import hash_password
from ..utils.jwt import create_access_token
from ..config import settings
from ..services.audit_service import log_operation
from ..services.stats_service import platform_summary, recent_school_activity, school_metrics

router = APIRouter(prefix="/api/v1/platform", tags=["平台管理"])


def _validate_initial_password(password: str) -> None:
    if not password or len(password) < 10:
        raise HTTPException(status_code=400, detail="初始密码至少10位")
    if password in {"admin123", "padm123", "123456", "password"}:
        raise HTTPException(status_code=400, detail="初始密码不能使用弱默认密码")


def _create_school_admin(db: Session, school_id: int, data: dict) -> User:
    username = (data.get("username") or data.get("admin_username") or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="学校管理员用户名不能为空")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail=f"用户名 {username} 已存在")
    password = (data.get("password") or data.get("admin_password") or "").strip()
    _validate_initial_password(password)
    admin = User(
        school_id=school_id,
        username=username,
        password_hash=hash_password(password),
        real_name=(data.get("real_name") or data.get("admin_name") or "学校管理员").strip(),
        role="school_admin",
        phone=(data.get("phone") or "").strip(),
        status=True,
        must_change_password=True,
    )
    db.add(admin)
    db.flush()
    return admin


# ==================== 学校管理 ====================

@router.get("/schools")
def list_schools(page: int = Query(1), page_size: int = Query(20), keyword: str = Query(""),
                 user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    q = db.query(School)
    if keyword:
        q = q.filter(School.name.contains(keyword) | School.code.contains(keyword))
    total = q.count()
    schools = q.order_by(School.id).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for s in schools:
        student_count = db.query(func.count(User.id)).filter(User.school_id == s.id, User.role == "student").scalar()
        teacher_count = db.query(func.count(User.id)).filter(User.school_id == s.id, User.role.in_(["teacher", "counselor"])).scalar()
        admin_user = db.query(User).filter(User.school_id == s.id, User.role == "school_admin").first()
        metrics = school_metrics(db, s.id)
        active_at = recent_school_activity(db, s.id)
        items.append({
            "id": s.id, "name": s.name, "code": s.code, "address": s.address, "phone": s.phone,
            "student_count": student_count, "teacher_count": teacher_count,
            "admin_name": admin_user.real_name if admin_user else "未设置",
            "admin_username": admin_user.username if admin_user else "",
            "task_count": metrics["task_count"], "answer_sheet_count": metrics["answer_sheet_count"],
            "risk_count": metrics["risk_count"], "pending_risk_count": metrics["pending_risk_count"],
            "completion_rate": metrics["completion_rate"],
            "last_active_at": active_at.isoformat() if active_at else None,
            "status": s.status, "created_at": s.created_at.isoformat() if s.created_at else None,
        })
    return APIResponse.success({"items": items, "total": total, "page": page, "page_size": page_size,
                                "total_pages": max((total + page_size - 1) // page_size, 1)})


@router.post("/schools")
def create_school(data: dict, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    code = (data.get("code") or "").strip()
    if not name or not code:
        raise HTTPException(status_code=400, detail="学校名称和编码不能为空")

    existing = db.query(School).filter(School.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"学校编码 {code} 已存在")

    school = School(name=name, code=code, address=data.get("address", ""), phone=data.get("phone", ""))
    db.add(school)
    db.flush()

    admin = None
    if data.get("create_admin", True):
        admin_data = {
            "username": data.get("admin_username") or f"admin_{code}",
            "password": data.get("admin_password") or data.get("password"),
            "real_name": data.get("admin_name") or f"{name}管理员",
            "phone": data.get("admin_phone", ""),
        }
        admin = _create_school_admin(db, school.id, admin_data)
    db.commit()
    db.refresh(school)
    log_operation(db, user=user, request=request, module="platform_school", action="create",
                  object_type="school", object_id=school.id, object_name=school.name, result="success")
    if admin:
        log_operation(db, user=user, request=request, module="school_admin_account", action="create",
                      object_type="user", object_id=admin.id, object_name=admin.real_name, result="success")
    return APIResponse.success({"id": school.id, "name": school.name, "code": school.code,
                                "admin_username": admin.username if admin else ""}, message="学校创建成功")


@router.put("/schools/{school_id}")
def update_school(school_id: int, data: dict, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")
    for field in ["name", "code", "address", "phone"]:
        if field in data:
            setattr(school, field, data[field])
    if "status" in data:
        school.status = data["status"]
    db.commit()
    log_operation(db, user=user, request=request, module="platform_school", action="update",
                  object_type="school", object_id=school.id, object_name=school.name, result="success")
    return APIResponse.success(message="学校信息更新成功")


@router.delete("/schools/{school_id}")
def disable_school(school_id: int, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")
    school.status = False
    db.commit()
    log_operation(db, user=user, request=request, module="platform_school", action="disable",
                  object_type="school", object_id=school.id, object_name=school.name, result="success")
    return APIResponse.success(message="学校已停用")


@router.post("/schools/{school_id}/enable")
def enable_school(school_id: int, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")
    school.status = True
    db.commit()
    log_operation(db, user=user, request=request, module="platform_school", action="enable",
                  object_type="school", object_id=school.id, object_name=school.name, result="success")
    return APIResponse.success(message="学校已启用")


@router.post("/schools/{school_id}/enter")
def enter_school(school_id: int, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    """平台管理员以代入模式进入学校后台——JWT 保留平台身份并附加 school_context_id。"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")
    # 签发代入 token：保持平台管理员身份 + school_context_id
    token = create_access_token({
        "user_id": user.id,
        "role": "platform_admin",
        "school_context_id": school_id,
        "acting_as": "school_view",
    })
    return APIResponse.success({
        "access_token": token,
        "user": {
            "id": user.id,
            "school_id": user.school_id,
            "username": user.username,
            "real_name": user.real_name,
            "role": "platform_admin",
            "teacher_type": user.teacher_type,
            "gender": user.gender or "",
            "phone": user.phone or "",
            "student_no": user.student_no or "",
            "grade_id": user.grade_id,
            "class_id": user.class_id,
            "must_change_password": user.must_change_password,
        },
        "school_context": {"id": school.id, "name": school.name},
    })


@router.delete("/schools/{school_id}/force")
def force_delete_school(school_id: int, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")
    school_name = school.name
    # 删除该学校所有关联数据
    db.query(Intervention).filter(Intervention.school_id == school_id).delete()
    db.query(RiskAlert).filter(RiskAlert.school_id == school_id).delete()
    db.query(AnswerSheet).filter(AnswerSheet.student_id.in_(
        db.query(User.id).filter(User.school_id == school_id)
    )).delete(synchronize_session=False)
    db.query(Task).filter(Task.school_id == school_id).delete()
    db.query(User).filter(User.school_id == school_id).delete()
    db.query(Class).filter(Class.school_id == school_id).delete()
    db.query(Grade).filter(Grade.school_id == school_id).delete()
    db.delete(school)
    db.commit()
    log_operation(db, user=user, request=request, module="platform_school", action="force_delete",
                  object_type="school", object_id=school_id, object_name=school_name, result="success")
    return APIResponse.success(message="学校已彻底删除")


@router.get("/schools/{school_id}")
def get_school_detail(school_id: int, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")

    student_count = db.query(func.count(User.id)).filter(User.school_id == school_id, User.role == "student").scalar()
    teacher_count = db.query(func.count(User.id)).filter(User.school_id == school_id, User.role.in_(["teacher", "counselor"])).scalar()
    admin_user = db.query(User).filter(User.school_id == school_id, User.role == "school_admin").first()
    class_count = db.query(func.count(Class.id)).filter(Class.school_id == school_id).scalar()
    task_count = db.query(func.count(Task.id)).filter(Task.school_id == school_id).scalar()
    risk_count = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id).scalar()
    pending_risks = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id, RiskAlert.status == "pending").scalar()
    metrics = school_metrics(db, school_id)
    answer_sheet_count = metrics["answer_sheet_count"]
    recent_tasks = db.query(Task).filter(Task.school_id == school_id).order_by(Task.updated_at.desc()).limit(5).all()
    recent_logins = db.query(LoginLog).filter(LoginLog.school_id == school_id, LoginLog.result == "success").order_by(LoginLog.login_time.desc()).limit(5).all()
    recent_risk_updates = db.query(RiskAlert).filter(RiskAlert.school_id == school_id).order_by(RiskAlert.updated_at.desc()).limit(5).all()

    # 各年级统计
    grades = db.query(Grade).filter(Grade.school_id == school_id).all()
    grade_stats = []
    for g in grades:
        g_students = db.query(func.count(User.id)).filter(User.school_id == school_id, User.role == "student", User.grade_id == g.id).scalar()
        g_classes = db.query(func.count(Class.id)).filter(Class.grade_id == g.id).scalar()
        grade_stats.append({"name": g.name, "students": g_students, "classes": g_classes})

    # 风险分布
    from sqlalchemy import func as sa_func
    risk_dist = {}
    for level in ["low", "medium", "high", "urgent"]:
        risk_dist[level] = db.query(sa_func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id, RiskAlert.risk_level == level).scalar()

    return APIResponse.success({
        "id": school.id, "name": school.name, "code": school.code,
        "address": school.address, "phone": school.phone, "status": school.status,
        "admin_name": admin_user.real_name if admin_user else "未设置",
        "admin_username": admin_user.username if admin_user else "",
        "student_count": student_count, "teacher_count": teacher_count,
        "class_count": class_count, "task_count": task_count,
        "answer_sheet_count": answer_sheet_count,
        "risk_count": risk_count, "pending_risks": pending_risks,
        "metrics": metrics,
        "recent_tasks": [{"id": t.id, "name": t.name, "status": t.status, "updated_at": t.updated_at.isoformat() if t.updated_at else None} for t in recent_tasks],
        "recent_logins": [{"username": l.username, "role": l.user_role, "login_time": l.login_time.isoformat() if l.login_time else None} for l in recent_logins],
        "recent_risk_updates": [{"id": r.id, "student_id": r.student_id, "status": r.status, "latest_handled_at": r.latest_handled_at.isoformat() if r.latest_handled_at else None} for r in recent_risk_updates],
        "grades": grade_stats, "risk_distribution": risk_dist,
        "created_at": school.created_at.isoformat() if school.created_at else None,
    })

@router.get("/dashboard")
def platform_dashboard(user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    return APIResponse.success(platform_summary(db))


@router.get("/schools/{school_id}/admins")
def list_school_admins(school_id: int, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    if not db.query(School.id).filter(School.id == school_id).first():
        raise HTTPException(status_code=404, detail="学校不存在")
    admins = db.query(User).filter(User.school_id == school_id, User.role == "school_admin").order_by(User.id).all()
    return APIResponse.success([{
        "id": a.id,
        "username": a.username,
        "real_name": a.real_name,
        "phone": a.phone,
        "status": a.status,
        "must_change_password": a.must_change_password,
        "last_login_at": a.last_login_at.isoformat() if a.last_login_at else None,
    } for a in admins])


@router.post("/schools/{school_id}/admins")
def create_school_admin(school_id: int, data: dict, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    if not db.query(School.id).filter(School.id == school_id).first():
        raise HTTPException(status_code=404, detail="学校不存在")
    admin = _create_school_admin(db, school_id, data)
    db.commit()
    log_operation(db, user=user, request=request, module="school_admin_account", action="create",
                  object_type="user", object_id=admin.id, object_name=admin.real_name, result="success")
    return APIResponse.success({"id": admin.id, "username": admin.username}, message="学校管理员创建成功")


@router.post("/schools/{school_id}/admins/{admin_id}/reset-password")
def reset_school_admin_password(school_id: int, admin_id: int, data: dict, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_id, User.school_id == school_id, User.role == "school_admin").first()
    if not admin:
        raise HTTPException(status_code=404, detail="学校管理员不存在")
    password = (data.get("password") or "").strip()
    _validate_initial_password(password)
    admin.password_hash = hash_password(password)
    admin.must_change_password = True
    db.commit()
    log_operation(db, user=user, request=request, module="school_admin_account", action="reset_password",
                  object_type="user", object_id=admin.id, object_name=admin.real_name, result="success")
    return APIResponse.success(message="学校管理员密码已重置")


@router.post("/schools/{school_id}/admins/{admin_id}/disable")
def disable_school_admin(school_id: int, admin_id: int, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_id, User.school_id == school_id, User.role == "school_admin").first()
    if not admin:
        raise HTTPException(status_code=404, detail="学校管理员不存在")
    admin.status = False
    db.commit()
    log_operation(db, user=user, request=request, module="school_admin_account", action="disable",
                  object_type="user", object_id=admin.id, object_name=admin.real_name, result="success")
    return APIResponse.success(message="学校管理员已停用")


# ==================== 平台设置 ====================

@router.get("/settings")
def get_platform_settings(user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    from ..models.system_config import SystemConfig
    configs = {c.config_key: c.config_value for c in db.query(SystemConfig).filter(
        SystemConfig.config_key.in_(["platform_system_name", "platform_support_contact",
                                      "platform_default_admin_password"]),
        SystemConfig.school_id.is_(None)
    ).all()}
    return APIResponse.success({
        "system_name": configs.get("platform_system_name", "青盾 · 青少年风险防范测评管理系统"),
        "support_contact": configs.get("platform_support_contact", ""),
        "default_admin_password": configs.get("platform_default_admin_password", settings.ADMIN_PASSWORD),
    })


@router.put("/settings")
def update_platform_settings(data: dict, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    from ..models.system_config import SystemConfig
    key_map = {
        "system_name": "platform_system_name",
        "support_contact": "platform_support_contact",
        "default_admin_password": "platform_default_admin_password",
    }
    for field, config_key in key_map.items():
        if field in data:
            value = str(data[field]) if not isinstance(data[field], bool) else str(data[field]).lower()
            existing = db.query(SystemConfig).filter(SystemConfig.config_key == config_key, SystemConfig.school_id.is_(None)).first()
            if existing:
                existing.config_value = value
            else:
                db.add(SystemConfig(config_key=config_key, config_value=value, description=f"平台设置 - {field}"))
    db.commit()
    return APIResponse.success(message="平台设置保存成功")


# ============ 公安监管端 API ============

@router.get("/risk-alerts")
def platform_risk_alerts(
    page: int = Query(1), page_size: int = Query(20),
    school_id: int | None = Query(None), risk_level: str = Query(""),
    status: str = Query(""), keyword: str = Query(""),
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """平台风险预警中心——跨校风险列表"""
    q = db.query(RiskAlert).join(User, User.id == RiskAlert.student_id).join(School, School.id == RiskAlert.school_id)
    if school_id:
        q = q.filter(RiskAlert.school_id == school_id)
    if risk_level:
        q = q.filter(RiskAlert.risk_level == risk_level)
    if status:
        q = q.filter(RiskAlert.status == status)
    if keyword:
        q = q.filter(User.real_name.contains(keyword))
    total = q.count()
    items = q.order_by(RiskAlert.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    students = {u.id: u for u in db.query(User).filter(User.id.in_([a.student_id for a in items])).all()} if items else {}
    school_names = dict(db.query(School.id, School.name).filter(School.id.in_([a.school_id for a in items])).all()) if items else {}
    grade_names = dict(db.query(Grade.id, Grade.name).filter(Grade.id.in_([u.grade_id for u in students.values() if u.grade_id])).all()) if students else {}
    class_names = dict(db.query(Class.id, Class.name).filter(Class.id.in_([u.class_id for u in students.values() if u.class_id])).all()) if students else {}
    return APIResponse.success({
        "items": [{
            "id": a.id, "student_id": a.student_id, "student_name": students.get(a.student_id).real_name if students.get(a.student_id) else "",
            "school_id": a.school_id, "school_name": school_names.get(a.school_id, ""),
            "risk_level": a.risk_level, "risk_type": a.risk_type or "",
            "status": a.status, "created_at": a.created_at.isoformat() if a.created_at else None,
            "student_grade": grade_names.get(students[a.student_id].grade_id, "") if a.student_id in students else "",
            "student_class": class_names.get(students[a.student_id].class_id, "") if a.student_id in students else "",
        } for a in items],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/key-students")
def platform_key_students(
    page: int = Query(1), page_size: int = Query(20),
    school_id: int | None = Query(None), risk_level: str = Query(""),
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """重点学生——高风险/紧急风险学生详情"""
    q = db.query(RiskAlert).join(User, User.id == RiskAlert.student_id).join(School, School.id == RiskAlert.school_id).filter(
        RiskAlert.risk_level.in_(["high", "urgent"]))
    if school_id:
        q = q.filter(RiskAlert.school_id == school_id)
    if risk_level:
        q = q.filter(RiskAlert.risk_level == risk_level)
    total = q.count()
    alerts = q.order_by(
        case((RiskAlert.risk_level == "urgent", 0), (RiskAlert.risk_level == "high", 1), else_=2),
        RiskAlert.id.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()
    students = {u.id: u for u in db.query(User).filter(User.id.in_([a.student_id for a in alerts])).all()} if alerts else {}
    school_names = dict(db.query(School.id, School.name).filter(School.id.in_([a.school_id for a in alerts])).all()) if alerts else {}
    grade_names = dict(db.query(Grade.id, Grade.name).filter(Grade.id.in_([u.grade_id for u in students.values() if u.grade_id])).all()) if students else {}
    class_names = dict(db.query(Class.id, Class.name).filter(Class.id.in_([u.class_id for u in students.values() if u.class_id])).all()) if students else {}

    def _latest_score(student_id):
        sr = db.query(ScoringResult).join(AnswerSheet).filter(
            AnswerSheet.student_id == student_id).order_by(ScoringResult.id.desc()).first()
        if sr:
            int_count = db.query(func.count(Intervention.id)).filter(
                Intervention.student_id == student_id).scalar() or 0
            return {"total_score": sr.total_score, "risk_type": sr.risk_type or "", "intervention_count": int_count}
        return {"total_score": 0, "risk_type": "", "intervention_count": 0}

    return APIResponse.success({
        "items": [{
            **{k: v for k, v in a.__dict__.items() if not k.startswith("_")},
            "student_name": students.get(a.student_id).real_name if students.get(a.student_id) else "",
            "school_name": school_names.get(a.school_id, ""),
            "student_grade": grade_names.get(students[a.student_id].grade_id, "") if a.student_id in students else "",
            "student_class": class_names.get(students[a.student_id].class_id, "") if a.student_id in students else "",
            "latest_score": _latest_score(a.student_id),
            "created_at": a.created_at.isoformat() if a.created_at else None,
        } for a in alerts],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/tasks")
def platform_tasks(
    page: int = Query(1), page_size: int = Query(20),
    school_id: int | None = Query(None), status: str = Query(""),
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """测评任务监管——跨校任务列表"""
    q = db.query(Task).join(School, School.id == Task.school_id)
    if school_id:
        q = q.filter(Task.school_id == school_id)
    if status:
        q = q.filter(Task.status == status)
    total = q.count()
    tasks = q.order_by(Task.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    school_names = dict(db.query(School.id, School.name).filter(School.id.in_([t.school_id for t in tasks])).all()) if tasks else {}
    return APIResponse.success({
        "items": [{
            "id": t.id, "name": t.name, "school_id": t.school_id,
            "school_name": school_names.get(t.school_id, ""),
            "status": t.status, "questionnaire_title": (t.questionnaire.title if t.questionnaire else ""),
            "created_by_name": (t.created_by_user.real_name if hasattr(t, 'created_by_user') and t.created_by_user else ""),
            "start_time": t.start_time.isoformat() if t.start_time else None,
            "end_time": t.end_time.isoformat() if t.end_time else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in tasks],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/interventions")
def platform_interventions(
    page: int = Query(1), page_size: int = Query(20),
    school_id: int | None = Query(None), status: str = Query(""),
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """干预督办——跨校干预记录列表"""
    q = db.query(Intervention).join(User, User.id == Intervention.student_id).join(School, School.id == Intervention.school_id)
    if school_id:
        q = q.filter(Intervention.school_id == school_id)
    if status:
        q = q.filter(Intervention.status == status)
    total = q.count()
    items = q.order_by(Intervention.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    student_names = dict(db.query(User.id, User.real_name).filter(User.id.in_([iv.student_id for iv in items])).all()) if items else {}
    teacher_names = dict(db.query(User.id, User.real_name).filter(User.id.in_([iv.teacher_id for iv in items if iv.teacher_id])).all()) if items else {}
    school_names = dict(db.query(School.id, School.name).filter(School.id.in_([iv.school_id for iv in items])).all()) if items else {}
    return APIResponse.success({
        "items": [{
            "id": iv.id, "student_id": iv.student_id, "school_id": iv.school_id,
            "student_name": student_names.get(iv.student_id, ""),
            "school_name": school_names.get(iv.school_id, ""),
            "teacher_name": teacher_names.get(iv.teacher_id, ""),
            "method": iv.method, "status": iv.status, "content": (iv.content or "")[:200],
            "need_follow_up": iv.need_follow_up,
            "intervention_time": iv.intervention_time.isoformat() if iv.intervention_time else None,
            "next_follow_up_time": iv.next_follow_up_time.isoformat() if iv.next_follow_up_time else None,
            "created_at": iv.created_at.isoformat() if iv.created_at else None,
        } for iv in items],
        "total": total, "page": page, "page_size": page_size,
    })


@router.put("/interventions/{intervention_id}/urge")
def platform_urge_intervention(
    intervention_id: int, request: Request,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """干预督办——督促学校处理"""
    iv = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if not iv:
        raise HTTPException(status_code=404, detail="干预记录不存在")
    iv.status = "follow_up"
    iv.need_follow_up = True
    db.commit()
    log_operation(db, user, request, module="platform_supervision", action="urge_intervention",
                  object_type="intervention", object_id=intervention_id, object_name=str(iv.student_id),
                  detail=f"school_id={iv.school_id}")
    return APIResponse.success(message="已督促学校处理")


@router.get("/audit-logs")
def platform_audit_logs(
    page: int = Query(1), page_size: int = Query(20),
    module: str = Query(""), action: str = Query(""),
    operator_role: str = Query(""), keyword: str = Query(""),
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """操作日志审计"""
    q = db.query(OperationLog)
    if module:
        q = q.filter(OperationLog.module == module)
    if action:
        q = q.filter(OperationLog.action == action)
    if operator_role:
        q = q.filter(OperationLog.operator_role == operator_role)
    if keyword:
        q = q.filter(
            OperationLog.operator_name.contains(keyword) |
            OperationLog.module.contains(keyword) |
            OperationLog.action.contains(keyword)
        )
    total = q.count()
    items = q.order_by(OperationLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return APIResponse.success({
        "items": [{
            "id": log.id, "module": log.module, "action": log.action,
            "operator_name": log.operator_name, "operator_role": log.operator_role,
            "object_type": log.object_type, "object_id": log.object_id,
            "object_name": log.object_name, "result": log.result,
            "detail": log.detail or "", "ip": log.ip or "",
            "created_at": log.created_at.isoformat() if log.created_at else None,
        } for log in items],
        "total": total, "page": page, "page_size": page_size,
    })


# ============ 短信中心 ============

@router.get("/sms-logs")
def platform_sms_logs(
    page: int = Query(1), page_size: int = Query(20),
    status: str = Query(""), keyword: str = Query(""),
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """公安监管端短信日志——跨校短信发送记录"""
    q = db.query(SMSLog)
    if status:
        q = q.filter(SMSLog.status == status)
    if keyword:
        q = q.filter(SMSLog.phone.contains(keyword))
    total = q.count()
    items = q.order_by(SMSLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return APIResponse.success({
        "items": [{
            "id": s.id, "recipient_name": s.recipient_name, "phone": s.phone or "",
            "sms_type": s.sms_type or "", "status": s.status or "",
            "failure_reason": s.failure_reason or "", "school_id": s.school_id,
            "sent_at": s.sent_at.isoformat() if s.sent_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        } for s in items],
        "total": total, "page": page, "page_size": page_size,
    })


@router.post("/send-sms")
def platform_send_sms(
    data: dict, request: Request,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """公安监管端发送催办短信"""
    phone = (data.get("phone") or "").strip()
    content = (data.get("content") or "").strip()
    if not phone or len(phone) < 11:
        raise HTTPException(status_code=400, detail="请输入正确的手机号")
    if not content:
        raise HTTPException(status_code=400, detail="请输入短信内容")

    sms_sent = False
    failure_reason = ""
    from ..models.system_config import SystemConfig
    sms_url_config = db.query(SystemConfig).filter(
        SystemConfig.config_key == "sms_api_url", SystemConfig.school_id.is_(None)).first()
    sms_key_config = db.query(SystemConfig).filter(
        SystemConfig.config_key == "sms_app_key", SystemConfig.school_id.is_(None)).first()
    sms_url = settings.SMS_API_URL or (sms_url_config.config_value if sms_url_config else "")
    sms_key = settings.SMS_APP_KEY or (sms_key_config.config_value if sms_key_config else "")

    if sms_url and sms_key:
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    sms_url,
                    json={"phone": phone, "content": content},
                    headers={"Authorization": f"Bearer {sms_key}"},
                )
                sms_sent = resp.status_code == 200
                if not sms_sent:
                    failure_reason = f"短信服务返回 HTTP {resp.status_code}"
        except Exception as exc:
            failure_reason = str(exc)[:300]
    else:
        failure_reason = "短信服务暂未配置"

    status = "sent" if sms_sent else ("not_configured" if not sms_url else "failed")
    db.add(SMSLog(
        recipient_name="", phone=phone,
        school_id=None, sms_type="platform_urge",
        template_code="manual", content=content,
        status=status, failure_reason=failure_reason,
        sender_id=user.id, sent_at=func.now(),
    ))
    db.commit()

    log_operation(db, user, request, module="platform_sms", action="send",
                  object_type="sms", object_id=phone[-4:],
                  result="success" if sms_sent else "failure",
                  detail=f"status={status};content_len={len(content)}")

    if not sms_sent:
        return APIResponse.success({"message": "短信发送失败", "reason": failure_reason, "sms_sent": False}, message="发送失败")
    return APIResponse.success({"message": "短信发送成功", "sms_sent": True}, message="发送成功")


# ============ 风险预警详情 ============

@router.get("/risks/{alert_id}")
def platform_risk_detail(alert_id: int, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    alert = db.query(RiskAlert).filter(RiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="风险预警不存在")
    student = db.query(User).filter(User.id == alert.student_id).first()
    school = db.query(School).filter(School.id == alert.school_id).first()
    sr = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == alert.answer_sheet_id).first()
    qa = db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id == alert.answer_sheet_id).first()
    interventions = db.query(Intervention).filter(Intervention.risk_alert_id == alert.id).all()
    log_operation(db, user, request, module="platform_risk", action="view_detail",
                  object_type="risk_alert", object_id=alert_id, object_name=student.real_name if student else "")
    return APIResponse.success({
        "id": alert.id, "risk_level": alert.risk_level, "risk_type": alert.risk_type or "",
        "status": alert.status, "trigger_method": alert.trigger_method or "",
        "student_name": student.real_name if student else "", "student_id": alert.student_id,
        "school_name": school.name if school else "", "school_id": alert.school_id,
        "total_score": sr.total_score if sr else 0, "dimension_scores": sr.dimension_scores if sr else {},
        "quality_level": qa.quality_level if qa else "", "quality_score": qa.quality_score if qa else 0,
        "interventions": [{"id": iv.id, "method": iv.method, "status": iv.status, "content": iv.content or "",
            "created_at": iv.created_at.isoformat() if iv.created_at else None} for iv in interventions],
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    })


# ============ 重点关注学生档案 ============

@router.get("/key-students/{student_id}")
def platform_student_profile(student_id: int, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    alerts = db.query(RiskAlert).filter(RiskAlert.student_id == student_id).order_by(RiskAlert.id.desc()).all()
    interventions = db.query(Intervention).filter(Intervention.student_id == student_id).order_by(Intervention.id.desc()).all()
    scores = db.query(ScoringResult).join(AnswerSheet).filter(AnswerSheet.student_id == student_id).order_by(ScoringResult.id.desc()).all()
    qas = db.query(QualityAssessment).join(AnswerSheet).filter(AnswerSheet.student_id == student_id).all()
    log_operation(db, user, request, module="platform_student", action="view_profile",
                  object_type="student", object_id=student_id, object_name=student.real_name)
    return APIResponse.success({
        "student_id": student.id, "student_name": student.real_name,
        "school_name": student.school.name if student.school else "",
        "grade": student.grade.name if student.grade else "", "class": student.class_.name if student.class_ else "",
        "alerts": [{"id": a.id, "risk_level": a.risk_level, "risk_type": a.risk_type or "", "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None} for a in alerts],
        "interventions": [{"id": iv.id, "method": iv.method, "status": iv.status, "content": (iv.content or "")[:200],
            "created_at": iv.created_at.isoformat() if iv.created_at else None} for iv in interventions],
        "scores": [{"total_score": s.total_score, "risk_level": s.risk_level, "dimension_scores": s.dimension_scores or {},
            "created_at": s.created_at.isoformat() if s.created_at else None} for s in scores],
        "quality": [{"level": q.quality_level, "score": q.quality_score, "validity": q.validity} for q in qas],
    })


# ============ 超期干预 ============

@router.get("/interventions/overdue")
def platform_overdue_interventions(user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    from datetime import datetime, timedelta, timezone
    tz = timezone(timedelta(hours=8))
    deadline = datetime.now(tz) - timedelta(days=7)
    items = db.query(Intervention).filter(
        Intervention.status.in_(["pending", "in_progress", "follow_up"]),
        Intervention.created_at < deadline,
    ).order_by(Intervention.created_at).limit(50).all()
    return APIResponse.success({"items": [{
        "id": iv.id, "student_id": iv.student_id, "school_id": iv.school_id,
        "status": iv.status, "created_at": iv.created_at.isoformat() if iv.created_at else None,
    } for iv in items], "total": len(items)})


# ============ 督办提醒 ============

@router.post("/interventions/{intervention_id}/remind")
def platform_remind_intervention(intervention_id: int, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    iv = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if not iv:
        raise HTTPException(status_code=404, detail="干预记录不存在")
    log_operation(db, user, request, module="platform_supervision", action="remind",
                  object_type="intervention", object_id=intervention_id, detail=f"school_id={iv.school_id}")
    return APIResponse.success(message="督办提醒已发送")


# ============ AI 研判 ============

@router.get("/ai-logs")
def platform_ai_logs(page: int = Query(1), page_size: int = Query(20), user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    q = db.query(AIAnalysisLog).order_by(AIAnalysisLog.id.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return APIResponse.success({"items": [{
        "id": l.id, "analysis_type": l.analysis_type, "model_name": l.model_name or "", "status": l.status or "",
        "duration_ms": l.duration_ms or 0, "user_role": l.user_role or "", "error_message": l.error_message or "",
        "created_at": l.created_at.isoformat() if l.created_at else None,
    } for l in items], "total": total, "page": page, "page_size": page_size})


@router.post("/ai-analysis/regional")
def platform_ai_regional(data: dict | None = None, request: Request = None, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    summary = platform_summary(db)
    schools = summary.get("completion_rankings", [])[:5]
    risks = summary.get("risk_rankings", [])[:5]
    prompt = f"""区域风险态势研判报告:
接入学校{summary.get('school_total',0)}所, 学生{summary.get('student_total',0)}人, 风险预警{summary.get('risk_alert_total',0)}条, 待处理{summary.get('pending_risk_total',0)}条。
学校完成率排名: {', '.join(f"{s['name']}: {s.get('completion_rate',0)}%" for s in schools)}。
风险排名: {', '.join(f"{s['name']}: {s.get('risk_count',0)}条" for s in risks)}。
请生成教育管理部门视角的区域风险防范态势研判。"""
    return APIResponse.success({"analysis": prompt, "configured": False})


# ============ 审计日志增强 ============

@router.get("/audit/login-logs")
def platform_login_logs(page: int = Query(1), page_size: int = Query(20), school_id: int | None = Query(None),
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    q = db.query(LoginLog).order_by(LoginLog.id.desc())
    if school_id: q = q.filter(LoginLog.school_id == school_id)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return APIResponse.success({"items": [{
        "id": l.id, "username": l.username, "user_role": l.user_role, "school_id": l.school_id,
        "login_time": l.login_time.isoformat() if l.login_time else None,
        "login_ip": l.login_ip or "", "result": l.result, "failure_reason": l.failure_reason or "",
    } for l in items], "total": total, "page": page, "page_size": page_size})


@router.get("/audit/export-logs")
def platform_export_logs(page: int = Query(1), page_size: int = Query(20),
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    q = db.query(OperationLog).filter(OperationLog.action.ilike("%export%")).order_by(OperationLog.id.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return APIResponse.success({"items": [{
        "id": l.id, "operator_name": l.operator_name, "operator_role": l.operator_role,
        "module": l.module, "action": l.action, "object_name": l.object_name,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    } for l in items], "total": total, "page": page, "page_size": page_size})

