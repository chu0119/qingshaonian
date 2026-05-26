import json
import httpx
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models.external import AIAnalysisLog
from ..models.risk import QualityAssessment, RiskAlert, ScoringResult
from ..models.task import AnswerSheet, Task
from ..models.user import Class, School, User
from ..models.system_config import SystemConfig
from ..dependencies import require_role
from ..services.audit_service import log_operation
from ..utils.access_control import can_access_class, can_access_student, can_access_task
from ..utils.response import APIResponse

router = APIRouter(prefix="/api/v1/ai", tags=["AI分析"])

AI_CONFIG_KEYS = ["ai_api_url", "ai_api_key", "ai_model_name"]
AI_DISCLAIMER = "本分析仅作为学校教育管理和学生关怀参考，不作为医学诊断依据。"


class SafeDict(dict):
    """安全格式化字典，缺失键返回'未知'，避免KeyError"""
    def __missing__(self, key):
        return "未知"


def _mask_api_key(key: str) -> str:
    """对API密钥进行脱敏处理，中间用***代替"""
    if not key:
        return ""
    if len(key) <= 8:
        return key[:2] + "***" + key[-2:] if len(key) >= 4 else "***"
    return key[:4] + "***" + key[-4:]


def _get_ai_configs(db: Session) -> dict:
    """从system_configs表读取AI配置"""
    configs = db.query(SystemConfig).filter(
        SystemConfig.config_key.in_(AI_CONFIG_KEYS),
        SystemConfig.school_id.is_(None),
    ).all()
    config_map = {}
    for c in configs:
        config_map[c.config_key] = c.config_value or ""
    if settings.AI_API_URL:
        config_map["ai_api_url"] = settings.AI_API_URL
    if settings.AI_API_KEY:
        config_map["ai_api_key"] = settings.AI_API_KEY
    return config_map


def _require_ai_scope(db: Session, user: User, analysis_type: str, request_data: dict) -> str:
    """Reject teacher/counselor AI requests that are not tied to their allowed data range."""
    if user.role == "platform_admin":
        return str(request_data.get("school_id") or request_data.get("object_id") or "platform")
    if user.role == "school_admin":
        return str(request_data.get("school_id") or user.school_id)

    if analysis_type == "overall_report":
        raise HTTPException(status_code=403, detail="教师仅能分析自己负责班级或学生的数据")

    if analysis_type == "student_risk":
        student_id = request_data.get("student_id")
        if not student_id:
            raise HTTPException(status_code=400, detail="学生分析需指定学生ID")
        student = db.query(User).filter(User.id == int(student_id)).first()
        if not can_access_student(db, user, student):
            raise HTTPException(status_code=403, detail="无权限分析该学生数据")
        return str(student_id)

    if analysis_type == "class_report":
        class_id = request_data.get("class_id")
        if not class_id:
            raise HTTPException(status_code=400, detail="班级分析需指定班级ID")
        if not can_access_class(db, user, int(class_id)):
            raise HTTPException(status_code=403, detail="无权限分析该班级数据")
        return str(class_id)

    if analysis_type == "quality_report":
        task_id = request_data.get("task_id")
        class_id = request_data.get("class_id")
        if task_id:
            from ..models.task import Task
            task = db.query(Task).filter(Task.id == int(task_id)).first()
            if not can_access_task(db, user, task):
                raise HTTPException(status_code=403, detail="无权限分析该任务数据")
            return str(task_id)
        if class_id and can_access_class(db, user, int(class_id)):
            return str(class_id)
        raise HTTPException(status_code=400, detail="答题质量分析需指定任务ID或班级ID")

    raise HTTPException(status_code=400, detail=f"不支持的分析类型: {analysis_type}")


