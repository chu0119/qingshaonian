import json
import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import case, func
from ..database import get_db
from ..models.user import User, School, Grade, Class, TeacherClass
from ..models.task import Task, AnswerSheet, AnswerRecord
from ..models.risk import RiskAlert, Intervention, ScoringResult, QualityAssessment
from ..models.audit import LoginLog, OperationLog
from ..utils.validators import mask_id_card, mask_phone
from ..models.questionnaire import Questionnaire
from ..models.external import SMSLog, AIAnalysisLog
from ..dependencies import require_role
from ..services.questionnaire_import_service import (
    generate_import_template, import_questionnaire, export_questionnaire_to_excel, batch_export_to_zip,
)
from ..utils.response import APIResponse
from ..utils.password import hash_password
from ..utils.jwt import create_access_token
from ..config import settings
from ..services.audit_service import log_operation
from ..services.stats_service import platform_summary, recent_school_activity, school_metrics

router = APIRouter(prefix="/api/v1/platform", tags=["平台管理"])


def _validate_initial_password(password: str) -> None:
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="初始密码至少6位")
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

    # 自动创建默认年级（小学→初中→高中→中专）
    from ..database import create_default_grades
    create_default_grades(db, school.id)

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
def enter_school(school_id: int, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    """平台管理员以代入模式进入学校后台——JWT 保留平台身份并附加 school_context_id。"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")
    log_operation(db, user, request, module="platform_school", action="enter_school",
                  object_type="school", object_id=school_id, object_name=school.name,
                  detail="平台管理员进入学校后台")
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
    student_ids = [u.id for u in db.query(User.id).filter(User.school_id == school_id, User.role == "student").all()]
    teacher_ids = [u.id for u in db.query(User.id).filter(User.school_id == school_id, User.role.in_(["teacher", "counselor"])).all()]
    task_ids = [t.id for t in db.query(Task.id).filter(Task.school_id == school_id).all()]
    sheet_ids = [s.id for s in db.query(AnswerSheet.id).filter(AnswerSheet.task_id.in_(task_ids)).all()] if task_ids else []
    # 1. 删除答卷明细
    if sheet_ids:
        db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
        db.query(ScoringResult).filter(ScoringResult.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
        db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
        db.query(AnswerSheet).filter(AnswerSheet.id.in_(sheet_ids)).delete(synchronize_session=False)
    # 2. 删除风险和干预
    db.query(Intervention).filter(Intervention.school_id == school_id).delete()
    db.query(RiskAlert).filter(RiskAlert.school_id == school_id).delete()
    # 3. 删除任务（不删除问卷，问卷是平台级资源）
    db.query(Task).filter(Task.school_id == school_id).delete()
    # 4. 删除教师-班级关联
    if teacher_ids:
        db.query(TeacherClass).filter(TeacherClass.teacher_id.in_(teacher_ids)).delete(synchronize_session=False)
    db.query(TeacherClass).filter(TeacherClass.class_id.in_(
        db.query(Class.id).filter(Class.school_id == school_id)
    )).delete(synchronize_session=False)
    # 5. 删除用户、班级、年级
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
    grades = db.query(Grade).filter(Grade.school_id == school_id, Grade.status == True).order_by(Grade.sort_order).all()
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
        "phone": mask_phone(a.phone),
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

@router.get("/students")
def platform_students(
    page: int = Query(1), page_size: int = Query(20),
    school_id: int | None = Query(None), grade_id: int | None = Query(None),
    class_id: int | None = Query(None), keyword: str = Query(""),
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """平台管理员 -- 跨校学生列表"""
    q = db.query(User).filter(User.role == "student")
    if school_id:
        q = q.filter(User.school_id == school_id)
    if grade_id:
        q = q.filter(User.grade_id == grade_id)
    if class_id:
        q = q.filter(User.class_id == class_id)
    if keyword:
        q = q.filter(User.real_name.contains(keyword) | User.username.contains(keyword) | User.student_no.contains(keyword))
    total = q.count()
    items = q.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    school_ids = list(set(u.school_id for u in items if u.school_id))
    grade_ids = list(set(u.grade_id for u in items if u.grade_id))
    class_ids_list = list(set(u.class_id for u in items if u.class_id))
    school_names = dict(db.query(School.id, School.name).filter(School.id.in_(school_ids)).all()) if school_ids else {}
    grade_names = dict(db.query(Grade.id, Grade.name).filter(Grade.id.in_(grade_ids)).all()) if grade_ids else {}
    class_names = dict(db.query(Class.id, Class.name).filter(Class.id.in_(class_ids_list)).all()) if class_ids_list else {}


    return APIResponse.success({
        "items": [{
            "id": u.id, "student_name": u.real_name, "student_no": u.student_no or "",
            "id_card": mask_id_card(u.username),
            "school_id": u.school_id, "school_name": school_names.get(u.school_id, ""),
            "grade_id": u.grade_id, "grade_name": grade_names.get(u.grade_id, "") if u.grade_id else "",
            "class_id": u.class_id, "class_name": class_names.get(u.class_id, "") if u.class_id else "",
            "phone": (u.phone[:3] + "****" + u.phone[-4:]) if u.phone and len(u.phone) >= 7 else (u.phone or ""),
            "gender": u.gender or "",
            "status": u.status, "created_at": u.created_at.isoformat() if u.created_at else None,
        } for u in items],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/students/{student_id}")
def platform_student_detail(
    student_id: int,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """平台管理员 -- 学生详情"""
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    school = db.query(School).filter(School.id == student.school_id).first()
    grade = db.query(Grade).filter(Grade.id == student.grade_id).first() if student.grade_id else None

    klass = db.query(Class).filter(Class.id == student.class_id).first() if student.class_id else None
    return APIResponse.success({
        "id": student.id, "student_name": student.real_name, "student_no": student.student_no or "",
        "id_card": mask_id_card(student.username), "school_name": school.name if school else "",
        "grade_name": grade.name if grade else "", "class_name": klass.name if klass else "",
        "phone": (student.phone[:3] + "****" + student.phone[-4:]) if student.phone and len(student.phone) >= 7 else (student.phone or ""),
        "gender": student.gender or "",
        "status": student.status, "created_at": student.created_at.isoformat() if student.created_at else None,
    })


@router.post("/verify-password")
def platform_verify_password(data: dict, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    """验证平台管理员密码（用于查看敏感信息）"""
    password = (data.get("password") or "").strip()
    if not password:
        raise HTTPException(status_code=400, detail="请输入密码")
    from ..utils.password import verify_password as check_pw
    if not check_pw(password, user.password_hash):
        raise HTTPException(status_code=400, detail="密码错误")
    return APIResponse.success({"verified": True})


@router.post("/students/{student_id}/reveal-id-card")
def reveal_student_id_card(
    student_id: int, data: dict, request: Request,
    user: User = Depends(require_role("platform_admin")),
    db: Session = Depends(get_db),
):
    """验证密码后返回学生真实身份证号"""
    password = (data.get("password") or "").strip()
    if not password:
        raise HTTPException(status_code=400, detail="请输入密码")
    from ..utils.password import verify_password as check_pw
    if not check_pw(password, user.password_hash):
        raise HTTPException(status_code=400, detail="密码错误")
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    log_operation(db, user, request, module="platform_student", action="view_detail",
                  object_type="student", object_id=student_id, object_name=student.real_name,
                  detail="查看完整身份证号")
    return APIResponse.success({"id_card": student.username})


@router.get("/settings")
def get_platform_settings(user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    from ..models.system_config import SystemConfig
    config_keys = [
        "platform_system_name", "platform_support_contact", "platform_default_admin_password",
        "sms_enabled", "sms_provider", "sms_api_url", "sms_app_key", "sms_api_secret",
        "sms_template_code", "sms_sign_name",
        "ai_provider", "ai_api_key", "ai_base_url", "ai_model", "ai_system_prompt",
        "password_min_length", "password_expire_days", "login_lock_threshold", "login_lock_minutes", "session_timeout_minutes",
        "feature_ai_analysis", "feature_sms_notify", "feature_student_view_result", "feature_data_export", "feature_auto_risk_alert",
        "data_retention_months", "log_retention_months", "auto_cleanup_enabled",
        "template_risk_alert", "template_task_assign", "template_password_reset",
    ]
    configs = {c.config_key: c.config_value for c in db.query(SystemConfig).filter(
        SystemConfig.config_key.in_(config_keys),
        SystemConfig.school_id.is_(None)
    ).all()}
    return APIResponse.success({
        "system_name": configs.get("platform_system_name", "金盾护苗 · 青少年关爱帮扶信息管理平台"),
        "support_contact": configs.get("platform_support_contact", ""),
        "default_admin_password": "••••••" if configs.get("platform_default_admin_password") else "",
        "sms_enabled": configs.get("sms_enabled", "false"),
        "sms_provider": configs.get("sms_provider", ""),
        "sms_api_url": configs.get("sms_api_url", ""),
        "sms_api_key": "••••••" if configs.get("sms_app_key") else "",
        "sms_api_secret": "••••••" if configs.get("sms_api_secret") else "",
        "sms_template_code": configs.get("sms_template_code", ""),
        "sms_sign_name": configs.get("sms_sign_name", ""),
        "ai_provider": configs.get("ai_provider", "openai"),
        "ai_api_key": "••••••" if configs.get("ai_api_key") else "",
        "ai_base_url": configs.get("ai_base_url", ""),
        "ai_model": configs.get("ai_model", "gpt-4o-mini"),
        "ai_system_prompt": configs.get("ai_system_prompt", ""),
        "password_min_length": int(configs.get("password_min_length", "6")),
        "password_expire_days": int(configs.get("password_expire_days", "0")),
        "login_lock_threshold": int(configs.get("login_lock_threshold", "5")),
        "login_lock_minutes": int(configs.get("login_lock_minutes", "30")),
        "session_timeout_minutes": int(configs.get("session_timeout_minutes", "480")),
        "feature_ai_analysis": configs.get("feature_ai_analysis", "true") == "true",
        "feature_sms_notify": configs.get("feature_sms_notify", "false") == "true",
        "feature_student_view_result": configs.get("feature_student_view_result", "false") == "true",
        "feature_data_export": configs.get("feature_data_export", "true") == "true",
        "feature_auto_risk_alert": configs.get("feature_auto_risk_alert", "true") == "true",
        "data_retention_months": int(configs.get("data_retention_months", "36")),
        "log_retention_months": int(configs.get("log_retention_months", "12")),
        "auto_cleanup_enabled": configs.get("auto_cleanup_enabled", "false"),
        "template_risk_alert": configs.get("template_risk_alert", "尊敬的{school_name}，学生{student_name}的风险评估等级为{risk_level}，请及时关注。"),
        "template_task_assign": configs.get("template_task_assign", "尊敬的老师，{school_name}已下发新的测评任务，请及时组织学生完成。"),
        "template_password_reset": configs.get("template_password_reset", "您的账号密码已被管理员重置，请使用新密码登录并及时修改。"),
    })


@router.put("/settings")
def update_platform_settings(data: dict, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    from ..models.system_config import SystemConfig
    key_map = {
        "system_name": "platform_system_name",
        "support_contact": "platform_support_contact",
        "default_admin_password": "platform_default_admin_password",
        "sms_enabled": "sms_enabled",
        "sms_provider": "sms_provider",
        "sms_api_url": "sms_api_url",
        "sms_api_key": "sms_app_key",
        "sms_api_secret": "sms_api_secret",
        "sms_template_code": "sms_template_code",
        "sms_sign_name": "sms_sign_name",
        "ai_provider": "ai_provider",
        "ai_api_key": "ai_api_key",
        "ai_base_url": "ai_base_url",
        "ai_model": "ai_model",
        "ai_system_prompt": "ai_system_prompt",
        "password_min_length": "password_min_length",
        "password_expire_days": "password_expire_days",
        "login_lock_threshold": "login_lock_threshold",
        "login_lock_minutes": "login_lock_minutes",
        "session_timeout_minutes": "session_timeout_minutes",
        "feature_ai_analysis": "feature_ai_analysis",
        "feature_sms_notify": "feature_sms_notify",
        "feature_student_view_result": "feature_student_view_result",
        "feature_data_export": "feature_data_export",
        "feature_auto_risk_alert": "feature_auto_risk_alert",
        "data_retention_months": "data_retention_months",
        "log_retention_months": "log_retention_months",
        "auto_cleanup_enabled": "auto_cleanup_enabled",
        "template_risk_alert": "template_risk_alert",
        "template_task_assign": "template_task_assign",
        "template_password_reset": "template_password_reset",
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


# ============ 平台管理员管理 ============

@router.get("/admins")
def list_platform_admins(
    page: int = Query(1), page_size: int = Query(20),
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """列出所有平台管理员"""
    q = db.query(User).filter(User.role == "platform_admin").order_by(User.id)
    total = q.count()
    admins = q.offset((page - 1) * page_size).limit(page_size).all()
    return APIResponse.success({
        "total": total,
        "items": [{
            "id": a.id,
            "username": a.username,
            "real_name": a.real_name,
            "phone": (a.phone[:3] + "****" + a.phone[-4:]) if a.phone and len(a.phone) >= 7 else (a.phone or ""),
            "status": a.status,
            "last_login_at": a.last_login_at.isoformat() if a.last_login_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        } for a in admins],
    })


@router.post("/admins")
def create_platform_admin(
    data: dict, request: Request,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """创建平台管理员"""
    from ..utils.password import hash_password
    username = (data.get("username") or "").strip()
    real_name = (data.get("real_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    password = (data.get("password") or "").strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码长度不能少于6位")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    admin = User(
        username=username,
        real_name=real_name,
        phone=phone,
        role="platform_admin",
        password_hash=hash_password(password),
        status=True,
        must_change_password=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    log_operation(db, user=user, request=request, module="admin", action="create",
                  object_type="platform_admin", object_id=admin.id, object_name=admin.username, result="success")
    return APIResponse.success({"id": admin.id, "username": admin.username}, message="平台管理员创建成功")


@router.put("/admins/{admin_id}")
def update_platform_admin(
    admin_id: int, data: dict, request: Request,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """编辑平台管理员信息"""
    target = db.query(User).filter(User.id == admin_id, User.role == "platform_admin").first()
    if not target:
        raise HTTPException(status_code=404, detail="管理员不存在")
    allowed = {"real_name", "phone", "status"}
    for k, v in data.items():
        if k in allowed and hasattr(target, k):
            setattr(target, k, v)
    db.commit()
    log_operation(db, user=user, request=request, module="admin", action="update",
                  object_type="platform_admin", object_id=admin_id, object_name=target.username, result="success")
    return APIResponse.success(message="更新成功")


@router.put("/admins/{admin_id}/reset-password")
def reset_platform_admin_password(
    admin_id: int, data: dict, request: Request,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """重置平台管理员密码"""
    from ..utils.password import hash_password
    target = db.query(User).filter(User.id == admin_id, User.role == "platform_admin").first()
    if not target:
        raise HTTPException(status_code=404, detail="管理员不存在")
    new_password = (data.get("new_password") or "").strip()
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="密码长度不能少于6位")
    target.password_hash = hash_password(new_password)
    target.must_change_password = True
    db.commit()
    log_operation(db, user=user, request=request, module="admin", action="reset_password",
                  object_type="platform_admin", object_id=admin_id, object_name=target.username, result="success")
    return APIResponse.success(message="密码重置成功")


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
            "id_card": mask_id_card(students.get(a.student_id).username) if students.get(a.student_id) else "",
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
    """重点学生——警告/危急学生详情"""
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
            "id_card": mask_id_card(students.get(a.student_id).username) if students.get(a.student_id) else "",
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


@router.get("/tasks/{task_id}")
def platform_task_detail(task_id: int, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    qnr = task.questionnaire
    school = db.query(School).filter(School.id == task.school_id).first()
    snapshot = task.target_snapshot or {}
    student_ids = snapshot.get("student_ids", [])
    if isinstance(student_ids, list):
        student_ids = [int(s) for s in student_ids if str(s).isdigit()]
    total_students = len(student_ids)
    submitted = db.query(func.count(AnswerSheet.id)).filter(
        AnswerSheet.task_id == task_id, AnswerSheet.status == "submitted"
    ).scalar() or 0
    grades_q = db.query(Grade).filter(Grade.school_id == task.school_id, Grade.status == True).order_by(Grade.sort_order).all()
    grade_stats = []
    for g in grades_q:
        g_students = db.query(User.id).filter(User.grade_id == g.id, User.role == "student")
        g_ids = [s[0] for s in g_students.all()]
        target_in_grade = list(set(g_ids) & set(student_ids))
        if not target_in_grade:
            continue
        g_submitted = db.query(func.count(AnswerSheet.id)).filter(
            AnswerSheet.task_id == task_id, AnswerSheet.student_id.in_(target_in_grade), AnswerSheet.status == "submitted"
        ).scalar() or 0
        grade_stats.append({
            "grade_name": g.name, "total": len(target_in_grade), "submitted": g_submitted,
            "rate": round(g_submitted / max(len(target_in_grade), 1) * 100, 1),
        })
    # 学生完成明细
    students = db.query(User).filter(User.id.in_(student_ids), User.role == "student").all()
    sheets = {s.student_id: s for s in db.query(AnswerSheet).filter(AnswerSheet.task_id == task_id).all()}
    student_details = []
    for stu in students:
        sheet = sheets.get(stu.id)
        student_details.append({
            "student_id": stu.id, "student_name": stu.real_name,
            "status": sheet.status if sheet else "not_started",
            "submitted_at": sheet.submitted_at.isoformat() if sheet and sheet.submitted_at else None,
        })

    return APIResponse.success({
        "id": task.id, "name": task.name, "school_name": school.name if school else "",
        "questionnaire_title": qnr.title if qnr else "", "status": task.status,
        "target_type": task.target_type, "description": task.description or "",
        "start_time": task.start_time.isoformat() if task.start_time else None,
        "end_time": task.end_time.isoformat() if task.end_time else None,
        "published_at": task.published_at.isoformat() if task.published_at else None,
        "total_students": total_students, "submitted": submitted,
        "completion_rate": round(submitted / max(total_students, 1) * 100, 1) if total_students else 0,
        "grade_stats": grade_stats, "student_details": student_details,
    })

@router.post("/tasks/{task_id}/close")
def platform_close_task(task_id: int, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = "closed"
    task.closed_at = func.now()
    db.commit()
    log_operation(db, user, request, module="task_supervision", action="close", object_type="task", object_id=task.id, object_name=task.name)
    return APIResponse.success(message="任务已关闭")

@router.post("/tasks/{task_id}/extend")
def platform_extend_task(task_id: int, data: dict, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    from datetime import datetime
    end_time = data.get("end_time")
    if not end_time:
        raise HTTPException(status_code=400, detail="请设置新的截止时间")
    task.end_time = datetime.fromisoformat(str(end_time).replace("Z", "+00:00")).replace(tzinfo=None)
    task.extended_at = datetime.now()
    if task.status == "ended":
        task.status = "in_progress"
    db.commit()
    log_operation(db, user, request, module="task_supervision", action="extend", object_type="task", object_id=task.id, object_name=task.name)
    return APIResponse.success(message="任务已延期")

@router.put("/tasks/{task_id}")
def platform_edit_task(task_id: int, data: dict, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in ("draft", "not_started"):
        raise HTTPException(status_code=400, detail="只能编辑草稿或未开始的任务")
    if "name" in data:
        task.name = data["name"]
    if "description" in data:
        task.description = data["description"]
    if "start_time" in data:
        task.start_time = datetime.fromisoformat(str(data["start_time"]).replace("Z", "+00:00")).replace(tzinfo=None) if data["start_time"] else None
    if "end_time" in data:
        task.end_time = datetime.fromisoformat(str(data["end_time"]).replace("Z", "+00:00")).replace(tzinfo=None) if data["end_time"] else None
    db.commit()
    log_operation(db, user, request, module="task_supervision", action="edit", object_type="task", object_id=task.id, object_name=task.name)
    return APIResponse.success(message="任务更新成功")

@router.post("/tasks/{task_id}/archive")
def platform_archive_task(task_id: int, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = "archived"
    db.commit()
    log_operation(db, user, request, module="task_supervision", action="archive", object_type="task", object_id=task.id, object_name=task.name)
    return APIResponse.success(message="任务已归档")


@router.post("/tasks/{task_id}/recall")
def platform_recall_answer_sheet(task_id: int, data: dict, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    """平台管理员打回已提交的答卷，让学生重做"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    student_id = data.get("student_id")
    if not student_id:
        raise HTTPException(status_code=400, detail="请指定学生ID")
    sheet = db.query(AnswerSheet).filter(AnswerSheet.task_id == task_id, AnswerSheet.student_id == student_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="该学生无此任务的答卷")
    if sheet.status != "submitted":
        raise HTTPException(status_code=400, detail="只能打回已提交的答卷")
    db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == sheet.id).delete()
    db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id == sheet.id).delete()
    alert_ids = [a.id for a in db.query(RiskAlert.id).filter(RiskAlert.answer_sheet_id == sheet.id).all()]
    if alert_ids:
        db.query(Intervention).filter(Intervention.risk_alert_id.in_(alert_ids)).delete(synchronize_session=False)
    db.query(RiskAlert).filter(RiskAlert.answer_sheet_id == sheet.id).delete()
    sheet.status = "in_progress"
    sheet.submitted_at = None
    db.commit()
    student = db.query(User).filter(User.id == student_id).first()
    log_operation(db, user, request, module="task_supervision", action="recall", object_type="answer_sheet",
                  object_id=sheet.id, object_name=f"{student.real_name if student else student_id}的答卷")
    return APIResponse.success(message="答卷已打回，学生可重新作答")
