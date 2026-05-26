from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models.user import User, UserRole
from .utils.jwt import decode_access_token

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
    x_platform_school_id: str | None = Header(None),
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
    # 平台管理员可以通过Header临时切换到指定学校视角
    if user.role == "platform_admin" and x_platform_school_id:
        try:
            user.school_id = int(x_platform_school_id)
        except ValueError:
            pass
    return user


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        # 平台管理员拥有所有学校级权限（当设置了X-Platform-School-Id时自动授权）
        effective_roles = list(roles)
        if user.role == "platform_admin" and user.school_id is not None:
            effective_roles.append("platform_admin")
        if user.role not in effective_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限访问")
        return user
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
