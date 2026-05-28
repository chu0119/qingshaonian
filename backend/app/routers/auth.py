from fastapi import APIRouter, Depends, Body, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.external import SMSLog
from ..schemas.auth import LoginRequest, ChangePasswordRequest, ResetPasswordRequest
from ..schemas.common import PaginationParams
from ..services import auth_service
from ..dependencies import get_current_user, require_role
from ..utils.response import APIResponse
from ..utils.password import hash_password
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


def _save_code(phone: str, purpose: str) -> str:
    code = _generate_code()
    _verification_codes[phone] = {
        "code": code,
        "expires": time.time() + 300,  # 5分钟有效期
        "purpose": purpose,
        "attempts": 0,
    }
    return code


def _verify_code(phone: str, code: str, purpose: str) -> bool:
    stored = _verification_codes.get(phone)
    if not stored:
        return False
    if stored["expires"] < time.time():
        del _verification_codes[phone]
        return False
    if stored.get("attempts", 0) >= 5:
        del _verification_codes[phone]
        return False
    stored["attempts"] = stored.get("attempts", 0) + 1
    if stored["code"] != code or stored["purpose"] != purpose:
        return False
    del _verification_codes[phone]  # 一次性使用
    return True


@router.post("/login")
def login(request_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request_data.username).first()
    try:
        result = auth_service.authenticate(db, request_data)
        logged_user = db.query(User).filter(User.id == result.user.id).first() if result.user else user
        log_login(db, username=request_data.username, user=logged_user, request=request, result="success")
        return APIResponse.success(result.model_dump())
    except HTTPException as exc:
        log_login(
            db,
            username=request_data.username,
            user=user,
            request=request,
            result="failure",
            failure_reason=str(exc.detail),
        )
        raise


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return APIResponse.success(auth_service.get_user_info(user).model_dump())


@router.put("/change-password")
def change_password(request: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_service.change_password(db, user, request.old_password, request.new_password)
    return APIResponse.success(message="密码修改成功")


@router.put("/reset-password/{user_id}")
def reset_password(user_id: int, request_data: ResetPasswordRequest, request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.role == "platform_admin":
        raise HTTPException(status_code=403, detail="不能重置平台管理员密码")
    if target.school_id != user.school_id:
        raise HTTPException(status_code=403, detail="只能重置本校用户密码")
    auth_service.reset_user_password(db, user_id, request_data.new_password)
    log_operation(db, user=user, request=request, module="auth", action="reset_password",
                  object_type="user", object_id=user_id, object_name=target.real_name,
                  detail=f"operator_school={user.school_id}")
    return APIResponse.success(message="密码重置成功")


# ======================== 短信验证码 ========================

@router.post("/send-sms-code")
def send_sms_code(data: dict, request: Request, db: Session = Depends(get_db)):
    """发送短信验证码（用于重置密码或登录验证）"""
    phone = (data.get("phone") or "").strip()
    purpose = data.get("purpose", "reset_password")

    if not phone or len(phone) < 11:
        raise HTTPException(status_code=400, detail="请输入正确的手机号")

    now = time.time()
    recent_sends = [ts for ts in _sms_send_records.get(phone, []) if now - ts < 3600]
    if len(recent_sends) >= 5:
        raise HTTPException(status_code=429, detail="验证码发送过于频繁，请稍后再试")

    # 频率限制：60秒内不能重复发送
    stored = _verification_codes.get(phone)
    if stored and stored["expires"] - 300 + 60 > now:
        remaining = int(stored["expires"] - 300 + 60 - now)
        raise HTTPException(status_code=429, detail=f"请{remaining}秒后再试")

    # 检查短信配置
    from ..models.system_config import SystemConfig
    from ..config import settings

    # 如果配置了短信API，尝试真实发送
    sms_sent = False
    sms_url_config = db.query(SystemConfig).filter(SystemConfig.config_key == "sms_api_url", SystemConfig.school_id.is_(None)).first()
    sms_key_config = db.query(SystemConfig).filter(SystemConfig.config_key == "sms_app_key", SystemConfig.school_id.is_(None)).first()
    sms_url = settings.SMS_API_URL or (sms_url_config.config_value if sms_url_config else "")
    sms_key = settings.SMS_APP_KEY or (sms_key_config.config_value if sms_key_config else "")

    if not sms_url or not sms_key:
        if settings.DEBUG:
            code = _save_code(phone, purpose)
            recent_sends.append(now)
            _sms_send_records[phone] = recent_sends
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
            return APIResponse.success({"message": "验证码已发送", "code": code, "phone": phone, "sms_sent": False})

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

    code = _save_code(phone, purpose)
    recent_sends.append(now)
    _sms_send_records[phone] = recent_sends

    if sms_url and sms_key:
        failure_reason = ""
        try:
            import httpx
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    sms_url,
                    json={"phone": phone, "code": code, "template_id": "verification"},
                    headers={"Authorization": f"Bearer {sms_key}"},
                )
                sms_sent = resp.status_code == 200
                if not sms_sent:
                    failure_reason = f"短信服务返回 HTTP {resp.status_code}"
        except Exception as exc:
            failure_reason = str(exc)[:300]  # 短信发送失败不阻塞流程，开发模式下验证码仍可用
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

    # 开发模式：返回验证码；生产环境绝不返回验证码。
    if settings.DEBUG:
        return APIResponse.success({"message": "验证码已发送", "code": code, "phone": phone, "sms_sent": sms_sent})

    return APIResponse.success({"message": "验证码已发送" if sms_sent else "短信发送失败，请稍后重试", "sms_sent": sms_sent})


@router.post("/verify-sms-code")
def verify_sms_code(data: dict):
    """校验短信验证码"""
    phone = (data.get("phone") or "").strip()
    code = (data.get("code") or "").strip()
    purpose = data.get("purpose", "reset_password")

    if not phone or not code:
        raise HTTPException(status_code=400, detail="手机号和验证码不能为空")

    valid = _verify_code(phone, code, purpose)
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

    # 校验验证码
    if not _verify_code(phone, code, "reset_password"):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 查找用户
    user = db.query(User).filter(User.username == username, User.phone == phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="未找到匹配的用户，请检查账号和手机号")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()

    return APIResponse.success(message="密码重置成功，请使用新密码登录")