def _build_authorized_analysis_data(db: Session, user: User, analysis_type: str, object_id: str | int | None) -> dict:
    from sqlalchemy import func

    if analysis_type == "overall_report":
        school_id = int(object_id or user.school_id) if user.role != "platform_admin" else None
        if user.role == "school_admin" and school_id != user.school_id:
            raise HTTPException(status_code=403, detail="无权限分析该学校数据")
        school_name = "全平台" if school_id is None else (db.query(School).filter(School.id == school_id).first().name if db.query(School).filter(School.id == school_id).first() else "")
        user_filter = [] if school_id is None else [User.school_id == school_id]
        task_filter = [] if school_id is None else [Task.school_id == school_id]
        risk_filter = [] if school_id is None else [RiskAlert.school_id == school_id]
        total_students = db.query(func.count(User.id)).filter(User.role == "student", *user_filter).scalar() or 0
        completed_count = db.query(func.count(AnswerSheet.id)).join(Task, Task.id == AnswerSheet.task_id).filter(AnswerSheet.status == "submitted", *task_filter).scalar() or 0
        risks = db.query(RiskAlert.risk_level, func.count(RiskAlert.id)).filter(*risk_filter).group_by(RiskAlert.risk_level).all()
        return {
            "school_id": school_id or "platform",
            "school_name": school_name,
            "total_students": total_students,
            "completed_count": completed_count,
            "completion_rate": round(completed_count / max(total_students, 1) * 100, 1) if total_students else 0,
            "risk_distribution": dict(risks),
            "grade_overview": [],
            "dimension_avg_scores": {},
            "quality_overview": {},
        }

    if analysis_type == "class_report":
        class_id = int(object_id or 0)
        if not can_access_class(db, user, class_id):
            raise HTTPException(status_code=403, detail="无权限分析该班级数据")
        klass = db.query(Class).filter(Class.id == class_id).first()
        total_students = db.query(func.count(User.id)).filter(User.class_id == class_id, User.role == "student").scalar() or 0
        completed = db.query(func.count(AnswerSheet.id)).filter(AnswerSheet.class_id == class_id, AnswerSheet.status == "submitted").scalar() or 0
        return {
            "class_id": class_id,
            "class_name": klass.name if klass else "",
            "grade_name": klass.grade.name if klass and klass.grade else "",
            "total_students": total_students,
            "completed_count": completed,
            "completion_rate": round(completed / max(total_students, 1) * 100, 1) if total_students else 0,
            "risk_distribution": {},
            "avg_score": 0,
            "dimension_avg_scores": {},
            "quality_overview": {},
        }

    if analysis_type == "student_risk":
        student_id = int(object_id or 0)
        student = db.query(User).filter(User.id == student_id).first()
        if not can_access_student(db, user, student):
            raise HTTPException(status_code=403, detail="无权限分析该学生数据")
        alert = db.query(RiskAlert).filter(RiskAlert.student_id == student_id).order_by(RiskAlert.id.desc()).first()
        scoring = db.query(ScoringResult).filter(ScoringResult.answer_sheet_id == alert.answer_sheet_id).first() if alert else None
        quality = db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id == alert.answer_sheet_id).first() if alert else None
        sheet = db.query(AnswerSheet).filter(AnswerSheet.id == alert.answer_sheet_id).first() if alert else None
        return {
            "student_id": student_id,
            "name": student.real_name if student else "",
            "risk_level": alert.risk_level if alert else "暂无",
            "risk_type": alert.risk_type if alert else "暂无",
            "total_score": scoring.total_score if scoring else 0,
            "dimension_scores": scoring.dimension_scores if scoring else {},
            "quality_level": quality.quality_level if quality else "暂无",
            "quality_score": quality.quality_score if quality else 0,
            "attention_passed": quality.attention_passed if quality else True,
            "duration": sheet.total_duration_seconds if sheet else 0,
        }

    if analysis_type == "quality_report":
        task_id = int(object_id or 0)
        task = db.query(Task).filter(Task.id == task_id).first()
        if not can_access_task(db, user, task):
            raise HTTPException(status_code=403, detail="无权限分析该任务数据")
        sheets = db.query(AnswerSheet).filter(AnswerSheet.task_id == task_id, AnswerSheet.status == "submitted").all()
        sheet_ids = [s.id for s in sheets]
        qs = db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id.in_(sheet_ids)).all() if sheet_ids else []
        by_level = {}
        for q in qs:
            by_level[q.quality_level] = by_level.get(q.quality_level, 0) + 1
        return {
            "task_id": task_id,
            "total": len(sheets),
            "effective_rate": round(len([q for q in qs if q.validity in ("valid", "basically_valid")]) / max(len(qs), 1) * 100, 1) if qs else 0,
            "suggest_retest_count": len([q for q in qs if q.suggest_retest]),
            "quality_level_distribution": by_level,
            "anomaly_summary": "按答题时长、连续同选项、注意力检测、矛盾题等规则综合评估。",
        }

    raise HTTPException(status_code=400, detail=f"不支持的分析类型: {analysis_type}")


