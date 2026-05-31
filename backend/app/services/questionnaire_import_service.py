"""
问卷导入导出服务 — Excel 模板驱动

模板格式:
  Sheet 1 "题目": 每行一道题，选项以3列一组(内容/分值/风险)排列，最多6个选项
  Sheet 2 "问卷设置": key-value 逐行填写问卷元数据
  Sheet 3 "填写说明": 字段说明（不参与解析）
"""

from io import BytesIO
from typing import Any

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from sqlalchemy.orm import Session

from ..models.questionnaire import (
    ContradictionGroup,
    Option,
    Question,
    Questionnaire,
    QuestionType,
)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# Sheet 1 表头
QUESTION_HEADERS = [
    "题号", "题目编码", "题目内容", "题目类型", "所属维度", "风险标签", "反向计分",
    "选项1内容", "选项1分值", "选项1风险",
    "选项2内容", "选项2分值", "选项2风险",
    "选项3内容", "选项3分值", "选项3风险",
    "选项4内容", "选项4分值", "选项4风险",
    "选项5内容", "选项5分值", "选项5风险",
    "选项6内容", "选项6分值", "选项6风险",
    "注意力检测", "正确答案",
]

# 题目类型映射 (中文 → 代码)
TYPE_MAP = {
    "单选": "single_choice", "单选题": "single_choice",
    "多选": "multi_choice", "多选题": "multi_choice",
    "判断": "true_false", "判断题": "true_false",
    "量表": "scale", "量表题": "scale",
    "填空": "fill_blank", "填空题": "fill_blank",
    "简答": "short_answer", "简答题": "short_answer",
}

# 类型代码 → 中文
TYPE_REVERSE = {v: k for k, v in TYPE_MAP.items()}
TYPE_REVERSE.setdefault("single_choice", "单选")

# Sheet 2 问卷设置字段顺序
SETTINGS_ROWS = [
    ("问卷标题", "必填。问卷的显示名称"),
    ("问卷描述", "问卷用途说明"),
    ("分类", "可选值: mental_health / bullying / internet_addiction / family_relationship / safety_awareness / interpersonal / academic_pressure / custom"),
    ("适用年级", "逗号分隔，如: 初一,初二,初三"),
    ("维度列表", "格式: 编码:名称，分号分隔。如 empathy:同理心;egocentrism:自我中心"),
    ("评分方式", "默认 sum"),
    ("风险判定依据", "默认 total_score。可选: total_score / total_score_pct"),
    ("低风险范围", "格式: 最小值-最大值，如 26-50"),
    ("中风险范围", "格式: 最小值-最大值，如 51-75"),
    ("高风险范围", "格式: 最小值-最大值，如 76-104"),
    ("紧急风险范围", "(可选) 格式: 最小值-最大值"),
    ("风险标签规则", "(可选) 格式: 标签:级别:中文标签，多条用分号分隔。如 self_safety:urgent:风险信号"),
    ("维度百分比规则", "(可选) 格式: 维度:百分比:级别，多条用分号分隔。如 antisocial:80:urgent"),
    ("低风险提示语", "低风险结果的建议文案"),
    ("中风险提示语", "中风险结果的建议文案"),
    ("高风险提示语", "高风险结果的建议文案"),
    ("紧急风险提示语", "(可选) 紧急风险结果的建议文案"),
]

YES_VALUES = {"是", "yes", "true", "1", "Y", "y"}
NO_VALUES = {"否", "no", "false", "0", "N", "n", ""}


# ---------------------------------------------------------------------------
# 样式常量
# ---------------------------------------------------------------------------

HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
SETTINGS_KEY_FONT = Font(bold=True, size=11)
SETTINGS_HINT_FONT = Font(italic=True, color="888888", size=10)
TITLE_FONT = Font(bold=True, size=14)
SAMPLE_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")


# ---------------------------------------------------------------------------
# 模板生成
# ---------------------------------------------------------------------------

