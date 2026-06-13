#!/usr/bin/env python3
"""
重新评分现有风险预警记录
使用新的 min_count 阈值和风险等级升级逻辑
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from app.models.task import AnswerSheet, AnswerRecord
from app.models.questionnaire import Questionnaire, Question, Option
from app.models.risk import RiskAlert, ScoringResult
from app.services.scoring_service import calculate_scores
from sqlalchemy.orm import Session

def rescore_all():
    db = next(get_db())

    # 获取综合问卷
    questionnaire = db.query(Questionnaire).filter(Questionnaire.id == 40).first()
    if not questionnaire:
        print("问卷 40 不存在")
        return

    print(f"问卷: {questionnaire.title}")
    print(f"风险规则: {questionnaire.risk_rules.get('risk_tag_rules', {})}")
    print()

    # 获取所有已完成的答题记录
    answer_sheets = db.query(AnswerSheet).filter(
        AnswerSheet.questionnaire_id == 40,
        AnswerSheet.status.in_(['completed', 'submitted'])
    ).all()

    print(f"找到 {len(answer_sheets)} 条答题记录")
    print()

    updated_count = 0
    for sheet in answer_sheets:
        # 获取该答题记录的评分结果
        scoring = db.query(ScoringResult).filter(
            ScoringResult.answer_sheet_id == sheet.id
        ).first()

        if not scoring:
            print(f"答题记录 {sheet.id} 没有评分结果，跳过")
            continue

        # 重新计算分数
        try:
            new_scoring = calculate_scores(db, sheet.id)
            if new_scoring:
                old_risk_level = scoring.risk_level
                new_risk_level = new_scoring.get('risk_level', old_risk_level)
                old_risk_type = scoring.risk_type
                new_risk_type = new_scoring.get('risk_type', old_risk_type)

                # 更新评分结果
                scoring.risk_level = new_risk_level
                scoring.risk_type = new_risk_type
                scoring.triggered_rules = new_scoring.get('triggered_rules', [])

                # 更新风险预警
                alert = db.query(RiskAlert).filter(
                    RiskAlert.answer_sheet_id == sheet.id
                ).first()

                if alert:
                    alert.risk_level = new_risk_level
                    alert.risk_type = new_risk_type

                if old_risk_level != new_risk_level or old_risk_type != new_risk_type:
                    updated_count += 1
                    print(f"更新 答题记录 {sheet.id}:")
                    print(f"  风险等级: {old_risk_level} -> {new_risk_level}")
                    print(f"  风险类型: {old_risk_type} -> {new_risk_type}")
        except Exception as e:
            print(f"重新评分 答题记录 {sheet.id} 失败: {e}")

    db.commit()
    print()
    print(f"完成! 更新了 {updated_count} 条记录")

if __name__ == "__main__":
    rescore_all()
