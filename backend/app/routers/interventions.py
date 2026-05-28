from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.risk import Intervention, RiskAlert
from ..dependencies import require_role
from ..services.audit_service import log_operation
from ..utils.access_control import can_access_student
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/interventions", tags=["干预记录"])


@router.get("")
def list_interventions(page: int = Query(1), page_size: int = Query(20), status: str = Query(""),
                       user: User = Depends(require_role("school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    q = db.query(Intervention).filter(Intervention.school_id == (getattr(user, '_effective_school_id', None) or user.school_id))
    if user.role in ("teacher", "counselor"):
        q = q.filter(Intervention.teacher_id == user.id)
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
            "content": inv.content, "result": inv.result,
            "intervention_time": inv.intervention_time.isoformat() if inv.intervention_time else None,
            "status": inv.status, "need_follow_up": inv.need_follow_up,
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
    for k, v in data.items():
        if hasattr(inv, k):
            setattr(inv, k, v)
    db.commit()
    log_operation(db, user, request, module="intervention", action="update", object_type="intervention", object_id=intervention_id)
    return APIResponse.success(message="更新成功")
