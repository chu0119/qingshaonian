from fastapi import APIRouter, Depends, Query, HTTPException, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from ..database import get_db
from ..models.user import User
from ..models.notification import Notification
from ..dependencies import get_current_user, require_role
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/notifications", tags=["消息通知"])


@router.get("")
def list_notifications(
    page: int = Query(1), page_size: int = Query(20),
    is_read: bool | None = Query(None),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    q = db.query(Notification).filter(Notification.user_id == user.id)
    if is_read is not None:
        q = q.filter(Notification.is_read == is_read)
    total = q.count()
    items = q.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return APIResponse.success({
        "items": [{
            "id": n.id, "type": n.type, "title": n.title, "content": n.content,
            "related_type": n.related_type, "related_id": n.related_id,
            "is_read": n.is_read, "read_at": n.read_at.isoformat() if n.read_at else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        } for n in items],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.query(func.count(Notification.id)).filter(
        Notification.user_id == user.id, Notification.is_read == False
    ).scalar() or 0
    return APIResponse.success({"count": count})


@router.put("/{notification_id}/read")
def mark_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="消息不存在")
    n.is_read = True
    n.read_at = datetime.now(timezone.utc)
    db.commit()
    return APIResponse.success(message="已标记已读")


@router.put("/read-all")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).update(
        {"is_read": True, "read_at": datetime.now(timezone.utc)}
    )
    db.commit()
    return APIResponse.success(message="全部已读")


@router.post("")
async def create_notification(request: Request, user: User = Depends(require_role("school_admin", "platform_admin")), db: Session = Depends(get_db)):
    """创建通知"""
    import json
    try:
        body = json.loads(await request.body())
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="请求体格式错误")
    target_user_id = body.get("user_id")
    if not target_user_id:
        raise HTTPException(status_code=400, detail="user_id 不能为空")
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="目标用户不存在")
    if user.role == "school_admin":
        school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
        if target_user.school_id != school_id:
            raise HTTPException(status_code=403, detail="只能给本校用户发送通知")
    n = Notification(
        user_id=target_user_id, sender_id=user.id,
        type=body.get("type", "system"), title=body.get("title", ""),
        content=body.get("content", ""),
        related_type=body.get("related_type"), related_id=body.get("related_id"),
    )
    db.add(n)
    db.commit()
    return APIResponse.success({"id": n.id}, message="通知发送成功")


@router.delete("/{notification_id}")
def delete_notification(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除通知"""
    n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="消息不存在")
    db.delete(n)
    db.commit()
    return APIResponse.success(message="删除成功")
