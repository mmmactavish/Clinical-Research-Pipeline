"""
PPT 自动生成器
从 CRP 各阶段输出文件读取内容，生成汇报 PPT

用法:
    python ppt_builder.py \
      --input-dir ./crp_output \
      --output ./crp_output/phase5_ppt/final_report.pptx \
      --title "SGLT2抑制剂对心力衰竭患者预后的影响" \
      --author "张三" \
      --type 开题报告

依赖: pip install python-pptx
"""

import json
import sys
import argparse
import os
import re
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu, Cm
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.enum.shapes import MSO_SHAPE
except ImportError:
    sys.stderr.write("Error: python-pptx not installed. Run: pip install python-pptx\n")
    sys.exit(1)


# === 颜色主题 ===
COLOR_PRIMARY = RGBColor(0x1B, 0x3A, 0x5C)    # 深蓝
COLOR_ACCENT = RGBColor(0xE8, 0x77, 0x22)      # 橙色
COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
COLOR_BLACK = RGBColor(0x00, 0x00, 0x00)
COLOR_GRAY = RGBColor(0x66, 0x66, 0x66)
COLOR_LIGHT_BG = RGBColor(0xF5, 0xF7, 0xFA)

# 字体
FONT_CN_TITLE = "微软雅黑"
FONT_CN_BODY = "宋体"
FONT_EN = "Calibri"