def _write_ai_log(db: Session, user: User, analysis_type: str, object_id: str, status: str, duration_ms: int, model_name: str = "", error: str = "") -> None:
    db.add(AIAnalysisLog(
        user_id=user.id,
        user_role=user.role,
        school_id=None if user.role == "platform_admin" else user.school_id,
        object_type=analysis_type,
        object_id=str(object_id or ""),
        analysis_type=analysis_type,
        status=status,
        error_message=error[:500],
        duration_ms=duration_ms,
        model_name=model_name,
    ))
    db.commit()


# ========== 提示词模板 ==========

PROMPT_STUDENT_RISK = """你是一位专业的青少年心理健康专家。请根据以下学生的测评数据进行综合分析：

- 学生姓名：{name}
- 风险等级：{risk_level}
- 风险类型：{risk_type}
- 测评总分：{total_score}
- 各维度得分：{dimension_scores}
- 答题质量等级：{quality_level}
- 质量评分：{quality_score}
- 注意力检测：{attention_passed}
- 答题时长：{duration}

请从以下几个方面给出分析建议：
1. 数据解读（对各项得分进行专业解读）
2. 风险评估（评估当前风险等级和潜在问题）
3. 干预建议（给出具体的、可操作的建议）
4. 后续关注点（需要持续关注的方面）

请用温和、专业的中文进行表述，避免使用诊断性语言。"""

PROMPT_CLASS_REPORT = """你是一位专业的教育数据分析师。请根据以下班级测评数据进行综合分析：

- 班级名称：{class_name}
- 年级：{grade_name}
- 学生总数：{total_students}
- 已完成测评人数：{completed_count}
- 完成率：{completion_rate}%
- 风险等级分布：{risk_distribution}
- 平均分：{avg_score}
- 各维度平均分：{dimension_avg_scores}
- 答题质量概况：{quality_overview}

请从以下几个方面给出分析建议：
1. 整体情况概述（班级完成情况和整体水平）
2. 风险分布分析（重点关注的风险类型和人群）
3. 重点关注领域（得分异常偏高或偏低的维度）
4. 班级干预建议（针对班级整体的改进措施）

请用专业、客观的中文进行表述，注重数据驱动和可操作性。"""

PROMPT_OVERALL_REPORT = """你是一位专业的教育数据分析师。请根据以下学校整体测评数据进行综合分析：

- 学校名称：{school_name}
- 学生总数：{total_students}
- 已完成测评人数：{completed_count}
- 整体完成率：{completion_rate}%
- 风险等级分布：{risk_distribution}
- 各年级完成情况：{grade_overview}
- 各维度整体平均分：{dimension_avg_scores}
- 答题质量整体概况：{quality_overview}

请从以下几个方面给出分析建议：
1. 学校整体测评情况概述
2. 风险预警分析（整体风险态势和重点关注方向）
3. 年级差异分析（不同年级的对比和特点）
4. 整体改进建议（学校层面的系统性建议）

请用专业、客观的中文进行表述，注重数据驱动和可操作性。"""

PROMPT_QUALITY_REPORT = """你是一位专业的教育测评质量分析师。请根据以下答题质量数据进行综合分析：

- 答卷总数：{total}
- 有效答卷率：{effective_rate}%
- 建议复测人数：{suggest_retest_count}
- 质量等级分布：{quality_level_distribution}
- 异常情况汇总：{anomaly_summary}

请从以下几个方面给出分析建议：
1. 答题质量整体评估
2. 主要质量问题分析
3. 影响评估（质量问题对测评结果可靠性的影响）
4. 改进建议（如何提高答题质量）

请用专业、客观的中文进行表述，注重数据驱动和可操作性。"""