def generate_import_template() -> bytes:
    """生成空白 Excel 导入模板，返回字节流"""
    wb = openpyxl.Workbook()

    # ---- Sheet 1: 题目 ----
    ws_q = wb.active
    ws_q.title = "题目"
    _write_headers(ws_q, QUESTION_HEADERS)
    _set_question_col_widths(ws_q)
    # 示例行
    sample = [
        1, "empathy_1", "当你意识到自己做了一件伤害他人的事，你的心情是？", "单选", "empathy", "self_safety", "否",
        "非常愧疚", 1, "否",
        "觉得无所谓", 2, "否",
        "反而觉得掌控感", 3, "否",
        "觉得对方活该", 4, "否",
        "", "", "",
        "", "", "",
        "否", "",
    ]
    ws_q.append(sample)
    for cell in ws_q[2]:
        cell.fill = SAMPLE_FILL
    # 第二行示例
    sample2 = [
        2, "empathy_2", "当你看到别人处于极度痛苦中，你的第一反应是？", "单选", "empathy", "self_safety", "否",
        "想要帮助", 1, "否",
        "感到不适", 2, "否",
        "毫无波动", 3, "否",
        "感到一丝兴奋", 4, "是",
        "", "", "",
        "", "", "",
        "否", "",
    ]
    ws_q.append(sample2)
    for cell in ws_q[3]:
        cell.fill = SAMPLE_FILL

    # ---- Sheet 2: 问卷设置 ----
    ws_s = wb.create_sheet("问卷设置")
    ws_s.column_dimensions["A"].width = 18
    ws_s.column_dimensions["B"].width = 50
    ws_s.column_dimensions["C"].width = 60

    ws_s.append(["字段", "值", "填写说明"])
    _style_header_row(ws_s[1])

    for field_name, hint in SETTINGS_ROWS:
        row_num = ws_s.max_row + 1
        ws_s.append([field_name, "", hint])
        ws_s.cell(row=row_num, column=1).font = SETTINGS_KEY_FONT
        ws_s.cell(row=row_num, column=3).font = SETTINGS_HINT_FONT

    # 填入示例值
    ws_s["B1"] = "青少年自我认知与心理特质调研"
    ws_s["B3"] = "custom"
    ws_s["B4"] = "初一,初二,初三"
    ws_s["B5"] = "empathy:同理心与道德感知;egocentrism:自我中心与优越感"
    ws_s["B6"] = "sum"
    ws_s["B7"] = "total_score"
    ws_s["B8"] = "26-50"
    ws_s["B9"] = "51-75"
    ws_s["B10"] = "76-104"

    # ---- Sheet 3: 填写说明 ----
    ws_i = wb.create_sheet("填写说明")
    ws_i.column_dimensions["A"].width = 80
    instructions = [
        "【问卷导入模板 — 填写说明】",
        "",
        "一、基本流程",
        "  1. 在「问卷设置」Sheet 中填写问卷的基本信息",
        "  2. 在「题目」Sheet 中逐行填写每道题目及其选项",
        "  3. 保存为 .xlsx 文件后在平台上传导入",
        "",
        "二、题目 Sheet 字段说明",
        "  · 题号: 题目的顺序编号（数字），必填",
        "  · 题目编码: 英文标识符（如 empathy_1），可选",
        "  · 题目内容: 题目的具体文字，必填",
        "  · 题目类型: 单选/多选/判断/量表/填空/简答，必填",
        "  · 所属维度: 对应「维度列表」中的编码，可选",
        "  · 风险标签: 如 self_safety / safety_awareness / family_support 等，可选",
        "  · 反向计分: 填 是 或 否，默认否",
        "  · 选项: 每个选项占 3 列（内容/分值/是否风险），最多 6 个选项",
        "    - 选项内容: 选项的显示文字",
        "    - 选项分值: 整数分值",
        "    - 选项风险: 填 是 表示该选项为高风险选项",
        "  · 注意力检测: 填 是 表示该题为注意力检测题",
        "  · 正确答案: 注意力检测题的正确答案（仅注意力检测题需要）",
        "",
        "三、问卷设置 Sheet 说明",
        "  · 问卷标题: 必填",
        "  · 分类: 必填，可选值见 C 列说明",
        "  · 维度列表: 格式 编码:名称，多条用分号分隔",
        "  · 风险范围: 格式 最小值-最大值，从低到高填写",
        "  · 风险标签规则: 格式 标签:级别:中文说明，级别可选 low/medium/high/urgent",
        "  · 维度百分比规则: 格式 维度编码:百分比:级别",
        "",
        "四、注意事项",
        "  · 绿色行为例数据行，导入时会被解析，如不需要请删除",
        "  · 题目行如果整行为空则跳过",
        "  · 填空题和简答题不需要填写选项列",
        "  · 导入后问卷为「草稿」状态，需手动发布",
    ]
    for i, line in enumerate(instructions, 1):
        ws_i.cell(row=i, column=1, value=line)
    ws_i["A1"].font = TITLE_FONT

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


