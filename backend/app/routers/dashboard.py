from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.user import User, Grade, Class
from ..models.task import Task, AnswerSheet
from ..models.risk import RiskAlert, Intervention, QualityAssessment
from ..dependencies import require_role, get_effective_school_id
from ..services.stats_service import school_metrics, target_student_ids
from ..utils.access_control import effective_task_status, teacher_class_ids
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/dashboard", tags=["看板"])


@router.get("/school")
def school_dashboard(request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    school_id = get_effective_school_id(request, user)
    metrics = school_metrics(db, school_id)
    active_tasks = db.query(func.count(Task.id)).filter(Task.school_id == school_id, Task.status.in_(["not_started", "in_progress", "active"])).scalar()

    risk_count = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id).scalar()
    pending_risks = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id, RiskAlert.status == "pending").scalar()
    pending_interventions = db.query(func.count(Intervention.id)).filter(Intervention.school_id == school_id, Intervention.status.in_(["pending", "processing"])).scalar()

    # 答题质量统计
    quality_stats = db.query(
        QualityAssessment.quality_level,
        func.count(QualityAssessment.id)
    ).join(AnswerSheet).join(Task).filter(Task.school_id == school_id).group_by(QualityAssessment.quality_level).all()
    quality_dist = {level: cnt for level, cnt in quality_stats}

    # 风险分布
    risk_dist = db.query(
        RiskAlert.risk_level, func.count(RiskAlert.id)
    ).filter(RiskAlert.school_id == school_id).group_by(RiskAlert.risk_level).all()
    risk_level_dist = {level: cnt for level, cnt in risk_dist}

    return APIResponse.success({
        "stats": {
            "student_count": metrics["student_count"], "teacher_count": metrics["teacher_count"],
            "class_count": metrics["class_count"], "active_tasks": active_tasks,
            "total_answer_sheets": metrics["answer_sheet_count"], "risk_count": risk_count,
            "pending_risks": pending_risks, "pending_interventions": pending_interventions,
            "completion_rate": metrics["completion_rate"],
            "valid_answer_rate": metrics["valid_answer_rate"],
            "intervention_completion_rate": metrics["intervention_completion_rate"],
        },
        "quality_distribution": quality_dist,
        "risk_level_distribution": risk_level_dist,
    })


@router.get("/teacher")
def teacher_dashboard(user: User = Depends(require_role("teacher", "counselor")), db: Session = Depends(get_db)):
    class_ids = teacher_class_ids(db, user)
    _sid = getattr(user, '_effective_school_id', None) or user.school_id
    my_students = db.query(func.count(User.id)).filter(User.class_id.in_(class_ids), User.role == "student").scalar() if class_ids else 0

    tasks = [t for t in db.query(Task).filter(Task.school_id == _sid, Task.status.in_(["not_started", "in_progress", "active"])).all()
             if set(t.target_ids or []).intersection(class_ids)]
    expected = 0
    completed = 0
    task_rates = []
    for t in tasks:
        t_target = [sid for sid in target_student_ids(db, t) if db.query(User.class_id).filter(User.id == sid).scalar() in class_ids]
        t_expected = len(t_target)
        t_completed = db.query(func.count(AnswerSheet.id)).filter(
            AnswerSheet.task_id == t.id, AnswerSheet.student_id.in_(t_target), AnswerSheet.status == "submitted"
        ).scalar() or 0 if t_target else 0
        expected += t_expected
        completed += t_completed
        if t_expected > 0:
            task_rates.append(t_completed / t_expected * 100)
    avg_completion = round(sum(task_rates) / max(len(task_rates), 1), 1) if task_rates else 0
    pending_risks = (
        db.query(func.count(RiskAlert.id))
        .join(User, User.id == RiskAlert.student_id)
        .filter(RiskAlert.school_id == _sid, RiskAlert.status == "pending", User.class_id.in_(class_ids))
        .scalar()
        if class_ids else 0
    )
    pending_interventions = db.query(func.count(Intervention.id)).filter(
        Intervention.teacher_id == user.id,
        Intervention.status.in_(["pending", "processing", "follow_up", "ongoing"]),
    ).scalar()

    return APIResponse.success({
        "stats": {
            "my_classes": len(class_ids), "my_students": my_students,
            "active_tasks": len(tasks), "pending_risks": pending_risks,
            "pending_interventions": pending_interventions,
            "average_completion_rate": avg_completion,
            "uncompleted_students": max(expected - completed, 0),
        }
    })


