from fastapi import APIRouter, Depends, Body, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.external import SMSLog
from ..schemas.auth import LoginRequest, ChangePasswordRequest, ResetPasswordRequest, CaptchaResponse
from ..schemas.common import PaginationParams
from ..services import auth_service
from ..dependencies import get_current_user, require_role
from ..utils.response import APIResponse
from ..utils.password import hash_password
from ..utils.jwt import create_access_token
from ..services.audit_service import log_login, log_operation
import random, json, time

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])

# 内存验证码存储（重启丢失，但足够开发使用）
_verification_codes: dict = {}  # {phone: {"code":"123456","expires":1234567890,"purpose":"reset_pwd"}}
_sms_send_records: dict[str, list[float]] = {}


def _log_sms_code(db: Session, *, phone: str, purpose: str, status: str, failure_reason: str = "") -> None:
    db.add(SMSLog(
        recipient_name="",
        phone=phone,
        school_id=None,
        sms_type=f"verification_{purpose}",
        template_code="verification",
        content="验证码短信",
        status=status,
        failure_reason=failure_reason,
    ))
    db.commit()

def _generate_code() -> str:
    return str(random.randint(100000, 999999))


def _save_code(phone: str, username: str, purpose: str) -> str:
    code = _generate_code()
    key = f"{phone}:{username}"
    _verification_codes[key] = {
        "code": code,
        "expires": time.time() + 300,  # 5分钟有效期
        "purpose": purpose,
        "attempts": 0,
    }
    return code


def _verify_code(phone: str, username: str, code: str, purpose: str) -> bool:
    key = f"{phone}:{username}"
    stored = _verification_codes.get(key)
    if not stored:
        return False
    if stored["expires"] < time.time():
        del _verification_codes[key]
        return False
    if stored.get("attempts", 0) >= 5:
        del _verification_codes[key]
        return False
    stored["attempts"] = stored.get("attempts", 0) + 1
    if stored["code"] != code or stored["purpose"] != purpose:
        return False
    del _verification_codes[key]  # 一次性使用
    return True


@router.get("/captcha")
def get_captcha():
    """Generate a new image CAPTCHA. Returns base64 PNG + captcha_key."""
    result = auth_service.generate_captcha()
    return APIResponse.success(result)


@router.post("/login")
def login(request_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request_data.username).first()
    try:
        result = auth_service.authenticate(db, request_data, request)
        logged_user = db.query(User).filter(User.id == result.user.id).first() if result.user else user
        log_login(db, username=request_data.username, user=logged_user, request=request, result="success")
        return APIResponse.success(result.model_dump())
    except HTTPException as exc:
        # Extract structured detail for logging
        detail = exc.detail
        log_msg = detail.get("message", str(detail)) if isinstance(detail, dict) else str(detail)
        log_login(
            db,
            username=request_data.username,
            user=user,
            request=request,
            result="failure",
            failure_reason=log_msg,
        )
        raise


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return APIResponse.success(auth_service.get_user_info(user).model_dump())


