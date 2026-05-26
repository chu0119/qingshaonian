from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import require_role, get_current_user
from ..models.user import User, UserRole
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/common", tags=["通用"])


@router.get("/dict/categories")
def get_categories(user: User = Depends(get_current_user)):
    categories = [
        {"value": "mental_health", "label": "心理健康筛查"},
        {"value": "bullying", "label": "校园欺凌排查"},
        {"value": "internet_addiction", "label": "网络沉迷评估"},
        {"value": "family_relationship", "label": "家庭关系调查"},
        {"value": "safety_awareness", "label": "安全意识测评"},
        {"value": "interpersonal", "label": "人际关系测评"},
        {"value": "academic_pressure", "label": "学业压力测评"},
        {"value": "custom", "label": "自定义分类"},
    ]
    return APIResponse.success(categories)


@router.get("/dict/dimensions")
def get_dimensions(user: User = Depends(get_current_user)):
    dimensions = [
        {"value": "emotion", "label": "情绪状态"},
        {"value": "sleep", "label": "睡眠状态"},
        {"value": "academic_pressure", "label": "学习压力"},
        {"value": "interpersonal", "label": "人际关系"},
        {"value": "family_support", "label": "家庭支持"},
        {"value": "campus_safety", "label": "校园安全"},
        {"value": "internet_use", "label": "网络使用"},
        {"value": "self_safety", "label": "自我安全风险"},
    ]
    return APIResponse.success(dimensions)


@router.get("/dict/risk-tags")
def get_risk_tags(user: User = Depends(get_current_user)):
    tags = [
        {"value": "mental_pressure", "label": "心理压力风险"},
        {"value": "bullying", "label": "校园欺凌风险"},
        {"value": "internet_addiction", "label": "网络沉迷风险"},
        {"value": "family_relationship", "label": "家庭关系风险"},
        {"value": "interpersonal", "label": "人际关系风险"},
        {"value": "academic_pressure", "label": "学业压力风险"},
        {"value": "safety_awareness", "label": "安全意识风险"},
        {"value": "self_safety", "label": "自我安全风险"},
    ]
    return APIResponse.success(tags)


@router.get("/dict/teacher-types")
def get_teacher_types(user: User = Depends(get_current_user)):
    types = [
        {"value": "head_teacher", "label": "班主任"},
        {"value": "counselor", "label": "心理老师"},
        {"value": "grade_director", "label": "年级主任"},
        {"value": "moral_edu", "label": "德育老师"},
        {"value": "normal", "label": "普通教师"},
    ]
    return APIResponse.success(types)


@router.get("/dict/risk-levels")
def get_risk_levels(user: User = Depends(get_current_user)):
    levels = [
        {"value": "low", "label": "低风险", "color": "#1890FF"},
        {"value": "medium", "label": "中风险", "color": "#FA8C16"},
        {"value": "high", "label": "高风险", "color": "#FF4D4F"},
        {"value": "urgent", "label": "紧急风险", "color": "#CF1322"},
    ]
    return APIResponse.success(levels)


@router.get("/dict/intervention-methods")
def get_intervention_methods(user: User = Depends(get_current_user)):
    methods = [
        {"value": "student_talk", "label": "学生谈话"},
        {"value": "teacher_communication", "label": "班主任沟通"},
        {"value": "counselor_guidance", "label": "心理老师辅导"},
        {"value": "family_school", "label": "家校沟通"},
        {"value": "home_visit", "label": "家访"},
        {"value": "referral", "label": "转介专业机构"},
        {"value": "observation", "label": "持续观察"},
        {"value": "other", "label": "其他"},
    ]
    return APIResponse.success(methods)


@router.get("/dict/process-statuses")
def get_process_statuses(user: User = Depends(get_current_user)):
    statuses = [
        {"value": "pending", "label": "待处理"},
        {"value": "viewed", "label": "已查看"},
        {"value": "processing", "label": "处理中"},
        {"value": "ongoing", "label": "持续跟进"},
        {"value": "completed", "label": "已完成"},
        {"value": "closed", "label": "已关闭"},
    ]
    return APIResponse.success(statuses)


@router.get("/dict/grades")
def get_grades_list(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from ..models.user import Grade
    grades = db.query(Grade).filter(Grade.status == True).order_by(Grade.sort_order).all()
    return APIResponse.success([{"value": g.id, "label": g.name} for g in grades])
