"""
一次性脚本：为已下发的任务补开题目/选项乱序

用法：
    cd backend
    python scripts/enable_shuffle_for_task.py <task_id>

功能：
1. 设置 Task.shuffle_questions = True, Task.shuffle_options = True
2. 对所有 status='in_progress' 的 AnswerSheet 重新生成乱序的 question_order 和 option_orders
3. 对已有 AnswerRecord 重新计算 selected_display_index
4. 跳过已提交的答卷（status='submitted'）

安全性：
- answer_content 存的是选项真实 ID，评分不依赖顺序
- selected_display_index 仅用于质量检测（规律作答检测），重新计算后仍然准确
"""
import sys
import os
import random

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.task import Task, AnswerSheet, AnswerRecord
from app.models.questionnaire import Question, Option


def enable_shuffle(task_id: int):
    db = SessionLocal()
    try:
        # 1. 找到任务
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            print(f"❌ 任务 ID={task_id} 不存在")
            return

        print(f"📋 任务: {task.name} (ID={task_id})")
        print(f"   问卷ID: {task.questionnaire_id}")
        print(f"   当前 shuffle_questions={task.shuffle_questions}, shuffle_options={task.shuffle_options}")

        # 2. 开启乱序
        task.shuffle_questions = True
        task.shuffle_options = True

        # 3. 查询问卷的所有题目和选项
        questions = (
            db.query(Question)
            .filter(Question.questionnaire_id == task.questionnaire_id)
            .order_by(Question.sort_order)
            .all()
        )
        all_question_ids = [q.id for q in questions]
        print(f"   共 {len(questions)} 道题目")

        # 预加载每题的选项ID列表
        option_ids_map = {}
        for q in questions:
            if q.type in ("single_choice", "multi_choice"):
                opts = db.query(Option).filter(Option.question_id == q.id).order_by(Option.sort_order).all()
                option_ids_map[q.id] = [o.id for o in opts]

        # 4. 找到所有 in_progress 的答卷
        sheets = (
            db.query(AnswerSheet)
            .filter(AnswerSheet.task_id == task_id)
            .all()
        )
        in_progress = [s for s in sheets if s.status == "in_progress"]
        submitted = [s for s in sheets if s.status == "submitted"]

        print(f"   答卷总数: {len(sheets)} (进行中: {len(in_progress)}, 已提交: {len(submitted)})")

        if not in_progress:
            print("   ⚠️ 没有进行中的答卷需要处理")
            db.commit()
            print("✅ 任务乱序设置已更新")
            return

        # 5. 对每张 in_progress 答卷重新生成乱序
        for sheet in in_progress:
            # 生成新的题目乱序
            new_question_order = list(all_question_ids)
            random.shuffle(new_question_order)
            sheet.question_order = new_question_order

            # 生成新的选项乱序
            new_option_orders = {}
            for qid, opt_ids in option_ids_map.items():
                shuffled = list(opt_ids)
                random.shuffle(shuffled)
                new_option_orders[str(qid)] = shuffled
            sheet.option_orders = new_option_orders

            # 重新计算已有 AnswerRecord 的 selected_display_index
            records = db.query(AnswerRecord).filter(AnswerRecord.answer_sheet_id == sheet.id).all()
            for record in records:
                content = record.answer_content
                if not content or not isinstance(content, dict):
                    continue
                selected_id = content.get("selected_option_id")
                if not selected_id:
                    selected_ids = content.get("selected_option_ids") or []
                    selected_id = selected_ids[0] if selected_ids else None
                if not selected_id:
                    continue
                order_list = new_option_orders.get(str(record.question_id)) or []
                if order_list:
                    try:
                        record.selected_display_index = order_list.index(int(selected_id))
                    except (ValueError, TypeError):
                        pass

            print(f"   ✅ 答卷 ID={sheet.id} (学生ID={sheet.student_id}) 已重新乱序，{len(records)} 条答题记录已更新")

        db.commit()
        print(f"\n✅ 完成！共处理 {len(in_progress)} 张进行中的答卷")
        print(f"   已提交的 {len(submitted)} 张答卷未受影响")

    except Exception as e:
        db.rollback()
        print(f"❌ 错误: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/enable_shuffle_for_task.py <task_id>")
        sys.exit(1)

    task_id = int(sys.argv[1])
    enable_shuffle(task_id)