# ---------------------------------------------------------------------------
# 解析与导入
# ---------------------------------------------------------------------------

def parse_questionnaire_excel(file_bytes: bytes) -> tuple[dict, list[dict], list[dict]]:
    """解析 Excel，返回 (settings, questions, errors)"""
    errors: list[dict] = []
    questions: list[dict] = []

    try:
        wb = openpyxl.load_workbook(BytesIO(file_bytes))
    except Exception as e:
        errors.append({"row": 0, "field": "文件", "message": f"无法读取Excel文件: {str(e)}"})
        return {}, [], errors

    # ---- 解析 Sheet 2: 问卷设置 ----
    settings: dict[str, str] = {}
    if "问卷设置" in wb.sheetnames:
        ws_s = wb["问卷设置"]
        for row in ws_s.iter_rows(min_row=2, max_col=2, values_only=True):
            key, val = row[0], row[1]
            if key and val is not None:
                settings[str(key).strip()] = str(val).strip()

    # 校验设置必填项
    if not settings.get("问卷标题"):
        errors.append({"row": 0, "field": "问卷标题", "message": "问卷标题不能为空"})

    # 解析维度
    dimensions = _parse_dimensions(settings.get("维度列表", ""))
    dim_codes = {d["code"] for d in dimensions}

    # 解析风险范围
    risk_ranges, range_errors = _parse_risk_ranges(settings)
    errors.extend(range_errors)

    # 解析风险标签规则
    risk_tag_rules = _parse_risk_tag_rules(settings.get("风险标签规则", ""))

    # 解析维度百分比规则
    dimension_pct_rules = _parse_dimension_pct_rules(settings.get("维度百分比规则", ""))

    # 构建完整 settings dict
    settings["_dimensions"] = dimensions
    settings["_risk_ranges"] = risk_ranges
    settings["_risk_tag_rules"] = risk_tag_rules
    settings["_dimension_pct_rules"] = dimension_pct_rules

    # ---- 解析 Sheet 1: 题目 ----
    ws_q = wb.worksheets[0]  # 第一个 sheet
    header_row = [str(c.value or "").strip() if c.value else "" for c in ws_q[1]]

    for row_idx, row in enumerate(ws_q.iter_rows(min_row=2, values_only=True), start=2):
        # 跳过空行
        title_val = _safe_str(row[2]) if len(row) > 2 else ""
        if not title_val:
            continue

        q: dict[str, Any] = {
            "sort_order": _safe_int(row[0], row_idx - 1),
            "code": _safe_str(row[1]) if len(row) > 1 else "",
            "title": title_val,
            "type": "single_choice",
            "dimension": _safe_str(row[4]) if len(row) > 4 else "",
            "risk_tag": _safe_str(row[5]) if len(row) > 5 else "",
            "is_reverse": False,
            "options": [],
            "is_attention_check": False,
            "attention_correct_answer": "",
        }

        # 题目类型
        type_str = _safe_str(row[3]) if len(row) > 3 else ""
        if type_str:
            resolved = TYPE_MAP.get(type_str)
            if resolved:
                q["type"] = resolved
            elif type_str in [e.value for e in QuestionType]:
                q["type"] = type_str
            else:
                errors.append({"row": row_idx, "field": "题目类型", "message": f"未知的题目类型: {type_str}"})

        # 反向计分
        if len(row) > 6:
            q["is_reverse"] = _safe_str(row[6]) in YES_VALUES

        # 选项解析 (列 7-24, 每3列一组)
        for opt_idx in range(6):
            base_col = 7 + opt_idx * 3
            if base_col >= len(row):
                break
            opt_content = _safe_str(row[base_col])
            if not opt_content:
                break
            opt_score = _safe_int(row[base_col + 1], 0) if base_col + 1 < len(row) else 0
            opt_risk = False
            if base_col + 2 < len(row) and _safe_str(row[base_col + 2]) in YES_VALUES:
                opt_risk = True
            q["options"].append({
                "content": opt_content,
                "score": opt_score,
                "sort_order": opt_idx + 1,
                "is_risk_option": opt_risk,
            })

        # 注意力检测
        if len(row) > 25:
            q["is_attention_check"] = _safe_str(row[25]) in YES_VALUES
        if len(row) > 26:
            q["attention_correct_answer"] = _safe_str(row[26])

        # 校验
        if not q["title"]:
            errors.append({"row": row_idx, "field": "题目内容", "message": "题目内容不能为空"})
        if q["type"] in ("single_choice", "multi_choice", "scale") and not q["options"]:
            errors.append({"row": row_idx, "field": "选项", "message": f"题目类型 {q['type']} 至少需要一个选项"})
        if q["dimension"] and dim_codes and q["dimension"] not in dim_codes:
            errors.append({"row": row_idx, "field": "所属维度", "message": f"维度编码 '{q['dimension']}' 不在维度列表中"})

        questions.append(q)

    if not questions and not errors:
        errors.append({"row": 0, "field": "题目", "message": "未找到任何题目数据"})

    return settings, questions, errors


