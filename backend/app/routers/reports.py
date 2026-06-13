from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.user import User, Grade, Class, School
from ..models.task import Task, AnswerSheet, AnswerRecord
from ..models.risk import RiskAlert, Intervention, QualityAssessment, ScoringResult
from ..models.questionnaire import Questionnaire, Question, Option
from ..dependencies import require_role
from ..utils.access_control import can_access_student
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/reports", tags=["报表"])


@router.get("/school-overview")
def school_overview(user: User = Depends(require_role("school_admin", "teacher", "counselor")),
                    class_id: int | None = Query(None),
                    db: Session = Depends(get_db)):
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    grades = db.query(Grade).filter(Grade.school_id == school_id, Grade.status == True).order_by(Grade.sort_order).all()
    grade_data = []
    total_students = 0
    total_completed = 0

    for g in grades:
        if class_id:
            classes = db.query(Class).filter(Class.id == class_id, Class.grade_id == g.id).all()
        else:
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
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    total = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id).scalar()

    by_level = db.query(RiskAlert.risk_level, func.count(RiskAlert.id)).filter(
        RiskAlert.school_id == school_id
    ).group_by(RiskAlert.risk_level).all()

    by_status = db.query(RiskAlert.status, func.count(RiskAlert.id)).filter(
        RiskAlert.school_id == school_id
    ).group_by(RiskAlert.status).all()

    level_labels = {"low": "关注", "medium": "预警", "high": "警告", "urgent": "危急"}
    status_labels = {"pending": "待处理", "viewed": "已查看", "processing": "处理中", "resolved": "已解决", "completed": "已完成", "closed": "已关闭", "follow_up": "持续跟进"}

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


@router.get("/student-longitudinal/{student_id}")
def student_longitudinal(student_id: int, user: User = Depends(require_role("school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student or student.school_id != school_id:
        raise HTTPException(status_code=404, detail="学生不存在")
    if user.role in ("teacher", "counselor"):
        if not can_access_student(db, user, student):
            raise HTTPException(status_code=403, detail="无权限查看该学生")

    sheets = db.query(AnswerSheet).filter(
        AnswerSheet.student_id == student_id, AnswerSheet.status == "submitted"
    ).order_by(AnswerSheet.submitted_at).all()

    results = []
    for sheet in sheets:
        sr = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == sheet.id).first()
        q = db.query(Questionnaire).filter(Questionnaire.id == sheet.questionnaire_id).first()
        results.append({
            "answer_sheet_id": sheet.id,
            "task_id": sheet.task_id,
            "questionnaire_title": q.title if q else "",
            "submitted_at": sheet.submitted_at.isoformat() if sheet.submitted_at else None,
            "total_score": sr.total_score if sr else None,
            "dimension_scores": sr.dimension_scores if sr else {},
            "risk_level": sr.risk_level if sr else None,
        })

    return APIResponse.success({
        "student_id": student.id,
        "student_name": student.real_name,
        "records": results,
    })


@router.get("/group-summary")
def group_summary(
    scope: str = Query("grade", description="class | grade | school"),
    scope_id: int = Query(None, description="班级或年级ID"),
    user: User = Depends(require_role("school_admin", "platform_admin")),
    db: Session = Depends(get_db),
):
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)

    if scope == "school":
        student_q = db.query(User.id).filter(User.school_id == school_id, User.role == "student", User.status == True)
        group_name = "全校"
    elif scope == "grade" and scope_id:
        classes = db.query(Class).filter(Class.grade_id == scope_id).all()
        class_ids = [c.id for c in classes]
        student_q = db.query(User.id).filter(User.class_id.in_(class_ids), User.role == "student", User.status == True)
        grade = db.query(Grade).filter(Grade.id == scope_id).first()
        group_name = grade.name if grade else "年级"
    elif scope == "class" and scope_id:
        student_q = db.query(User.id).filter(User.class_id == scope_id, User.role == "student", User.status == True)
        cls = db.query(Class).filter(Class.id == scope_id).first()
        group_name = cls.name if cls else "班级"
    else:
        raise HTTPException(status_code=400, detail="请指定 scope 和 scope_id")

    student_ids = [s[0] for s in student_q.all()]
    if not student_ids:
        return APIResponse.success({"group_name": group_name, "student_count": 0, "avg_total_score": 0, "dimension_avg": {}, "risk_distribution": {}, "completion_rate": 0})

    student_count = len(student_ids)
    sheets = db.query(AnswerSheet).filter(
        AnswerSheet.student_id.in_(student_ids), AnswerSheet.status == "submitted"
    ).all()
    sheet_ids = [s.id for s in sheets]
    completed_students = len(set(s.student_id for s in sheets))

    scoring_results = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id.in_(sheet_ids)).all() if sheet_ids else []

    avg_total = 0
    dim_accum: dict = {}
    dim_count: dict = {}  # 每个维度实际出现的次数
    risk_dist: dict = {"low": 0, "medium": 0, "high": 0, "urgent": 0}

    for sr in scoring_results:
        avg_total += sr.total_score or 0
        if sr.risk_level in risk_dist:
            risk_dist[sr.risk_level] += 1
        if sr.dimension_scores and isinstance(sr.dimension_scores, dict):
            for dim_key, dim_val in sr.dimension_scores.items():
                if isinstance(dim_val, (int, float)):
                    dim_accum[dim_key] = dim_accum.get(dim_key, 0) + dim_val
                    dim_count[dim_key] = dim_count.get(dim_key, 0) + 1

    n = len(scoring_results) or 1
    avg_total = round(avg_total / n, 1)
    dim_avg = {k: round(v / max(dim_count.get(k, 1), 1), 1) for k, v in dim_accum.items()}

    return APIResponse.success({
        "group_name": group_name,
        "student_count": student_count,
        "completed_count": completed_students,
        "avg_total_score": avg_total,
        "dimension_avg": dim_avg,
        "risk_distribution": risk_dist,
        "completion_rate": round(completed_students / max(student_count, 1) * 100, 1),
    })