@router.get("/student")
def student_dashboard(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    _sid = getattr(user, '_effective_school_id', None) or user.school_id
    pending_count = sum(1 for task in db.query(Task).filter(Task.school_id == _sid, Task.status.in_(["not_started", "in_progress", "active"])).all() if effective_task_status(task) in ("not_started", "in_progress"))
    completed_count = db.query(func.count(AnswerSheet.id)).filter(AnswerSheet.student_id == user.id, AnswerSheet.status == "submitted").scalar()

    return APIResponse.success({
        "pending_count": pending_count, "completed_count": completed_count,
    })


# ======================== 趋势数据 ========================

@router.get("/school/trends")
def school_trends(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    """学校维度的月度趋势数据（最近6个月）"""
    from datetime import datetime
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    now = datetime.now()
    trends = []
    for i in range(5, -1, -1):
        # 正确计算月份：先减去 i 个月，再取当月1日和下月1日
        y = now.year
        m = now.month - i
        while m <= 0:
            m += 12
            y -= 1
        month_start = datetime(y, m, 1)
        if i > 0:
            nm, ny = m + 1, y
            if nm > 12:
                nm = 1
                ny += 1
            month_end = datetime(ny, nm, 1)
        else:
            month_end = now
        month_label = month_start.strftime("%Y-%m")
        # 该月提交的答卷数
        submit_count = db.query(func.count(AnswerSheet.id)).join(Task).filter(
            Task.school_id == school_id, AnswerSheet.status == "submitted",
            AnswerSheet.submitted_at >= month_start, AnswerSheet.submitted_at < month_end
        ).scalar() or 0
        # 该月新增风险预警数
        risk_count = db.query(func.count(RiskAlert.id)).filter(
            RiskAlert.school_id == school_id,
            RiskAlert.created_at >= month_start, RiskAlert.created_at < month_end
        ).scalar() or 0
        trends.append({"month": month_label, "submits": submit_count, "risks": risk_count})
    return APIResponse.success(trends)


@router.get("/teacher/trends")
def teacher_trends(user: User = Depends(require_role("teacher", "counselor")), db: Session = Depends(get_db)):
    """教师维度的月度趋势数据（最近6个月）"""
    from datetime import datetime
    class_ids = teacher_class_ids(db, user)
    now = datetime.now()
    student_ids = [s[0] for s in db.query(User.id).filter(User.class_id.in_(class_ids), User.role == "student").all()] if class_ids else []
    trends = []
    for i in range(5, -1, -1):
        y = now.year
        m = now.month - i
        while m <= 0:
            m += 12
            y -= 1
        month_start = datetime(y, m, 1)
        if i > 0:
            nm, ny = m + 1, y
            if nm > 12:
                nm = 1
                ny += 1
            month_end = datetime(ny, nm, 1)
        else:
            month_end = now
        month_label = month_start.strftime("%Y-%m")
        submit_count = 0
        risk_count = 0
        if student_ids:
            submit_count = db.query(func.count(AnswerSheet.id)).filter(
                AnswerSheet.student_id.in_(student_ids), AnswerSheet.status == "submitted",
                AnswerSheet.submitted_at >= month_start, AnswerSheet.submitted_at < month_end
            ).scalar() or 0
            risk_count = db.query(func.count(RiskAlert.id)).filter(
                RiskAlert.student_id.in_(student_ids),
                RiskAlert.created_at >= month_start, RiskAlert.created_at < month_end
            ).scalar() or 0
        trends.append({"month": month_label, "submits": submit_count, "risks": risk_count})
    return APIResponse.success(trends)