def import_questionnaire(
    db: Session,
    file_bytes: bytes,
    school_id: int | None,
    created_by: int,
) -> dict:
    """完整导入流程: 解析 → 校验 → 创建问卷。返回结果 dict"""
    settings, questions, errors = parse_questionnaire_excel(file_bytes)

    if errors:
        return {"success": False, "errors": errors, "total_errors": len(errors)}

    # 构建问卷记录
    dimensions = settings.get("_dimensions", [])
    risk_ranges = settings.get("_risk_ranges", [])
    risk_tag_rules = settings.get("_risk_tag_rules", {})
    dimension_pct_rules = settings.get("_dimension_pct_rules", [])

    # scoring_rule
    scoring_rule = {
        "method": settings.get("评分方式", "sum") or "sum",
        "score_types": ["single_choice", "multi_choice", "scale", "true_false"],
        "exclude_attention_check": True,
        "exclude_types": ["fill_blank", "short_answer"],
    }

    # risk_rules
    basis = settings.get("风险判定依据", "total_score") or "total_score"
    risk_rules: dict[str, Any] = {"basis": basis}

    if basis == "total_score":
        risk_rules["total_score_ranges"] = risk_ranges
    elif basis == "total_score_pct":
        risk_rules["total_pct_ranges"] = risk_ranges

    if risk_tag_rules:
        risk_rules["risk_tag_rules"] = risk_tag_rules
    if dimension_pct_rules:
        risk_rules["dimension_pct_rules"] = dimension_pct_rules

    # messages
    messages = {}
    level_map = {"低风险提示语": "low", "中风险提示语": "medium", "高风险提示语": "high", "紧急风险提示语": "urgent"}
    for key, level in level_map.items():
        msg = settings.get(key, "")
        if msg:
            messages[level] = msg
    if messages:
        risk_rules["messages"] = messages

    # 创建问卷
    qn = Questionnaire(
        school_id=school_id,
        title=settings.get("问卷标题", "未命名问卷"),
        description=settings.get("问卷描述", ""),
        category=settings.get("分类", "custom") or "custom",
        applicable_grades=settings.get("适用年级", ""),
        is_builtin=False,
        source_type="imported",
        disclaimer="本问卷通过模板导入创建。",
        dimensions=dimensions,
        scoring_rule=scoring_rule,
        risk_rules=risk_rules,
        quality_rules={},
        status="draft",
        created_by=created_by,
        version=1,
        locked_after_publish=False,
        rule_version="imported-v1",
    )
    db.add(qn)
    db.flush()

    # 创建题目和选项
    for q_data in questions:
        question = Question(
            questionnaire_id=qn.id,
            code=q_data.get("code", ""),
            title=q_data["title"],
            type=q_data["type"],
            required=True,
            sort_order=q_data.get("sort_order", 0),
            dimension=q_data.get("dimension", ""),
            risk_tag=q_data.get("risk_tag", ""),
            is_reverse=q_data.get("is_reverse", False),
            is_attention_check=q_data.get("is_attention_check", False),
            attention_correct_answer=q_data.get("attention_correct_answer", ""),
        )
        db.add(question)
        db.flush()

        for opt_data in q_data.get("options", []):
            option = Option(
                question_id=question.id,
                content=opt_data["content"],
                score=opt_data.get("score", 0),
                sort_order=opt_data.get("sort_order", 0),
                is_risk_option=opt_data.get("is_risk_option", False),
            )
            db.add(option)

    db.commit()
    db.refresh(qn)

    return {
        "success": True,
        "questionnaire_id": qn.id,
        "title": qn.title,
        "question_count": len(questions),
        "status": qn.status,
        "message": f"导入成功，共 {len(questions)} 道题，问卷已创建为草稿状态",
    }


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------

