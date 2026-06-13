"""短信发送服务 — 对接腾讯云短信 SDK

配置优先级：环境变量 > system_configs 表（school_id=NULL）> 默认值
腾讯云短信要求使用模板 + 签名发送，不能发任意内容。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from ..config import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

SENSITIVE_WORDS = ("高风险学生", "心理异常", "心理疾病", "确诊")

# ==================== 短信模板定义 ====================

DEFAULT_TEMPLATES: dict[str, dict] = {
    "verification": {
        "code": "verification",
        "name": "验证码",
        "content": "您的验证码是{1}，5分钟内有效，请勿泄露。",
        "params": ["验证码"],
        "category": "系统通知",
    },
    "task_publish": {
        "code": "task_publish",
        "name": "任务通知",
        "content": "{1}您好，学校发布了新的心理测评任务，请在规定时间内完成。",
        "params": ["姓名"],
        "category": "任务通知",
    },
    "unfinished_reminder": {
        "code": "unfinished_reminder",
        "name": "未完成提醒",
        "content": "{1}您好，您还有心理测评问卷未完成，请合理安排时间完成。",
        "params": ["姓名"],
        "category": "任务通知",
    },
    "password_reset": {
        "code": "password_reset",
        "name": "密码重置",
        "content": "{1}您好，您的平台账号密码已重置，请及时登录并修改密码。",
        "params": ["姓名"],
        "category": "系统通知",
    },
    "risk_reminder": {
        "code": "risk_reminder",
        "name": "风险关注",
        "content": "{1}您好，有学生关怀事项需要您及时查看并跟进。",
        "params": ["姓名"],
        "category": "风险通知",
    },
    "intervention_followup": {
        "code": "intervention_followup",
        "name": "干预跟进",
        "content": "{1}您好，您有学生关怀跟进事项待处理，请及时查看。",
        "params": ["姓名"],
        "category": "风险通知",
    },
}

TEMPLATE_NAMES = {code: tpl["name"] for code, tpl in DEFAULT_TEMPLATES.items()}


# ==================== 配置读取 ====================


def _get_config(db: Session, key: str, env_value: str = "") -> str:
    """从 system_configs 表读取配置，环境变量优先"""
    if env_value:
        return env_value
    from ..models.system_config import SystemConfig
    config = (
        db.query(SystemConfig)
        .filter(SystemConfig.config_key == key, SystemConfig.school_id.is_(None))
        .first()
    )
    return (config.config_value or "") if config else ""


def get_sms_config(db: Session) -> dict:
    """获取完整短信配置"""
    templates_json = _get_config(db, "sms_templates", "{}")
    try:
        templates = json.loads(templates_json) if templates_json else {}
    except (json.JSONDecodeError, TypeError):
        templates = {}

    return {
        "enabled": _get_config(db, "sms_enabled", str(settings.SMS_ENABLED).lower()),
        "provider": _get_config(db, "sms_provider", settings.SMS_PROVIDER),
        "secret_id": _get_config(db, "sms_app_key", settings.SMS_APP_KEY),
        "secret_key": _get_config(db, "sms_app_secret", settings.SMS_APP_SECRET),
        "sign_name": _get_config(db, "sms_sign_name", settings.SMS_SIGN_NAME),
        "sdk_app_id": _get_config(db, "sms_sdk_app_id", settings.SMS_SDK_APP_ID),
        "api_url": _get_config(db, "sms_api_url", settings.SMS_API_URL),
        "templates": templates,
    }


def get_template_id(config: dict, template_code: str) -> str:
    """根据模板code获取腾讯云模板ID"""
    return config.get("templates", {}).get(template_code, "")


# ==================== 腾讯云 SDK 发送 ====================


def _build_tencent_client(config: dict):
    """构建腾讯云短信客户端"""
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.sms.v20210111 import sms_client

    cred = credential.Credential(config["secret_id"], config["secret_key"])
    http_profile = HttpProfile()
    http_profile.endpoint = "sms.tencentcloudapi.com"
    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    return sms_client.SmsClient(cred, "ap-guangzhou", client_profile)


def _send_tencent_sms(
    config: dict,
    phone: str,
    template_id: str,
    template_params: list[str],
) -> tuple[bool, str]:
    """通过腾讯云 SDK 发送模板短信"""
    if not config.get("secret_id") or not config.get("secret_key"):
        return False, "短信服务密钥未配置（SecretId/SecretKey）"
    if not config.get("sdk_app_id"):
        return False, "短信应用 SDKAppID 未配置"
    if not template_id:
        return False, f"短信模板ID未配置（请在系统设置中配置对应模板的腾讯云模板ID）"
    if not config.get("sign_name"):
        return False, "短信签名未配置"

    try:
        client = _build_tencent_client(config)
        from tencentcloud.sms.v20210111 import models

        req = models.SendSmsRequest()
        req.SmsSdkAppId = config["sdk_app_id"]
        req.SignName = config["sign_name"]
        req.TemplateId = template_id
        phone_formatted = phone if phone.startswith("+86") else f"+86{phone}"
        req.PhoneNumberSet = [phone_formatted]
        req.TemplateParamSet = template_params

        response = client.SendSms(req)

        if response.SendStatusSet:
            status = response.SendStatusSet[0]
            if status.Code == "Ok":
                return True, ""
            else:
                return False, f"[{status.Code}] {status.Message}"
        return False, "腾讯云未返回发送状态"

    except Exception as exc:
        logger.exception("腾讯云短信发送异常")
        return False, str(exc)[:300]


# ==================== 对外发送接口 ====================


def render_sms_content(template_code: str, **kwargs) -> str:
    """渲染短信模板内容（用于日志记录）"""
    tpl = DEFAULT_TEMPLATES.get(template_code)
    template = tpl["content"] if tpl else DEFAULT_TEMPLATES["task_publish"]["content"]
    try:
        content = template.format(**kwargs)
    except KeyError:
        content = template
    if any(word in content for word in SENSITIVE_WORDS):
        raise ValueError("短信内容包含不适合发送的敏感表述")
    return content


def send_verification_code(
    db: Session,
    *,
    phone: str,
    code: str,
) -> tuple[bool, str]:
    """发送验证码短信"""
    from ..models.external import SMSLog

    config = get_sms_config(db)
    if config["enabled"] != "true":
        return False, "短信服务未启用，请在系统设置中开启"

    template_code = "verification"
    tencent_template_id = get_template_id(config, template_code)
    content = render_sms_content(template_code, code=code)

    success, reason = _send_tencent_sms(config, phone, tencent_template_id, [code])

    db.add(SMSLog(
        recipient_name="",
        phone=phone,
        school_id=None,
        sms_type="verification",
        template_code=template_code,
        content=content,
        status="sent" if success else "failed",
        failure_reason=reason,
        sender_id=None,
        sent_at=datetime.now() if success else None,
    ))
    db.commit()

    return success, reason


def send_business_sms(
    db: Session,
    *,
    sender,
    recipient,
    sms_type: str,
    template_code: str,
    template_params: list[str] | None = None,
):
    """发送业务短信（任务通知、提醒等）"""
    from ..models.external import SMSLog
    from ..models.user import User as UserType

    recipient: UserType = recipient

    if not recipient.phone:
        log = SMSLog(
            recipient_user_id=recipient.id,
            recipient_name=recipient.real_name,
            phone="",
            school_id=recipient.school_id,
            sms_type=sms_type,
            template_code=template_code,
            content=f"[{template_code}]",
            status="failed",
            failure_reason="接收人未配置手机号",
            sender_id=sender.id if sender else None,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    config = get_sms_config(db)
    name = recipient.real_name or recipient.username

    try:
        content = render_sms_content(template_code, name=name)
    except Exception:
        content = f"[{template_code}]"

    if config["enabled"] != "true":
        log = SMSLog(
            recipient_user_id=recipient.id,
            recipient_name=name,
            phone=recipient.phone,
            school_id=recipient.school_id,
            sms_type=sms_type,
            template_code=template_code,
            content=content,
            status="not_configured",
            failure_reason="短信服务未启用，请在系统设置中开启",
            sender_id=sender.id if sender else None,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    tencent_template_id = get_template_id(config, template_code)
    params = [name]
    if template_params:
        params.extend(template_params)

    success, reason = _send_tencent_sms(config, recipient.phone, tencent_template_id, params)

    if not success and "模板ID未配置" in reason:
        status = "not_configured"
    elif not success:
        status = "failed"
    else:
        status = "sent"

    log = SMSLog(
        recipient_user_id=recipient.id,
        recipient_name=name,
        phone=recipient.phone,
        school_id=recipient.school_id,
        sms_type=sms_type,
        template_code=template_code,
        content=content,
        status=status,
        failure_reason=reason,
        sender_id=sender.id if sender else None,
        sent_at=datetime.now() if success else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def send_custom_sms(
    db: Session,
    *,
    sender,
    phone: str,
    content: str,
    sms_type: str = "platform_urge",
    template_code: str = "task_publish",
) -> tuple[bool, str]:
    """平台管理员手动发送短信

    使用指定模板，将自定义内容作为模板变量传入。
    腾讯云模板 {1} = 第一个参数（姓名/内容），{2} = 第二个参数。

    Returns:
        (success, error_message)
    """
    from ..models.external import SMSLog

    config = get_sms_config(db)
    if config["enabled"] != "true":
        return False, "短信服务未启用，请在平台管理端开启"

    tencent_template_id = get_template_id(config, template_code)
    # 将自定义内容作为模板的第一个参数 {1}
    success, reason = _send_tencent_sms(config, phone, tencent_template_id, [content])

    db.add(SMSLog(
        recipient_name="",
        phone=phone,
        school_id=None,
        sms_type=sms_type,
        template_code=template_code,
        content=content,
        status="sent" if success else "failed",
        failure_reason=reason,
        sender_id=sender.id if sender else None,
        sent_at=datetime.now() if success else None,
    ))
    db.commit()

    return success, reason