def platform_school_classes(school_id: int, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    """获取指定学校的班级列表（用于发布任务）"""
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")
    classes = db.query(Class).filter(Class.school_id == school_id).order_by(Class.grade_id, Class.name).all()
    items = []
    for c in classes:
        grade = db.query(Grade).filter(Grade.id == c.grade_id).first()
        items.append({"id": c.id, "name": c.name, "grade_name": grade.name if grade else ""})
    return APIResponse.success(items)


@router.post("/tasks")
def platform_create_task(data: dict, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    """平台管理员发布测评任务（需指定学校）"""
    school_id = data.get("school_id")
    if not school_id:
        raise HTTPException(status_code=400, detail="请选择学校")
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="学校不存在")

    questionnaire_id = data.get("questionnaire_id")
    if not questionnaire_id:
        raise HTTPException(status_code=400, detail="问卷ID不能为空")
    qnr = db.query(Questionnaire).filter(Questionnaire.id == questionnaire_id).first()
    if not qnr:
        raise HTTPException(status_code=404, detail="问卷不存在")

    target_type = data.get("target_type", "class")
    target_ids = [int(x) for x in (data.get("target_ids") or []) if str(x).isdigit()]
    # Validate classes belong to the school
    if target_type == "class" and target_ids:
        valid_ids = {c.id for c in db.query(Class).filter(Class.school_id == school_id, Class.id.in_(target_ids)).all()}
        invalid = set(target_ids) - valid_ids
        if invalid:
            raise HTTPException(status_code=400, detail=f"班级不属于该校: {invalid}")

    def parse_dt(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)

    status_value = data.get("status") or "in_progress"
    if status_value == "active":
        status_value = "in_progress"
    if status_value not in ("draft", "not_started", "in_progress"):
        status_value = "in_progress"
    published_at = datetime.now() if status_value != "draft" else None

    task = Task(
        school_id=school_id, questionnaire_id=questionnaire_id,
        name=data.get("name", ""), target_type=target_type,
        target_ids=target_ids, start_time=parse_dt(data.get("start_time")),
        end_time=parse_dt(data.get("end_time")), shuffle_questions=data.get("shuffle_questions", False),
        shuffle_options=data.get("shuffle_options", False),
        allow_edit=data.get("allow_edit", False),
        description=data.get("description", ""),
        reminder_strategy=data.get("reminder_strategy") or {},
        enable_quality_check=data.get("enable_quality_check", True),
        status=status_value, published_at=published_at, created_by=user.id,
    )
    task.target_snapshot = {"student_ids": target_student_ids(db, task), "target_type": target_type, "target_ids": target_ids}
    db.add(task)
    db.commit()
    db.refresh(task)
    log_operation(db, user, request, module="task_supervision", action="create", object_type="task", object_id=task.id, object_name=task.name)
    return APIResponse.success({"id": task.id}, message="任务发布成功")

@router.delete("/tasks/{task_id}")
def platform_delete_task(task_id: int, request: Request, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in ("draft", "archived"):
        raise HTTPException(status_code=400, detail="只能删除草稿或已归档的任务")
    task_name = task.name
    # 级联删除关联记录（数据库无 cascade，需手动删除）
    sheet_ids = [s.id for s in db.query(AnswerSheet.id).filter(AnswerSheet.task_id == task_id).all()]
    if sheet_ids:
        db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
        db.query(ScoringResult).filter(ScoringResult.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
        db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
        alert_ids = [a.id for a in db.query(RiskAlert.id).filter(RiskAlert.task_id == task_id).all()]
        if alert_ids:
            db.query(Intervention).filter(Intervention.risk_alert_id.in_(alert_ids)).delete(synchronize_session=False)
        db.query(RiskAlert).filter(RiskAlert.task_id == task_id).delete(synchronize_session=False)
        db.query(AnswerSheet).filter(AnswerSheet.task_id == task_id).delete(synchronize_session=False)
    db.delete(task)
    db.commit()
    log_operation(db, user, request, module="task_supervision", action="delete", object_type="task", object_id=task_id, object_name=task_name)
    return APIResponse.success(message="任务已删除")

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
    students = {u.id: u for u in db.query(User).filter(User.id.in_([iv.student_id for iv in items])).all()} if items else {}
    teacher_names = dict(db.query(User.id, User.real_name).filter(User.id.in_([iv.teacher_id for iv in items if iv.teacher_id])).all()) if items else {}
    school_names = dict(db.query(School.id, School.name).filter(School.id.in_([iv.school_id for iv in items])).all()) if items else {}
    grade_names = dict(db.query(Grade.id, Grade.name).filter(Grade.id.in_([u.grade_id for u in students.values() if u.grade_id])).all()) if students else {}
    class_names = dict(db.query(Class.id, Class.name).filter(Class.id.in_([u.class_id for u in students.values() if u.class_id])).all()) if students else {}
    return APIResponse.success({
        "items": [{
            "id": iv.id, "student_id": iv.student_id, "school_id": iv.school_id,
            "student_name": students.get(iv.student_id).real_name if students.get(iv.student_id) else "",
            "id_card": mask_id_card(students.get(iv.student_id).username) if students.get(iv.student_id) else "",
            "school_name": school_names.get(iv.school_id, ""),
            "teacher_name": teacher_names.get(iv.teacher_id, ""),
            "student_grade": grade_names.get(students[iv.student_id].grade_id, "") if iv.student_id in students else "",
            "student_class": class_names.get(students[iv.student_id].class_id, "") if iv.student_id in students else "",
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
    MODULE_LABELS = {
        "platform_school": "学校管理", "auth": "认证管理", "student": "学生管理",
        "teacher": "教师管理", "ai_analysis": "AI研判", "sms": "短信管理",
        "platform_supervision": "监管督办", "system": "系统设置", "intervention": "干预管理",
        "report": "报告管理", "questionnaire": "问卷管理", "task": "任务管理", "risk": "风险预警",
        "platform_student": "学生管理", "platform_risk": "风险预警", "platform_sms": "短信管理",
        "platform_ai": "AI研判", "school_admin_account": "学校管理员",
    }
    ACTION_LABELS = {
        "create": "创建", "update": "更新", "delete": "删除", "disable": "停用",
        "enable": "启用", "export": "导出", "import": "导入", "send": "发送",
        "view_detail": "查看详情", "view_profile": "查看档案", "enter_school": "进入学校",
        "force_delete": "彻底删除", "reset_password": "重置密码", "change_password": "修改密码",
        "assign_classes": "分配班级", "urge_intervention": "督促处理", "remind": "发送提醒",
        "send_code": "发送验证码", "regional_analysis": "区域分析", "seed_demo_data": "初始化演示数据",
        "update_school_info": "更新学校信息", "update_risk_config": "更新风险配置",
        "update_sms_config": "更新短信配置", "update_screen_config": "更新大屏配置",
        "create_grade": "创建年级", "delete_grade": "删除年级",
    }
    OBJECT_TYPE_LABELS = {
        "school": "学校", "user": "用户", "student_list": "学生列表", "student_batch": "学生批次",
        "config": "配置", "risk_alert": "风险预警", "intervention": "干预记录",
        "sms_log": "短信记录", "report": "报告", "phone": "手机号", "grade": "年级",
        "sms": "短信", "task": "任务", "student": "学生",
    }
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
            "module_label": MODULE_LABELS.get(log.module, log.module),
            "action_label": ACTION_LABELS.get(log.action, log.action),
            "object_type": log.object_type, "object_type_label": OBJECT_TYPE_LABELS.get(log.object_type, log.object_type),
            "operator_name": log.operator_name, "operator_role": log.operator_role,
            "object_id": log.object_id,
            "object_name": log.object_name, "result": log.result,
            "detail": log.detail or "", "ip": log.request_ip or "",
            "created_at": log.operation_time.isoformat() if log.operation_time else None,
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
            "id": s.id, "recipient_name": s.recipient_name, "phone": mask_phone(s.phone),
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
    students = {u.id: u for u in db.query(User).filter(User.id.in_([iv.student_id for iv in items])).all()} if items else {}
    teacher_names = dict(db.query(User.id, User.real_name).filter(User.id.in_([iv.teacher_id for iv in items if iv.teacher_id])).all()) if items else {}
    school_names = dict(db.query(School.id, School.name).filter(School.id.in_([iv.school_id for iv in items])).all()) if items else {}
    grade_names = dict(db.query(Grade.id, Grade.name).filter(Grade.id.in_([u.grade_id for u in students.values() if u.grade_id])).all()) if students else {}
    class_names = dict(db.query(Class.id, Class.name).filter(Class.id.in_([u.class_id for u in students.values() if u.class_id])).all()) if students else {}
    return APIResponse.success({"items": [{
        "id": iv.id, "student_id": iv.student_id, "school_id": iv.school_id,
        "student_name": students.get(iv.student_id).real_name if students.get(iv.student_id) else "",
        "id_card": mask_id_card(students.get(iv.student_id).username) if students.get(iv.student_id) else "",
        "school_name": school_names.get(iv.school_id, ""),
        "teacher_name": teacher_names.get(iv.teacher_id, ""),
        "student_grade": grade_names.get(students[iv.student_id].grade_id, "") if iv.student_id in students else "",
        "student_class": class_names.get(students[iv.student_id].class_id, "") if iv.student_id in students else "",
        "method": iv.method, "status": iv.status, "content": (iv.content or "")[:200],
        "need_follow_up": iv.need_follow_up,
        "intervention_time": iv.intervention_time.isoformat() if iv.intervention_time else None,
        "created_at": iv.created_at.isoformat() if iv.created_at else None,
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
    school_total = summary.get("school_total", 0)
    student_total = summary.get("student_total", 0)
    risk_total = summary.get("risk_alert_total", 0)
    pending_total = summary.get("pending_risk_total", 0)
    completion_rankings = summary.get("completion_rankings", [])
    risk_rankings = summary.get("risk_rankings", [])
    risk_level_dist = summary.get("risk_level_distribution", {})

    # School risk density: risks per 100 students
    school_risk_density = []
    for s in risk_rankings[:10]:
        density = round(s.get("risk_count", 0) / max(s.get("student_count", 1), 1) * 100, 1)
        school_risk_density.append({"name": s["name"], "risk_count": s.get("risk_count", 0), "student_count": s.get("student_count", 0), "density": density})

    # Intervention efficiency per school
    school_interventions = []
    all_schools = db.query(School).filter(School.status == True).all()
    for sch in all_schools:
        total_alerts = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == sch.id).scalar() or 0
        resolved = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == sch.id, RiskAlert.status.in_(["resolved", "closed", "completed"])).scalar() or 0
        pending = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == sch.id, RiskAlert.status == "pending").scalar() or 0
        if total_alerts > 0:
            school_interventions.append({"name": sch.name, "total_alerts": total_alerts, "resolved": resolved, "pending": pending, "resolution_rate": round(resolved / total_alerts * 100, 1)})

    # Anomaly detection: schools with high pending ratios
    anomaly_schools = []
    for si in school_interventions:
        if si["pending"] > 0 and si["resolution_rate"] < 30:
            anomaly_schools.append({"name": si["name"], "pending": si["pending"], "resolution_rate": si["resolution_rate"], "alert": "干预处置率过低，需重点关注"})

    # Low completion rate tasks
    low_completion_tasks = []
    recent_tasks = db.query(Task).filter(Task.status.in_(["in_progress", "active", "not_started"])).order_by(Task.id.desc()).limit(20).all()
    for t in recent_tasks:
        snapshot = t.target_snapshot or {}
        student_ids = snapshot.get("student_ids", [])
        if isinstance(student_ids, list):
            total_s = len(student_ids)
        else:
            total_s = 0
        submitted = db.query(func.count(AnswerSheet.id)).filter(AnswerSheet.task_id == t.id, AnswerSheet.status == "submitted").scalar() or 0
        rate = round(submitted / max(total_s, 1) * 100, 1)
        if total_s > 0 and rate < 30:
            school = db.query(School).filter(School.id == t.school_id).first()
            low_completion_tasks.append({"task_name": t.name, "school_name": school.name if school else "", "rate": rate, "total": total_s, "submitted": submitted})

    # Risk level distribution by school
    school_risk_levels = []
    for sch in all_schools[:15]:
        dist = {}
        for level in ["low", "medium", "high", "urgent"]:
            c = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == sch.id, RiskAlert.risk_level == level).scalar() or 0
            if c > 0:
                dist[level] = c
        if dist:
            school_risk_levels.append({"name": sch.name, **dist})

    # High risk student dimension patterns
    high_risk_scores = db.query(ScoringResult).join(RiskAlert, RiskAlert.answer_sheet_id == ScoringResult.answer_sheet_id).filter(
        RiskAlert.risk_level.in_(["high", "urgent"])
    ).limit(200).all()
    dimension_totals: dict[str, list[float]] = {}
    for sr in high_risk_scores:
        if sr.dimension_scores and isinstance(sr.dimension_scores, dict):
            for k, v in sr.dimension_scores.items():
                dimension_totals.setdefault(k, []).append(float(v))
    dimension_patterns = [{"dimension": k, "avg_score": round(sum(v) / len(v), 1), "count": len(v)} for k, v in dimension_totals.items() if v]
    dimension_patterns.sort(key=lambda x: x["avg_score"])
    # 维度名称翻译
    dimension_labels = {
        "emotion": "情绪状态", "sleep": "睡眠状态", "academic_pressure": "学业压力",
        "interpersonal": "人际关系", "family_support": "家庭支持", "campus_safety": "校园安全",
        "internet_use": "网络使用", "self_safety": "自我安全", "general": "综合",
    }
    for dp in dimension_patterns:
        dp["dimension"] = dimension_labels.get(dp["dimension"], dp["dimension"])

    # Monthly risk trend (last 6 months)
    from datetime import datetime, timedelta
    monthly_risks = []
    for i in range(5, -1, -1):
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30 * i)
        month_end = month_start + timedelta(days=30)
        count = db.query(func.count(RiskAlert.id)).filter(RiskAlert.created_at >= month_start, RiskAlert.created_at < month_end).scalar() or 0
        monthly_risks.append({"month": month_start.strftime("%Y-%m"), "count": count})

    # Overall assessment summary text
    avg_completion = round(sum(s.get("completion_rate", 0) for s in completion_rankings) / max(len(completion_rankings), 1), 1) if completion_rankings else 0
    high_risk_pct = round((risk_level_dist.get("high", 0) + risk_level_dist.get("urgent", 0)) / max(risk_total, 1) * 100, 1)
    assessment = {
        "risk_level": "高" if high_risk_pct > 20 else "中" if high_risk_pct > 10 else "低",
        "summary": f"区域接入{school_total}所学校，覆盖{student_total}名学生。累计风险预警{risk_total}条，待处理{pending_total}条。"
                   f"高危+紧急占比{high_risk_pct}%，区域平均测评完成率{avg_completion}%。",
        "recommendations": [],
    }
    if pending_total > 50:
        assessment["recommendations"].append(f"当前有{pending_total}条待处理风险预警，建议督促相关学校加快干预处置进度。")
    if anomaly_schools:
        assessment["recommendations"].append(f"{len(anomaly_schools)}所学校干预处置率低于30%，需重点关注并约谈学校负责人。")
    if low_completion_tasks:
        assessment["recommendations"].append(f"{len(low_completion_tasks)}项测评任务完成率不足30%，建议了解原因并适当延期。")
    if dimension_patterns and dimension_patterns[0]["avg_score"] < 40:
        assessment["recommendations"].append(f"警告学生群体在「{dimension_patterns[0]['dimension']}」维度平均得分仅{dimension_patterns[0]['avg_score']}，建议开展针对性辅导。")

    if request:
        log_operation(db, user, request, module="platform_ai", action="regional_analysis", object_type="report", object_id=0, object_name="区域综合分析")

    return APIResponse.success({
        "overview": {"school_total": school_total, "student_total": student_total, "risk_total": risk_total, "pending_total": pending_total},
        "assessment": assessment,
        "school_risk_density": school_risk_density[:8],
        "school_interventions": sorted(school_interventions, key=lambda x: x["resolution_rate"])[:8],
        "anomaly_schools": anomaly_schools,
        "low_completion_tasks": low_completion_tasks[:5],
        "school_risk_levels": school_risk_levels,
        "dimension_patterns": dimension_patterns[:8],
        "monthly_risks": monthly_risks,
        "risk_level_dist": risk_level_dist,
    })


# ============ 答题详情 ============

@router.get("/answer-sheets/{sheet_id}/detail")
def platform_answer_detail(
    sheet_id: int, request: Request,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    from ..services.questionnaire_service import get_answer_detail
    try:
        detail = get_answer_detail(db, sheet_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    log_operation(db, user, request, module="platform_risk", action="view_detail",
                  object_type="answer_sheet", object_id=sheet_id,
                  object_name=detail.get("student_name", ""), detail="查看答题详情")
    return APIResponse.success(detail)


@router.get("/students/{student_id}/answer-sheets")
def platform_student_answer_sheets(
    student_id: int,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    from ..services.questionnaire_service import list_student_answer_sheets
    sheets = list_student_answer_sheets(db, student_id)
    return APIResponse.success(sheets)


@router.get("/risks/{alert_id}/answers")
def platform_risk_answer_detail(
    alert_id: int, request: Request,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    alert = db.query(RiskAlert).filter(RiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="风险预警不存在")
    if not alert.answer_sheet_id:
        raise HTTPException(status_code=404, detail="该预警无关联答卷")
    from ..services.questionnaire_service import get_answer_detail
    try:
        detail = get_answer_detail(db, alert.answer_sheet_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    log_operation(db, user, request, module="platform_risk", action="view_detail",
                  object_type="answer_sheet", object_id=alert.answer_sheet_id,
                  object_name=detail.get("student_name", ""), detail=f"通过风险预警{alert_id}查看答题详情")
    return APIResponse.success(detail)


# ============ 审计日志增强 ============

@router.get("/audit/login-logs")
def platform_login_logs(page: int = Query(1), page_size: int = Query(20), school_id: int | None = Query(None),
    keyword: str = Query(""), result: str = Query(""), user_role: str = Query(""),
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    q = db.query(LoginLog).order_by(LoginLog.id.desc())
    if school_id: q = q.filter(LoginLog.school_id == school_id)
    if keyword: q = q.filter(LoginLog.username.contains(keyword))
    if result: q = q.filter(LoginLog.result == result)
    if user_role: q = q.filter(LoginLog.user_role == user_role)
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


# ============ 问卷管理 ============

@router.get("/questionnaires")
def platform_questionnaires(
    page: int = Query(1), page_size: int = Query(20),
    category: str = Query(""), status: str = Query(""), keyword: str = Query(""),
    source_type: str = Query(""),
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    from ..services.questionnaire_service import list_questionnaires
    result = list_questionnaires(db, school_id=None, page=page, page_size=page_size,
                                 category=category, status=status, keyword=keyword, include_builtin=True)
    items = result["items"]
    if source_type:
        items = [i for i in items if i.get("source_type") == source_type]
        result["items"] = items
        result["total"] = len(items)
    for item in items:
        task_count = db.query(func.count(Task.id)).filter(Task.questionnaire_id == item["id"]).scalar() or 0
        answer_count = db.query(func.count(AnswerSheet.id)).join(Task).filter(Task.questionnaire_id == item["id"]).scalar() or 0
        item["task_count"] = task_count
        item["answer_count"] = answer_count
    return APIResponse.success(result)


# ---------------------------------------------------------------------------
# 平台问卷导入导出（必须在 {qid} 路由之前定义，避免路径冲突）
# ---------------------------------------------------------------------------

@router.get("/questionnaires/import-template")
def platform_download_import_template(user: User = Depends(require_role("platform_admin"))):
    """下载问卷导入 Excel 模板"""
    data = generate_import_template()
    import io
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=questionnaire_template.xlsx"},
    )


@router.post("/questionnaires/import")
def platform_import_questionnaire(
    file: UploadFile = File(...),
    user: User = Depends(require_role("platform_admin")),
    db: Session = Depends(get_db),
):
    """平台级导入问卷（school_id=None）"""
    if not file.filename or not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 格式的 Excel 文件")

    file_bytes = file.file.read()
    result = import_questionnaire(db, file_bytes, school_id=None, created_by=user.id)

    if not result.get("success"):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={
            "code": 400,
            "message": f"导入失败，共发现 {result.get('total_errors', 0)} 个错误",
            "data": {"errors": result.get("errors", []), "total_errors": result.get("total_errors", 0)},
        })

    log_operation(db, user, None, module="questionnaire", action="import",
                  object_type="questionnaire", object_id=str(result["questionnaire_id"]),
                  detail=f"平台导入问卷: {result['title']}")
    return APIResponse.success(data=result, message=result.get("message", "导入成功"))


@router.get("/questionnaires/{qid}/export")
def platform_export_questionnaire(
    qid: int,
    user: User = Depends(require_role("platform_admin")),
    db: Session = Depends(get_db),
):
    """导出单个问卷为 Excel"""
    q = db.query(Questionnaire).filter(Questionnaire.id == qid).first()
    if not q:
        raise HTTPException(status_code=404, detail="问卷不存在")
    try:
        data = export_questionnaire_to_excel(db, q.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    import io, re, urllib.parse
    safe_name = re.sub(r'[\\/*?:"<>|]', "", q.title or "questionnaire").replace(" ", "_")[:80]
    encoded_name = urllib.parse.quote(f"{safe_name}.xlsx")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )
async def platform_batch_export(
    request: Request,
    user: User = Depends(require_role("platform_admin")),
    db: Session = Depends(get_db),
):
    """批量导出多个问卷为 ZIP"""
    body_bytes = await request.body()
    body = json.loads(body_bytes.decode())
    ids = body.get("questionnaire_ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要导出的问卷")

    import io
    zip_data = batch_export_to_zip(db, ids)
    return StreamingResponse(
        io.BytesIO(zip_data),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=questionnaires_export.zip"},
    )


@router.get("/questionnaires/{qid}")
def platform_questionnaire_detail(qid: int, user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    from ..services.questionnaire_service import get_questionnaire_detail
    try:
        return APIResponse.success(get_questionnaire_detail(db, qid))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/questionnaires")
def platform_create_questionnaire(
    data: dict, request: Request,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    from ..services.questionnaire_service import create_questionnaire
    from ..schemas.questionnaire import QuestionnaireCreate
    qn_data = QuestionnaireCreate(**data)
    q = create_questionnaire(db, qn_data, user_id=user.id, school_id=None)
    log_operation(db, user, request, module="questionnaire", action="create",
                  object_type="questionnaire", object_id=q.id, object_name=q.title, result="success")
    return APIResponse.success({"id": q.id, "title": q.title}, message="问卷创建成功")


@router.put("/questionnaires/{qid}")
def platform_update_questionnaire(
    qid: int, data: dict, request: Request,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    q = db.query(Questionnaire).filter(Questionnaire.id == qid).first()
    if not q:
        raise HTTPException(status_code=404, detail="问卷不存在")
    if q.is_builtin:
        raise HTTPException(status_code=400, detail="内置问卷不可编辑")
    from ..services.questionnaire_service import update_questionnaire
    from ..schemas.questionnaire import QuestionnaireUpdate
    update_data = QuestionnaireUpdate(**data)
    updated = update_questionnaire(db, qid, update_data)
    log_operation(db, user, request, module="questionnaire", action="update",
                  object_type="questionnaire", object_id=qid, object_name=updated.title, result="success")
    return APIResponse.success(message="问卷更新成功")


@router.delete("/questionnaires/{qid}")
def platform_delete_questionnaire(
    qid: int, request: Request,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    q = db.query(Questionnaire).filter(Questionnaire.id == qid).first()
    if not q:
        raise HTTPException(status_code=404, detail="问卷不存在")
    if q.is_builtin:
        raise HTTPException(status_code=400, detail="内置问卷不可删除")
    from ..services.questionnaire_service import delete_questionnaire
    try:
        delete_questionnaire(db, qid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    log_operation(db, user, request, module="questionnaire", action="delete",
                  object_type="questionnaire", object_id=qid, object_name=q.title, result="success")
    return APIResponse.success(message="问卷删除成功")


@router.post("/questionnaires/{qid}/push")
def platform_push_questionnaire(
    qid: int, data: dict, request: Request,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    """推送问卷到指定学校（创建学校级副本）"""
    q = db.query(Questionnaire).filter(Questionnaire.id == qid).first()
    if not q:
        raise HTTPException(status_code=404, detail="问卷不存在")
    school_ids = data.get("school_ids", [])
    push_all = data.get("push_all", False)
    if push_all:
        school_ids = [s.id for s in db.query(School).filter(School.status == True).all()]
    if not school_ids:
        raise HTTPException(status_code=400, detail="请选择目标学校")
    from ..services.questionnaire_service import copy_questionnaire
    pushed = []
    for sid in school_ids:
        school = db.query(School).filter(School.id == sid).first()
        if not school:
            continue
        existing = db.query(Questionnaire).filter(
            Questionnaire.source_questionnaire_id == qid,
            Questionnaire.school_id == sid,
        ).first()
        if existing:
            continue
        new_q = copy_questionnaire(db, qid, user_id=user.id, school_id=sid)
        new_q.title = q.title
        new_q.source_questionnaire_id = qid
        db.commit()
        pushed.append({"school_id": sid, "school_name": school.name, "questionnaire_id": new_q.id})
    log_operation(db, user, request, module="questionnaire", action="push",
                  object_type="questionnaire", object_id=qid, object_name=q.title,
                  detail=f"推送到{len(pushed)}所学校")
    return APIResponse.success({"pushed": pushed, "count": len(pushed)}, message=f"已推送到{len(pushed)}所学校")


@router.post("/questionnaires/{qid}/copy")
def platform_copy_questionnaire(
    qid: int, request: Request,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    from ..services.questionnaire_service import copy_questionnaire
    try:
        new_q = copy_questionnaire(db, qid, user_id=user.id, school_id=None)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    log_operation(db, user, request, module="questionnaire", action="create",
                  object_type="questionnaire", object_id=new_q.id, object_name=new_q.title,
                  detail=f"复制自问卷{qid}")
    return APIResponse.success({"id": new_q.id, "title": new_q.title}, message="问卷复制成功")


@router.get("/questionnaires/{qid}/usage")
def platform_questionnaire_usage(
    qid: int,
    user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db),
):
    q = db.query(Questionnaire).filter(Questionnaire.id == qid).first()
    if not q:
        raise HTTPException(status_code=404, detail="问卷不存在")
    task_count = db.query(func.count(Task.id)).filter(Task.questionnaire_id == qid).scalar() or 0
    answer_count = db.query(func.count(AnswerSheet.id)).join(Task).filter(Task.questionnaire_id == qid).scalar() or 0
    submitted = db.query(func.count(AnswerSheet.id)).join(Task).filter(
        Task.questionnaire_id == qid, AnswerSheet.status == "submitted").scalar() or 0
    school_ids = [t.school_id for t in db.query(Task.school_id).filter(Task.questionnaire_id == qid).distinct().all()]
    school_names = dict(db.query(School.id, School.name).filter(School.id.in_(school_ids)).all()) if school_ids else {}
    copies = db.query(Questionnaire).filter(Questionnaire.source_questionnaire_id == qid).count()
    return APIResponse.success({
        "task_count": task_count, "answer_count": answer_count, "submitted": submitted,
        "schools": [{"id": sid, "name": school_names.get(sid, "")} for sid in school_ids],
        "copies": copies,
    })




@router.get("/system-info")
def platform_system_info(user: User = Depends(require_role("platform_admin")), db: Session = Depends(get_db)):
    school_count = db.query(func.count(School.id)).scalar() or 0
    student_count = db.query(func.count(User.id)).filter(User.role == "student").scalar() or 0
    teacher_count = db.query(func.count(User.id)).filter(User.role.in_(["teacher", "counselor"])).scalar() or 0
    task_count = db.query(func.count(Task.id)).scalar() or 0
    risk_count = db.query(func.count(RiskAlert.id)).scalar() or 0
    from ..config import settings as app_settings
    db_url = str(app_settings.DATABASE_URL) if hasattr(app_settings, 'DATABASE_URL') else ''
    db_type = 'MySQL' if 'mysql' in db_url.lower() else 'SQLite'
    return APIResponse.success({
        "version": "v2.1.0",
        "tech_stack": "Python FastAPI + React 18 + Ant Design 5 + ECharts",
        "db_type": db_type,
        "school_count": school_count,
        "student_count": student_count,
        "teacher_count": teacher_count,
        "task_count": task_count,
        "risk_count": risk_count,
    })

