from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models.external import SMSLog
from ..models.system_config import SystemConfig
from ..models.user import User

SENSITIVE_WORDS = ("高风险学生", "心理异常", "心理疾病", "确诊")

DEFAULT_TEMPLATES = {
    "account_open": "您好，{name}，您的学校平台账号已开通，请及时登录并修改初始密码。",
    "password_reset": "您好，{name}，您的平台账号密码已重置，请及时登录并修改密码。",
    "task_publish": "您好，{name}，学校发布了新的问卷任务，请在规定时间内完成。",
    "unfinished_reminder": "您好，{name}，您还有问卷任务未完成，请合理安排时间完成。",
    "risk_teacher_reminder": "您好，{name}，有学生关怀事项需要您及时查看并跟进。",
    "intervention_followup": "您好，{name}，您有学生关怀跟进事项待处理，请及时查看。",
}


def render_sms_content(template_code: str, recipient: User) -> str:
    template = DEFAULT_TEMPLATES.get(template_code, DEFAULT_TEMPLATES.get("task_publish", "您好，{name}，您有新的平台通知。"))
    content = template.format(name=recipient.real_name or recipient.username)
    if any(word in content for word in SENSITIVE_WORDS):
        raise ValueError("短信内容包含不适合发送的敏感表述")
    return content


def get_sms_provider_config(db: Session) -> tuple[str, str]:
    url = settings.SMS_API_URL
    key = settings.SMS_APP_KEY
    if url and key:
        return url, key
    configs = db.query(SystemConfig).filter(SystemConfig.config_key.in_(["sms_api_url", "sms_app_key"]), SystemConfig.school_id.is_(None)).all()
    values = {c.config_key: c.config_value or "" for c in configs}
    return values.get("sms_api_url", ""), values.get("sms_app_key", "")


def send_business_sms(
    db: Session,
    *,
    sender: User | None,
    recipient: User,
    sms_type: str,
    template_code: str,
) -> SMSLog:
    if not recipient.phone:
        log = SMSLog(
            recipient_user_id=recipient.id,
            recipient_name=recipient.real_name,
            phone="",
            school_id=recipient.school_id,
            sms_type=sms_type,
            template_code=template_code,
            status="failed",
            failure_reason="接收人未配置手机号",
            sender_id=sender.id if sender else None,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    content = render_sms_content(template_code, recipient)
    url, key = get_sms_provider_config(db)
    status = "not_configured"
    failure_reason = "短信服务暂未配置"
    sent_at = None

    if url and key:
        try:
            resp = httpx.post(
                url,
                json={"phone": recipient.phone, "content": content, "type": sms_type, "template": template_code},
                headers={"Authorization": f"Bearer {key}"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                status = "sent"
                failure_reason = ""
                sent_at = datetime.now()
            else:
                status = "failed"
                failure_reason = f"短信服务返回 HTTP {resp.status_code}"
        except Exception as exc:
            status = "failed"
            failure_reason = str(exc)[:300]

    log = SMSLog(
        recipient_user_id=recipient.id,
        recipient_name=recipient.real_name,
        phone=recipient.phone,
        school_id=recipient.school_id,
        sms_type=sms_type,
        template_code=template_code,
        content=content,
        status=status,
        failure_reason=failure_reason,
        sender_id=sender.id if sender else None,
        sent_at=sent_at,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
