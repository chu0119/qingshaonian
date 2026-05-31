"""
金盾护苗平台操作手册生成脚本（交付版）

用法: python docs/generate_manual.py
输出: docs/金盾护苗平台操作手册.docx
"""

import json
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
ACCOUNTS_FILE = PROJECT_DIR / "backend" / "scripts" / "demo_accounts.json"


def set_cell_shading(cell, color):
    shading = cell._element.get_or_add_tcPr()
    shd = shading.makeelement(qn('w:shd'), {
        qn('w:val'): 'clear',
        qn('w:color'): 'auto',
        qn('w:fill'): color,
    })
    shading.append(shd)


def add_styled_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_shading(cell, "2B579A")

    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = str(val)
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9)
            if ri % 2 == 1:
                set_cell_shading(cell, "EBF5FB")

    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)

    return table


def add_feature_block(doc, title, description):
    p = doc.add_paragraph()
    run = p.add_run(title)
    run.bold = True
    run.font.size = Pt(11)
    p.add_run(f"：{description}")


def add_numbered_steps(doc, steps):
    for i, step in enumerate(steps, 1):
        doc.add_paragraph(f"{i}. {step}")


def add_bullet_list(doc, items):
    for item in items:
        doc.add_paragraph(item, style='List Bullet')


def generate_manual():
    doc = Document()

    # ── 默认样式 ──
    style = doc.styles['Normal']
    style.font.name = 'Microsoft YaHei'
    style.font.size = Pt(11)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')

    # ════════════════════════════════════════════════
    # 封面
    # ════════════════════════════════════════════════
    doc.add_paragraph("")
    doc.add_paragraph("")
    doc.add_paragraph("")

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("金盾护苗")
    run.bold = True
    run.font.size = Pt(36)
    run.font.color.rgb = RGBColor(0x1A, 0x56, 0xA8)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("青少年关爱帮扶信息管理平台")
    run.bold = True
    run.font.size = Pt(22)
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    doc.add_paragraph("")

    manual_title = doc.add_paragraph()
    manual_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = manual_title.add_run("操 作 手 册")
    run.bold = True
    run.font.size = Pt(28)
    run.font.color.rgb = RGBColor(0x2B, 0x57, 0x9A)

    doc.add_paragraph("")
    doc.add_paragraph("")

    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info.add_run("平利县公安局老县派出所")
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    info2 = doc.add_paragraph()
    info2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info2.add_run("陕西安楠云芯科技有限公司")
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    doc.add_page_break()

    # ════════════════════════════════════════════════
    # 目录
    # ════════════════════════════════════════════════
    doc.add_heading("目 录", level=1)
    toc_items = [
        "一、系统概述",
        "二、访问地址与浏览器要求",
        "三、演示账号一览",
        "四、公安民警（平台管理员）操作流程",
        "    4.1 登录系统",
        "    4.2 监管首页",
        "    4.3 学校管理",
        "    4.4 风险预警中心",
        "    4.5 重点关注学生",
        "    4.6 学生管理",
        "    4.7 问卷管理",
        "    4.8 测评任务监管",
        "    4.9 干预督办",
        "    4.10 区域数据大屏",
        "    4.11 AI研判分析",
        "    4.12 通知与短信",
        "    4.13 日志审计",
        "    4.14 系统管理",
        "五、学校管理员操作流程",
        "    5.1 首页看板",
        "    5.2 班级管理",
        "    5.3 学生管理",
        "    5.4 教师管理",
        "    5.5 问卷库",
        "    5.6 问卷编辑器",
        "    5.7 问卷任务",
        "    5.8 风险预警",
        "    5.9 风险详情与AI分析",
        "    5.10 干预记录",
        "    5.11 数据报表",
        "    5.12 数据大屏",
        "    5.13 系统设置",
        "六、教师 / 心理老师操作流程",
        "    6.1 教师首页",
        "    6.2 我的班级",
        "    6.3 我的问卷与问卷编辑",
        "    6.4 问卷任务",
        "    6.5 风险学生",
        "    6.6 干预记录",
        "    6.7 班级报告",
        "七、学生操作流程",
        "    7.1 登录系统",
        "    7.2 首页",
        "    7.3 填写问卷",
        "    7.4 已完成",
        "    7.5 健康贴士",
        "    7.6 个人中心",
        "八、核心工作流程",
        "    8.1 问卷测评全流程",
        "    8.2 风险预警与干预流程",
        "    8.3 身份证号安全机制",
        "    8.4 答题质量检测体系",
        "九、常见问题",
    ]
    for item in toc_items:
        p = doc.add_paragraph(item)
        p.paragraph_format.space_after = Pt(2)
        for run in p.runs:
            run.font.size = Pt(12)

    doc.add_page_break()

    # ════════════════════════════════════════════════
    # 一、系统概述
    # ════════════════════════════════════════════════
    doc.add_heading("一、系统概述", level=1)
    doc.add_paragraph(
        "金盾护苗·青少年关爱帮扶信息管理平台是由平利县公安局老县派出所主导，"
        "陕西安楠云芯科技有限公司研发的一套面向青少年关爱帮扶的信息化管理系统。"
        "平台通过标准化心理测评问卷、智能风险识别、AI辅助分析等技术手段，"
        "帮助公安民警、学校管理员、教师和心理老师全面掌握青少年心理和行为状况，"
        '及时发现风险信号并采取干预措施，实现"早发现、早介入、早帮扶"的工作目标。'
    )

    doc.add_heading("平台角色体系", level=2)
    add_styled_table(doc,
        ["角色", "系统称谓", "路由入口", "权限范围"],
        [
            ["平台管理员", "公安民警", "/platform/", "全区监管，可进入任意学校后台"],
            ["学校管理员", "学校负责人", "/school-admin/", "本校完整管理"],
            ["教师", "班主任/任课教师", "/teacher/", "所负责班级的学生和任务"],
            ["心理老师", "心理辅导教师", "/counselor/", "全校学生心理辅导和干预"],
            ["学生", "被测评对象", "/student/", "填写问卷、查看个人记录"],
        ],
        col_widths=[3, 3, 3, 5]
    )

    doc.add_heading("平台核心功能", level=2)
    features = [
        ("关爱筛查评估", "提供20套标准化评估量表，覆盖心理健康、校园欺凌、网络成瘾、家庭关系、安全意识、人际关系、学业压力等多个维度，支持自定义问卷。"),
        ("智能风险识别", "基于评分规则自动识别风险等级（关注/预警/警告/危急），通过颜色直观区分轻重缓急，并自动生成风险预警记录。"),
        ("答题质量检测", "自动检测答卷有效性，包括注意力检测题、快速作答、规律性作答、连续同选项、矛盾题分析、全否定检测等多维度质量评估，确保数据真实可靠。"),
        ("AI研判分析", "平台管理员可使用AI辅助分析功能，对区域整体或单个学生进行综合研判，生成风险趋势分析、学校对比、维度分析等可视化报告。"),
        ("干预跟进管理", "支持10种干预方式记录（学生谈话、班主任沟通、心理老师辅导、家校沟通、家访、转介专业机构、持续观察等），可设置跟进提醒。"),
        ("数据可视化", "提供区域/学校两级数据大屏、统计报表、趋势分析、维度雷达图等多种数据可视化功能，支持大屏全屏展示。"),
        ("安全与审计", "身份证号/手机号默认脱敏显示，敏感操作需密码二次验证，全操作日志审计追踪。"),
    ]
    for title_text, desc in features:
        add_feature_block(doc, title_text, desc)

    doc.add_heading("风险等级说明", level=2)
    add_styled_table(doc,
        ["等级", "标签", "颜色", "含义", "建议措施"],
        [
            ["low", "关注", "蓝色", "测评结果显示需要正常关注和支持", "班主任日常观察"],
            ["medium", "预警", "橙色", "存在一定的风险信号", "班主任谈话、持续观察"],
            ["high", "警告", "红色", "存在较为明显的风险信号", "心理老师介入、家校沟通"],
            ["urgent", "危急", "深红色", "存在需要立即关注的严重风险", "紧急干预、考虑转介专业机构"],
        ],
        col_widths=[1.5, 1.5, 1.5, 4, 4]
    )

    # ════════════════════════════════════════════════
    # 二、访问地址
    # ════════════════════════════════════════════════
    doc.add_heading("二、访问地址与浏览器要求", level=1)
    doc.add_heading("访问地址", level=2)
    p = doc.add_paragraph("平台地址：")
    run = p.add_run("https://a.annanyun.com")
    run.bold = True
    run.font.color.rgb = RGBColor(0x00, 0x66, 0xCC)

    doc.add_heading("浏览器要求", level=2)
    add_bullet_list(doc, [
        "推荐使用 Chrome（谷歌浏览器）、Edge（微软浏览器）、Firefox 等现代浏览器",
        "支持手机端浏览器访问（页面自适应布局）",
        "不支持 IE 浏览器",
    ])

    # ════════════════════════════════════════════════
    # 三、演示账号
    # ════════════════════════════════════════════════
    doc.add_heading("三、演示账号一览", level=1)
    doc.add_paragraph(
        "以下为演示环境中的测试账号。首次登录后系统将强制要求修改密码。"
        '所有演示数据均为虚构，名称后缀"(演示)"以示区分。正式使用时需清理演示数据并导入真实数据。'
    )

    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        accounts = json.load(f)

    doc.add_heading("3.1 平台管理员（公安民警）", level=2)
    add_styled_table(doc,
        ["角色", "姓名", "账号", "密码", "说明"],
        [["平台管理员", "平台管理员", "padm", "Admin@2026!", "首次登录需修改密码"]],
        col_widths=[3, 3, 3.5, 3, 4]
    )

    doc.add_heading("3.2 学校管理员", level=2)
    school_admins = [a for a in accounts if a["role"] == "school_admin"]
    add_styled_table(doc,
        ["学校", "姓名", "账号", "密码"],
        [[a["school"], a["name"], a["username"], a["password"]] for a in school_admins],
        col_widths=[4, 3, 3.5, 3]
    )

    doc.add_heading("3.3 心理老师", level=2)
    counselors = [a for a in accounts if a["role"] == "counselor"]
    add_styled_table(doc,
        ["学校", "姓名", "账号", "密码"],
        [[a["school"], a["name"], a["username"], a["password"]] for a in counselors],
        col_widths=[4, 3, 3.5, 3]
    )

    doc.add_heading("3.4 班主任", level=2)
    doc.add_paragraph("共 18 位班主任，每校 6 位。以下列出每校前 2 位：")
    teachers = [a for a in accounts if a["role"] == "teacher"]
    display_teachers = []
    for school_name in ["青云中学(演示)", "明德中学(演示)", "星河中学(演示)"]:
        school_teachers = [t for t in teachers if t["school"] == school_name][:2]
        display_teachers.extend(school_teachers)
    add_styled_table(doc,
        ["学校", "姓名", "账号", "密码"],
        [[a["school"], a["name"], a["username"], a["password"]] for a in display_teachers],
        col_widths=[4, 3, 3.5, 3]
    )

    doc.add_heading("3.5 学生账号", level=2)
    doc.add_paragraph(
        "学生账号使用 18 位身份证号作为登录账号（虚构号码，以 9901 开头），"
        "默认密码为身份证号后 6 位。首次登录需修改密码。"
        "演示环境中共约 489 名学生，分布在 3 所学校、9 个年级、18 个班级中。"
    )

    # ════════════════════════════════════════════════
    # 四、公安民警（平台管理员）操作流程
    # ════════════════════════════════════════════════
    doc.add_page_break()
    doc.add_heading("四、公安民警（平台管理员）操作流程", level=1)

    doc.add_paragraph(
        "平台管理员（公安民警）拥有全区监管权限，可查看所有学校数据、管理风险预警、"
        "督办干预处理、生成AI研判报告、查看审计日志等。"
        "左侧导航栏包含 13 个功能菜单。"
    )

    # 4.1 登录
    doc.add_heading("4.1 登录系统", level=2)
    add_numbered_steps(doc, [
        "打开浏览器，访问 https://a.annanyun.com",
        "在登录页面输入账号 padm 和密码 Admin@2026!",
        "如果是首次登录，系统将强制要求修改密码（密码长度不少于 10 位）",
        "登录成功后进入公安监管端首页",
    ])

    # 4.2 监管首页
    doc.add_heading("4.2 监管首页", level=2)
    doc.add_paragraph(
        "登录成功后进入监管首页，展示全区宏观统计数据，帮助快速掌握整体情况。"
    )

    doc.add_heading("统计卡片", level=3)
    doc.add_paragraph("页面顶部展示 11 个核心统计指标：")
    add_bullet_list(doc, [
        "学校总数、启用学校数、停用学校数",
        "学生总数、教师总数",
        "问卷任务数、答卷总数",
        "风险提示数、待处理提示数",
        "AI调用次数、短信发送量",
    ])

    doc.add_heading("图表区域", level=3)
    add_bullet_list(doc, [
        "风险等级分布饼图：展示全区关注/预警/警告/危急各级别占比",
        "学校完成率排名柱状图：各学校测评完成率对比",
        "学校风险对比柱状图：各学校风险数量对比",
    ])

    doc.add_heading("数据表格", level=3)
    add_bullet_list(doc, [
        "完成率明细表：按学校展示完成率、答卷数、风险数",
        "风险排名表：按学校展示各级别风险数量",
        "最近活跃学校列表",
    ])

    # 4.3 学校管理
    doc.add_heading("4.3 学校管理", level=2)
    doc.add_paragraph(
        "点击左侧菜单「学校管理」，可查看和管理所有学校。"
        "这是平台管理员最常用的功能入口之一。"
    )

    doc.add_heading("学校列表", level=3)
    doc.add_paragraph("支持按关键词搜索（学校名称/编码）。表格展示以下信息：")
    add_styled_table(doc,
        ["列名", "说明"],
        [
            ["学校名称", "学校的全称"],
            ["学校编码", "唯一标识编码"],
            ["管理员", "该校主管理员姓名"],
            ["学生数 / 教师数", "该校注册的学生和教师数量"],
            ["状态", "正常（绿色）或停用（红色）"],
            ["操作", "详情、编辑、进入后台、停用/启用、删除"],
        ],
        col_widths=[3, 12]
    )

    doc.add_heading("新增学校", level=3)
    add_numbered_steps(doc, [
        "点击「新增学校」按钮",
        "填写学校基本信息：学校名称、学校编码、地址、联系电话",
        "（可选）勾选「同步创建管理员」，填写管理员账号、初始密码（至少10位）、姓名、手机号",
        "点击确定完成创建",
    ])

    doc.add_heading("学校详情", level=3)
    doc.add_paragraph("点击「详情」按钮，打开学校详情弹窗，包含丰富的信息：")
    add_bullet_list(doc, [
        "统计卡片：学生/教师/班级/任务/答卷/预警数量，待处理数、完成率、干预完成率",
        "学校基本信息：名称、编码、管理员、状态、地址、电话",
        "学校管理员列表：可重置密码、停用、添加新管理员",
        "风险分布：按等级展示进度条",
        "年级概况表",
        "最近使用情况：最近任务、最近登录、最近风险处理",
    ])

    doc.add_heading("进入学校后台", level=3)
    doc.add_paragraph(
        "点击「进入后台」按钮，系统以平台管理员身份进入该校的管理视角，"
        "可以看到学校管理员看到的所有数据和功能（班级管理、学生管理、教师管理等）。"
        '页面顶部会显示蓝色提示条"当前以代入模式访问"，可随时点击「返回平台管理」退出。'
    )

    # 4.4 风险预警中心
    doc.add_heading("4.4 风险预警中心", level=2)
    doc.add_paragraph(
        "点击左侧菜单「风险预警中心」，查看全区所有学校的风险预警记录。"
        "这是平台管理员监控区域风险态势的核心页面。"
    )

    doc.add_heading("筛选功能", level=3)
    add_bullet_list(doc, [
        "按学校筛选：下拉选择特定学校",
        "按风险等级筛选：关注/预警/警告/危急",
        "按处理状态筛选：待处理/处理中/持续跟进/已完成/已关闭",
        "关键词搜索：按学生姓名搜索",
    ])

    doc.add_heading("预警列表", level=3)
    doc.add_paragraph("表格展示以下信息：学生姓名、身份证号（脱敏显示）、学校、年级、班级、风险等级（彩色标签）、风险类型、处理状态、创建时间。")

    doc.add_heading("身份证号查看", level=3)
    doc.add_paragraph(
        "身份证号默认脱敏显示（如 990****0015）。如需查看完整号码，点击身份证号旁的「眼睛」图标，"
        "在弹窗中输入当前登录密码，验证通过后显示完整身份证号。此操作会记录到审计日志。"
    )

    doc.add_heading("预警详情", level=3)
    doc.add_paragraph("点击「详情」按钮，在右侧抽屉中查看完整预警信息：")
    add_bullet_list(doc, [
        "学生基本信息和身份证号",
        "风险等级、风险类型、触发方式、生成时间",
        "评分详情：总分 + 各维度得分进度条（情绪状态、睡眠状态、学习压力、人际关系、家庭支持、校园安全、网络使用、自我安全）",
        "答题质量评估：质量等级、质量评分",
        "干预记录列表：干预方式、内容、状态、时间",
        "「查看原始答题详情」按钮：查看该学生每道题的具体作答",
    ])

    doc.add_heading("导出CSV", level=3)
    doc.add_paragraph(
        "点击右上角「导出 CSV」按钮，输入密码验证身份后，"
        "将当前筛选条件的风险预警数据导出为 CSV 文件（含学生姓名、身份证号脱敏、学校、年级、班级、风险等级等）。"
    )

    # 4.5 重点关注学生
    doc.add_heading("4.5 重点关注学生", level=2)
    doc.add_paragraph(
        "点击左侧菜单「重点关注学生」，查看被系统标记为重点关注的学生列表。"
        "可按风险等级、学校、关键词筛选。"
    )

    doc.add_heading("学生画像", level=3)
    doc.add_paragraph("点击「画像」按钮，打开学生360度画像视图：")
    add_bullet_list(doc, [
        "基本信息：姓名、身份证号（脱敏，可验证查看）、学校、年级、班级",
        "统计卡片：预警次数、干预次数、测评次数",
        "风险预警历史：时间线展示历次预警（风险等级标签、类型、状态、日期）",
        "评分变化表：历次测评的总分、风险等级、时间，可查看答题详情",
        "干预记录列表：干预方式、内容、状态",
    ])

    doc.add_heading("导出CSV", level=3)
    doc.add_paragraph("同风险预警中心，需密码验证后导出，包含学生基本信息、风险等级、测评总分、干预次数等。")

    # 4.6 学生管理
    doc.add_heading("4.6 学生管理", level=2)
    doc.add_paragraph(
        "点击左侧菜单「学生管理」，可查看全区所有学校的学生信息。"
        "支持按学校、关键词（姓名/学号/身份证号）筛选。"
    )
    doc.add_paragraph(
        "表格展示：学生姓名、学号、身份证号（脱敏，可验证查看）、学校、年级、班级、手机号、状态。"
    )
    doc.add_paragraph(
        "点击「详情」可查看学生完整信息和答卷列表（问卷名称、总分、风险等级、提交时间）。"
        "支持密码验证后导出 CSV。"
    )

    # 4.7 问卷管理
    doc.add_heading("4.7 问卷管理", level=2)
    doc.add_paragraph(
        "点击左侧菜单「问卷管理」，查看和管理系统中所有问卷。"
    )

    doc.add_heading("统计概览", level=3)
    doc.add_paragraph("页面顶部展示：问卷总数、内置问卷数、平台问卷数、学校问卷数。")

    doc.add_heading("筛选", level=3)
    add_bullet_list(doc, [
        "按类别筛选：心理健康、校园欺凌、家庭关系、网络成瘾、睡眠质量、综合、安全意识、金盾护苗行为筛查、金盾护苗家庭评估",
        "按来源类型筛选：内置/平台/学校",
        "关键词搜索",
    ])

    doc.add_heading("问卷列表", level=3)
    doc.add_paragraph(
        "展示问卷标题、类别、来源、题目数、使用次数、答卷数、状态（草稿/启用/已发布/已归档/已停用）。"
    )
    doc.add_paragraph("操作按钮：")
    add_bullet_list(doc, [
        "详情：查看问卷基本信息和题目列表（序号、题目内容、题型、维度、选项数）",
        "统计：查看该问卷的使用统计（关联任务数、答卷数、已推送学校数）",
        "复制：创建问卷副本",
        "推送到学校：将问卷推送到指定学校使用",
        "删除：仅草稿状态可删除",
    ])

    # 4.8 测评任务监管
    doc.add_heading("4.8 测评任务监管", level=2)
    doc.add_paragraph(
        "点击左侧菜单「测评任务监管」，查看所有学校发布的测评任务及完成情况。"
    )
    doc.add_paragraph("支持按学校、任务状态筛选。表格展示：任务名称、学校、关联问卷、状态（未开始/进行中/已结束等）、开始时间、截止时间。")
    doc.add_paragraph(
        "点击「详情」查看：任务信息、完成统计（目标学生数/已提交数/完成率）、各年级完成率明细。"
        "支持导出 CSV。"
    )

    # 4.9 干预督办
    doc.add_heading("4.9 干预督办", level=2)
    doc.add_paragraph(
        "点击左侧菜单「干预督办」，查看全区所有学校的干预记录，督促学校及时处理风险。"
    )

    doc.add_heading("两个Tab页", level=3)
    add_bullet_list(doc, [
        "全部干预：展示所有干预记录",
        "逾期未处理：仅展示超过处理时限的记录",
    ])

    doc.add_heading("干预列表", level=3)
    doc.add_paragraph(
        "展示：学生姓名、身份证号（脱敏）、学校、负责教师、干预方式、处理状态、内容摘要、干预时间、是否需跟进。"
    )

    doc.add_heading("督办操作", level=3)
    add_bullet_list(doc, [
        "督促：向学校发送督促通知，提醒尽快处理",
        "提醒：向负责教师发送提醒通知",
        "详情：查看干预详细信息和答题详情",
    ])

    # 4.10 区域数据大屏
    doc.add_heading("4.10 区域数据大屏", level=2)
    doc.add_paragraph(
        "点击左侧菜单「区域数据大屏」，进入深色主题数据可视化大屏。"
        "该页面适合在会议、汇报等场景下全屏展示，数据每 30 秒自动刷新。"
    )

    doc.add_heading("大屏内容", level=3)
    add_bullet_list(doc, [
        "顶部 KPI 卡片（6项）：接入学校、启用学校、学生总数、教师总数、问卷任务、答卷总数",
        "侧边 KPI（6项）：测评完成率、风险提示数、待处理风险数、AI分析次数、短信发送量、停用学校数",
        "仪表盘：学校启用率、测评完成率、风险处置率（三个圆形仪表盘）",
        "图表区：完成率排名列表、风险等级分布饼图、风险排名列表、活跃学校列表",
    ])
    doc.add_paragraph("页面右上角有全屏按钮，可切换全屏模式。支持移动端自适应布局。")

    # 4.11 AI研判分析
    doc.add_heading("4.11 AI研判分析", level=2)
    doc.add_paragraph(
        "点击左侧菜单「AI研判分析」，可使用AI辅助分析功能对区域数据进行综合研判。"
        "（需在系统管理中开启AI分析功能并配置API密钥）"
    )

    doc.add_heading("区域研判报告", level=3)
    doc.add_paragraph("点击「生成区域报告」按钮，系统将分析全区数据并生成报告，包含：")
    add_bullet_list(doc, [
        "区域风险等级告警：摘要和建议文本",
        "概览统计：接入学校、学生总数、风险预警、待处理数量",
        "风险等级分布饼图",
        "近6月风险趋势折线图",
        "学校风险密度柱状图（每百人风险数）",
        "学校干预解决率柱状图",
        "预警学生维度雷达图（情绪、睡眠、学习压力等8个维度）",
        "异常告警区：标记异常学校和低完成率任务",
        "学校风险等级构成表",
    ])

    doc.add_heading("分析历史", level=3)
    doc.add_paragraph(
        "页面下方展示历史分析记录表格：分析时间、分析类型、使用模型、状态（成功/失败）、"
        "耗时(ms)、操作人、错误信息。"
    )

    # 4.12 通知与短信
    doc.add_heading("4.12 通知与短信", level=2)
    doc.add_paragraph(
        "点击左侧菜单「通知与短信」，查看短信发送记录和发送催办短信。"
        "（需在系统管理中配置短信服务）"
    )
    doc.add_paragraph(
        "支持按状态和手机号筛选。展示：接收人、手机号（脱敏）、类型、状态（成功/失败）、"
        "发送时间、失败原因。"
    )
    doc.add_paragraph("点击「发送催办短信」按钮，可向指定手机号发送催办短信。")

    # 4.13 日志审计
    doc.add_heading("4.13 日志审计", level=2)
    doc.add_paragraph(
        "点击左侧菜单「日志审计」，查看系统操作日志和登录日志。"
        "所有敏感操作（查看学生详情、导出数据、进入学校后台等）都会被记录。"
    )

    doc.add_heading("操作日志", level=3)
    doc.add_paragraph("支持按模块（13种）、角色、关键词筛选。表格展示：操作时间、模块、操作类型、操作人（含角色标签）、对象类型、对象名称、结果（成功/失败）、详情、IP地址。")

    doc.add_heading("登录日志", level=3)
    doc.add_paragraph("支持按角色、结果、用户名筛选。表格展示：登录时间、用户名、角色、IP地址、结果（成功/失败）、失败原因。")

    # 4.14 系统管理
    doc.add_heading("4.14 系统管理", level=2)
    doc.add_paragraph("点击左侧菜单「系统管理」，进入系统级配置页面。包含 8 个设置标签页：")

    doc.add_heading("标签页 1：基本设置", level=3)
    add_bullet_list(doc, [
        "系统名称：可自定义系统显示名称",
        "技术支持联系方式",
        "新学校默认管理员密码",
    ])

    doc.add_heading("标签页 2：AI配置", level=3)
    add_bullet_list(doc, [
        "AI供应商：支持 OpenAI、智谱AI（GLM）、通义千问、DeepSeek、自定义接口",
        "Base URL 和 API Key",
        "模型名称",
        "系统提示词模板",
    ])

    doc.add_heading("标签页 3：短信服务", level=3)
    add_bullet_list(doc, [
        "短信启用开关",
        "供应商选择：阿里云、腾讯云、自定义",
        "API URL、Access Key、Secret、模板编码、签名",
    ])

    doc.add_heading("标签页 4：安全设置", level=3)
    add_bullet_list(doc, [
        "密码最小长度",
        "密码过期天数",
        "登录锁定阈值（连续失败次数）",
        "锁定时长",
        "会话超时时间",
    ])

    doc.add_heading("标签页 5：功能开关", level=3)
    add_bullet_list(doc, [
        "AI智能分析：开启/关闭",
        "短信通知：开启/关闭",
        "学生查看结果：是否允许学生查看自己的测评结果",
        "数据导出：开启/关闭",
        "自动风险预警：开启/关闭",
    ])

    doc.add_heading("标签页 6：数据与通知", level=3)
    add_bullet_list(doc, [
        "数据保留月数、日志保留月数、自动清理开关",
        "通知模板编辑：风险预警通知、任务下发通知、密码重置通知（支持变量替换）",
    ])

    doc.add_heading("标签页 7：管理员账号", level=3)
    doc.add_paragraph(
        "管理所有平台管理员账号。可新增、编辑、停用、重置密码。"
        "重置密码时系统自动生成 JdHm + 时间戳格式的临时密码。"
    )

    doc.add_heading("标签页 8：系统信息", level=3)
    doc.add_paragraph("展示系统版本号、技术栈、数据库类型、各功能模块状态。")

    # ════════════════════════════════════════════════
    # 五、学校管理员操作流程
    # ════════════════════════════════════════════════
    doc.add_page_break()
    doc.add_heading("五、学校管理员操作流程", level=1)

    doc.add_paragraph(
        "学校管理员负责本校的日常管理工作，包括班级管理、学生管理、教师管理、"
        "问卷管理、任务发布、风险预警查看、干预记录管理、数据报表等。"
        "左侧导航栏包含 11 个功能菜单。"
    )

    # 5.1 首页看板
    doc.add_heading("5.1 首页看板", level=2)
    doc.add_paragraph(
        "登录后进入首页看板，展示本校核心统计数据。"
    )
    add_bullet_list(doc, [
        "统计卡片（6项）：学生总数、教师总数、班级数量、进行中任务、答卷总数、待处理预警",
        "风险汇总告警：危急 + 警告数量提示条",
        "风险等级分布：关注/预警/警告/危急各级别进度条",
        "答题质量分布：正常/轻度异常/中度异常/严重异常 + 有效率",
        "待处理风险预警表：学生姓名、班级、风险等级、触发问卷，可点击查看详情",
    ])

    # 5.2 班级管理
    doc.add_heading("5.2 班级管理", level=2)
    doc.add_paragraph("点击左侧菜单「班级管理」，查看和管理本校所有班级。")
    add_bullet_list(doc, [
        "支持按年级筛选",
        "表格展示：年级、班级名称、班主任、心理老师、学生人数、状态",
        "新增/编辑班级：选择年级、填写班级名称、分配班主任和心理老师",
    ])

    # 5.3 学生管理
    doc.add_heading("5.3 学生管理", level=2)
    doc.add_paragraph("点击左侧菜单「学生管理」，查看和管理本校所有学生。")

    doc.add_heading("筛选与列表", level=3)
    doc.add_paragraph("支持按年级、班级、关键词（姓名/学号/身份证号）筛选。表格展示：学号、姓名、性别、年级、班级、身份证号（脱敏）、状态。")

    doc.add_heading("新增学生", level=3)
    add_numbered_steps(doc, [
        "点击「新增学生」按钮",
        "填写姓名、身份证号（18位，系统自动校验）、性别、年级、班级",
        "初始密码默认为身份证号后6位（可自定义）",
        "可选填手机号",
        "点击确定完成添加",
    ])

    doc.add_heading("批量导入", level=3)
    add_numbered_steps(doc, [
        "点击「下载导入模板」，获取 Excel 模板文件",
        "按模板格式填写学生数据",
        "点击「批量导入」上传 Excel 文件（支持 .xlsx/.xls）",
        "系统显示导入结果：成功条数、失败条数及错误详情",
    ])

    doc.add_heading("其他操作", level=3)
    add_bullet_list(doc, [
        "编辑：修改学生信息",
        "重置密码：重置为身份证号后 6 位",
        "删除：删除学生记录",
    ])

    # 5.4 教师管理
    doc.add_heading("5.4 教师管理", level=2)
    doc.add_paragraph("点击左侧菜单「教师管理」，查看和管理本校教师。")

    doc.add_heading("教师列表", level=3)
    doc.add_paragraph("支持按教师类型、关键词筛选。表格展示：身份证号（脱敏）、姓名、手机号、教师类型（班主任/心理老师/年级主任/德育老师/普通教师）、角色、状态。")

    doc.add_heading("新增教师", level=3)
    add_numbered_steps(doc, [
        "点击「新增教师」按钮",
        "填写姓名、身份证号、角色（教师/心理老师）、教师类型",
        "设置初始密码",
        "可选填手机号",
        "点击确定完成添加",
    ])

    doc.add_heading("分配班级", level=3)
    doc.add_paragraph(
        "点击「分配班级」按钮，使用穿梭框（Transfer）将教师分配到指定班级。"
        "班主任负责所分配班级的学生管理和风险预警。"
    )

    # 5.5 问卷库
    doc.add_heading("5.5 问卷库", level=2)
    doc.add_paragraph("点击左侧菜单「问卷库」，查看系统内置问卷和自定义问卷。")

    doc.add_heading("内置问卷", level=3)
    doc.add_paragraph(
        "系统预置 20 套标准化评估量表，覆盖 8 大类别：心理健康筛查、校园欺凌排查、网络沉迷评估、"
        "家庭关系调查、安全意识测评、人际关系测评、学业压力测评、综合评估。"
        "内置问卷可预览但不可编辑，可通过「复制为副本」创建可编辑的副本。"
    )

    doc.add_heading("自定义问卷", level=3)
    doc.add_paragraph("支持学校自建问卷，点击「新建问卷」进入问卷编辑器。")

    doc.add_heading("问卷筛选", level=3)
    doc.add_paragraph(
        "支持按分类、状态、关键词筛选。"
        "表格展示：问卷标题、分类、题目数、适用年级、维度标签、类型（内置/自建）、状态。"
    )

    # 5.6 问卷编辑器
    doc.add_heading("5.6 问卷编辑器", level=2)
    doc.add_paragraph(
        "问卷编辑器是功能强大的问卷设计工具，支持创建完整的评估量表。"
    )

    doc.add_heading("基本信息", level=3)
    add_bullet_list(doc, [
        "问卷标题、问卷说明",
        "问卷分类：10 个类别可选（含金盾护苗行为筛查、金盾护苗家庭评估专用类别）",
        "适用年级：多选（七年级~九年级等）",
    ])

    doc.add_heading("高级配置", level=3)
    add_bullet_list(doc, [
        "维度定义：可添加多个评估维度（编码 + 名称），如情绪状态、睡眠状态等",
        "评分规则：配置计分方式（如 Likert 5级量表 0-4 分）、计分题型、排除注意力检测题等",
        "风险规则：设置总分百分比区间对应的风险等级（关注/预警/警告/危急）",
        "质量规则：配置全否定检测、快速作答检测等答题质量评估规则",
    ])

    doc.add_heading("题目编辑", level=3)
    doc.add_paragraph("支持的题型：")
    add_styled_table(doc,
        ["题型", "说明", "选项配置"],
        [
            ["单选题", "从多个选项中选择一个", "选项内容 + 分值 + 是否风险项"],
            ["多选题", "从多个选项中选择多个", "选项内容 + 分值"],
            ["量表题", "Likert 量表评分", "5级/4级等标准化选项"],
            ["判断题", "是/否二选一", "选项内容"],
            ["填空题", "文本输入", "无需选项"],
            ["简答题", "开放性文本", "无需选项"],
        ],
        col_widths=[2.5, 5, 7]
    )
    doc.add_paragraph("每道题可配置：")
    add_bullet_list(doc, [
        "维度归属（关联到维度定义）",
        "风险标签和风险阈值",
        "反向计分标记",
        "注意力检测标记（含正确答案）",
        "题目排序（上移/下移）",
    ])

    doc.add_heading("矛盾题组", level=3)
    doc.add_paragraph(
        "可设置矛盾题组，将两道相关联的题目配对，配置关系类型（相反/正相关/互斥）和允许的最大分差。"
        "系统在答题质量检测时自动分析矛盾题组的答题一致性。"
    )

    doc.add_heading("问卷预览", level=3)
    doc.add_paragraph("支持逐题预览，可模拟答题视角检查问卷设计是否合理。")

    # 5.7 问卷任务
    doc.add_heading("5.7 问卷任务", level=2)
    doc.add_paragraph("点击左侧菜单「问卷任务」，管理本校的测评任务。")

    doc.add_heading("发布任务", level=3)
    add_numbered_steps(doc, [
        "点击「发布任务」按钮",
        "填写任务名称",
        "从问卷库中选择要使用的问卷",
        "选择目标班级（多选，支持全校/指定年级/指定班级）",
        "填写任务说明",
        "设置起止时间",
        "配置高级选项：",
    ])
    add_bullet_list(doc, [
        "允许提交后修改（Switch 开关）",
        "题目随机排序（Switch 开关）",
        "选项随机排序（Switch 开关）",
        "答题质量检测（Switch 开关，默认开启）",
        "提醒策略：不提醒 / 截止前24小时 / 截止前2小时",
    ])
    doc.add_paragraph("8. 点击确认发布。")

    doc.add_heading("任务管理", level=3)
    doc.add_paragraph(
        "任务列表展示：任务名称、问卷名称、状态（进行中/已结束等）、"
        "完成情况（进度条）、题目随机、质量检测、创建时间。"
    )
    doc.add_paragraph("可执行的操作：查看完成详情（已提交/未完成学生列表）、关闭任务、归档任务。")

    # 5.8 风险预警
    doc.add_heading("5.8 风险预警", level=2)
    doc.add_paragraph(
        "点击左侧菜单「风险预警」，查看本校所有风险预警。"
        "预警由系统根据学生问卷评分自动生成。"
    )
    doc.add_paragraph("支持按风险等级、处理状态筛选。")
    doc.add_paragraph(
        "表格展示：学生姓名、年级、班级、风险类型、风险等级（彩色标签）、处理状态、触发时间、触发问卷。"
        "操作：点击「详情」跳转风险详情页，点击「答题」查看原始答题详情。"
    )

    # 5.9 风险详情
    doc.add_heading("5.9 风险详情与AI分析", level=2)
    doc.add_paragraph("从风险预警列表点击「详情」进入风险详情页面。")

    doc.add_heading("风险信息", level=3)
    doc.add_paragraph("展示学生姓名、风险等级、风险类型、处理状态、测评总分。")

    doc.add_heading("答题质量评估", level=3)
    doc.add_paragraph("展示该学生答卷的质量分析：")
    add_bullet_list(doc, [
        "质量评分和质量等级（正常/存疑/轻度异常/中度异常/严重异常）",
        "答题时长、有效性判定",
        "多维度检测：注意力检测、连续相同选项、矛盾题分析、规律性检测、快速作答、相同选项比率",
        "扣分明细",
    ])

    doc.add_heading("维度得分", level=3)
    doc.add_paragraph(
        "以进度条形式展示 8 个标准维度的得分情况："
        "情绪状态、睡眠状态、学习压力、人际关系、家庭支持、校园安全、网络使用、自我安全。"
        "每个维度用颜色区分风险程度（蓝色正常、橙色关注、红色高风险）。"
    )

    doc.add_heading("综合评估", level=3)
    doc.add_paragraph("展示系统自动生成的评估文本和维度分析列表（每项含标签、等级、比率、建议）。")

    doc.add_heading("操作按钮", level=3)
    add_bullet_list(doc, [
        "新增干预记录：跳转到干预记录页面，自动预填充学生和预警信息",
        "AI智能分析：打开AI分析弹窗，对单个学生进行AI研判分析",
    ])

    # 5.10 干预记录
    doc.add_heading("5.10 干预记录", level=2)
    doc.add_paragraph("点击左侧菜单「干预记录」，查看和管理对风险学生的干预跟进记录。")

    doc.add_heading("干预方式", level=3)
    add_styled_table(doc,
        ["方式代码", "中文名称", "说明"],
        [
            ["student_talk", "学生谈话", "与学生进行面对面谈话"],
            ["teacher_communication", "班主任沟通", "与班主任交流学生情况"],
            ["counselor_guidance", "心理老师辅导", "心理老师进行专业辅导"],
            ["family_school", "家校沟通", "与家长/监护人沟通"],
            ["home_visit", "家访", "上门了解学生家庭情况"],
            ["referral", "转介专业机构", "建议家长带孩子寻求专业帮助"],
            ["observation", "持续观察", "持续关注学生状态变化"],
            ["other", "其他", "其他干预方式"],
        ],
        col_widths=[3.5, 3, 9]
    )

    doc.add_heading("新增干预记录", level=3)
    add_numbered_steps(doc, [
        "点击「新增干预」按钮",
        "选择学生（支持远程搜索）",
        "选择干预方式",
        "填写干预内容、处理结果、后续建议",
        "设置是否需要持续跟进",
        "如需跟进，设置下次跟进时间",
        "选择处理状态",
        "点击确定保存",
    ])
    doc.add_paragraph(
        "如果从风险详情页跳转，学生和预警信息会自动预填充，无需手动选择。"
    )

    # 5.11 数据报表
    doc.add_heading("5.11 数据报表", level=2)
    doc.add_paragraph("点击左侧菜单「数据报表」，查看本校统计分析报表。包含 5 个报表标签页：")

    doc.add_heading("学校综合报表", level=3)
    doc.add_paragraph(
        "展示总学生数、已完成数、完成率 + 进度条。"
        "可按年级、班级展开查看详细完成率表格。支持AI分析。"
    )

    doc.add_heading("风险预警报表", level=3)
    doc.add_paragraph(
        "展示风险总数、各级别分布（关注/预警/警告/危急）、各状态分布（待处理/处理中/已完成/已关闭）。"
    )

    doc.add_heading("答题质量报表", level=3)
    doc.add_paragraph("展示答卷总数、有效率、建议复测数、质量等级分布。")

    doc.add_heading("问卷统计", level=3)
    doc.add_paragraph("展示所有问卷的基本信息（标题、分类、题目数、状态、适用年级、类型）。")

    doc.add_heading("学生纵向追踪", level=3)
    doc.add_paragraph(
        "选择特定学生后，展示该学生的测评历史："
        "总分折线图 + 维度得分折线图（时间轴），以及记录表格（测评时间、问卷、总分、风险等级）。"
    )

    # 5.12 数据大屏
    doc.add_heading("5.12 数据大屏", level=2)
    doc.add_paragraph(
        "点击左侧菜单「数据大屏」，进入本校深色主题数据可视化大屏。"
        "数据每 30 秒自动刷新。"
    )
    add_bullet_list(doc, [
        "顶部 KPI 卡片（6项）：学生总数、教师总数、班级数量、进行中任务、答卷总数、风险提示",
        "侧边 KPI（4项）：测评完成率、有效答卷率、待处理风险、干预完成率",
        "仪表盘：测评完成率、答卷有效率、干预完成率（三个圆形仪表盘）",
        "图表区：风险等级分布饼图、风险等级柱状分布、答题质量分布饼图、维度关注信号分布、干预处理状态柱状图、维度得分排行榜",
    ])
    doc.add_paragraph("支持全屏展示和移动端自适应。")

    # 5.13 系统设置
    doc.add_heading("5.13 系统设置", level=2)
    doc.add_paragraph("点击左侧菜单「系统设置」，进行学校级配置。包含 6 个设置标签页：")

    doc.add_heading("基础设置", level=3)
    doc.add_paragraph("学校名称、学校编码（只读）、学校地址、联系电话。")

    doc.add_heading("AI分析设置", level=3)
    doc.add_paragraph(
        "AI供应商选择（支持 DeepSeek、通义千问、智谱AI、月之暗面、零一万物、百川、OpenAI、自定义），"
        "API URL（按供应商自动填充）、API Key、模型选择（含「获取模型列表」按钮）、连接测试。"
    )

    doc.add_heading("风险规则", level=3)
    doc.add_paragraph(
        "可编辑表格，按风险等级（关注/预警/警告/危急）设置最低分和最高分阈值。"
        "学生测评总分落入哪个区间，即判定为对应的风险等级。"
    )

    doc.add_heading("年级管理", level=3)
    doc.add_paragraph("管理本校的年级列表，支持添加和删除。")

    doc.add_heading("数据大屏设置", level=3)
    doc.add_paragraph("自定义大屏标题和副标题。")

    # ════════════════════════════════════════════════
    # 六、教师/心理老师操作流程
    # ════════════════════════════════════════════════
    doc.add_page_break()
    doc.add_heading("六、教师 / 心理老师操作流程", level=1)

    doc.add_paragraph(
        "教师和心理老师共用相同的页面和功能。区别在于："
    )
    add_styled_table(doc,
        ["角色", "数据范围", "特殊说明"],
        [
            ["教师（班主任）", "仅所负责班级的学生", "负责班级日常管理和初步干预"],
            ["心理老师", "全校所有学生", "可进行专业心理辅导和深度干预"],
        ],
        col_widths=[3, 5, 6]
    )
    doc.add_paragraph("心理老师通过 /counselor/ 路由前缀访问相同的功能页面。")

    # 6.1 教师首页
    doc.add_heading("6.1 教师首页", level=2)
    doc.add_paragraph("登录后进入教师首页，展示所负责工作的概况。")
    add_bullet_list(doc, [
        "统计卡片（7项）：我的班级数、我的学生数、进行中任务、待处理预警、待跟进干预、平均完成率、未完成学生数",
        "待处理风险提示列表：学生姓名 + 风险等级标签 + 风险原因，点击可跳转风险学生页",
        "待跟进干预列表：学生姓名 + 待跟进标签 + 描述，点击可跳转干预记录页",
    ])

    # 6.2 我的班级
    doc.add_heading("6.2 我的班级", level=2)
    doc.add_paragraph(
        "以卡片网格展示所负责的班级。每个班级卡片展示年级+班级名称、学生人数、状态标签。"
        "点击班级卡片可展开查看该班级所有学生的测评完成情况："
        "每名学生展示姓名、任务信息、完成进度条（已完成数/总数）或完成状态标签。"
    )

    # 6.3 我的问卷
    doc.add_heading("6.3 我的问卷与问卷编辑", level=2)
    doc.add_paragraph(
        "点击左侧菜单「我的问卷」，查看系统内置问卷和自建问卷。"
        "支持按关键词搜索。展示问卷标题、分类、题目数、适用年级、来源、状态。"
    )
    doc.add_paragraph(
        "教师可点击「新建问卷」进入问卷编辑器创建自定义问卷，编辑器功能与学校管理员版本相同（详见 5.6 节）。"
        "内置问卷可预览不可编辑，自建问卷可编辑。"
    )

    # 6.4 问卷任务
    doc.add_heading("6.4 问卷任务", level=2)
    doc.add_paragraph("包含两个标签页：")

    doc.add_heading("发布任务", level=3)
    add_numbered_steps(doc, [
        "填写任务名称",
        "从下拉列表选择问卷",
        "选择发布班级（仅显示自己负责的班级）",
        "填写任务说明",
        "设置起止时间",
        "配置高级选项：允许修改、题目随机、选项随机、质量检测、提醒策略",
        "点击发布",
    ])
    doc.add_paragraph("注意：如果没有负责的班级或没有可用问卷，发布按钮将禁用并显示提示。")

    doc.add_heading("我的任务", level=3)
    doc.add_paragraph(
        "展示已发布的任务列表：任务名称、关联问卷、状态标签、完成情况（进度条）。"
        "点击「查看」可打开完成情况弹窗，查看每名学生的姓名、完成状态、提交时间、答题用时。"
    )

    # 6.5 风险学生
    doc.add_heading("6.5 风险学生", level=2)
    doc.add_paragraph(
        "点击左侧菜单「风险学生」，查看所负责班级（心理老师为全校）中的风险学生。"
    )
    doc.add_paragraph(
        "表格展示：学生姓名、年级、班级、风险类型、风险等级（彩色标签）、触发问卷、"
        "答题质量状态、处理状态、时间。"
    )
    doc.add_paragraph("操作按钮：")
    add_bullet_list(doc, [
        "新增干预：跳转干预记录页面，自动预填充学生和预警信息",
        "答题详情：打开答题详情组件，查看该学生每道题的具体作答",
    ])

    # 6.6 干预记录
    doc.add_heading("6.6 干预记录", level=2)
    doc.add_paragraph("点击左侧菜单「干预记录」，查看和管理干预跟进记录。")

    doc.add_heading("干预列表", level=3)
    doc.add_paragraph(
        "展示：学生姓名、干预方式、内容（截断显示）、干预时间、处理状态标签、"
        "是否持续跟进标签、下次跟进时间。"
    )

    doc.add_heading("新增/编辑干预", level=3)
    doc.add_paragraph("弹窗表单包含以下字段：")
    add_bullet_list(doc, [
        "选择学生（支持远程搜索，输入姓名实时匹配）",
        "干预方式（10种可选）",
        "干预时间（日期 + 时间选择器）",
        "干预内容（多行文本）",
        "处理结果（多行文本）",
        "后续建议（多行文本）",
        "需持续跟进（Switch 开关）",
        "下次跟进时间（开启持续跟进后显示，必填）",
        "处理状态",
    ])

    doc.add_heading("查看详情", level=3)
    doc.add_paragraph("点击「查看」打开详情弹窗，展示所有干预信息的完整内容。")

    # 6.7 班级报告
    doc.add_heading("6.7 班级报告", level=2)
    doc.add_paragraph(
        "以卡片网格展示所负责的班级。每个班级卡片展示年级+班级名称、学生数、完成率进度条、风险提示数标签。"
    )
    doc.add_paragraph("点击班级卡片打开报告弹窗：")
    add_bullet_list(doc, [
        "统计：学生数、完成测评数、完成率、风险提示数",
        "质量概况：整体风险等级标签、各级别提示数、测评进度条、质量摘要",
    ])

    # ════════════════════════════════════════════════
    # 七、学生操作流程
    # ════════════════════════════════════════════════
    doc.add_page_break()
    doc.add_heading("七、学生操作流程", level=1)

    doc.add_paragraph(
        "学生端使用顶部导航栏布局（非侧边栏），界面简洁友好。"
        "包含 5 个导航项：首页、待填写、已完成、健康贴士、个人中心。"
    )

    # 7.1 登录
    doc.add_heading("7.1 登录系统", level=2)
    add_numbered_steps(doc, [
        "打开浏览器，访问 https://a.annanyun.com",
        "输入 18 位身份证号作为账号",
        "输入密码（初始密码为身份证号后 6 位）",
        "首次登录需修改密码（新密码至少 6 位）",
        "登录成功后进入学生首页",
    ])

    # 7.2 首页
    doc.add_heading("7.2 首页", level=2)
    doc.add_paragraph("首页展示：")
    add_bullet_list(doc, [
        "统计卡片（2项）：待填写问卷数、已完成问卷数",
        "待填写问卷列表（最多显示 5 条）：问卷标题、任务名称、截止时间",
        "每条问卷有「开始填写」或「继续填写」按钮",
    ])

    # 7.3 填写问卷
    doc.add_heading("7.3 填写问卷", level=2)
    doc.add_paragraph("完整的问卷填写流程包含以下步骤：")

    doc.add_heading("第 1 步：知情同意", level=3)
    doc.add_paragraph(
        "进入问卷前，系统展示知情同意书，包含保密承诺说明和 4 条要点。"
        "学生需勾选「我已阅读并同意」复选框，然后点击「同意并开始测评」按钮。"
    )

    doc.add_heading("第 2 步：答题", level=3)
    doc.add_paragraph("答题界面包含：")
    add_bullet_list(doc, [
        "顶部：问卷标题、任务名称、描述、截止时间",
        "进度条：显示当前答题进度",
        "题目卡片：题干文本",
        "答题区域：根据题型不同展示不同输入控件",
    ])

    doc.add_paragraph("题型对应的答题方式：")
    add_styled_table(doc,
        ["题型", "答题方式"],
        [
            ["单选题 / 量表题", "点击 Radio 单选按钮"],
            ["多选题", "勾选 Checkbox 多选框"],
            ["判断题", "点击 Radio.Button 选择"],
            ["填空题 / 简答题", "在 TextArea 中输入文本"],
        ],
        col_widths=[4, 10]
    )

    doc.add_heading("第 3 步：保存与提交", level=3)
    add_bullet_list(doc, [
        "自动保存：系统每 30 秒自动保存答题进度，断开连接后可继续",
        "手动保存：点击「保存进度」按钮",
        "提交：完成所有题目后点击「提交问卷」按钮",
        "确认提交：系统弹窗提醒「提交后不可修改」，确认后完成提交",
    ])

    doc.add_heading("第 4 步：完成", level=3)
    doc.add_paragraph("提交成功后显示完成提示页面，可导航至「已完成」或返回首页。")

    # 7.4 已完成
    doc.add_heading("7.4 已完成", level=2)
    doc.add_paragraph(
        "以卡片列表展示已提交的问卷。每张卡片展示：问卷标题、任务名称、已完成标签、提交日期。"
    )
    doc.add_paragraph("点击卡片可展开查看详情：")
    add_bullet_list(doc, [
        "问卷名称、所属任务",
        "提交时间、答题用时",
        "得分（如系统管理允许学生查看结果）",
        "答题质量（good/medium/poor）",
        "评语",
    ])

    # 7.5 健康贴士
    doc.add_heading("7.5 健康贴士", level=2)
    doc.add_paragraph("提供心理健康教育内容：")

    doc.add_heading("心理健康小知识", level=3)
    add_bullet_list(doc, [
        "认识情绪：了解不同情绪是正常的",
        "释放压力：运动、音乐、绘画等方式缓解压力",
        "人际关系：学会表达和倾听",
        "照顾自己：保持规律的作息和饮食",
        "积极思维：用积极的视角看待困难",
    ])

    doc.add_heading("情绪管理小技巧", level=3)
    add_bullet_list(doc, [
        "深呼吸：感到紧张时，慢慢深呼吸几次",
        "写日记：把心情写下来，帮助整理思绪",
        "找人倾诉：和信任的人聊聊感受",
        "运动：运动能帮助改善情绪",
    ])

    doc.add_heading("寻求帮助途径", level=3)
    add_styled_table(doc,
        ["途径", "说明"],
        [
            ["学校心理老师", "可以在学校找到心理老师倾诉"],
            ["12355 热线", "24小时青少年服务热线"],
            ["信任的老师", "可以找班主任或信任的老师聊聊"],
            ["家人", "可以和家人说说自己的感受"],
        ],
        col_widths=[3, 11]
    )

    p = doc.add_paragraph()
    run = p.add_run("24小时心理援助热线：12355、400-161-9995")
    run.bold = True
    run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
    run.font.size = Pt(13)

    # 7.6 个人中心
    doc.add_heading("7.6 个人中心", level=2)
    doc.add_paragraph("点击顶部导航「个人中心」，查看个人信息。")
    add_bullet_list(doc, [
        "基本信息卡片：姓名、账号、角色标签、学号、性别、手机号",
        "最近测评记录列表：问卷标题 + 任务名称 + 已完成标签 + 提交时间 + 答题用时",
        "修改密码：点击「修改密码」按钮，输入原密码和新密码（至少 6 位），修改成功后需重新登录",
    ])

    # ════════════════════════════════════════════════
    # 八、核心工作流程
    # ════════════════════════════════════════════════
    doc.add_page_break()
    doc.add_heading("八、核心工作流程", level=1)

    # 8.1 问卷测评全流程
    doc.add_heading("8.1 问卷测评全流程", level=2)
    doc.add_paragraph("以下是一次完整的问卷测评从创建到结果产出的全流程：")
    add_numbered_steps(doc, [
        "学校管理员/教师创建或选择问卷（可使用内置问卷或自建问卷）",
        "发布测评任务（选择目标班级、设置起止时间、配置质量检测等）",
        "学生登录系统，在「待填写」页面看到待完成的问卷",
        "学生进入答题 → 签署知情同意书 → 逐题作答（每 30 秒自动保存进度）",
        "学生提交问卷",
        "后端自动执行评分（按评分规则计算各维度分和总分）",
        "后端自动执行答题质量检测（注意力检测、快速作答、规律性、矛盾题、相同选项比率等）",
        "按风险规则判定风险等级（关注/预警/警告/危急）",
        "达到预警等级（橙色及以上）的自动生成风险预警记录",
        "学校管理员/教师在风险预警页面看到新预警",
        "教师/心理老师新增干预记录，跟进处理",
        "平台管理员在风险预警中心/干预督办查看全区情况",
    ])

    # 8.2 风险预警与干预流程
    doc.add_heading("8.2 风险预警与干预流程", level=2)
    doc.add_paragraph("风险预警生成后的标准处理流程：")
    add_numbered_steps(doc, [
        "系统自动生成风险预警记录（根据评分结果和风险规则）",
        "学校管理员/教师/心理老师在风险预警页面查看待处理预警",
        "查看风险详情：了解学生的维度得分、答题质量、综合评估",
        "（可选）使用AI智能分析获取辅助研判建议",
        "选择干预方式并新增干预记录",
        "持续跟进：对标记为「需持续跟进」的学生定期更新干预记录",
        "更新处理状态：待处理 → 处理中 → 持续跟进 → 已完成/已关闭",
        "平台管理员通过干预督办督促未及时处理的学校",
    ])

    # 8.3 身份证号安全机制
    doc.add_heading("8.3 身份证号安全机制", level=2)
    doc.add_paragraph("为保护学生隐私，系统对身份证号实施多层安全保护：")
    add_numbered_steps(doc, [
        "所有列表和详情页面中，身份证号默认脱敏显示（如 990****0015）",
        "如需查看完整身份证号，点击身份证号旁的「眼睛」图标",
        "系统弹出密码验证对话框，要求输入当前登录密码",
        "后端验证密码正确后返回完整身份证号",
        "完整身份证号仅在本次会话中显示，刷新页面后恢复脱敏",
        "每次查看完整身份证号都会记录到审计日志",
        "导出包含敏感字段的 CSV 文件同样需要密码验证",
    ])

    # 8.4 答题质量检测体系
    doc.add_heading("8.4 答题质量检测体系", level=2)
    doc.add_paragraph("系统通过多维度检测确保答卷数据真实可靠：")

    add_styled_table(doc,
        ["检测维度", "说明", "判定标准"],
        [
            ["注意力检测题", "问卷中内嵌测试题", "答错则扣分"],
            ["快速作答检测", "答题速度过快", "单题答题时间低于阈值（默认 3 秒）"],
            ["连续相同选项", "多题选择同一选项", "连续 N 题选择相同选项"],
            ["矛盾题分析", "相关题目答案矛盾", "矛盾题组答案差异超过允许范围"],
            ["规律性检测", "作答呈现规律模式", "如交替选择 A/B/C/D"],
            ["全否定/全肯定", "所有题目选择同一极值", "全部选择最高/最低分选项"],
            ["相同选项比率", "某选项占比过高", "同一选项占比超过阈值"],
        ],
        col_widths=[3, 5, 6]
    )

    doc.add_paragraph("质量等级判定：")
    add_styled_table(doc,
        ["等级", "含义", "处理建议"],
        [
            ["正常", "答卷数据可信", "正常纳入统计"],
            ["存疑", "存在轻微异常", "建议关注，可纳入统计"],
            ["轻度异常", "存在一定问题", "建议复测"],
            ["中度异常", "数据可靠性不足", "建议复测，谨慎使用"],
            ["严重异常", "数据不可信", "不建议纳入统计，需重新测评"],
        ],
        col_widths=[2.5, 4, 8]
    )

    # ════════════════════════════════════════════════
    # 九、常见问题
    # ════════════════════════════════════════════════
    doc.add_page_break()
    doc.add_heading("九、常见问题", level=1)

    faqs = [
        ("忘记密码怎么办？",
         "登录页面点击「忘记密码」，输入用户名和绑定的手机号，"
         "发送短信验证码后设置新密码。如未绑定手机号，请联系学校管理员重置密码。"),

        ("学生账号是什么？",
         "学生账号为 18 位身份证号，默认密码为身份证号后 6 位。首次登录需修改密码。"),

        ("如何重置用户密码？",
         "学校管理员可在「学生管理」或「教师管理」中点击对应用户的「重置密码」按钮。"
         "学生密码重置为身份证号后 6 位。平台管理员密码重置会自动生成临时密码。"),

        ("风险预警是如何生成的？",
         "系统根据学生问卷评分自动计算风险等级。达到「预警」（橙色）及以上等级时，"
         "系统自动生成风险预警记录，由学校教师跟进干预。风险等级可在系统设置中调整阈值。"),

        ("如何查看完整身份证号？",
         "点击身份证号旁的「眼睛」图标，在弹窗中输入当前登录密码，验证通过后即可查看。"
         "此操作会记录到审计日志。"),

        ("数据是否安全？",
         "所有数据使用加密传输（HTTPS），身份证号和手机号默认脱敏显示。"
         "敏感操作（查看身份证号、导出数据、进入学校后台）需要密码二次验证并记录审计日志。"),

        ("AI研判分析如何使用？",
         "平台管理员在系统管理中配置 AI 接口（支持 DeepSeek、通义千问、智谱 AI 等），"
         "然后在 AI 研判分析页面生成区域报告，或在单个学生的风险详情中使用 AI 分析。"
         "学校管理员可在本校系统设置中单独配置 AI 接口。"),

        ("问卷可以自定义吗？",
         "可以。学校管理员和教师可创建自定义问卷，支持 6 种题型、自定义维度、"
         "评分规则、风险规则和答题质量规则。也可将内置问卷复制为副本后修改。"),

        ("如何批量导入学生？",
         "在「学生管理」页面，先下载导入模板，按模板格式填写学生数据后上传 Excel 文件。"
         "系统会显示导入结果，包括成功和失败的条数及错误详情。"),

        ("演示数据说明",
         "当前系统中的数据均为虚构演示数据，所有名称后缀\"(演示)\"以示区分。"
         "正式使用时需清理演示数据并导入真实数据。包含 3 所演示学校、489 名学生、"
         "18 位教师、3 位心理老师、20 套问卷、520 条风险预警、20 条干预记录。"),
    ]
    for q, a in faqs:
        p = doc.add_paragraph()
        run = p.add_run(f"Q：{q}")
        run.bold = True
        run.font.color.rgb = RGBColor(0x2B, 0x57, 0x9A)
        run.font.size = Pt(12)
        p = doc.add_paragraph(f"A：{a}")
        p.paragraph_format.space_after = Pt(12)

    # ── 附录：技术架构 ──
    doc.add_page_break()
    doc.add_heading("附录：技术架构", level=1)

    add_styled_table(doc,
        ["项目", "技术"],
        [
            ["前端框架", "React 18 + TypeScript"],
            ["UI 组件库", "Ant Design 5"],
            ["图表库", "ECharts 5"],
            ["状态管理", "Zustand"],
            ["路由", "React Router 6"],
            ["构建工具", "Vite"],
            ["后端框架", "Python FastAPI"],
            ["ORM", "SQLAlchemy 2"],
            ["数据库", "MySQL"],
            ["认证方式", "JWT Token"],
            ["AI 接入", "OpenAI 兼容接口（支持 DeepSeek、通义千问、智谱 AI 等）"],
            ["短信服务", "阿里云 / 腾讯云短信"],
            ["部署环境", "宝塔面板 + systemd"],
        ],
        col_widths=[4, 10]
    )

    # ── 保存 ──
    output_path = SCRIPT_DIR / "金盾护苗平台操作手册.docx"
    doc.save(str(output_path))
    print(f"文档已生成: {output_path}")


if __name__ == "__main__":
    generate_manual()
