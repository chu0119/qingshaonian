from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User, Grade, Class as ClassModel
from ..schemas.class_ import ClassCreate, ClassUpdate
from ..dependencies import get_current_user, require_role
from ..services import class_service
from ..services.audit_service import log_operation
from ..utils.access_control import can_access_class
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/classes", tags=["班级管理"])


@router.get("")
def list_classes(
    grade_id: int | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
    user: User = Depends(require_role("school_admin", "teacher")),
    db: Session = Depends(get_db),
):
    school_id = user.school_id
    if user.role in ("teacher", "counselor"):
        result = {"items": class_service.get_my_classes(db, user.id), "total": 0, "page": page, "page_size": page_size, "total_pages": 1}
        result["total"] = len(result["items"])
    else:
        result = class_service.list_classes(db, school_id, grade_id, page, page_size)
    return APIResponse.success(result)


@router.post("")
def create_class(data: ClassCreate, request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    grade = db.query(Grade).filter(Grade.id == data.grade_id, Grade.school_id == user.school_id).first()
    if not grade:
        raise HTTPException(status_code=403, detail="年级不属于当前学校")
    c = class_service.create_class(db, user.school_id, data)
    log_operation(db, user, request, module="class", action="create", object_type="class", object_id=c.id, object_name=c.name)
    return APIResponse.success({"id": c.id}, message="班级创建成功")


@router.get("/my")
def my_classes(user: User = Depends(require_role("teacher", "counselor")), db: Session = Depends(get_db)):
    result = class_service.get_my_classes(db, user.id)
    return APIResponse.success(result)


@router.get("/{class_id}")
def get_class(class_id: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    from ..schemas.class_ import ClassInfo
    from ..models.user import Grade as GradeModel
    from sqlalchemy import func as sa_func
    c = db.query(ClassModel).filter(ClassModel.id == class_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="班级不存在")
    if not can_access_class(db, user, class_id):
        raise HTTPException(status_code=404, detail="班级不存在")
    student_count = db.query(sa_func.count(User.id)).filter(User.class_id == c.id, User.role == "student").scalar()
    head_teacher = db.query(User).filter(User.id == c.head_teacher_id).first()
    counselor = db.query(User).filter(User.id == c.counselor_id).first()
    grade = db.query(GradeModel).filter(GradeModel.id == c.grade_id).first()
    return APIResponse.success(ClassInfo(
        id=c.id, school_id=c.school_id, grade_id=c.grade_id, name=c.name,
        head_teacher_id=c.head_teacher_id, counselor_id=c.counselor_id, status=c.status,
        grade_name=grade.name if grade else "",
        head_teacher_name=head_teacher.real_name if head_teacher else "",
        counselor_name=counselor.real_name if counselor else "",
        student_count=student_count,
    ).model_dump())


@router.put("/{class_id}")
def update_class(class_id: int, data: ClassUpdate, request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    try:
        klass = db.query(ClassModel).filter(ClassModel.id == class_id, ClassModel.school_id == user.school_id).first()
        if not klass:
            raise HTTPException(status_code=404, detail="班级不存在")
        if data.grade_id:
            grade = db.query(Grade).filter(Grade.id == data.grade_id, Grade.school_id == user.school_id).first()
            if not grade:
                raise HTTPException(status_code=403, detail="年级不属于当前学校")
        c = class_service.update_class(db, class_id, data)
        log_operation(db, user, request, module="class", action="update", object_type="class", object_id=c.id, object_name=c.name)
        return APIResponse.success(message="班级更新成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{class_id}")
def delete_class(class_id: int, request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    klass = db.query(ClassModel).filter(ClassModel.id == class_id, ClassModel.school_id == user.school_id).first()
    if not klass:
        raise HTTPException(status_code=404, detail="班级不存在")
    class_name = klass.name
    class_service.delete_class(db, class_id)
    log_operation(db, user, request, module="class", action="delete", object_type="class", object_id=class_id, object_name=class_name)
    return APIResponse.success(message="班级删除成功")