@router.put("/change-password")
def change_password(request: ChangePasswordRequest, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_service.change_password(db, user, request.old_password, request.new_password)
    log_operation(db, user, http_request, module="auth", action="change_password",
                  object_type="user", object_id=user.id, object_name=user.real_name)
    return APIResponse.success(message="密码修改成功")


@router.put("/reset-password/{user_id}")
def reset_password(user_id: int, request_data: ResetPasswordRequest, request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.role == "platform_admin":
        raise HTTPException(status_code=403, detail="不能重置平台管理员密码")
    effective_school_id = getattr(user, '_effective_school_id', None) or user.school_id
    if target.school_id != effective_school_id:
        raise HTTPException(status_code=403, detail="只能重置本校用户密码")
    if not request_data.new_password or len(request_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="请提供至少6位的新密码")
    auth_service.reset_user_password(db, user_id, request_data.new_password)
    log_operation(db, user=user, request=request, module="auth", action="reset_password",
                  object_type="user", object_id=user_id, object_name=target.real_name,
                  detail=f"operator_school={effective_school_id}")
    return APIResponse.success(message="密码重置成功")


# ======================== 登出 / Token 刷新 / 二维码入口 ========================

@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    """登出（JWT 无状态，前端清除 token 即可）"""
    return APIResponse.success(message="登出成功")


@router.post("/refresh")
def refresh_token(user: User = Depends(get_current_user)):
    """刷新 token — 用当前有效 token 换取新 token"""
    new_token = create_access_token({"user_id": user.id, "role": user.role})
    return APIResponse.success({"access_token": new_token, "token_type": "bearer"})


@router.get("/qr-token")
def get_qr_token(task_id: int, db: Session = Depends(get_db)):
    """生成扫码进入测评的临时 token"""
    from ..models.task import Task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    token = create_access_token({"task_id": task_id, "purpose": "qr_entry"}, expires_minutes=30)
    return APIResponse.success({"token": token, "task_id": task_id, "task_name": task.name})


# ======================== 短信验证码 ========================

@router.post("/send-sms-code")
def send_sms_code(data: dict, request: Request, db: Session = Depends(get_db)):
    """发送短信验证码（用于重置密码或登录验证）"""
    phone = (data.get("phone") or "").strip()
    username = (data.get("username") or "").strip()
    purpose = data.get("purpose", "reset_password")

    if not phone or len(phone) < 11:
        raise HTTPException(status_code=400, detail="请输入正确的手机号")

    # 验证手机号是否属于该用户
    if username:
        user = db.query(User).filter(User.username == username).first()
        if not user or user.phone != phone:
            raise HTTPException(status_code=400, detail="手机号与账号不匹配")
    else:
        # 兼容：无 username 时检查手机号是否已注册
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            raise HTTPException(status_code=400, detail="该手机号未注册")
        username = user.username

    now = time.time()
    record_key = f"{phone}:{username}"
    recent_sends = [ts for ts in _sms_send_records.get(record_key, []) if now - ts < 3600]
    if len(recent_sends) >= 5:
        raise HTTPException(status_code=429, detail="验证码发送过于频繁，请稍后再试")

    # 频率限制：60秒内不能重复发送
    code_key = f"{phone}:{username}"
    stored = _verification_codes.get(code_key)
    if stored and stored["expires"] - 300 + 60 > now:
        remaining = int(stored["expires"] - 300 + 60 - now)
        raise HTTPException(status_code=429, detail=f"请{remaining}秒后再试")

    # 检查短信配置
    from ..models.system_config import SystemConfig
    from ..config import settings

    # 如果平台管理员显式关闭了短信服务，直接拒绝
    sms_enabled_config = db.query(SystemConfig).filter(SystemConfig.config_key == "sms_enabled", SystemConfig.school_id.is_(None)).first()
    if sms_enabled_config and sms_enabled_config.config_value == "false":
        raise HTTPException(status_code=400, detail="短信服务已被管理员关闭")

    # 检查短信是否已配置（新配置格式：sms_app_key + sms_sdk_app_id）
    sms_key_config = db.query(SystemConfig).filter(SystemConfig.config_key == "sms_app_key", SystemConfig.school_id.is_(None)).first()
    sms_app_id_config = db.query(SystemConfig).filter(SystemConfig.config_key == "sms_sdk_app_id", SystemConfig.school_id.is_(None)).first()
    sms_key = settings.SMS_APP_KEY or (sms_key_config.config_value if sms_key_config else "")
    sms_app_id = settings.SMS_SDK_APP_ID or (sms_app_id_config.config_value if sms_app_id_config else "")

    if not sms_key or not sms_app_id:
        if settings.DEBUG:
            code = _save_code(phone, username, purpose)
            recent_sends.append(now)
            _sms_send_records[record_key] = recent_sends
            _log_sms_code(db, phone=phone, purpose=purpose, status="not_configured", failure_reason="短信服务暂未配置，调试模式返回验证码")
            log_operation(
                db,
                user=None,
                request=request,
                module="sms",
                action="send_code",
                object_type="phone",
                object_id=phone[-4:],
                result="success",
                detail="debug code returned; sms service not configured",
            )
            return APIResponse.success({"message": "验证码已发送", "sms_sent": False})

        _log_sms_code(db, phone=phone, purpose=purpose, status="not_configured", failure_reason="短信服务暂未配置")
        log_operation(
            db,
            user=None,
            request=request,
            module="sms",
            action="send_code",
            object_type="phone",
            object_id=phone[-4:],
            result="failure",
            detail="sms service not configured",
        )
        return APIResponse.success({"message": "短信服务暂未配置", "sms_sent": False})

    code = _save_code(phone, username, purpose)
    recent_sends.append(now)
    _sms_send_records[record_key] = recent_sends

    # 到这里说明短信已配置（sms_key + sms_app_id 均非空），实际发送验证码
    from ..services.sms_service import send_verification_code
    sms_sent = False
    failure_reason = ""
    try:
        sms_sent, failure_reason = send_verification_code(db, phone=phone, code=code)
    except Exception as exc:
        sms_sent = False
        failure_reason = str(exc)[:300]
    _log_sms_code(
        db,
        phone=phone,
        purpose=purpose,
        status="sent" if sms_sent else "failed",
        failure_reason="" if sms_sent else (failure_reason or "短信发送失败"),
    )

    log_operation(
        db,
        user=None,
        request=request,
        module="sms",
        action="send_code",
        object_type="phone",
        object_id=phone[-4:],
        result="success" if sms_sent else "failure",
        detail="" if sms_sent else "sms provider returned failure or request failed",
    )

    return APIResponse.success({"message": "验证码已发送" if sms_sent else "短信发送失败，请稍后重试", "sms_sent": sms_sent})


@router.post("/verify-sms-code")
def verify_sms_code(data: dict):
    """校验短信验证码"""
    phone = (data.get("phone") or "").strip()
    username = (data.get("username") or "").strip()
    code = (data.get("code") or "").strip()
    purpose = data.get("purpose", "reset_password")

    if not phone or not code or not username:
        raise HTTPException(status_code=400, detail="手机号、账号和验证码不能为空")

    valid = _verify_code(phone, username, code, purpose)
    if not valid:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    return APIResponse.success({"message": "验证通过", "verified": True})


@router.post("/reset-password-by-sms")
def reset_password_by_sms(data: dict, db: Session = Depends(get_db)):
    """通过短信验证码重置密码"""
    phone = (data.get("phone") or "").strip()
    code = (data.get("code") or "").strip()
    new_password = (data.get("new_password") or "").strip()
    username = (data.get("username") or "").strip()

    if not phone or not code or not new_password or not username:
        raise HTTPException(status_code=400, detail="请填写完整信息")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")

    # 校验验证码（使用复合 key）
    if not _verify_code(phone, username, code, "reset_password"):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 查找用户
    user = db.query(User).filter(User.username == username, User.phone == phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="未找到匹配的用户，请检查账号和手机号")

    if not user.status:
        raise HTTPException(status_code=403, detail="账号已被禁用，无法重置密码")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()

    return APIResponse.success(message="密码重置成功，请使用新密码登录")