def export_questionnaire_to_excel(db: Session, questionnaire_id: int) -> bytes:
    """导出单个问卷为 Excel"""
    qn = db.query(Questionnaire).filter(Questionnaire.id == questionnaire_id).first()
    if not qn:
        raise ValueError("问卷不存在")

    questions = (
        db.query(Question)
        .filter(Question.questionnaire_id == questionnaire_id)
        .order_by(Question.sort_order)
        .all()
    )

    wb = openpyxl.Workbook()

    # ---- Sheet 1: 题目 ----
    ws_q = wb.active
    ws_q.title = "题目"
    _write_headers(ws_q, QUESTION_HEADERS)
    _set_question_col_widths(ws_q)

    for q in questions:
        opts = sorted(q.options, key=lambda o: o.sort_order)
        row_data: list[Any] = [
            q.sort_order,
            q.code or "",
            q.title,
            TYPE_REVERSE.get(q.type, q.type),
            q.dimension or "",
            q.risk_tag or "",
            "是" if q.is_reverse else "否",
        ]
        for i in range(6):
            if i < len(opts):
                row_data.extend([opts[i].content, opts[i].score, "是" if opts[i].is_risk_option else "否"])
            else:
                row_data.extend(["", "", ""])
        row_data.extend(["是" if q.is_attention_check else "否", q.attention_correct_answer or ""])
        ws_q.append(row_data)

    # ---- Sheet 2: 问卷设置 ----
    ws_s = wb.create_sheet("问卷设置")
    ws_s.column_dimensions["A"].width = 18
    ws_s.column_dimensions["B"].width = 50
    ws_s.column_dimensions["C"].width = 60
    ws_s.append(["字段", "值", "填写说明"])
    _style_header_row(ws_s[1])

    # 维度列表
    dims_str = ";".join(f"{d['code']}:{d['title']}" for d in (qn.dimensions or []))

    # 风险范围
    risk_rules = qn.risk_rules or {}
    basis = risk_rules.get("basis", "total_score")
    ranges_key = "total_score_ranges" if basis == "total_score" else "total_pct_ranges"
    ranges = risk_rules.get(ranges_key, [])
    range_vals = {}
    for r in ranges:
        level = r.get("level", "")
        range_vals[level] = f"{r.get('min', 0)}-{r.get('max', 0)}"

    # 风险标签规则
    tag_rules = risk_rules.get("risk_tag_rules", {})
    tag_str = ";".join(f"{k}:{v.get('level','')}:v.get('type_label','')" for k, v in tag_rules.items()) if isinstance(tag_rules, dict) else ""

    # 维度百分比规则
    dim_pct = risk_rules.get("dimension_pct_rules", [])
    dim_pct_str = ";".join(f"{r.get('dimension','')}:{r.get('min_pct','')}:{r.get('level','')}" for r in dim_pct) if isinstance(dim_pct, list) else ""

    # 提示语
    messages = risk_rules.get("messages", {})

    settings_values = [
        qn.title or "",
        qn.description or "",
        qn.category or "custom",
        qn.applicable_grades or "",
        dims_str,
        (qn.scoring_rule or {}).get("method", "sum"),
        basis,
        range_vals.get("low", ""),
        range_vals.get("medium", ""),
        range_vals.get("high", ""),
        range_vals.get("urgent", ""),
        tag_str,
        dim_pct_str,
        messages.get("low", ""),
        messages.get("medium", ""),
        messages.get("high", ""),
        messages.get("urgent", ""),
    ]

    for i, (field_name, hint) in enumerate(SETTINGS_ROWS):
        row_num = i + 2
        ws_s.cell(row=row_num, column=1, value=field_name).font = SETTINGS_KEY_FONT
        ws_s.cell(row=row_num, column=2, value=settings_values[i] if i < len(settings_values) else "")
        ws_s.cell(row=row_num, column=3, value=hint).font = SETTINGS_HINT_FONT

    # ---- Sheet 3: 填写说明 (与模板相同) ----
    _add_instructions_sheet(wb)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def batch_export_to_zip(db: Session, questionnaire_ids: list[int]) -> bytes:
    """批量导出多个问卷为 ZIP 文件"""
    import zipfile

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for qid in questionnaire_ids:
            try:
                excel_bytes = export_questionnaire_to_excel(db, qid)
                qn = db.query(Questionnaire).filter(Questionnaire.id == qid).first()
                safe_name = _safe_filename(qn.title if qn else f"questionnaire_{qid}")
                zf.writestr(f"{safe_name}.xlsx", excel_bytes)
            except Exception:
                continue

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _write_headers(ws, headers: list[str]):
    ws.append(headers)
    _style_header_row(ws[1])