@router.get("/audit-logs")
def school_audit_logs(
    page: int = Query(1), page_size: int = Query(20),
    action: str = Query(""), start_date: str = Query(""), end_date: str = Query(""),
    user: User = Depends(require_role("school_admin", "platform_admin")), db: Session = Depends(get_db),
):
    """学校管理员查看本校操作日志"""
    from ..models.audit import OperationLog
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    q = db.query(OperationLog).filter(OperationLog.school_id == school_id)
    if action:
        q = q.filter(OperationLog.action == action)
    if start_date:
        q = q.filter(OperationLog.operation_time >= start_date)
    if end_date:
        end_dt = datetime.fromisoformat(end_date) + timedelta(days=1)
        q = q.filter(OperationLog.operation_time < end_dt.isoformat())
    total = q.count()
    logs = q.order_by(OperationLog.operation_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return APIResponse.success({
        "total": total,
        "items": [{
            "id": l.id,
            "operator_name": l.operator_name,
            "operator_role": l.operator_role,
            "module": l.module,
            "action": l.action,
            "object_type": l.object_type,
            "object_name": l.object_name,
            "operation_time": l.operation_time.isoformat() if l.operation_time else None,
            "request_ip": l.request_ip,
            "result": l.result,
            "detail": l.detail,
        } for l in logs],
    })


# ======================== 报表导出 ========================

@router.get("/school-overview/export")
def export_school_overview(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    """导出学校概览为 Excel"""
    import openpyxl, io
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "学校概览"
    ws.append(["年级", "班级", "学生数", "已完成", "完成率(%)"])
    grades = db.query(Grade).filter(Grade.school_id == school_id, Grade.status == True).order_by(Grade.sort_order).all()
    for g in grades:
        classes = db.query(Class).filter(Class.grade_id == g.id).all()
        for c in classes:
            student_count = db.query(func.count(User.id)).filter(User.class_id == c.id, User.role == "student").scalar()
            student_ids_q = db.query(User.id).filter(User.class_id == c.id, User.role == "student")
            completed = db.query(func.count(func.distinct(AnswerSheet.student_id))).filter(
                AnswerSheet.student_id.in_(student_ids_q), AnswerSheet.status == "submitted").scalar()
            rate = round(completed / max(student_count, 1) * 100, 1)
            ws.append([g.name, c.name, student_count, completed, rate])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=school_overview.xlsx"})


@router.get("/risk-summary/export")
def export_risk_summary(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    """导出风险汇总为 Excel"""
    import openpyxl, io
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "风险汇总"
    ws.append(["风险等级", "数量", "占比(%)"])
    level_labels = {"low": "关注", "medium": "预警", "high": "警告", "urgent": "危急"}
    total = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id).scalar()
    by_level = db.query(RiskAlert.risk_level, func.count(RiskAlert.id)).filter(
        RiskAlert.school_id == school_id).group_by(RiskAlert.risk_level).all()
    for level, count in by_level:
        ws.append([level_labels.get(level, level), count, round(count / max(total, 1) * 100, 1)])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=risk_summary.xlsx"})


# ======================== 问卷单题分析 ========================

@router.get("/question-analysis")
def question_analysis(
    questionnaire_id: int = Query(...),
    task_id: int | None = Query(None),
    user: User = Depends(require_role("school_admin", "teacher", "counselor")),
    db: Session = Depends(get_db),
):
    """单题分析：每道题的选项分布、回答率、与风险等级的关联"""
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)

    questions = db.query(Question).filter(Question.questionnaire_id == questionnaire_id).order_by(Question.sort_order).all()
    if not questions:
        return APIResponse.success([])

    sheets_q = db.query(AnswerSheet).filter(AnswerSheet.questionnaire_id == questionnaire_id)
    if task_id:
        sheets_q = sheets_q.filter(AnswerSheet.task_id == task_id)
    sheets = sheets_q.all()
    sheet_ids = [s.id for s in sheets]

    risk_by_sheet = {}
    if sheet_ids:
        scorings = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id.in_(sheet_ids)).all()
        risk_by_sheet = {s.answer_sheet_id: s.risk_level for s in scorings}

    result = []
    for q in questions:
        options = db.query(Option).filter(Option.question_id == q.id).order_by(Option.sort_order).all()
        records = db.query(AnswerRecord).filter(
            AnswerRecord.question_id == q.id,
            AnswerRecord.answer_sheet_id.in_(sheet_ids) if sheet_ids else False,
        ).all()

        option_stats = {}
        for opt in options:
            option_stats[opt.id] = {"id": opt.id, "content": opt.content, "score": opt.score, "count": 0, "risk_counts": {"low": 0, "medium": 0, "high": 0, "urgent": 0}}

        total_answers = len(records)
        answered = 0
        for rec in records:
            answer = rec.answer_content or {}
            sheet_risk = risk_by_sheet.get(rec.answer_sheet_id, "low")
            if answer.get("selected_option_id"):
                oid = answer["selected_option_id"]
                if oid in option_stats:
                    option_stats[oid]["count"] += 1
                    option_stats[oid]["risk_counts"][sheet_risk] = option_stats[oid]["risk_counts"].get(sheet_risk, 0) + 1
                answered += 1
            elif answer.get("selected_option_ids"):
                for oid in answer["selected_option_ids"]:
                    if oid in option_stats:
                        option_stats[oid]["count"] += 1
                        option_stats[oid]["risk_counts"][sheet_risk] = option_stats[oid]["risk_counts"].get(sheet_risk, 0) + 1
                answered += 1
            elif answer.get("value") is not None:
                answered += 1
            elif answer.get("text"):
                answered += 1

        result.append({
            "id": q.id,
            "title": q.title,
            "type": q.type,
            "sort_order": q.sort_order,
            "required": q.required,
            "options": list(option_stats.values()),
            "total_answers": total_answers,
            "answer_rate": round(answered / max(total_answers, 1) * 100, 1) if total_answers else 0,
        })

    return APIResponse.success(result)