# === Slide 内容映射 (Bilingual: zh + en) ===
SLIDE_CONTENT_MAP = {
    "zh": {
        "开题报告": [
            {"title": "封面", "source": None, "type": "cover"},
            {"title": "目录", "source": None, "type": "toc"},
            {"title": "研究背景 — 疾病负担与未满足需求", "source": "phase1_background/01_background.md", "type": "content"},
            {"title": "研究背景 — 现有证据与知识空白", "source": "phase1_background/02_knowledge_gap.md", "type": "content"},
            {"title": "文献综述 — 关键文献矩阵", "source": "phase2_literature/04_literature_matrix.md", "type": "table"},
            {"title": "文献综述 — 关键词热点与趋势", "source": "phase2_literature/05_keyword_analysis.md", "type": "content"},
            {"title": "研究目的与假设", "source": "phase1_background/03_storyline.md", "type": "content"},
            {"title": "研究设计 — 类型与PICO框架", "source": "phase3_design/07_study_design.md", "type": "content"},
            {"title": "研究设计 — 入排标准与流程图", "source": "phase3_design/07_study_design.md", "type": "flowchart"},
            {"title": "样本量估算", "source": "phase3_design/07_study_design.md", "type": "table"},
            {"title": "统计分析计划", "source": "phase4_statistics/10_statistical_plan.md", "type": "content"},
            {"title": "预期结果", "source": None, "type": "placeholder"},
            {"title": "不足与展望", "source": "phase4_statistics/11_limitations.md", "type": "content"},
            {"title": "致谢 / Q&A", "source": None, "type": "closing"},
        ],
        "结题汇报": [
            {"title": "封面", "source": None, "type": "cover"},
            {"title": "目录", "source": None, "type": "toc"},
            {"title": "研究背景与目的", "source": "phase1_background/03_storyline.md", "type": "content"},
            {"title": "研究设计与方法", "source": "phase3_design/07_study_design.md", "type": "content"},
            {"title": "基线特征", "source": None, "type": "placeholder"},
            {"title": "主要结果", "source": None, "type": "placeholder"},
            {"title": "次要结果", "source": None, "type": "placeholder"},
            {"title": "亚组分析", "source": None, "type": "placeholder"},
            {"title": "安全性", "source": None, "type": "placeholder"},
            {"title": "讨论 — 与既往研究对比", "source": "phase2_literature/06_inspiration.md", "type": "content"},
            {"title": "不足与展望", "source": "phase4_statistics/11_limitations.md", "type": "content"},
            {"title": "结论", "source": None, "type": "placeholder"},
            {"title": "致谢 / Q&A", "source": None, "type": "closing"},
        ],
        "基金申请": [
            {"title": "封面", "source": None, "type": "cover"},
            {"title": "立项依据", "source": "phase1_background/01_background.md", "type": "content"},
            {"title": "研究目标与假说", "source": "phase1_background/03_storyline.md", "type": "content"},
            {"title": "研究方案概览", "source": "phase3_design/07_study_design.md", "type": "content"},
            {"title": "关键技术路线", "source": "phase3_design/07_study_design.md", "type": "flowchart"},
            {"title": "可行性分析", "source": "phase3_design/09_reference_cases.md", "type": "content"},
            {"title": "预期成果", "source": None, "type": "placeholder"},
            {"title": "研究团队与预算", "source": None, "type": "placeholder"},
        ],
    },
    "en": {
        "Research Proposal": [
            {"title": "Cover", "source": None, "type": "cover"},
            {"title": "Table of Contents", "source": None, "type": "toc"},
            {"title": "Background — Disease Burden & Unmet Needs", "source": "phase1_background/01_background.md", "type": "content"},
            {"title": "Background — Existing Evidence & Knowledge Gaps", "source": "phase1_background/02_knowledge_gap.md", "type": "content"},
            {"title": "Literature Review — Key Study Matrix", "source": "phase2_literature/04_literature_matrix.md", "type": "table"},
            {"title": "Literature Review — Keyword Hotspots & Trends", "source": "phase2_literature/05_keyword_analysis.md", "type": "content"},
            {"title": "Study Aims & Hypotheses", "source": "phase1_background/03_storyline.md", "type": "content"},
            {"title": "Study Design — Type & PICO Framework", "source": "phase3_design/07_study_design.md", "type": "content"},
            {"title": "Study Design — Eligibility Criteria & Flow Diagram", "source": "phase3_design/07_study_design.md", "type": "flowchart"},
            {"title": "Sample Size Estimation", "source": "phase3_design/07_study_design.md", "type": "table"},
            {"title": "Statistical Analysis Plan", "source": "phase4_statistics/10_statistical_plan.md", "type": "content"},
            {"title": "Expected Results", "source": None, "type": "placeholder"},
            {"title": "Limitations & Future Directions", "source": "phase4_statistics/11_limitations.md", "type": "content"},
            {"title": "Acknowledgements / Q&A", "source": None, "type": "closing"},
        ],
        "Final Report": [
            {"title": "Cover", "source": None, "type": "cover"},
            {"title": "Table of Contents", "source": None, "type": "toc"},
            {"title": "Background & Aims", "source": "phase1_background/03_storyline.md", "type": "content"},
            {"title": "Study Design & Methods", "source": "phase3_design/07_study_design.md", "type": "content"},
            {"title": "Baseline Characteristics", "source": None, "type": "placeholder"},
            {"title": "Primary Results", "source": None, "type": "placeholder"},
            {"title": "Secondary Results", "source": None, "type": "placeholder"},
            {"title": "Subgroup Analyses", "source": None, "type": "placeholder"},
            {"title": "Safety Outcomes", "source": None, "type": "placeholder"},
            {"title": "Discussion — Comparison with Prior Studies", "source": "phase2_literature/06_inspiration.md", "type": "content"},
            {"title": "Limitations & Future Directions", "source": "phase4_statistics/11_limitations.md", "type": "content"},
            {"title": "Conclusions", "source": None, "type": "placeholder"},
            {"title": "Acknowledgements / Q&A", "source": None, "type": "closing"},
        ],
        "Grant Application": [
            {"title": "Cover", "source": None, "type": "cover"},
            {"title": "Background & Rationale", "source": "phase1_background/01_background.md", "type": "content"},
            {"title": "Aims & Hypotheses", "source": "phase1_background/03_storyline.md", "type": "content"},
            {"title": "Study Design Overview", "source": "phase3_design/07_study_design.md", "type": "content"},
            {"title": "Key Technical Approach", "source": "phase3_design/07_study_design.md", "type": "flowchart"},
            {"title": "Feasibility Analysis", "source": "phase3_design/09_reference_cases.md", "type": "content"},
            {"title": "Expected Outcomes", "source": None, "type": "placeholder"},
            {"title": "Research Team & Budget", "source": None, "type": "placeholder"},
        ],
    },
}

