from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.user import User, Grade, Class
from ..models.task import Task, AnswerSheet
from ..models.risk import RiskAlert, Intervention, QualityAssessment, ScoringResult
from ..models.questionnaire import Questionnaire
from ..dependencies import require_role
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/reports", tags=["报表"])


@router.get("/school-overview")
def school_overview(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    school_id = user.school_id
    grades = db.query(Grade).filter(Grade.school_id == school_id).all()
    grade_data = []
    total_students = 0
    total_completed = 0

    for g in grades:
        classes = db.query(Class).filter(Class.grade_id == g.id).all()
        class_data = []
        grade_students = 0
        grade_completed = 0

        for c in classes:
            student_ids_query = db.query(User.id).filter(User.class_id == c.id, User.role == "student")
            student_count = db.query(func.count(User.id)).filter(User.class_id == c.id, User.role == "student").scalar()
            # 统计去重学生数，避免同一学生多份答卷导致完成率超100%
            completed_count = db.query(func.count(func.distinct(AnswerSheet.student_id))).filter(
                AnswerSheet.student_id.in_(student_ids_query),
                AnswerSheet.status == "submitted"
            ).scalar()
            class_data.append({
                "class_name": c.name,
                "student_count": student_count,
                "completed_count": completed_count,
                "completion_rate": round(completed_count / max(student_count, 1) * 100, 1),
            })
            grade_students += student_count
            grade_completed += completed_count

        grade_data.append({
            "grade_name": g.name,
            "student_count": grade_students,
            "completed_count": grade_completed,
            "completion_rate": round(grade_completed / max(grade_students, 1) * 100, 1),
            "classes": class_data,
        })
        total_students += grade_students
        total_completed += grade_completed

    return APIResponse.success({
        "grades": grade_data,
        "total_students": total_students,
        "total_completed": total_completed,
        "overall_completion_rate": round(total_completed / max(total_students, 1) * 100, 1),
    })


@router.get("/risk-summary")
def risk_summary(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    school_id = user.school_id
    total = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id).scalar()

    by_level = db.query(RiskAlert.risk_level, func.count(RiskAlert.id)).filter(
        RiskAlert.school_id == school_id
    ).group_by(RiskAlert.risk_level).all()

    by_status = db.query(RiskAlert.status, func.count(RiskAlert.id)).filter(
        RiskAlert.school_id == school_id
    ).group_by(RiskAlert.status).all()

    level_labels = {"low": "低风险", "medium": "中风险", "high": "高风险", "urgent": "紧急风险"}
    status_labels = {"pending": "待处理", "processing": "处理中", "resolved": "已解决", "closed": "已关闭"}

    level_data = [{
        "level": l,
        "label": level_labels.get(l, l),
        "count": c,
        "percentage": round(c / max(total, 1) * 100, 1),
    } for l, c in by_level]

    status_data = [{
        "status": s,
        "label": status_labels.get(s, s),
        "count": c,
        "percentage": round(c / max(total, 1) * 100, 1),
    } for s, c in by_status]

    return APIResponse.success({
        "total": total,
        "by_level": level_data,
        "by_status": status_data,
    })
