from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from ..database import get_db
from ..models.user import User
from ..models.notification import Notification
from ..dependencies import get_current_user
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