PROMPTS = {
    "student_risk": PROMPT_STUDENT_RISK,
    "class_report": PROMPT_CLASS_REPORT,
    "overall_report": PROMPT_OVERALL_REPORT,
    "quality_report": PROMPT_QUALITY_REPORT,
}


def _build_prompt(analysis_type: str, data: dict) -> str:
    """根据分析类型构建提示词"""
    template = PROMPTS.get(analysis_type)
    if not template:
        raise HTTPException(status_code=400, detail=f"不支持的分析类型: {analysis_type}")
    # 使用SafeDict避免KeyError
    return template.format_map(SafeDict(data))


# ===== API端点 =====

@router.get("/config")
def get_ai_config(user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    """获取AI配置（API密钥脱敏返回）"""
    config_map = _get_ai_configs(db)
    raw_key = config_map.get("ai_api_key", "")
    return APIResponse.success({
        "api_url": config_map.get("ai_api_url", ""),
        "api_key": _mask_api_key(raw_key),
        "model_name": config_map.get("ai_model_name", "deepseek-chat"),
        "configured": bool(config_map.get("ai_api_url") and config_map.get("ai_api_key")),
    })


@router.put("/config")
def update_ai_config(data: dict, user: User = Depends(require_role("school_admin")), db: Session = Depends(get_db)):
    """保存AI配置"""
    data = {
        "ai_api_url": data.get("ai_api_url", data.get("api_url", "")),
        "ai_api_key": data.get("ai_api_key", data.get("api_key", "")),
        "ai_model_name": data.get("ai_model_name", data.get("model_name", "")),
    }
    updated = []
    for key in AI_CONFIG_KEYS:
        if key not in data:
            continue
        value = str(data[key]) if data[key] is not None else ""

        # 特殊处理api_key：如果传入的值包含***（脱敏标记），说明用户未修改，保留原值
        if key == "ai_api_key" and "***" in value:
            existing = db.query(SystemConfig).filter(
                SystemConfig.config_key == key,
                SystemConfig.school_id.is_(None),
            ).first()
            if existing and existing.config_value:
                # 保留原值不变，跳过更新
                continue
            # 如果没有已有配置或已有配置为空，跳过
            continue

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
                description=f"AI分析配置 - {key}",
            )
            db.add(new_config)
            updated.append(key)

    db.commit()
    if updated:
        return APIResponse.success(message=f"AI配置已保存: {', '.join(updated)}")
    return APIResponse.success(message="无配置需要更新")


