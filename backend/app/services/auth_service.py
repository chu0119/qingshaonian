import time
import uuid
import random
import base64
from datetime import datetime, timedelta, timezone
from io import BytesIO

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from ..models.user import User
from ..utils.password import verify_password, hash_password
from ..utils.jwt import create_access_token
from ..schemas.auth import LoginRequest, LoginResponse, UserInfo

tz = timezone(timedelta(hours=8))

# --- In-memory security state ---

# Per-username security state
_username_security: dict[str, dict] = {}

# CAPTCHA storage: captcha_key -> {answer, expires, consumed}
_captcha_store: dict[str, dict] = {}

# IP rate limiting: ip -> [timestamps]
_ip_login_attempts: dict[str, list[float]] = {}

# CAPTCHA character set (excluding ambiguous: 0/O, 1/l/I)
_CAPTCHA_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _get_username_security(username: str) -> dict:
    """Get or create security state for a username."""
    if username not in _username_security:
        _username_security[username] = {
            "failure_count": 0,
            "captcha_required": False,
            "lockout_count": 0,
            "locked_until": None,
            "last_failure_ts": 0,
        }
    return _username_security[username]


def _cleanup_stale_entries():
    """Remove expired CAPTCHAs, old IP attempts, and stale username entries."""
    now = time.time()
    # Clean expired CAPTCHAs
    expired_keys = [k for k, v in _captcha_store.items() if v["expires"] < now]
    for k in expired_keys:
        del _captcha_store[k]

    # Clean IP attempts older than 15 minutes
    for ip in list(_ip_login_attempts.keys()):
        _ip_login_attempts[ip] = [t for t in _ip_login_attempts[ip] if now - t < 900]
        if not _ip_login_attempts[ip]:
            del _ip_login_attempts[ip]

    # Clean username security entries with no activity in 24 hours
    stale = [u for u, v in _username_security.items()
             if v["last_failure_ts"] > 0 and now - v["last_failure_ts"] > 86400]
    for u in stale:
        del _username_security[u]


def _check_ip_rate(request: Request):
    """Limit each IP to 100 login attempts per 15-minute window."""
    ip = _get_client_ip(request)
    now = time.time()
    attempts = [t for t in _ip_login_attempts.get(ip, []) if now - t < 900]
    if len(attempts) >= 100:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后重试")
    _ip_login_attempts[ip] = attempts


def _record_ip_attempt(request: Request):
    """Record this login attempt in the IP tracker."""
    ip = _get_client_ip(request)
    _ip_login_attempts.setdefault(ip, []).append(time.time())