# Type key mapping between zh/en
OUTPUT_TYPE_MAP = {
    "zh": {"开题报告": "开题报告", "结题汇报": "结题汇报", "基金申请": "基金申请"},
    "en": {"Research Proposal": "Research Proposal", "Final Report": "Final Report", "Grant Application": "Grant Application"},
}


def read_file_content(filepath: str) -> str:
    """读取文件内容"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"[文件未找到: {filepath}]"
    except Exception as e:
        return f"[读取错误: {e}]"


def extract_bullets(text: str, max_bullets: int = 6) -> list[str]:
    """从 markdown 文本中提取 bullet points"""
    bullets = []

    # 提取 markdown bullet 行
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            bullet = line[2:].strip()
            # 清理 markdown 格式
            bullet = re.sub(r'\*\*(.*?)\*\*', r'\1', bullet)
            bullet = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', bullet)
            if len(bullet) > 5:
                bullets.append(bullet)

    # 如果没有 bullet points，提取表格行或段落首句
    if not bullets:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and not p.startswith("#")]
        for p in paragraphs[:max_bullets]:
            # 取每段首句
            first_sentence = re.split(r'[。.]', p)[0]
            if len(first_sentence) > 10:
                bullets.append(first_sentence.strip())

    return bullets[:max_bullets]


def extract_table_data(text: str, max_rows: int = 8) -> Optional[list[list[str]]]:
    """从 markdown 文本中提取表格数据"""
    lines = text.split("\n")
    table_lines = []
    in_table = False

    for line in lines:
        if line.startswith("|"):
            if not in_table:
                in_table = True
            table_lines.append(line)
        elif in_table and not line.startswith("|"):
            break

    if not table_lines:
        return None

    # 解析表格
    rows = []
    for line in table_lines:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if all(c.replace("-", "").replace(":", "").strip() == "" for c in cells):
            continue  # 跳过分隔行
        if cells:
            rows.append(cells)

    return rows[:max_rows] if rows else None


def add_slide_number(slide, num: int, total: int):
    """在 slide 底部添加页码"""
    left = Inches(0)
    top = Inches(7.0)
    width = Inches(10)
    height = Inches(0.3)

    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = f"{num} / {total}"
    p.font.size = Pt(10)
    p.font.color.rgb = COLOR_GRAY
    p.alignment = PP_ALIGN.CENTER


def add_bottom_bar(slide):
    """底部装饰条"""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(7.1),
        Inches(10), Inches(0.05),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLOR_ACCENT
    shape.line.fill.background()


def build_slide_content(prs, slide_info: dict, input_dir: str, total_slides: int, slide_num: int, lang: str = "zh"):
    """根据 slide 类型构建内容"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout

    slide_type = slide_info["type"]
    title_text = slide_info["title"]

    if slide_type == "cover":
        build_cover_slide(slide, input_dir, lang)
        return

    if slide_type == "toc":
        build_toc_slide(slide, prs, input_dir, lang)
        return

    if slide_type == "closing":
        build_closing_slide(slide, lang)
        add_slide_number(slide, slide_num, total_slides)
        return

    # 标准内容 slide: 标题 + 内容
    # 标题栏（深蓝背景）
    title_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0),
        Inches(10), Inches(0.9),
    )
    title_shape.fill.solid()
    title_shape.fill.fore_color.rgb = COLOR_PRIMARY
    title_shape.line.fill.background()

    tf = title_shape.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE
    p.font.name = FONT_CN_TITLE if lang == "zh" else FONT_EN
    p.alignment = PP_ALIGN.LEFT
    # 左边距
    tf.margin_left = Inches(0.6)

    # 内容区
    source = slide_info.get("source")
    if source:
        filepath = os.path.join(input_dir, source)
        text_content = read_file_content(filepath)

        if slide_type == "table":
            table_data = extract_table_data(text_content)
            if table_data:
                build_table_on_slide(slide, table_data, lang)
            else:
                bullets = extract_bullets(text_content)
                add_bullet_text(slide, bullets, lang)
        elif slide_type == "flowchart":
            bullets = extract_bullets(text_content, max_bullets=8)
            add_flowchart_text(slide, bullets, lang)
        elif slide_type == "placeholder":
            add_placeholder_text(slide, title_text, lang)
        else:
            bullets = extract_bullets(text_content)
            add_bullet_text(slide, bullets, lang)
    else:
        add_placeholder_text(slide, title_text, lang)

    add_slide_number(slide, slide_num, total_slides)
    add_bottom_bar(slide)


