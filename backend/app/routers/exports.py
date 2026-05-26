from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..dependencies import require_role
from ..services.audit_service import log_operation
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/exports", tags=["导出"])


@router.get("/students")
def export_students(request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    log_operation(db, user, request, module="export", action="export_students", object_type="student_list")
    return APIResponse.success({"message": "导出学生名单"})