def _style_header_row(row):
    for cell in row:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _set_question_col_widths(ws):
    widths = {
        "A": 6, "B": 14, "C": 40, "D": 10, "E": 12, "F": 14, "G": 10,
    }
    for col_letter, w in widths.items():
        ws.column_dimensions[col_letter].width = w
    # 选项列统一宽度
    for col_idx in range(8, 28):  # H to AA
        from openpyxl.utils import get_column_letter
        letter = get_column_letter(col_idx)
        ws.column_dimensions[letter].width = 12


def _add_instructions_sheet(wb):
    """添加填写说明 Sheet（与模板相同）"""
    ws = wb.create_sheet("填写说明")
    ws.column_dimensions["A"].width = 80
    instructions = [
        "【问卷导入模板 — 填写说明】", "",
        "一、基本流程",
        "  1. 在「问卷设置」Sheet 中填写问卷的基本信息",
        "  2. 在「题目」Sheet 中逐行填写每道题目及其选项",
        "  3. 保存为 .xlsx 文件后在平台上传导入", "",
        "二、题目 Sheet 字段说明",
        "  · 题号: 题目的顺序编号（数字），必填",
        "  · 题目编码: 英文标识符（如 empathy_1），可选",
        "  · 题目内容: 题目的具体文字，必填",
        "  · 题目类型: 单选/多选/判断/量表/填空/简答，必填",
        "  · 所属维度: 对应「维度列表」中的编码，可选",
        "  · 风险标签: 如 self_safety / safety_awareness / family_support 等，可选",
        "  · 反向计分: 填 是 或 否，默认否",
        "  · 选项: 每个选项占 3 列（内容/分值/是否风险），最多 6 个选项",
        "  · 注意力检测: 填 是 表示该题为注意力检测题",
        "  · 正确答案: 注意力检测题的正确答案", "",
        "三、问卷设置 Sheet 说明",
        "  · 维度列表: 格式 编码:名称，多条用分号分隔",
        "  · 风险范围: 格式 最小值-最大值，从低到高填写",
        "  · 风险标签规则: 格式 标签:级别:中文说明",
        "  · 维度百分比规则: 格式 维度编码:百分比:级别", "",
        "四、注意事项",
        "  · 导入后问卷为「草稿」状态，需手动发布",
    ]
    for i, line in enumerate(instructions, 1):
        ws.cell(row=i, column=1, value=line)
    ws["A1"].font = TITLE_FONT