# ======================== 常模对比 ========================

@router.get("/norm-comparison/{student_id}")
def norm_comparison(
    student_id: int,
    user: User = Depends(require_role("school_admin", "teacher", "counselor")),
    db: Session = Depends(get_db),
):
    """学生维度分数与学校平均分对比"""
    school_id = (getattr(user, '_effective_school_id', None) or user.school_id)

    latest_sheet = db.query(AnswerSheet).filter(
        AnswerSheet.student_id == student_id, AnswerSheet.status == "submitted"
    ).order_by(AnswerSheet.submitted_at.desc()).first()

    if not latest_sheet:
        return APIResponse.success({"student": None, "school_avg": None, "dimensions": []})

    student_scoring = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == latest_sheet.id).first()
    if not student_scoring:
        return APIResponse.success({"student": None, "school_avg": None, "dimensions": []})

    all_scorings = db.query(ScoringResult).join(AnswerSheet).filter(
        AnswerSheet.questionnaire_id == latest_sheet.questionnaire_id,
        AnswerSheet.school_id == school_id,
        AnswerSheet.status == "submitted",
    ).all()

    dim_totals = {}
    dim_counts = {}
    for s in all_scorings:
        for dim, score in (s.dimension_scores or {}).items():
            dim_totals[dim] = dim_totals.get(dim, 0) + (score or 0)
            dim_counts[dim] = dim_counts.get(dim, 0) + 1

    school_avg = {dim: round(dim_totals[dim] / max(dim_counts[dim], 1), 1) for dim in dim_totals}

    dimensions = []
    student_dims = student_scoring.dimension_scores or {}
    for dim in sorted(set(list(student_dims.keys()) + list(school_avg.keys()))):
        student_val = student_dims.get(dim, 0)
        avg_val = school_avg.get(dim, 0)
        dimensions.append({
            "dimension": dim,
            "student_score": student_val,
            "school_avg": avg_val,
            "diff": round(student_val - avg_val, 1),
        })

    return APIResponse.success({
        "student": {"total_score": student_scoring.total_score, "risk_level": student_scoring.risk_level},
        "school_avg_total": round(sum(s.total_score for s in all_scorings) / max(len(all_scorings), 1), 1),
        "dimensions": dimensions,
    })


