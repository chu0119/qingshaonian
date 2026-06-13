from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from io import BytesIO
from ..database import get_db
from ..models.user import User, Grade, Class
from ..models.task import Task, AnswerSheet
from ..models.risk import RiskAlert, ScoringResult, Intervention
from ..models.questionnaire import Questionnaire
from ..dependencies import require_role
from ..services.audit_service import log_operation
from ..utils.access_control import effective_school_id
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/exports", tags=["导出"])


@router.get("/students")
def export_students(request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    log_operation(db, user, request, module="export", action="export_students", object_type="student_list")
    return APIResponse.success({"message": "导出学生名单"})


@router.get("/report")
def export_report(
    request: Request,
    report_type: str = Query("overview", description="overview/risk/quality/completion"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    user: User = Depends(require_role("school_admin", "platform_admin")),
    db: Session = Depends(get_db),
):
    """Generate and return an Excel report."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from fastapi.responses import StreamingResponse

    school_id = effective_school_id(user)
    now = datetime.now()

    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else now - timedelta(days=30)
        end_dt = datetime.fromisoformat(end_date) if end_date else now
    except ValueError:
        start_dt = now - timedelta(days=30)
        end_dt = now

    wb = Workbook()
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="1677FF", end_color="1677FF", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )

    if report_type == "overview":
        ws = wb.active
        ws.title = "学校综合报表"
        ws.append(["指标", "数值"])
        for col in range(1, 3):
            cell = ws.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

        student_count = db.query(func.count(User.id)).filter(User.school_id == school_id, User.role == "student").scalar() or 0
        teacher_count = db.query(func.count(User.id)).filter(User.school_id == school_id, User.role.in_(["teacher", "counselor"])).scalar() or 0
        class_count = db.query(func.count(Class.id)).filter(Class.school_id == school_id).scalar() or 0
        task_count = db.query(func.count(Task.id)).filter(Task.school_id == school_id).scalar() or 0
        sheet_count = db.query(func.count(AnswerSheet.id)).join(Task).filter(Task.school_id == school_id).scalar() or 0
        risk_count = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id).scalar() or 0
        pending_risk = db.query(func.count(RiskAlert.id)).filter(RiskAlert.school_id == school_id, RiskAlert.status == "pending").scalar() or 0
        intervention_count = db.query(func.count(Intervention.id)).filter(Intervention.school_id == school_id).scalar() or 0

        rows = [
            ("学生总数", student_count), ("教师总数", teacher_count), ("班级数量", class_count),
            ("任务总数", task_count), ("答卷总数", sheet_count),
            ("风险提示总数", risk_count), ("待处理预警", pending_risk), ("干预记录总数", intervention_count),
            ("报表时间范围", f"{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}"),
            ("生成时间", now.strftime("%Y-%m-%d %H:%M")),
        ]
        for row in rows:
            ws.append(list(row))
        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 30

    elif report_type == "risk":
        ws = wb.active
        ws.title = "风险预警报表"
        headers = ["学生姓名", "年级", "班级", "风险等级", "风险类型", "状态", "触发时间", "问卷"]
        ws.append(headers)
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

        alerts = db.query(RiskAlert).filter(
            RiskAlert.school_id == school_id,
            RiskAlert.created_at >= start_dt, RiskAlert.created_at <= end_dt,
        ).order_by(RiskAlert.created_at.desc()).all()
        risk_labels = {"low": "低", "medium": "中", "high": "高", "urgent": "紧急"}
        status_labels = {"pending": "待处理", "viewed": "已查看", "processing": "处理中", "completed": "已完成", "closed": "已关闭"}
        for alert in alerts:
            student = db.query(User).filter(User.id == alert.student_id).first()
            class_ = db.query(Class).filter(Class.id == student.class_id).first() if student else None
            grade = db.query(Grade).filter(Grade.id == class_.grade_id).first() if class_ else None
            task = db.query(Task).filter(Task.id == alert.task_id).first() if alert.task_id else None
            qnr = db.query(Questionnaire).filter(Questionnaire.id == task.questionnaire_id).first() if task else None
            ws.append([
                student.real_name if student else "",
                grade.name if grade else "",
                class_.name if class_ else "",
                risk_labels.get(alert.risk_level, alert.risk_level),
                alert.risk_type or "",
                status_labels.get(alert.status, alert.status),
                alert.created_at.strftime("%Y-%m-%d %H:%M") if alert.created_at else "",
                qnr.title if qnr else "",
            ])
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[chr(64 + col)].width = 16

    elif report_type == "completion":
        ws = wb.active
        ws.title = "完成情况报表"
        headers = ["学生姓名", "年级", "班级", "任务名称", "状态", "提交时间"]
        ws.append(headers)
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

        sheets = db.query(AnswerSheet).join(Task).filter(
            Task.school_id == school_id,
            AnswerSheet.created_at >= start_dt, AnswerSheet.created_at <= end_dt,
        ).order_by(AnswerSheet.created_at.desc()).limit(500).all()
        status_labels = {"not_started": "未开始", "in_progress": "进行中", "submitted": "已提交"}
        for sheet in sheets:
            student = db.query(User).filter(User.id == sheet.student_id).first()
            task = db.query(Task).filter(Task.id == sheet.task_id).first()
            class_ = db.query(Class).filter(Class.id == student.class_id).first() if student else None
            grade = db.query(Grade).filter(Grade.id == class_.grade_id).first() if class_ else None
            ws.append([
                student.real_name if student else "",
                grade.name if grade else "",
                class_.name if class_ else "",
                task.name if task else "",
                status_labels.get(sheet.status, sheet.status),
                sheet.submitted_at.strftime("%Y-%m-%d %H:%M") if sheet.submitted_at else "",
            ])
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[chr(64 + col)].width = 18

    log_operation(db, user, request, module="export", action=f"export_{report_type}_report",
                  object_type="report", object_name=f"{report_type}_{now.strftime('%Y%m%d')}")

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"{report_type}_report_{now.strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
