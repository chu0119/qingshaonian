import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models.user import User
from ..dependencies import require_role
from ..services.seed_service import seed_demo_data
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/system", tags=["系统设置"])


@router.get("/school-info")
def get_school_info(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    from ..models.user import School
    school = db.query(School).filter(School.id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
    if school:
        return APIResponse.success({
            "id": school.id,
            "name": school.name,
            "code": school.code,
            "address": school.address or "",
            "phone": school.phone or "",
        })
    return APIResponse.success(None)


ALLOWED_SCHOOL_FIELDS = {"name", "address", "phone"}


@router.put("/school-info")
def update_school_info(data: dict, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    from ..models.user import School
    school = db.query(School).filter(School.id == (getattr(user, '_effective_school_id', None) or user.school_id)).first()
    if not school:
        raise HTTPException(status_code=404, detail="学校信息不存在")
    for k, v in data.items():
        if k in ALLOWED_SCHOOL_FIELDS and hasattr(school, k):
            setattr(school, k, v if v is not None else "")
    db.commit()
    db.refresh(school)
    return APIResponse.success(data={
        "id": school.id,
        "name": school.name,
        "code": school.code,
        "address": school.address or "",
        "phone": school.phone or "",
    }, message="学校信息更新成功")


@router.get("/risk-config")
def get_risk_config(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    from ..models.system_config import SystemConfig
    configs = db.query(SystemConfig).filter(
        SystemConfig.config_key.in_(["risk_levels", "quality_levels", "fast_answer_threshold", "consecutive_same_threshold"]),
        SystemConfig.school_id.is_(None)
    ).all()

    # If no risk configs exist, return sensible defaults
    if not configs:
        default_risk_levels = [
            {"level": "low", "label": "低风险", "min": 0, "max": 25, "color": "#1890FF"},
            {"level": "medium", "label": "中风险", "min": 26, "max": 50, "color": "#FA8C16"},
            {"level": "high", "label": "高风险", "min": 51, "max": 75, "color": "#FF4D4F"},
            {"level": "urgent", "label": "紧急风险", "min": 76, "max": 100, "color": "#CF1322"},
        ]
        return APIResponse.success({
            "risk_levels": default_risk_levels,
            "fast_answer_threshold": 30,
            "consecutive_same_threshold": 5,
        })

    result = {}
    for c in configs:
        try:
            result[c.config_key] = json.loads(c.config_value) if c.config_value else None
        except (json.JSONDecodeError, TypeError):
            result[c.config_key] = c.config_value
    return APIResponse.success(result)


@router.put("/risk-config")
def update_risk_config(data: dict, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    from ..models.system_config import SystemConfig
    updated = []
    for key, value in data.items():
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == key,
            SystemConfig.school_id.is_(None)
        ).first()
        if config:
            config.config_value = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            updated.append(key)
        else:
            new_config = SystemConfig(
                school_id=None,
                config_key=key,
                config_value=json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value,
                description=key,
            )
            db.add(new_config)
            updated.append(key)
    db.commit()
    return APIResponse.success(message=f"配置已更新: {', '.join(updated)}" if updated else "无配置需要更新")


@router.get("/grades")
def get_grades_for_admin(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    from ..models.user import Grade
    grades = db.query(Grade).filter(
        Grade.school_id == (getattr(user, '_effective_school_id', None) or user.school_id),
        Grade.status == True
    ).order_by(Grade.sort_order).all()
    return APIResponse.success([{"id": g.id, "name": g.name, "sort_order": g.sort_order} for g in grades])


@router.post("/grades")
def create_grade(data: dict, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    from ..models.user import Grade
    name = (data.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="年级名称不能为空")
    existing = db.query(Grade).filter(
        Grade.school_id == (getattr(user, '_effective_school_id', None) or user.school_id),
        Grade.name == name,
        Grade.status == True,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"年级「{name}」已存在")
    grade = Grade(
        school_id=(getattr(user, '_effective_school_id', None) or user.school_id),
        name=name,
        sort_order=data.get("sort_order", 0),
    )
    db.add(grade)
    db.commit()
    db.refresh(grade)
    return APIResponse.success({"id": grade.id, "name": grade.name, "sort_order": grade.sort_order}, message="年级添加成功")


@router.delete("/grades/{grade_id}")
def delete_grade(grade_id: int, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    from ..models.user import Grade
    grade = db.query(Grade).filter(
        Grade.id == grade_id,
        Grade.school_id == (getattr(user, '_effective_school_id', None) or user.school_id),
    ).first()
    if not grade:
        raise HTTPException(status_code=404, detail="年级不存在")
    grade.status = False
    db.commit()
    return APIResponse.success(message="年级已删除")


@router.post("/seed-demo-data")
def seed_demo(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    if settings.APP_ENV.lower() not in {"demo", "development"}:
        raise HTTPException(status_code=403, detail="当前环境不允许初始化演示数据")
    seeded = seed_demo_data(db, school_id=(getattr(user, '_effective_school_id', None) or user.school_id), current_settings=settings)
    return APIResponse.success({"seeded_school_ids": seeded}, message="演示数据初始化完成")


# ===== 短信配置（预留接口） =====

SMS_CONFIG_KEYS = ["sms_api_url", "sms_app_key", "sms_template_id"]
SMS_CONFIG_DEFAULTS = {
    "sms_api_url": "",
    "sms_app_key": "",
    "sms_template_id": "",
}


@router.get("/sms-config")
def get_sms_config(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    """获取短信配置（预留，当前不实际发送短信）"""
    from ..models.system_config import SystemConfig

    configs = db.query(SystemConfig).filter(
        SystemConfig.config_key.in_(SMS_CONFIG_KEYS),
        SystemConfig.school_id.is_(None),
    ).all()

    config_map: dict = {**SMS_CONFIG_DEFAULTS}
    for c in configs:
        config_map[c.config_key] = c.config_value or ""

    return APIResponse.success({
        "sms_api_url": config_map["sms_api_url"],
        "sms_app_key": config_map["sms_app_key"],
        "sms_template_id": config_map["sms_template_id"],
        "note": "短信功能为预留接口，当前仅支持配置存储，不实际发送短信。",
    })


@router.put("/sms-config")
def update_sms_config(data: dict, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    """保存短信配置（预留，仅做数据存储不实际发送）"""
    from ..models.system_config import SystemConfig

    updated = []
    for key in SMS_CONFIG_KEYS:
        if key not in data:
            continue
        value = str(data[key]) if data[key] is not None else ""
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == key,
            SystemConfig.school_id.is_(None),
        ).first()
        if config:
            config.config_value = value
            updated.append(key)
        else:
            new_config = SystemConfig(
                school_id=None,
                config_key=key,
                config_value=value,
                description=f"短信配置 - {key}",
            )
            db.add(new_config)
            updated.append(key)

    db.commit()
    if updated:
        return APIResponse.success(message=f"短信配置已保存: {', '.join(updated)}")
    return APIResponse.success(message="无配置需要更新")


# ===== 数据大屏设置 =====

SCREEN_CONFIG_KEYS = ["screen_title", "screen_subtitle"]
SCREEN_CONFIG_DEFAULTS = {
    "screen_title": "学生心理健康监测数据大屏",
    "screen_subtitle": "",
}


@router.get("/screen-config")
def get_screen_config(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    """获取数据大屏配置"""
    from ..models.system_config import SystemConfig

    configs = db.query(SystemConfig).filter(
        SystemConfig.config_key.in_(SCREEN_CONFIG_KEYS),
        SystemConfig.school_id.is_(None),
    ).all()

    config_map: dict = {**SCREEN_CONFIG_DEFAULTS}
    for c in configs:
        config_map[c.config_key] = c.config_value or SCREEN_CONFIG_DEFAULTS.get(c.config_key, "")

    return APIResponse.success({
        "screen_title": config_map["screen_title"],
        "screen_subtitle": config_map["screen_subtitle"],
    })


@router.put("/screen-config")
def update_screen_config(data: dict, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    """保存数据大屏配置"""
    from ..models.system_config import SystemConfig

    updated = []
    for key in SCREEN_CONFIG_KEYS:
        if key not in data:
            continue
        value = str(data[key]) if data[key] is not None else ""
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == key,
            SystemConfig.school_id.is_(None),
        ).first()
        if config:
            config.config_value = value
            updated.append(key)
        else:
            new_config = SystemConfig(
                school_id=None,
                config_key=key,
                config_value=value,
                description=f"数据大屏配置 - {key}",
            )
            db.add(new_config)
            updated.append(key)

    db.commit()
    if updated:
        return APIResponse.success(message=f"大屏配置已保存: {', '.join(updated)}")
    return APIResponse.success({"screen_title": data.get("screen_title", ""), "screen_subtitle": data.get("screen_subtitle", "")}, message="无配置需要更新")
