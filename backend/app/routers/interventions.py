from fastapi import APIRouter, Depends, Query, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.risk import Intervention, RiskAlert
from ..dependencies import require_role
from ..services.audit_service import log_operation
from ..services.notification_service import create_notification
from ..utils.access_control import can_access_student
from ..utils.response import APIResponse
import os, uuid

router = APIRouter(prefix="/api/v1/interventions", tags=["干预记录"])

METHOD_LABELS = {"student_talk": "学生谈话", "teacher_communication": "班主任沟通", "counselor_guidance": "心理老师辅导", "family_school": "家校沟通", "home_visit": "家访", "referral": "转介专业机构", "observation": "持续观察", "other": "其他"}
INTER_STATUS_LABELS = {"pending": "待处理", "processing": "处理中", "follow_up": "持续跟进", "completed": "已完成", "closed": "已关闭"}


@router.get("")
def list_interventions(page: int = Query(1), page_size: int = Query(20), status: str = Query(""),
                       student_id: int | None = Query(None),
                       user: User = Depends(require_role("school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    q = db.query(Intervention).filter(Intervention.school_id == (getattr(user, '_effective_school_id', None) or user.school_id))
    if user.role in ("teacher", "counselor"):
        q = q.filter(Intervention.teacher_id == user.id)
    if student_id:
        q = q.filter(Intervention.student_id == student_id)
    if status:
        q = q.filter(Intervention.status == status)
    total = q.count()
    interventions = q.order_by(Intervention.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for inv in interventions:
        student = db.query(User).filter(User.id == inv.student_id).first()
        teacher = db.query(User).filter(User.id == inv.teacher_id).first()
        items.append({
            "id": inv.id, "student_id": inv.student_id, "student_name": student.real_name if student else "",
            "teacher_name": teacher.real_name if teacher else "", "method": inv.method,
            "method_label": METHOD_LABELS.get(inv.method, inv.method or "其他"),
            "content": inv.content, "result": inv.result,
            "intervention_time": inv.intervention_time.isoformat() if inv.intervention_time else None,
            "status": inv.status, "status_label": INTER_STATUS_LABELS.get(inv.status, inv.status),
            "need_follow_up": inv.need_follow_up,
            "next_follow_up_time": inv.next_follow_up_time.isoformat() if inv.next_follow_up_time else None,
        })
    return APIResponse.success({"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": max((total + page_size - 1) // page_size, 1)})


@router.post("")
def create_intervention(data: dict, request: Request, user: User = Depends(require_role("school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    from datetime import datetime
    student_id = data.get("student_id")
    if not student_id:
        raise HTTPException(status_code=400, detail="学生ID不能为空")
    student = db.query(User).filter(User.id == student_id).first()
    if not can_access_student(db, user, student):
        raise HTTPException(status_code=403, detail="无权限访问该学生")
    risk_alert_id = data.get("risk_alert_id")
    if risk_alert_id:
        alert = db.query(RiskAlert).filter(RiskAlert.id == risk_alert_id, RiskAlert.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
        if not alert or alert.student_id != student_id:
            raise HTTPException(status_code=403, detail="预警不属于该学生")

    def parse_dt(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)

    inv = Intervention(
        school_id=(getattr(user, '_effective_school_id', None) or user.school_id), student_id=student_id,
        risk_alert_id=risk_alert_id, teacher_id=user.id,
        intervention_time=parse_dt(data.get("intervention_time")) or datetime.now(),
        method=data.get("method", "other"), content=data.get("content", ""),
        result=data.get("result", ""), follow_up_suggestion=data.get("follow_up_suggestion", ""),
        need_follow_up=data.get("need_follow_up", False),
        next_follow_up_time=parse_dt(data.get("next_follow_up_time")),
        status=data.get("status", "processing"),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    log_operation(db, user, request, module="intervention", action="create", object_type="intervention", object_id=inv.id, object_name=student.real_name)

    method_cn = METHOD_LABELS.get(inv.method, inv.method or "其他")
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    school_admins = db.query(User).filter(User.school_id == school_id, User.role == "school_admin", User.status == True).all()
    notify_content = f"教师「{user.real_name}」已对学生「{student.real_name}」创建干预记录（{method_cn}）。"
    for admin in school_admins:
        create_notification(db, user_id=admin.id, type="intervention", title="新干预记录",
                            content=notify_content, sender_id=user.id, related_type="intervention", related_id=inv.id)
    if inv.need_follow_up and inv.next_follow_up_time:
        create_notification(db, user_id=user.id, type="intervention", title="干预跟进提醒",
                            content=f"学生「{student.real_name}」的干预记录将在 {inv.next_follow_up_time.strftime('%Y-%m-%d')} 需要跟进。",
                            related_type="intervention", related_id=inv.id)
    db.commit()

    return APIResponse.success({"id": inv.id}, message="干预记录创建成功")


@router.put("/{intervention_id}")
def update_intervention(intervention_id: int, data: dict, request: Request, user: User = Depends(require_role("school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    inv = db.query(Intervention).filter(Intervention.id == intervention_id, Intervention.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
    if not inv:
        raise HTTPException(status_code=404, detail="干预记录不存在")
    if user.role in ("teacher", "counselor") and inv.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权限修改该记录")
    for dt_key in ("intervention_time", "next_follow_up_time"):
        if dt_key in data and data[dt_key]:
            from datetime import datetime
            data[dt_key] = datetime.fromisoformat(str(data[dt_key]).replace("Z", "+00:00")).replace(tzinfo=None)
    allowed_fields = {"method", "content", "status", "intervention_time", "next_follow_up_time", "need_follow_up", "teacher_id", "result", "follow_up_suggestion"}
    for k, v in data.items():
        if k in allowed_fields and hasattr(inv, k):
            setattr(inv, k, v)
    # 干预完成/关闭时同步更新关联预警状态
    new_status = data.get("status")
    if new_status in ("completed", "closed") and inv.risk_alert_id:
        risk_alert = db.query(RiskAlert).filter(RiskAlert.id == inv.risk_alert_id).first()
        if risk_alert and risk_alert.status in ("pending", "viewed", "processing"):
            risk_alert.status = new_status
    db.commit()
    log_operation(db, user, request, module="intervention", action="update", object_type="intervention", object_id=intervention_id)
    return APIResponse.success(message="更新成功")


@router.delete("/{intervention_id}")
def delete_intervention(intervention_id: int, request: Request,
                        user: User = Depends(require_role("school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    inv = db.query(Intervention).filter(Intervention.id == intervention_id, Intervention.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
    if not inv:
        raise HTTPException(status_code=404, detail="干预记录不存在")
    if user.role in ("teacher", "counselor") and inv.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权限删除该记录")
    # 级联清理附件文件
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "interventions")
    for att in (inv.attachments or []):
        fp = os.path.join(upload_dir, os.path.basename(str(att.get("filename", ""))))
        if fp.startswith(upload_dir) and os.path.exists(fp):
            try:
                os.remove(fp)
            except OSError:
                pass
    db.delete(inv)
    db.commit()
    log_operation(db, user, request, module="intervention", action="delete", object_type="intervention", object_id=intervention_id)
    return APIResponse.success(message="删除成功")


# ======================== 附件管理 ========================

@router.post("/{intervention_id}/attachments")
async def upload_attachment(intervention_id: int, request: Request, file: UploadFile = File(...),
                            user: User = Depends(require_role("school_admin", "teacher", "counselor")),
                            db: Session = Depends(get_db)):
    """上传干预记录附件"""
    inv = db.query(Intervention).filter(Intervention.id == intervention_id, Intervention.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
    if not inv:
        raise HTTPException(status_code=404, detail="干预记录不存在")
    if user.role in ("teacher", "counselor") and inv.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权限修改该记录")
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "interventions")
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    attachments = inv.attachments or []
    attachments.append({"filename": filename, "original_name": file.filename, "size": len(content)})
    inv.attachments = attachments
    db.commit()
    log_operation(db, user, request, module="intervention", action="upload_attachment", object_type="intervention", object_id=intervention_id, detail=f"file={filename}")
    return APIResponse.success({"filename": filename, "original_name": file.filename}, message="上传成功")


@router.delete("/{intervention_id}/attachments/{filename}")
def delete_attachment(intervention_id: int, filename: str, request: Request,
                      user: User = Depends(require_role("school_admin", "teacher", "counselor")),
                      db: Session = Depends(get_db)):
    """删除干预记录附件"""
    inv = db.query(Intervention).filter(Intervention.id == intervention_id, Intervention.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
    if not inv:
        raise HTTPException(status_code=404, detail="干预记录不存在")
    if user.role in ("teacher", "counselor") and inv.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权限修改该记录")
    attachments = inv.attachments or []
    new_attachments = [a for a in attachments if a.get("filename") != filename]
    if len(new_attachments) == len(attachments):
        raise HTTPException(status_code=404, detail="附件不存在")
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "interventions")
    safe_name = os.path.basename(filename)  # 防御性清洗：仅取文件名，杜绝路径穿越
    file_path = os.path.join(upload_dir, safe_name)
    if os.path.exists(file_path):
        os.remove(file_path)
    inv.attachments = new_attachments
    db.commit()
    log_operation(db, user, request, module="intervention", action="delete_attachment", object_type="intervention", object_id=intervention_id, detail=f"file={safe_name}")
    return APIResponse.success(message="附件删除成功")


# ======================== 批量操作 ========================

@router.put("/batch-update")
def batch_update_interventions(data: dict, request: Request,
                               user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    """批量更新干预状态"""
    ids = data.get("ids", [])
    new_status = data.get("status")
    if not ids or not new_status:
        raise HTTPException(status_code=400, detail="请选择干预记录和目标状态")
    allowed_statuses = {"pending", "processing", "follow_up", "completed", "closed"}
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"无效的状态值，允许: {', '.join(allowed_statuses)}")
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    interventions = db.query(Intervention).filter(Intervention.id.in_(ids), Intervention.school_id == school_id).all()
    updated = 0
    for inv in interventions:
        inv.status = new_status
        updated += 1
    db.commit()
    log_operation(db, user, request, module="intervention", action="batch_update", object_type="intervention_batch", detail=f"updated={updated};status={new_status}")
    return APIResponse.success({"updated": updated}, message=f"成功更新 {updated} 条记录")


# ======================== 干预模板 ========================

INTERVENTION_TEMPLATES = [
    {
        "id": "student_talk_basic",
        "name": "基础学生谈话",
        "method": "student_talk",
        "content_template": "谈话时间：\n谈话地点：\n谈话内容：\n1. 了解学生近期学习和生活状况\n2. 倾听学生的想法和困惑\n3. 给予正面引导和鼓励",
        "follow_up_suggestion": "一周后跟进谈话，关注学生情绪变化",
        "need_follow_up": True,
        "follow_up_days": 7,
    },
    {
        "id": "family_communication",
        "name": "家校沟通",
        "method": "family_school",
        "content_template": "沟通时间：\n沟通方式：（电话/面谈/家长会）\n家长姓名：\n沟通内容：\n1. 反馈学生在校表现\n2. 了解学生家庭情况\n3. 共同商讨帮扶措施",
        "follow_up_suggestion": "两周后回访家长，确认措施执行情况",
        "need_follow_up": True,
        "follow_up_days": 14,
    },
    {
        "id": "counselor_session",
        "name": "心理辅导",
        "method": "counselor_guidance",
        "content_template": "辅导时间：\n辅导时长：分钟\n辅导主题：\n辅导内容记录：\n学生情绪状态：\n辅导效果评估：",
        "follow_up_suggestion": "根据辅导效果安排后续辅导计划",
        "need_follow_up": True,
        "follow_up_days": 14,
    },
    {
        "id": "observation_record",
        "name": "持续观察记录",
        "method": "observation",
        "content_template": "观察周期：\n观察重点：\n观察记录：\n1. 课堂表现\n2. 同学交往\n3. 情绪状态\n4. 行为变化",
        "follow_up_suggestion": "持续观察一个月，记录变化趋势",
        "need_follow_up": True,
        "follow_up_days": 30,
    },
    {
        "id": "home_visit",
        "name": "家访记录",
        "method": "home_visit",
        "content_template": "家访时间：\n家访地点：\n家庭成员：\n家庭环境观察：\n与家长沟通内容：\n家访结论：",
        "follow_up_suggestion": "家访后一周内完成后续跟进",
        "need_follow_up": True,
        "follow_up_days": 7,
    },
]


@router.get("/templates")
def list_templates(user: User = Depends(require_role("school_admin", "teacher", "counselor"))):
    """获取干预模板列表"""
    return APIResponse.success(INTERVENTION_TEMPLATES)


# ======================== 跟进提醒 ========================

@router.get("/follow-up-reminders")
def follow_up_reminders(
    page: int = Query(1), page_size: int = Query(20),
    user: User = Depends(require_role("school_admin", "teacher", "counselor")),
    db: Session = Depends(get_db),
):
    """获取需要跟进的干预记录"""
    from datetime import datetime
    now = datetime.now()
    q = db.query(Intervention).filter(
        Intervention.school_id == (getattr(user, '_effective_school_id', None) or user.school_id),
        Intervention.need_follow_up == True,
        Intervention.status.in_(["processing", "follow_up"]),
    )
    if user.role in ("teacher", "counselor"):
        q = q.filter(Intervention.teacher_id == user.id)
    total = q.count()
    items = q.order_by(Intervention.next_follow_up_time.asc()).offset((page - 1) * page_size).limit(page_size).all()
    result = []
    for inv in items:
        student = db.query(User).filter(User.id == inv.student_id).first()
        is_overdue = inv.next_follow_up_time and inv.next_follow_up_time < now
        result.append({
            "id": inv.id, "student_name": student.real_name if student else "",
            "student_id": inv.student_id, "method": inv.method,
            "content": inv.content[:100] if inv.content else "",
            "next_follow_up_time": inv.next_follow_up_time.isoformat() if inv.next_follow_up_time else None,
            "is_overdue": is_overdue,
            "status": inv.status,
        })
    return APIResponse.success({"items": result, "total": total, "page": page, "page_size": page_size})
