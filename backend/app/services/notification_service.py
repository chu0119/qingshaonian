"""Helper to create notifications from other services."""
from sqlalchemy.orm import Session
from ..models.notification import Notification


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    content: str = "",
    type: str = "system",
    sender_id: int | None = None,
    related_type: str | None = None,
    related_id: int | None = None,
):
    """Create a notification for a user. Safe to call - never raises."""
    try:
        n = Notification(
            user_id=user_id, sender_id=sender_id, type=type,
            title=title, content=content,
            related_type=related_type, related_id=related_id,
        )
        db.add(n)
        db.flush()
    except Exception:
        pass  # notification failure should never break the main flow