# ======================== 跨校对比分析 ========================

@router.get("/cross-school-comparison")
def cross_school_comparison(
    user: User = Depends(require_role("platform_admin")),
    db: Session = Depends(get_db),
):
    """跨校对比分析：各学校完成率、风险分布、有效率等指标横向对比"""
    schools = db.query(School).filter(School.status == True).all()
    result = []

    for school in schools:
        student_count = db.query(func.count(User.id)).filter(User.school_id == school.id, User.role == "student").scalar() or 0
        teacher_count = db.query(func.count(User.id)).filter(User.school_id == school.id, User.role.in_(["teacher", "counselor"])).scalar() or 0

        total_tasks = db.query(func.count(Task.id)).filter(Task.school_id == school.id).scalar() or 0

        sheets = db.query(AnswerSheet).join(Task).filter(Task.school_id == school.id, AnswerSheet.status == "submitted").all()
        completed_count = len(set(s.student_id for s in sheets))

        completion_rate = round(completed_count / max(student_count, 1) * 100, 1)

        risk_alerts = db.query(RiskAlert).filter(RiskAlert.school_id == school.id).all()
        risk_dist = {"low": 0, "medium": 0, "high": 0, "urgent": 0}
        pending_risks = 0
        for ra in risk_alerts:
            if ra.risk_level in risk_dist:
                risk_dist[ra.risk_level] += 1
            if ra.status == "pending":
                pending_risks += 1

        sheet_ids = [s.id for s in sheets]
        quality_normal = 0
        quality_total_count = 0
        if sheet_ids:
            qa = db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id.in_(sheet_ids)).all()
            quality_total_count = len(qa)
            quality_normal = sum(1 for q in qa if q.quality_level == "normal")

        effective_rate = round(quality_normal / max(quality_total_count, 1) * 100, 1) if quality_total_count else 0

        avg_score = 0
        if sheet_ids:
            scorings = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id.in_(sheet_ids)).all()
            if scorings:
                avg_score = round(sum(s.total_score for s in scorings) / len(scorings), 1)

        result.append({
            "school_id": school.id,
            "school_name": school.name,
            "student_count": student_count,
            "teacher_count": teacher_count,
            "task_count": total_tasks,
            "completed_count": completed_count,
            "completion_rate": completion_rate,
            "risk_distribution": risk_dist,
            "total_risks": sum(risk_dist.values()),
            "pending_risks": pending_risks,
            "effective_rate": effective_rate,
            "avg_score": avg_score,
        })

    result.sort(key=lambda x: x["completion_rate"], reverse=True)

    summary = {
        "total_schools": len(result),
        "total_students": sum(r["student_count"] for r in result),
        "total_teachers": sum(r["teacher_count"] for r in result),
        "avg_completion_rate": round(sum(r["completion_rate"] for r in result) / max(len(result), 1), 1),
        "avg_effective_rate": round(sum(r["effective_rate"] for r in result if r["effective_rate"] > 0) / max(sum(1 for r in result if r["effective_rate"] > 0), 1), 1),
        "total_pending_risks": sum(r["pending_risks"] for r in result),
    }

    return APIResponse.success({"schools": result, "summary": summary})