def _safe_str(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _safe_int(val, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _parse_dimensions(dim_str: str) -> list[dict]:
    """解析维度列表字符串，如 'empathy:同理心;egocentrism:自我中心'"""
    if not dim_str:
        return []
    result = []
    for pair in dim_str.split(";"):
        pair = pair.strip()
        if ":" in pair:
            code, title = pair.split(":", 1)
            result.append({"code": code.strip(), "title": title.strip()})
    return result


def _parse_risk_ranges(settings: dict) -> tuple[list[dict], list[dict]]:
    """解析风险范围，返回 (ranges, errors)"""
    ranges = []
    errors = []
    level_map = [
        ("低风险范围", "low"),
        ("中风险范围", "medium"),
        ("高风险范围", "high"),
        ("紧急风险范围", "urgent"),
    ]
    for field, level in level_map:
        val = settings.get(field, "")
        if not val:
            continue
        try:
            parts = val.split("-")
            if len(parts) != 2:
                errors.append({"row": 0, "field": field, "message": f"范围格式错误，应为 最小值-最大值，实际: {val}"})
                continue
            min_v, max_v = int(parts[0].strip()), int(parts[1].strip())
            ranges.append({"min": min_v, "max": max_v, "level": level})
        except (ValueError, IndexError):
            errors.append({"row": 0, "field": field, "message": f"范围格式错误，应为 最小值-最大值，实际: {val}"})

    # 检查范围连续性
    if len(ranges) >= 2:
        for i in range(len(ranges) - 1):
            if ranges[i]["max"] >= ranges[i + 1]["min"]:
                errors.append({
                    "row": 0, "field": "风险范围",
                    "message": f"{ranges[i]['level']}范围上限({ranges[i]['max']})应小于{ranges[i+1]['level']}范围下限({ranges[i+1]['min']})"
                })

    return ranges, errors


def _parse_risk_tag_rules(rules_str: str) -> dict:
    """解析风险标签规则，如 'self_safety:urgent:风险信号;safety:high:安全信号'"""
    if not rules_str:
        return {}
    result = {}
    for item in rules_str.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":")
        if len(parts) >= 2:
            tag = parts[0].strip()
            level = parts[1].strip()
            label = parts[2].strip() if len(parts) > 2 else ""
            result[tag] = {"level": level, "type_label": label}
    return result


def _parse_dimension_pct_rules(rules_str: str) -> list[dict]:
    """解析维度百分比规则，如 'antisocial:80:urgent'"""
    if not rules_str:
        return []
    result = []
    for item in rules_str.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":")
        if len(parts) >= 3:
            result.append({
                "dimension": parts[0].strip(),
                "min_pct": _safe_int(parts[1], 75),
                "level": parts[2].strip(),
            })
    return result


def _safe_filename(title: str) -> str:
    """生成安全的文件名"""
    import re
    name = re.sub(r'[\\/*?:"<>|]', "", title)
    name = name.replace(" ", "_")
    return name[:80] if name else "questionnaire"
