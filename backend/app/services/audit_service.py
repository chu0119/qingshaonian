from fastapi import Request
from sqlalchemy.orm import Session

from ..models.audit import LoginLog, OperationLog
from ..models.user import User


def get_request_ip(request: Request | None) -> str:
    if request is None:
        return ""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def _audit_school_id(user: User | None) -> int | None:
    if not user or user.role == "platform_admin":
        return None
    return user.school_id


def log_login(
    db: Session,
    *,
    username: str,
    user: User | None,
    request: Request | None,
    result: str,
    failure_reason: str = "",
) -> None:
    db.add(LoginLog(
        user_id=user.id if user else None,
        username=username,
        user_role=user.role if user else "",
        school_id=_audit_school_id(user),
        login_ip=get_request_ip(request),
        result=result,
        failure_reason=failure_reason,
    ))
    db.commit()


def log_operation(
    db: Session,
    user: User | None,
    request: Request | None,
    module: str,
    action: str,
    object_type: str = "",
    object_id: str | int | None = None,
    object_name: str = "",
    result: str = "success",
    detail: str = "",
) -> None:
    db.add(OperationLog(
        operator_id=user.id if user else None,
        operator_name=user.real_name if user else "",
        operator_role=user.role if user else "",
        school_id=_audit_school_id(user),
        module=module,
        action=action,
        object_type=object_type,
        object_id=str(object_id or ""),
        object_name=object_name or "",
        request_ip=get_request_ip(request),
        result=result,
        detail=detail or "",
    ))
    db.commit()
