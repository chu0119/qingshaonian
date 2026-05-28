from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_role
from ..models.external import SMSLog
from ..models.user import User
from ..services.audit_service import log_operation
from ..services.sms_service import DEFAULT_TEMPLATES, send_business_sms
from ..utils.access_control import can_access_student
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/sms", tags=["短信"])


@router.get("/templates")
def list_sms_templates(user: User = Depends(require_role("platform_admin", "school_admin", "teacher", "counselor"))):
    return APIResponse.success([{"code": code, "content": content} for code, content in DEFAULT_TEMPLATES.items()])


@router.get("/logs")
def list_sms_logs(user: User = Depends(require_role("platform_admin", "school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    q = db.query(SMSLog)
    if user.role != "platform_admin":
        q = q.filter(SMSLog.school_id == (getattr(user, '_effective_school_id', None) or user.school_id))
    if user.role in ("teacher", "counselor"):
        q = q.filter(SMSLog.sender_id == user.id)
    logs = q.order_by(SMSLog.id.desc()).limit(100).all()
    return APIResponse.success([{
        "id": log.id,
        "recipient_user_id": log.recipient_user_id,
        "recipient_name": log.recipient_name,
        "phone": log.phone,
        "school_id": log.school_id,
        "sms_type": log.sms_type,
        "template_code": log.template_code,
        "status": log.status,
        "failure_reason": log.failure_reason,
        "sender_id": log.sender_id,
        "sent_at": log.sent_at.isoformat() if log.sent_at else None,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    } for log in logs])


@router.post("/send")
def send_sms(data: dict, request: Request, user: User = Depends(require_role("platform_admin", "school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    recipient_id = data.get("recipient_user_id")
    if not recipient_id:
        raise HTTPException(status_code=400, detail="请选择短信接收人")
    recipient = db.query(User).filter(User.id == int(recipient_id)).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="接收人不存在")
    if user.role != "platform_admin" and recipient.school_id != (getattr(user, '_effective_school_id', None) or user.school_id):
        raise HTTPException(status_code=403, detail="不能给其他学校人员发送短信")
    if user.role in ("teacher", "counselor") and not (recipient.id == user.id or can_access_student(db, user, recipient)):
        raise HTTPException(status_code=403, detail="无权限给该人员发送短信")

    sms_type = data.get("sms_type", "task_publish")
    template_code = data.get("template_code", sms_type)
    log = send_business_sms(db, sender=user, recipient=recipient, sms_type=sms_type, template_code=template_code)
    log_operation(db, user=user, request=request, module="sms", action="send_business", object_type="sms_log", object_id=log.id, object_name=recipient.real_name, result=log.status)
    return APIResponse.success({"id": log.id, "status": log.status, "failure_reason": log.failure_reason}, message="短信发送请求已处理")


@router.post("/logs/{log_id}/retry")
def retry_sms(log_id: int, request: Request, user: User = Depends(require_role("platform_admin", "school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    old = db.query(SMSLog).filter(SMSLog.id == log_id).first()
    if not old:
        raise HTTPException(status_code=404, detail="短信记录不存在")
    recipient = db.query(User).filter(User.id == old.recipient_user_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="接收人不存在")
    if user.role != "platform_admin" and old.school_id != (getattr(user, '_effective_school_id', None) or user.school_id):
        raise HTTPException(status_code=403, detail="无权限重试该短信")
    if user.role in ("teacher", "counselor") and old.sender_id != user.id:
        raise HTTPException(status_code=403, detail="无权限重试该短信")
    new_log = send_business_sms(db, sender=user, recipient=recipient, sms_type=old.sms_type, template_code=old.template_code)
    log_operation(db, user=user, request=request, module="sms", action="retry", object_type="sms_log", object_id=new_log.id, object_name=recipient.real_name, result=new_log.status)
    return APIResponse.success({"id": new_log.id, "status": new_log.status, "failure_reason": new_log.failure_reason}, message="短信重试请求已处理")
