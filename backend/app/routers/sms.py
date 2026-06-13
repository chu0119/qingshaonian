"""短信管理路由"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..dependencies import require_role
from ..models.external import SMSLog
from ..models.user import User
from ..services.audit_service import log_operation
from ..services.sms_service import (
    DEFAULT_TEMPLATES, TEMPLATE_NAMES,
    send_business_sms, send_custom_sms, get_sms_config,
)
from ..utils.validators import mask_phone
from ..utils.access_control import can_access_student
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/sms", tags=["短信"])


@router.get("/config")
def get_sms_config_view(user: User = Depends(require_role("platform_admin", "school_admin")), db: Session = Depends(get_db)):
    """获取短信配置状态"""
    config = get_sms_config(db)
    return APIResponse.success({
        "enabled": config["enabled"] == "true",
        "provider": config["provider"],
        "has_secret": bool(config.get("secret_id")),
        "has_app_id": bool(config.get("sdk_app_id")),
        "has_sign": bool(config.get("sign_name")),
        "templates_configured": {code: bool(config["templates"].get(code)) for code in DEFAULT_TEMPLATES},
    })


@router.get("/templates")
def list_sms_templates(user: User = Depends(require_role("platform_admin", "school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    """获取短信模板列表（含配置状态）"""
    config = get_sms_config(db)
    templates = []
    for code, tpl in DEFAULT_TEMPLATES.items():
        templates.append({
            "code": code,
            "name": tpl["name"],
            "content": tpl["content"],
            "params": tpl["params"],
            "category": tpl["category"],
            "template_id_configured": bool(config["templates"].get(code)),
            "tencent_template_id": config["templates"].get(code, ""),
        })
    return APIResponse.success(templates)


@router.get("/logs")
def list_sms_logs(
    page: int = Query(1),
    page_size: int = Query(20),
    status: str = Query(""),
    sms_type: str = Query(""),
    keyword: str = Query(""),
    user: User = Depends(require_role("platform_admin", "school_admin", "teacher", "counselor")),
    db: Session = Depends(get_db),
):
    """获取短信发送记录"""
    q = db.query(SMSLog)
    if user.role != "platform_admin":
        q = q.filter(SMSLog.school_id == (getattr(user, '_effective_school_id', None) or user.school_id))
    if user.role in ("teacher", "counselor"):
        q = q.filter(SMSLog.sender_id == user.id)
    if status:
        q = q.filter(SMSLog.status == status)
    if sms_type:
        q = q.filter(SMSLog.sms_type == sms_type)
    if keyword:
        q = q.filter(SMSLog.phone.contains(keyword) | SMSLog.recipient_name.contains(keyword))

    total = q.count()
    logs = q.order_by(SMSLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "recipient_user_id": log.recipient_user_id,
            "recipient_name": log.recipient_name,
            "phone": mask_phone(log.phone),
            "school_id": log.school_id,
            "sms_type": log.sms_type,
            "template_code": log.template_code,
            "content": log.content,
            "status": log.status,
            "failure_reason": log.failure_reason,
            "sender_id": log.sender_id,
            "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return APIResponse.success({"items": items, "total": total, "page": page, "page_size": page_size})


@router.get("/stats")
def sms_stats(user: User = Depends(require_role("platform_admin", "school_admin")), db: Session = Depends(get_db)):
    """短信发送统计"""
    q = db.query(SMSLog)
    if user.role != "platform_admin":
        q = q.filter(SMSLog.school_id == (getattr(user, '_effective_school_id', None) or user.school_id))

    total = q.count()
    sent = q.filter(SMSLog.status == "sent").count()
    failed = q.filter(SMSLog.status == "failed").count()
    not_configured = q.filter(SMSLog.status == "not_configured").count()

    config = get_sms_config(db)
    return APIResponse.success({
        "total": total,
        "sent": sent,
        "failed": failed,
        "not_configured": not_configured,
        "sms_enabled": config["enabled"] == "true",
    })


@router.post("/send")
def send_sms(
    data: dict,
    request: Request,
    user: User = Depends(require_role("platform_admin", "school_admin", "teacher", "counselor")),
    db: Session = Depends(get_db),
):
    """发送短信给指定用户"""
    recipient_id = data.get("recipient_user_id")
    template_code = data.get("template_code", "task_publish")
    custom_content = data.get("content", "")

    if not recipient_id:
        raise HTTPException(status_code=400, detail="请选择短信接收人")

    recipient = db.query(User).filter(User.id == int(recipient_id)).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="接收人不存在")
    if user.role != "platform_admin" and recipient.school_id != (getattr(user, '_effective_school_id', None) or user.school_id):
        raise HTTPException(status_code=403, detail="不能给其他学校人员发送短信")
    if user.role in ("teacher", "counselor") and not (recipient.id == user.id or can_access_student(db, user, recipient)):
        raise HTTPException(status_code=403, detail="无权限给该人员发送短信")

    if template_code and template_code not in DEFAULT_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"未知的短信模板: {template_code}")

    log = send_business_sms(
        db, sender=user, recipient=recipient,
        sms_type=template_code, template_code=template_code,
    )

    log_operation(db, user=user, request=request, module="sms", action="send",
                  object_type="sms_log", object_id=log.id,
                  object_name=recipient.real_name, result=log.status)

    return APIResponse.success({
        "id": log.id, "status": log.status,
        "failure_reason": log.failure_reason,
    }, message="短信发送请求已处理")


@router.post("/send-custom")
def send_custom(
    data: dict,
    request: Request,
    user: User = Depends(require_role("platform_admin", "school_admin")),
    db: Session = Depends(get_db),
):
    """手动发送自定义短信"""
    phone = data.get("phone", "").strip()
    content = data.get("content", "").strip()
    template_code = data.get("template_code", "task_publish")

    if not phone:
        raise HTTPException(status_code=400, detail="请输入手机号")
    if not content:
        raise HTTPException(status_code=400, detail="请输入短信内容")

    success, reason = send_custom_sms(
        db, sender=user, phone=phone, content=content,
        sms_type="platform_urge", template_code=template_code,
    )

    log_operation(db, user=user, request=request, module="sms", action="send_custom",
                  object_type="sms", object_id=phone[-4:],
                  result="success" if success else "failure")

    if not success:
        return APIResponse.success({"success": False, "reason": reason}, message=f"发送失败: {reason}")
    return APIResponse.success({"success": True}, message="短信发送成功")


@router.post("/batch-send")
def batch_send_sms(
    data: dict,
    request: Request,
    user: User = Depends(require_role("platform_admin", "school_admin")),
    db: Session = Depends(get_db),
):
    """批量发送短信（给未完成任务的学生/给风险学生的教师）"""
    sms_type = data.get("type", "")
    task_id = data.get("task_id")

    if sms_type == "batch_uncompleted" and task_id:
        # 批量提醒未完成任务的学生
        from ..models.task import Task, AnswerSheet
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 获取目标学生
        from ..services.stats_service import target_student_ids
        all_student_ids = target_student_ids(db, task)
        completed_ids = {s.student_id for s in db.query(AnswerSheet.student_id).filter(
            AnswerSheet.task_id == task_id, AnswerSheet.status == "submitted").all()}
        pending_ids = [sid for sid in all_student_ids if sid not in completed_ids]

        if not pending_ids:
            return APIResponse.success({"sent": 0, "failed": 0, "skipped": 0}, message="没有需要提醒的学生")

        sent_count = 0
        failed_count = 0
        skipped_count = 0
        for sid in pending_ids[:50]:  # 限制最多50人
            student = db.query(User).filter(User.id == sid).first()
            if not student or not student.phone:
                skipped_count += 1
                continue
            try:
                from ..services.sms_service import send_business_sms
                log = send_business_sms(
                    db, sender=user, recipient=student,
                    sms_type="unfinished_reminder", template_code="unfinished_reminder",
                )
                if log.status == "sent":
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1

        log_operation(db, user=user, request=request, module="platform_sms", action="batch_send",
                      object_type="task", object_id=task_id,
                      detail=f"sent={sent_count};failed={failed_count};skipped={skipped_count}")

        return APIResponse.success({
            "sent": sent_count, "failed": failed_count, "skipped": skipped_count,
        }, message=f"批量发送完成：成功{sent_count}条，失败{failed_count}条，跳过{skipped_count}条")

    raise HTTPException(status_code=400, detail="不支持的批量发送类型")


@router.post("/logs/{log_id}/retry")
def retry_sms(
    log_id: int,
    request: Request,
    user: User = Depends(require_role("platform_admin", "school_admin", "teacher", "counselor")),
    db: Session = Depends(get_db),
):
    """重试失败的短信"""
    old = db.query(SMSLog).filter(SMSLog.id == log_id).first()
    if not old:
        raise HTTPException(status_code=404, detail="短信记录不存在")
    recipient = db.query(User).filter(User.id == old.recipient_user_id).first() if old.recipient_user_id else None
    if not recipient:
        raise HTTPException(status_code=404, detail="接收人不存在")
    if user.role != "platform_admin" and old.school_id != (getattr(user, '_effective_school_id', None) or user.school_id):
        raise HTTPException(status_code=403, detail="无权限重试该短信")
    if user.role in ("teacher", "counselor") and old.sender_id != user.id:
        raise HTTPException(status_code=403, detail="无权限重试该短信")

    new_log = send_business_sms(
        db, sender=user, recipient=recipient,
        sms_type=old.sms_type, template_code=old.template_code or "task_publish",
    )
    log_operation(db, user=user, request=request, module="sms", action="retry",
                  object_type="sms_log", object_id=new_log.id,
                  object_name=recipient.real_name, result=new_log.status)

    return APIResponse.success({
        "id": new_log.id, "status": new_log.status, "failure_reason": new_log.failure_reason,
    }, message="短信重试请求已处理")


@router.post("/test")
def test_sms(
    data: dict,
    request: Request,
    user: User = Depends(require_role("platform_admin", "school_admin")),
    db: Session = Depends(get_db),
):
    """测试短信发送 — 发送一条测试短信到指定手机号"""
    phone = data.get("phone", "").strip()
    template_code = data.get("template_code", "verification")

    if not phone:
        raise HTTPException(status_code=400, detail="请输入测试手机号")
    if not phone.startswith("1") or len(phone) != 11:
        raise HTTPException(status_code=400, detail="请输入正确的11位手机号")

    # 检查短信配置
    config = get_sms_config(db)
    if config["enabled"] != "true":
        raise HTTPException(status_code=400, detail="短信服务未启用，请先在系统设置中启用")
    if not config.get("secret_id"):
        raise HTTPException(status_code=400, detail="短信 SecretId 未配置")
    if not config.get("sdk_app_id"):
        raise HTTPException(status_code=400, detail="短信 SDKAppID 未配置")
    if not config.get("sign_name"):
        raise HTTPException(status_code=400, detail="短信签名未配置")

    from ..services.sms_service import _send_tencent_sms, get_template_id, render_sms_content

    tencent_template_id = get_template_id(config, template_code)

    # 根据模板类型生成测试参数
    test_params_map = {
        "verification": ["123456"],
        "task_publish": ["测试用户"],
        "unfinished_reminder": ["测试用户"],
        "password_reset": ["测试用户"],
        "risk_reminder": ["测试用户"],
        "intervention_followup": ["测试用户"],
    }
    test_params = test_params_map.get(template_code, ["测试用户"])

    # 渲染测试内容用于日志
    try:
        content = render_sms_content(template_code, code="123456", name="测试用户")
    except Exception:
        content = f"[测试] {template_code}"

    success, reason = _send_tencent_sms(config, phone, tencent_template_id, test_params)

    # 记录测试发送日志
    from ..models.external import SMSLog
    log = SMSLog(
        recipient_user_id=None,
        recipient_name="测试发送",
        phone=phone,
        school_id=getattr(user, '_effective_school_id', None) or user.school_id,
        sms_type="test",
        template_code=template_code,
        content=content,
        status="sent" if success else "failed",
        failure_reason=reason,
        sender_id=user.id,
        sent_at=datetime.now() if success else None,
    )
    db.add(log)
    db.commit()

    log_operation(db, user=user, request=request, module="sms", action="test_send",
                  object_type="sms", object_id=phone[-4:],
                  result="success" if success else "failure",
                  detail=f"template={template_code};phone={phone[-4:]}")

    if success:
        return APIResponse.success({"success": True, "message": f"测试短信已发送到 {phone[:3]}****{phone[7:]}"})
    else:
        return APIResponse.success({"success": False, "message": f"发送失败: {reason}"})