def _check_account_lockout(username: str):
    """Check if account is currently locked out. Raises 423 if locked."""
    sec = _get_username_security(username)
    if sec["locked_until"] is not None:
        remaining = sec["locked_until"] - time.time()
        if remaining > 0:
            minutes = int(remaining // 60) + 1
            raise HTTPException(
                status_code=423,
                detail={"message": f"连续登录失败次数过多，账号已锁定{minutes}分钟", "captcha_required": True}
            )
        else:
            sec["locked_until"] = None


def _check_captcha(username: str, request_data: LoginRequest):
    """Validate CAPTCHA if required for this username."""
    sec = _get_username_security(username)
    if not sec["captcha_required"]:
        return

    if not request_data.captcha_key or not request_data.captcha_code:
        raise HTTPException(
            status_code=400,
            detail={"message": "请完成验证码验证", "captcha_required": True}
        )

    stored = _captcha_store.get(request_data.captcha_key)
    if not stored:
        raise HTTPException(
            status_code=400,
            detail={"message": "验证码已过期，请重新获取", "captcha_required": True}
        )

    if stored["consumed"]:
        del _captcha_store[request_data.captcha_key]
        raise HTTPException(
            status_code=400,
            detail={"message": "验证码已使用，请重新获取", "captcha_required": True}
        )

    if stored["expires"] < time.time():
        del _captcha_store[request_data.captcha_key]
        raise HTTPException(
            status_code=400,
            detail={"message": "验证码已过期，请重新获取", "captcha_required": True}
        )

    # Mark as consumed (one-time use)
    stored["consumed"] = True

    if stored["answer"].upper() != request_data.captcha_code.strip().upper():
        raise HTTPException(
            status_code=400,
            detail={"message": "验证码错误", "captcha_required": True}
        )


def _record_auth_failure(username: str):
    """Record a failed attempt. Handles CAPTCHA escalation and progressive lockout."""
    sec = _get_username_security(username)
    sec["failure_count"] += 1
    sec["last_failure_ts"] = time.time()

    # After 3 failures, CAPTCHA becomes required
    if sec["failure_count"] >= 3:
        sec["captcha_required"] = True

    # After 10 failures, trigger progressive lockout
    if sec["failure_count"] >= 10:
        sec["lockout_count"] += 1
        lockout_minutes = min(5 * sec["lockout_count"], 60)
        sec["locked_until"] = time.time() + (lockout_minutes * 60)
        sec["failure_count"] = 0  # reset for next cycle


def _clear_auth_failures(username: str):
    """Clear all security state on successful login."""
    _username_security.pop(username, None)


def is_captcha_required(username: str) -> bool:
    """Check if CAPTCHA is required for a given username (used by router)."""
    sec = _username_security.get(username)
    return sec["captcha_required"] if sec else False


def generate_captcha() -> dict:
    """Generate a CAPTCHA image and store the answer."""
    from captcha.image import ImageCaptcha

    answer = "".join(random.choices(_CAPTCHA_CHARS, k=4))
    image_generator = ImageCaptcha(width=160, height=60)
    img_data = image_generator.generate(answer)
    # .generate() returns a BytesIO with PNG data
    img_b64 = base64.b64encode(img_data.getvalue()).decode()

    captcha_key = str(uuid.uuid4())
    _captcha_store[captcha_key] = {
        "answer": answer.upper(),
        "expires": time.time() + 180,  # 3 minutes
        "consumed": False,
    }

    return {
        "captcha_key": captcha_key,
        "captcha_image": f"data:image/png;base64,{img_b64}",
    }


def authenticate(db: Session, request_data: LoginRequest, request: Request) -> LoginResponse:
    # 1. Periodic cleanup
    _cleanup_stale_entries()

    # 2. IP rate limiting
    _check_ip_rate(request)

    # 3. Account lockout check
    _check_account_lockout(request_data.username)

    # 4. CAPTCHA validation (if required)
    _check_captcha(request_data.username, request_data)

    # 5. Record this attempt in IP tracker
    _record_ip_attempt(request)

    # 6. Credential verification
    user = db.query(User).filter(User.username == request_data.username).first()
    if not user or not verify_password(request_data.password, user.password_hash):
        _record_auth_failure(request_data.username)
        # Check if this failure triggered a lockout
        sec = _get_username_security(request_data.username)
        captcha_required = sec["captcha_required"]
        if sec.get("locked_until"):
            lockout_minutes = int((sec["locked_until"] - time.time()) // 60) + 1
            raise HTTPException(
                status_code=423,
                detail={"message": f"连续登录失败次数过多，账号已锁定{lockout_minutes}分钟", "captcha_required": True}
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "账号或密码错误", "captcha_required": captcha_required}
        )

    if not user.status:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

    # 7. Success - clear all failure state
    _clear_auth_failures(request_data.username)

    # 8. Update last login and issue token
    user.last_login_at = datetime.now(tz)
    db.commit()
    access_token = create_access_token(data={"user_id": user.id, "role": user.role})
    user_info = UserInfo.model_validate(user)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_info,
    )


def get_user_info(user: User) -> UserInfo:
    return UserInfo.model_validate(user)


def change_password(db: Session, user: User, old_password: str, new_password: str):
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")
    if len(new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码长度不能少于6位")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()


def reset_user_password(db: Session, user_id: int, new_password: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if new_password and len(new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码长度不能少于6位")
    user.password_hash = hash_password(new_password)
    user.must_change_password = True
    db.commit()
