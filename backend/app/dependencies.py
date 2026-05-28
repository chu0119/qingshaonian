import logging
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models.user import User, UserRole
from .utils.jwt import decode_access_token

logger = logging.getLogger(__name__)
security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录信息无效")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if not user.status:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    # 平台管理员代入学堂上下文（不修改 ORM column，用独立属性）
    school_context_id = payload.get("school_context_id")
    if school_context_id:
        try:
            ctx_id = int(school_context_id)
            request.state.effective_school_id = ctx_id
            # Python 动态属性，不是 SQLAlchemy Column，不会写入数据库
            user._effective_school_id = ctx_id
        except (ValueError, TypeError):
            pass
        request.state.acting_user_id = payload.get("acting_user_id")

    return user


def get_effective_school_id(request: Request, user: User) -> int | None:
    """返回当前请求的有效学校上下文，不修改 ORM 对象。"""
    return getattr(user, "_effective_school_id", None) or user.school_id


def require_role(*roles: str):
    def checker(request: Request, user: User = Depends(get_current_user)) -> User:
        if user.role in roles:
            return user
        # 平台管理员带入学校上下文时，可访问该学校的页面
        if user.role == "platform_admin" and getattr(request.state, "effective_school_id", None):
            # school_admin/teacher/counselor 路由均放行
            if any(r in ("school_admin", "teacher", "counselor", "student") for r in roles):
                return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限访问")
    return checker


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    user_id = payload.get("user_id")
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()
