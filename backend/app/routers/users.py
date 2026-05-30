from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import Class, TeacherClass, User
from ..schemas.user import UserCreate, UserUpdate
from ..dependencies import get_current_user, require_role
from ..services import user_service
from ..services.audit_service import log_operation
from ..utils.access_control import can_access_class, can_access_student, teacher_class_ids
from ..utils.validators import validate_id_card
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/users", tags=["用户管理"])


@router.get("/students")
def list_students(
    page: int = Query(1),
    page_size: int = Query(20),
    grade_id: int | None = Query(None),
    class_id: int | None = Query(None),
    keyword: str = Query(""),
    user: User = Depends(require_role("school_admin", "teacher")),
    db: Session = Depends(get_db),
):
    class_ids = None
    if user.role in ("teacher", "counselor"):
        allowed = teacher_class_ids(db, user)
        if class_id and class_id not in allowed:
            raise HTTPException(status_code=403, detail="无权限访问该班级")
        class_ids = [class_id] if class_id else list(allowed)
    result = user_service.list_users(db, (getattr(user, '_effective_school_id', None) or user.school_id), "student", page, page_size, grade_id, class_id, keyword, class_ids=class_ids)
    return APIResponse.success(result)


@router.post("/students")
def create_student(data: UserCreate, request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    data.school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    data.role = "student"
    try:
        data.username = validate_id_card(data.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="该身份证号已被注册")
    if data.class_id and not can_access_class(db, user, data.class_id):
        raise HTTPException(status_code=403, detail="班级不属于当前学校")
    u = user_service.create_user(db, data)
    log_operation(db, user, request, module="student", action="create", object_type="user", object_id=u.id, object_name=u.real_name)
    return APIResponse.success({"id": u.id}, message="学生创建成功")


# ===== 静态路径必须在动态路径 {student_id} 之前 =====

@router.post("/students/import")
def import_students(request: Request, file: UploadFile = File(...), user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    content = file.file.read()
    result = user_service.import_students_from_excel(db, (getattr(user, '_effective_school_id', None) or user.school_id), content)
    log_operation(
        db,
        user,
        request,
        module="student",
        action="import",
        object_type="student_batch",
        result="success" if result.fail_count == 0 else "partial_success",
        detail=f"success={result.success_count};fail={result.fail_count}",
    )
    return APIResponse.success(result.model_dump())


@router.get("/students/template")
def download_template(user: User = Depends(require_role("school_admin"))):
    output = user_service.generate_student_template()
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=student_import_template.xlsx"},
    )


@router.get("/students/export")
def export_students(request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    result = user_service.list_users(db, (getattr(user, '_effective_school_id', None) or user.school_id), "student", page=1, page_size=5000)
    log_operation(db, user, request, module="student", action="export", object_type="student_list", detail=f"count={len(result['items'])}")
    return APIResponse.success(result["items"])


# ===== 动态路径 {student_id} =====

@router.get("/students/{student_id}")
def get_student(student_id: int, user: User = Depends(require_role("school_admin", "teacher")), db: Session = Depends(get_db)):
    try:
        student = db.query(User).filter(User.id == student_id).first()
        if not can_access_student(db, user, student):
            raise HTTPException(status_code=404, detail="学生不存在")
        info = user_service.get_user_info(db, student_id)
        return APIResponse.success(info.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/students/{student_id}")
def update_student(student_id: int, data: UserUpdate, request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    try:
        student = db.query(User).filter(User.id == student_id, User.school_id == (getattr(user, '_effective_school_id', None) or user.school_id), User.role == "student").first()
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")
        if data.class_id and not can_access_class(db, user, data.class_id):
            raise HTTPException(status_code=403, detail="班级不属于当前学校")
        updated = user_service.update_user(db, student_id, data)
        log_operation(db, user, request, module="student", action="update", object_type="user", object_id=student_id, object_name=updated.real_name)
        return APIResponse.success(message="学生信息更新成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/students/{student_id}")
def delete_student(student_id: int, request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    student = db.query(User).filter(User.id == student_id, User.school_id == (getattr(user, '_effective_school_id', None) or user.school_id), User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    student_name = student.real_name
    user_service.delete_user(db, student_id)
    log_operation(db, user, request, module="student", action="delete", object_type="user", object_id=student_id, object_name=student_name)
    return APIResponse.success(message="学生删除成功")


@router.put("/students/{student_id}/change-class")
def change_student_class(student_id: int, request: Request, class_id: int = Query(...), user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    student = db.query(User).filter(User.id == student_id, User.school_id == (getattr(user, '_effective_school_id', None) or user.school_id), User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if not can_access_class(db, user, class_id):
        raise HTTPException(status_code=403, detail="班级不属于当前学校")
    user_service.update_user(db, student_id, UserUpdate(class_id=class_id))
    log_operation(db, user, request, module="student", action="change_class", object_type="user", object_id=student_id, object_name=student.real_name, detail=f"class_id={class_id}")
    return APIResponse.success(message="班级调整成功")


# 教师管理
@router.get("/teachers")
def list_teachers(
    page: int = Query(1),
    page_size: int = Query(20),
    keyword: str = Query(""),
    teacher_type: str = Query(""),
    user: User = Depends(require_role("school_admin")),
    db: Session = Depends(get_db),
):
    result = user_service.list_teachers(db, (getattr(user, '_effective_school_id', None) or user.school_id), page, page_size, keyword=keyword, teacher_type=teacher_type)
    return APIResponse.success(result)


@router.post("/teachers")
def create_teacher(data: UserCreate, request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    if data.role and data.role not in ("teacher", "counselor"):
        raise HTTPException(status_code=400, detail="教师角色只能为 teacher 或 counselor")
    data.role = data.role or "teacher"
    data.school_id = (getattr(user, '_effective_school_id', None) or user.school_id)
    try:
        data.username = validate_id_card(data.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="该身份证号已被注册")
    u = user_service.create_user(db, data)
    log_operation(db, user, request, module="teacher", action="create", object_type="user", object_id=u.id, object_name=u.real_name)
    return APIResponse.success({"id": u.id}, message="教师创建成功")


@router.get("/teachers/{teacher_id}")
def get_teacher(teacher_id: int, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    try:
        teacher = db.query(User).filter(User.id == teacher_id, User.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
        if not teacher or teacher.role not in ("teacher", "counselor"):
            raise HTTPException(status_code=404, detail="教师不存在")
        info = user_service.get_user_info(db, teacher_id)
        return APIResponse.success(info.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/teachers/{teacher_id}")
def update_teacher(teacher_id: int, data: UserUpdate, request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    try:
        teacher = db.query(User).filter(User.id == teacher_id, User.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
        if not teacher or teacher.role not in ("teacher", "counselor"):
            raise HTTPException(status_code=404, detail="教师不存在")
        updated = user_service.update_user(db, teacher_id, data)
        log_operation(db, user, request, module="teacher", action="update", object_type="user", object_id=teacher_id, object_name=updated.real_name)
        return APIResponse.success(message="教师信息更新成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/teachers/{teacher_id}")
def delete_teacher(teacher_id: int, request: Request, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    teacher = db.query(User).filter(User.id == teacher_id, User.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
    if not teacher or teacher.role not in ("teacher", "counselor"):
        raise HTTPException(status_code=404, detail="教师不存在")
    teacher_name = teacher.real_name
    user_service.delete_user(db, teacher_id)
    log_operation(db, user, request, module="teacher", action="delete", object_type="user", object_id=teacher_id, object_name=teacher_name)
    return APIResponse.success(message="教师删除成功")


@router.get("/teachers/{teacher_id}/assigned-classes")
def get_teacher_assigned_classes(teacher_id: int, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    school_id = getattr(user, '_effective_school_id', None) or user.school_id
    teacher = db.query(User).filter(User.id == teacher_id, User.school_id == school_id).first()
    if not teacher or teacher.role not in ("teacher", "counselor"):
        raise HTTPException(status_code=404, detail="教师不存在")
    assigned = {
        row[0] for row in db.query(TeacherClass.class_id)
        .join(Class, Class.id == TeacherClass.class_id)
        .filter(TeacherClass.teacher_id == teacher_id, Class.school_id == school_id)
        .all()
    }
    direct = {
        row[0] for row in db.query(Class.id)
        .filter(Class.school_id == school_id, (Class.head_teacher_id == teacher_id) | (Class.counselor_id == teacher_id))
        .all()
    }
    return APIResponse.success(sorted(assigned | direct))


@router.put("/teachers/{teacher_id}/assign-classes")
def assign_classes(teacher_id: int, request: Request, class_ids: list[int] = [], user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    teacher = db.query(User).filter(User.id == teacher_id, User.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
    if not teacher or teacher.role not in ("teacher", "counselor"):
        raise HTTPException(status_code=404, detail="教师不存在")
    count = db.query(Class).filter(Class.id.in_(class_ids), Class.school_id == (getattr(user, '_effective_school_id', None) or user.school_id)).count() if class_ids else 0
    if count != len(set(class_ids)):
        raise HTTPException(status_code=403, detail="包含不属于当前学校的班级")
    user_service.assign_teacher_classes(db, teacher_id, class_ids)
    log_operation(db, user, request, module="teacher", action="assign_classes", object_type="user", object_id=teacher_id, object_name=teacher.real_name, detail=f"class_ids={class_ids}")
    return APIResponse.success(message="班级分配成功")
