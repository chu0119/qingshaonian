import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.user import User, School, Grade, Class
from ..models.task import Task, AnswerSheet
from ..models.risk import RiskAlert, Intervention
from ..models.audit import LoginLog
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
    """平台管理员模拟进入学校后台"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")
    admin = db.query(User).filter(
        User.school_id == school_id,
        User.role == "school_admin",
        User.status == True,
    ).first()
    if not admin:
        raise HTTPException(status_code=400, detail="该学校暂无启用的管理员账号，请先创建")
    token = create_access_token({"user_id": admin.id, "role": admin.role})
    return APIResponse.success({"access_token": token, "user": {
        "id": admin.id, "school_id": admin.school_id, "username": admin.username,
        "real_name": admin.real_name, "role": admin.role,
        "teacher_type": admin.teacher_type, "gender": admin.gender or "",
        "phone": admin.phone or "", "student_no": admin.student_no or "",
        "grade_id": admin.grade_id, "class_id": admin.class_id,
        "must_change_password": admin.must_change_password,
    }})


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