def build_cover_slide(slide, input_dir: str, lang: str = "zh"):
    """生成封面 slide"""
    # 深蓝背景
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = COLOR_PRIMARY

    # 橙色装饰条
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(3.0),
        Inches(10), Inches(0.06),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLOR_ACCENT
    shape.line.fill.background()

    # 尝试从 project_state.json 读取标题
    state_file = os.path.join(input_dir, "project_state.json")
    title = "临床研究汇报" if lang == "zh" else "Clinical Research Report"
    author = ""
    affiliation = ""
    date_str = datetime.now().strftime("%Y年%m月") if lang == "zh" else datetime.now().strftime("%B %Y")

    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
            title = (state.get("research_topic") or title) if lang == "zh" else (state.get("research_topic_en") or state.get("research_topic") or title)
            author = state.get("author_info", {}).get("name", "")
            affiliation = state.get("author_info", {}).get("affiliation", "")

    # 标题
    txBox = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(8), Inches(1.2))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE
    p.font.name = FONT_CN_TITLE if lang == "zh" else FONT_EN
    p.alignment = PP_ALIGN.CENTER

    # 副标题
    txBox2 = slide.shapes.add_textbox(Inches(1), Inches(3.5), Inches(8), Inches(1.0))
    tf2 = txBox2.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = author
    p2.font.size = Pt(20)
    p2.font.color.rgb = COLOR_WHITE
    p2.font.name = FONT_CN_BODY if lang == "zh" else FONT_EN
    p2.alignment = PP_ALIGN.CENTER

    if affiliation:
        p3 = tf2.add_paragraph()
        p3.text = affiliation
        p3.font.size = Pt(16)
        p3.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
        p3.font.name = FONT_CN_BODY if lang == "zh" else FONT_EN
        p3.alignment = PP_ALIGN.CENTER

    # 日期
    txBox3 = slide.shapes.add_textbox(Inches(1), Inches(5.5), Inches(8), Inches(0.5))
    tf3 = txBox3.text_frame
    p4 = tf3.paragraphs[0]
    p4.text = date_str
    p4.font.size = Pt(14)
    p4.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)
    p4.font.name = FONT_CN_BODY if lang == "zh" else FONT_EN
    p4.alignment = PP_ALIGN.CENTER


def build_toc_slide(slide, prs, input_dir: str, lang: str = "zh"):
    """生成目录 slide"""
    # 标题
    title_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0),
        Inches(10), Inches(0.9),
    )
    title_shape.fill.solid()
    title_shape.fill.fore_color.rgb = COLOR_PRIMARY
    title_shape.line.fill.background()
    tf = title_shape.text_frame
    tf.margin_left = Inches(0.6)
    p = tf.paragraphs[0]
    p.text = "目  录" if lang == "zh" else "Table of Contents"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE
    p.font.name = FONT_CN_TITLE if lang == "zh" else FONT_EN

    # 获取 slide 列表
    state_file = os.path.join(input_dir, "project_state.json")
    output_type_key = "开题报告" if lang == "zh" else "Research Proposal"
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
            raw_type = state.get("output_type", output_type_key)
            # Map to correct lang key
            reverse_map = {
                "开题报告": {"zh": "开题报告", "en": "Research Proposal"},
                "结题汇报": {"zh": "结题汇报", "en": "Final Report"},
                "基金申请": {"zh": "基金申请", "en": "Grant Application"},
            }
            output_type_key = reverse_map.get(raw_type, {}).get(lang, output_type_key)

    slides_list = SLIDE_CONTENT_MAP.get(lang, {}).get(output_type_key, [])
    if not slides_list:
        # fallback
        slides_list = SLIDE_CONTENT_MAP.get("zh", {}).get("开题报告", [])
    content_slides = [s for s in slides_list if s["type"] not in ("cover", "toc", "closing")]

    txBox = slide.shapes.add_textbox(Inches(1.5), Inches(1.3), Inches(7), Inches(5.3))
    tf2 = txBox.text_frame
    tf2.word_wrap = True

    for i, s in enumerate(content_slides, 1):
        p = tf2.add_paragraph() if i > 1 else tf2.paragraphs[0]
        p.text = f"  {i:02d}    {s['title']}"
        p.font.size = Pt(16)
        p.font.name = FONT_CN_BODY if lang == "zh" else FONT_EN
        p.font.color.rgb = COLOR_BLACK
        p.space_after = Pt(8)


