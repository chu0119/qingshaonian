from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.task import Task, AnswerSheet
from ..models.questionnaire import Questionnaire
from ..models.risk import RiskAlert, ScoringResult, QualityAssessment
from ..dependencies import require_role
from ..services.audit_service import log_operation
from ..utils.access_control import can_access_student
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/risks", tags=["风险预警"])

RISK_LEVEL_LABELS = {"low": "关注", "medium": "预警", "high": "警告", "urgent": "危急"}
RISK_STATUS_LABELS = {"pending": "待处理", "viewed": "已查看", "processing": "处理中", "follow_up": "持续跟进", "resolved": "已解决", "completed": "已完成", "closed": "已关闭"}
QUALITY_LEVEL_LABELS = {"normal": "正常", "mild_anomaly": "轻度异常", "moderate_anomaly": "中度异常", "severe_anomaly": "高度异常"}
VALIDITY_LABELS = {"valid": "有效", "basically_valid": "基本有效", "questionable": "存疑", "not_recommended": "不建议纳入", "invalid": "无效"}


@router.get("")
def list_risks(page: int = Query(1), page_size: int = Query(20), status: str = Query(""),
               student_id: int | None = Query(None),
               user: User = Depends(require_role("school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    q = db.query(RiskAlert).filter(RiskAlert.school_id == (getattr(user, '_effective_school_id', None) or user.school_id))
    if student_id:
        q = q.filter(RiskAlert.student_id == student_id)
    if status:
        q = q.filter(RiskAlert.status == status)
    all_alerts = q.order_by(RiskAlert.id.desc()).all()
    if user.role in ("teacher", "counselor"):
        all_alerts = [
            a for a in all_alerts
            if can_access_student(db, user, db.query(User).filter(User.id == a.student_id).first())
        ]
    total = len(all_alerts)
    alerts = all_alerts[(page - 1) * page_size: page * page_size]
    items = []
    for a in alerts:
        student = db.query(User).filter(User.id == a.student_id).first()
        task = db.query(Task).filter(Task.id == a.task_id).first()
        qnr = db.query(Questionnaire).filter(Questionnaire.id == task.questionnaire_id).first() if task else None
        items.append({
            "id": a.id, "student_id": a.student_id, "student_name": student.real_name if student else "",
            "grade_name": student.grade.name if student and student.grade else "",
            "class_name": student.class_.name if student and student.class_ else "",
            "risk_level": a.risk_level, "risk_type": a.risk_type, "status": a.status,
            "risk_level_label": RISK_LEVEL_LABELS.get(a.risk_level, a.risk_level),
            "status_label": RISK_STATUS_LABELS.get(a.status, a.status),
            "questionnaire_title": qnr.title if qnr else "",
            "answer_sheet_id": a.answer_sheet_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return APIResponse.success({"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": max((total + page_size - 1) // page_size, 1)})


@router.put("/{alert_id}")
def update_risk_alert(alert_id: int, data: dict, request: Request,
                      user: User = Depends(require_role("school_admin", "teacher", "counselor")),
                      db: Session = Depends(get_db)):
    """更新风险预警状态（确认收到等）"""
    alert = db.query(RiskAlert).filter(RiskAlert.id == alert_id, RiskAlert.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")
    # 教师/心理老师只能更新自己所负责学生的预警（与 get_risk_detail 保持一致）
    if user.role in ("teacher", "counselor"):
        student = db.query(User).filter(User.id == alert.student_id).first()
        if not can_access_student(db, user, student):
            raise HTTPException(status_code=404, detail="预警不存在")
    new_status = data.get("status")
    if new_status and new_status in ("viewed", "processing", "follow_up", "resolved", "completed", "closed"):
        alert.status = new_status
    db.commit()
    log_operation(db, user, request, module="risk_alert", action="update_status", object_type="risk_alert", object_id=alert_id, detail=f"status={new_status}")
    return APIResponse.success(message="状态更新成功")


@router.get("/{alert_id}")
def get_risk_detail(alert_id: int, request: Request, user: User = Depends(require_role("school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    alert = db.query(RiskAlert).filter(RiskAlert.id == alert_id, RiskAlert.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")
    student = db.query(User).filter(User.id == alert.student_id).first()
    if not can_access_student(db, user, student):
        raise HTTPException(status_code=404, detail="预警不存在")
    scoring = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == alert.answer_sheet_id).first()
    quality = db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id == alert.answer_sheet_id).first()
    log_operation(db, user, request, module="risk_alert", action="view_detail", object_type="risk_alert", object_id=alert.id, object_name=student.real_name if student else "")
    import json
    dim_analysis = []
    if scoring and scoring.triggered_rules:
        try:
            dim_analysis = json.loads(scoring.triggered_rules) if isinstance(scoring.triggered_rules, str) else scoring.triggered_rules
        except Exception: pass
    return APIResponse.success({
        "id": alert.id, "student_name": student.real_name if student else "",
        "risk_level": alert.risk_level, "risk_type": alert.risk_type, "status": alert.status,
        "risk_level_label": RISK_LEVEL_LABELS.get(alert.risk_level, alert.risk_level),
        "status_label": RISK_STATUS_LABELS.get(alert.status, alert.status),
        "total_score": scoring.total_score if scoring else 0,
        "dimension_scores": scoring.dimension_scores if scoring else {},
        "risk_description": scoring.risk_description if scoring else "",
        "dimension_analysis": dim_analysis,
        "quality_level": quality.quality_level if quality else "normal",
        "quality_level_label": QUALITY_LEVEL_LABELS.get(quality.quality_level, quality.quality_level) if quality else "正常",
        "quality_score": quality.quality_score if quality else 100,
        "suggest_retest": quality.suggest_retest if quality else False,
        "answer_sheet_id": alert.answer_sheet_id,
        "student_id": alert.student_id,
    })


@router.get("/{alert_id}/answers")
def risk_answer_detail(alert_id: int, request: Request, user: User = Depends(require_role("school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    alert = db.query(RiskAlert).filter(RiskAlert.id == alert_id, RiskAlert.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")
    student = db.query(User).filter(User.id == alert.student_id).first()
    if not can_access_student(db, user, student):
        raise HTTPException(status_code=404, detail="预警不存在")
    if not alert.answer_sheet_id:
        raise HTTPException(status_code=404, detail="该预警无关联答卷")
    from ..services.questionnaire_service import get_answer_detail
    try:
        detail = get_answer_detail(db, alert.answer_sheet_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    log_operation(db, user, request, module="risk_alert", action="view_detail",
                  object_type="answer_sheet", object_id=alert.answer_sheet_id,
                  object_name=student.real_name if student else "", detail="查看答题详情")
    return APIResponse.success(detail)


@router.get("/sheets/{sheet_id}/detail")
def answer_sheet_detail(sheet_id: int, request: Request, user: User = Depends(require_role("school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    from ..models.task import AnswerSheet
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="答卷不存在")
    student = db.query(User).filter(User.id == sheet.student_id).first()
    if not student or student.school_id != (getattr(user, '_effective_school_id', None) or user.school_id):
        raise HTTPException(status_code=404, detail="答卷不存在")
    if not can_access_student(db, user, student):
        raise HTTPException(status_code=404, detail="答卷不存在")
    from ..services.questionnaire_service import get_answer_detail
    try:
        detail = get_answer_detail(db, sheet_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    log_operation(db, user, request, module="risk_alert", action="view_detail",
                  object_type="answer_sheet", object_id=sheet_id,
                  object_name=student.real_name if student else "", detail="查看答题详情")
    return APIResponse.success(detail)