@router.post("/analyze")
def analyze_data(data: dict, request: Request, user: User = Depends(require_role("platform_admin", "school_admin", "teacher", "counselor")), db: Session = Depends(get_db)):
    """提交AI分析请求"""
    started = time.perf_counter()
    analysis_type = data.get("type", "")
    object_id = data.get("object_id") or (data.get("data") or {}).get("student_id") or (data.get("data") or {}).get("class_id") or (data.get("data") or {}).get("task_id") or (data.get("data") or {}).get("school_id")

    if analysis_type not in PROMPTS:
        raise HTTPException(status_code=400, detail=f"不支持的分析类型: {analysis_type}")
    request_data = _build_authorized_analysis_data(db, user, analysis_type, object_id)
    object_id = _require_ai_scope(db, user, analysis_type, request_data)

    # 读取AI配置
    config_map = _get_ai_configs(db)
    api_url = config_map.get("ai_api_url", "")
    api_key = config_map.get("ai_api_key", "")
    model_name = config_map.get("ai_model_name", "deepseek-chat")

    # 检查是否已配置
    if not api_url or not api_key:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _write_ai_log(db, user, analysis_type, object_id, "not_configured", duration_ms, model_name, "AI analysis service is not configured")
        log_operation(
            db,
            user,
            request,
            module="ai_analysis",
            action="analyze",
            object_type=analysis_type,
            object_id=object_id,
            result="failure",
            detail="AI analysis service is not configured",
        )
        return APIResponse.success({
            "analysis": f"{AI_DISCLAIMER}\n\n## 提示\n\nAI 分析服务暂未配置。\n\n请管理员在系统设置中配置 AI 接口地址、API 密钥和模型名称后再使用。",
            "model": "未配置",
            "configured": False,
        })

    # 构建提示词
    prompt = _build_prompt(analysis_type, request_data)

    # 调用AI API
    try:
        # 规范化API地址
        url = api_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            if url.endswith("/v1"):
                url += "/chat/completions"
            else:
                url += "/v1/chat/completions"

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": "你是一位专业的青少年心理健康与教育数据分析专家。请用中文回答问题，语气温和专业，避免诊断性语言。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            )

            if resp.status_code != 200:
                error_detail = resp.text[:300] if resp.text else "未知错误"
                duration_ms = int((time.perf_counter() - started) * 1000)
                _write_ai_log(db, user, analysis_type, object_id, "failure", duration_ms, model_name, error_detail)
                log_operation(
                    db,
                    user,
                    request,
                    module="ai_analysis",
                    action="analyze",
                    object_type=analysis_type,
                    object_id=object_id,
                    result="failure",
                    detail=f"http_status={resp.status_code};elapsed_ms={duration_ms};error={error_detail}",
                )
                return APIResponse.success({
                    "analysis": f"## AI接口调用失败\n\n{AI_DISCLAIMER}\n\nHTTP {resp.status_code}：{error_detail}",
                    "model": model_name,
                    "configured": True,
                })

            result = resp.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                content = f"AI返回数据异常：{json.dumps(result, ensure_ascii=False)[:300]}"
            duration_ms = int((time.perf_counter() - started) * 1000)
            _write_ai_log(db, user, analysis_type, object_id, "success", duration_ms, model_name)
            log_operation(
                db,
                user,
                request,
                module="ai_analysis",
                action="analyze",
                object_type=analysis_type,
                object_id=object_id,
                result="success",
                detail=f"elapsed_ms={duration_ms}",
            )

            return APIResponse.success({
                "analysis": f"{AI_DISCLAIMER}\n\n{content}",
                "model": model_name,
                "configured": True,
            })

    except httpx.ConnectError:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _write_ai_log(db, user, analysis_type, object_id, "failure", duration_ms, model_name, "connect_error")
        log_operation(db, user, request, module="ai_analysis", action="analyze", object_type=analysis_type, object_id=object_id, result="failure", detail=f"connect_error;elapsed_ms={duration_ms}")
        return APIResponse.success({
            "analysis": f"## 无法连接到AI接口\n\n{AI_DISCLAIMER}\n\nAI 分析服务暂时不可用，请稍后再试。",
            "model": model_name,
            "configured": True,
        })
    except httpx.TimeoutException:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _write_ai_log(db, user, analysis_type, object_id, "failure", duration_ms, model_name, "timeout")
        log_operation(db, user, request, module="ai_analysis", action="analyze", object_type=analysis_type, object_id=object_id, result="failure", detail=f"timeout;elapsed_ms={duration_ms}")
        return APIResponse.success({
            "analysis": f"## AI接口超时\n\n{AI_DISCLAIMER}\n\nAI 分析服务响应超时，请稍后再试。",
            "model": model_name,
            "configured": True,
        })
    except Exception as e:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _write_ai_log(db, user, analysis_type, object_id, "failure", duration_ms, model_name, str(e))
        log_operation(db, user, request, module="ai_analysis", action="analyze", object_type=analysis_type, object_id=object_id, result="failure", detail=f"error={str(e)[:300]};elapsed_ms={duration_ms}")
        return APIResponse.success({
            "analysis": f"## AI调用失败\n\n{AI_DISCLAIMER}\n\nAI 分析服务暂时不可用，请稍后再试。",
            "model": model_name,
            "configured": True,
        })
