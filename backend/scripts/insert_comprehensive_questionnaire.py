"""Insert the comprehensive questionnaire into the database."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.questionnaire import Questionnaire, Question, Option, ContradictionGroup
from app.models.task import Task, AnswerSheet, AnswerRecord
from app.models.risk import ScoringResult, QualityAssessment, RiskAlert, Intervention
from scripts.build_comprehensive_questionnaire import DIMENSIONS, QUESTIONS

# 每道题的风险标签映射 (按维度+题号)
RISK_TAG_MAP = {
    # self_trait: 反社会倾向(Q1-5,11-18), 自我安全(Q4,15,17,18)
    0: "antisocial",   # Q1 伤害他人
    1: "antisocial",   # Q2 看到痛苦
    2: "antisocial",   # Q3 弱者看法
    3: "self_safety",  # Q4 报复快感
    4: "antisocial",   # Q5 人性本恶
    5: "antisocial",   # Q6 世界虚伪
    6: "antisocial",   # Q7 优越感
    7: "antisocial",   # Q8 聪明俯视
    8: "antisocial",   # Q9 他人愚蠢
    9: "antisocial",   # Q10 疏离感
    10: "antisocial",  # Q11 不正当手段
    11: "antisocial",  # Q12 欺骗信任
    13: "antisocial",  # Q14 掌控力
    15: "antisocial",  # Q16 规矩约束弱者
    16: "self_safety", # Q17 破坏冲动
    17: "self_safety", # Q18 违法想法
    # family: 家庭支持缺失
    21: "family_support",  # Q22 不交流
    28: "family_support",  # Q29 当众数落
    29: "family_support",  # Q30 教育绝望
    30: "family_support",  # Q31 希望家里有人
    31: "family_support",  # Q32 独自过夜
    32: "family_support",  # Q33 被抛弃感
    33: "family_support",  # Q34 有条件的爱
    34: "family_support",  # Q35 无依靠
    # digital: 网络风险
    51: "digital_risk",  # Q52 暴力色情视频
    52: "digital_risk",  # Q53 刺激话题群
    53: "digital_risk",  # Q54 线下聚会
    54: "digital_risk",  # Q55 网络欺凌
    55: "digital_risk",  # Q56 极端思想
    56: "digital_risk",  # Q57 模仿危险行为
    58: "digital_risk",  # Q59 隐瞒行踪
    61: "digital_risk",  # Q62 长时间外出
    # social_rule: 自我安全
    68: "self_safety",  # Q69 暴力手段
    69: "self_safety",  # Q70 叫人堵截
    72: "self_safety",  # Q73 管制器具
    75: "self_safety",  # Q76 不良人员共处
    # social_support: 家庭支持
    96: "family_support",  # Q97 家庭变故
    97: "family_support",  # Q98 没人管自卑
    98: "family_support",  # Q99 没人管失落
}

def insert():
    db = SessionLocal()
    existing = db.query(Questionnaire).filter(Questionnaire.title == "金盾护苗专项综合调研问卷").first()
    if existing:
        print(f"Already exists (id={existing.id}), deleting old one...")
        # 级联删除所有关联数据
        task_ids = [t.id for t in db.query(Task.id).filter(Task.questionnaire_id == existing.id).all()]
        if task_ids:
            sheet_ids = [s.id for s in db.query(AnswerSheet.id).filter(AnswerSheet.task_id.in_(task_ids)).all()]
            if sheet_ids:
                db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
                db.query(ScoringResult).filter(ScoringResult.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
                db.query(QualityAssessment).filter(QualityAssessment.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
                alert_ids = [a.id for a in db.query(RiskAlert.id).filter(RiskAlert.answer_sheet_id.in_(sheet_ids)).all()]
                if alert_ids:
                    db.query(Intervention).filter(Intervention.risk_alert_id.in_(alert_ids)).delete(synchronize_session=False)
                db.query(RiskAlert).filter(RiskAlert.answer_sheet_id.in_(sheet_ids)).delete(synchronize_session=False)
                db.query(AnswerSheet).filter(AnswerSheet.id.in_(sheet_ids)).delete(synchronize_session=False)
            db.query(Task).filter(Task.id.in_(task_ids)).delete(synchronize_session=False)
        old_qids = [q.id for q in db.query(Question.id).filter(Question.questionnaire_id == existing.id).all()]
        if old_qids:
            db.query(AnswerRecord).filter(AnswerRecord.question_id.in_(old_qids)).delete(synchronize_session=False)
            db.query(Option).filter(Option.question_id.in_(old_qids)).delete(synchronize_session=False)
        db.query(ContradictionGroup).filter(ContradictionGroup.questionnaire_id == existing.id).delete()
        db.query(Question).filter(Question.questionnaire_id == existing.id).delete()
        db.delete(existing)
        db.commit()

    qnr = Questionnaire(
        title="金盾护苗专项综合调研问卷",
        description="综合覆盖自我认知、家庭环境、校园生活、网络行为、社会规则、社会支持六大维度，用于青少年风险筛查与关爱帮扶。本问卷整合了原有6份专项问卷的精华题目，去除重复和争议内容，保留100道核心风险信号题目。",
        category="custom",
        applicable_grades="四年级,五年级,六年级,初一,初二,初三,高一,高二,高三",
        is_builtin=True,
        status="active",
        source_type="jindun_comprehensive",
        code="builtin-jindun-comprehensive-v1",
        disclaimer="本问卷仅用于学校开展关爱帮扶工作，不会对外公开。个人数据严格保密，仅授权人员可查看。测评结果不会影响你的学习成绩和在校评价。",
        dimensions=[{"code": d["code"], "title": d["title"]} for d in DIMENSIONS],
        scoring_rule={
            "method": "sum",
            "score_types": ["single_choice"],
            "exclude_attention_check": True,
        },
        risk_rules={
            "basis": "total_score",
            "total_score_ranges": [
                {"min": 100, "max": 180, "level": "low"},
                {"min": 181, "max": 240, "level": "medium"},
                {"min": 241, "max": 310, "level": "high"},
                {"min": 311, "max": 400, "level": "urgent"},
            ],
            "dimension_pct_rules": [
                {"dimension": "self_trait", "min_pct": 75, "level": "high"},
                {"dimension": "social_rule", "min_pct": 75, "level": "high"},
                {"dimension": "family", "min_pct": 70, "level": "medium"},
                {"dimension": "digital", "min_pct": 70, "level": "medium"},
            ],
            "risk_tag_rules": {
                "self_safety": {"level": "high", "type_label": "自我安全关注信号", "min_count": 2},
                "antisocial": {"level": "medium", "type_label": "反社会倾向信号", "min_count": 3},
                "family_support": {"level": "medium", "type_label": "家庭支持缺失信号", "min_count": 3},
                "digital_risk": {"level": "medium", "type_label": "网络风险行为信号", "min_count": 3},
            },
            "messages": {
                "low": "综合评估未发现明显风险信号，学生心理状态和生活环境总体健康。建议保持常规关注。",
                "medium": "部分维度存在关注信号，建议班主任加强日常观察和沟通，了解学生的具体困难。",
                "high": "多个维度存在明显风险信号，建议学校安排心理辅导老师进行专业评估，并启动关爱帮扶流程。",
                "urgent": "存在高风险信号，建议学校立即启动干预流程，必要时联系家长和专业机构进行综合帮扶。",
            },
        },
        quality_rules={
            "all_negative_detection": True,
            "too_fast_detection": True,
            "fast_min_seconds": 1,
            "attention_check": False,
            "contradiction_check": True,
            "pattern_check": True,
            "consecutive_same": True,
            "consecutive_max": 12,
            "same_option_ratio": True,
            "same_option_max": 90,
        },
    )
    db.add(qnr)
    db.flush()

    for idx, (dim, title, opts) in enumerate(QUESTIONS):
        q = Question(
            questionnaire_id=qnr.id,
            title=title,
            type="single_choice",
            dimension=dim,
            risk_tag=RISK_TAG_MAP.get(idx, ""),
            sort_order=idx + 1,
            required=True,
            is_reverse=False,
            is_attention_check=False,
        )
        db.add(q)
        db.flush()
        for oidx, (content, score, is_risk) in enumerate(opts):
            db.add(Option(
                question_id=q.id,
                content=content,
                score=score,
                sort_order=oidx + 1,
                is_risk_option=is_risk,
            ))

    db.commit()
    print(f"Created questionnaire id={qnr.id}, {len(QUESTIONS)} questions")
    db.close()

if __name__ == "__main__":
    insert()