def build_closing_slide(slide, lang: str = "zh"):
    """生成致谢 slide"""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = COLOR_PRIMARY

    txBox = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(8), Inches(1.5))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = "感谢聆听" if lang == "zh" else "Thank You"
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE
    p.font.name = FONT_CN_TITLE if lang == "zh" else FONT_EN
    p.alignment = PP_ALIGN.CENTER

    p2 = tf.add_paragraph()
    p2.text = "Q & A"
    p2.font.size = Pt(28)
    p2.font.color.rgb = COLOR_ACCENT
    p2.font.name = FONT_EN
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(20)


def add_bullet_text(slide, bullets: list[str], lang: str = "zh"):
    """添加 bullet point 文本"""
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(8.4), Inches(5.5))
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, bullet in enumerate(bullets):
        p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
        p.text = f"• {bullet}"
        p.font.size = Pt(16)
        p.font.name = FONT_CN_BODY if lang == "zh" else FONT_EN
        p.font.color.rgb = COLOR_BLACK
        p.space_after = Pt(10)
        p.level = 0


def add_flowchart_text(slide, items: list[str], lang: str = "zh"):
    """用简单流程图样式展示条目"""
    y_start = 1.3
    for i, item in enumerate(items):
        y = y_start + i * 0.65

        # 序号圆
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(0.8), Inches(y),
            Inches(0.4), Inches(0.4),
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = COLOR_ACCENT
        circle.line.fill.background()
        tf = circle.text_frame
        p = tf.paragraphs[0]
        p.text = str(i + 1)
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE
        p.alignment = PP_ALIGN.CENTER

        # 箭头（最后一个不加）
        if i < len(items) - 1:
            arrow = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(0.98), Inches(y + 0.42),
                Inches(0.04), Inches(0.22),
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = COLOR_ACCENT
            arrow.line.fill.background()

        # 文字
        txBox = slide.shapes.add_textbox(Inches(1.5), Inches(y - 0.02), Inches(7.5), Inches(0.45))
        tf2 = txBox.text_frame
        p2 = tf2.paragraphs[0]
        p2.text = item[:100]  # 截断过长文字
        p2.font.size = Pt(14)
        p2.font.name = FONT_CN_BODY
        p2.font.color.rgb = COLOR_BLACK


def build_table_on_slide(slide, table_data: list[list[str]], lang: str = "zh"):
    """在 slide 上绘制表格"""
    if not table_data:
        return

    n_rows = len(table_data)
    n_cols = max(len(row) for row in table_data)

    left = Inches(0.4)
    top = Inches(1.2)
    width = Inches(9.2)
    height = Inches(5.5)

    table_shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, height)
    table = table_shape.table

    # 填充数据
    for r, row in enumerate(table_data):
        for c, cell_text in enumerate(row):
            if c < n_cols:
                cell = table.cell(r, c)
                cell.text = cell_text
                # 表头样式
                if r == 0:
                    for paragraph in cell.text_frame.paragraphs:
                        paragraph.font.bold = True
                        paragraph.font.size = Pt(11)
                        paragraph.font.name = FONT_CN_BODY
                        paragraph.font.color.rgb = COLOR_WHITE
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = COLOR_PRIMARY
                else:
                    for paragraph in cell.text_frame.paragraphs:
                        paragraph.font.size = Pt(10)
                        paragraph.font.name = FONT_CN_BODY

                # 交替行颜色
                if r % 2 == 0 and r > 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = COLOR_LIGHT_BG


def add_placeholder_text(slide, title: str, lang: str = "zh"):
    """添加占位符文本（用于尚未有数据源的 slide）"""
    txBox = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(8), Inches(1.5))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = f"📋 {title}"
    p.font.size = Pt(20)
    p.font.color.rgb = COLOR_GRAY
    p.font.name = FONT_CN_BODY if lang == "zh" else FONT_EN
    p.alignment = PP_ALIGN.CENTER

    p2 = tf.add_paragraph()
    p2.text = "此页面需要手动填充数据" if lang == "zh" else "This slide requires manual data entry"
    p2.font.size = Pt(14)
    p2.font.color.rgb = COLOR_GRAY
    p2.font.name = FONT_CN_BODY if lang == "zh" else FONT_EN
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(10)


def build_ppt(
    input_dir: str,
    output_path: str,
    title: str = "临床研究汇报",
    author: str = "",
    output_type: str = "开题报告",
    affiliation: str = "",
    lang: str = "zh",
) -> str:
    """
    主入口：根据 phase 输出文件生成 PPT

    Args:
        input_dir: CRP 项目输出目录 (包含 phase1_background/ 等子目录)
        output_path: 输出 .pptx 路径
        title: 研究标题
        author: 作者
        output_type: 开题报告 / 结题汇报 / 基金申请 (or English equivalents)
        affiliation: 单位
        lang: "zh" (中文) or "en" (English)

    Returns:
        输出文件路径
    """
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 创建 presentation (16:9)
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # 获取 slide 结构
    slides_list = SLIDE_CONTENT_MAP.get(lang, SLIDE_CONTENT_MAP["zh"]).get(output_type)
    if not slides_list:
        # Fallback: try zh version
        fallback_type = OUTPUT_TYPE_MAP.get("zh", {}).get(output_type, "开题报告")
        slides_list = SLIDE_CONTENT_MAP["zh"].get(fallback_type, SLIDE_CONTENT_MAP["zh"]["开题报告"])
    total = len(slides_list)

    sys.stderr.write(f"Building PPT ({lang}): {total} slides, type={output_type}\n")

    # 生成 slide 元数据
    slide_meta = []
    for i, slide_info in enumerate(slides_list, 1):
        build_slide_content(prs, slide_info, input_dir, total, i, lang)
        slide_meta.append({
            "slide_number": i,
            "title": slide_info["title"],
            "type": slide_info["type"],
        })

    # 保存
    prs.save(output_path)

    # 保存 slide 元数据
    meta_path = os.path.join(os.path.dirname(output_path), "slide_content.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"language": lang, "slides": slide_meta}, f, ensure_ascii=False, indent=2)

    sys.stderr.write(f"PPT saved to: {output_path}\n")
    sys.stderr.write(f"Slide metadata: {meta_path}\n")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="CRP PPT Builder")
    parser.add_argument("--input-dir", required=True, help="CRP project output directory")
    parser.add_argument("--output", required=True, help="Output .pptx file path")
    parser.add_argument("--title", default="临床研究汇报", help="Research title")
    parser.add_argument("--author", default="", help="Author name")
    parser.add_argument("--affiliation", default="", help="Author affiliation")
    parser.add_argument("--type", dest="output_type", default="开题报告",
                       help="Output PPT type (开题报告/结题汇报/基金申请 or Research Proposal/Final Report/Grant Application)")
    parser.add_argument("--lang", default="zh", choices=["zh", "en"],
                       help="Output language: zh (中文) or en (English)")

    args = parser.parse_args()

    result = build_ppt(
        input_dir=args.input_dir,
        output_path=args.output,
        title=args.title,
        author=args.author,
        output_type=args.output_type,
        affiliation=args.affiliation,
        lang=args.lang,
    )
    print(json.dumps({"status": "ok", "output": result, "language": args.lang}))


if __name__ == "__main__":
    main()
