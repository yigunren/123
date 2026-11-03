"""生成课程设计报告 DOCX（后续用 WPS 导出 PDF）。"""
import json
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ROOT, FIG_DIR, METRIC_DIR, CLASS_NAMES_EN, CLASS_NAMES_ZH

REPORT_DIR = ROOT / "report"
REPORT_DIR.mkdir(exist_ok=True)

GREEN = RGBColor(0x0B, 0x3B, 0x2E)
FOREST = RGBColor(0x14, 0x51, 0x3E)
AMBER = RGBColor(0x8A, 0x5A, 0x10)
GRAY = RGBColor(0x66, 0x6F, 0x68)
LIGHT = "F4F1E8"
DARK = "0B3B2E"


def set_run_font(run, name="宋体", size=11, bold=False, color=None, italic=False):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def fmt_para(p, first_line=True, line=1.55, before=0, after=5, align=None):
    pf = p.paragraph_format
    pf.line_spacing = line
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if first_line:
        pf.first_line_indent = Cm(0.74)
    if align is not None:
        p.alignment = align


def body(doc, text, indent=True, bold=False, size=11):
    p = doc.add_paragraph()
    fmt_para(p, first_line=indent)
    r = p.add_run(text)
    set_run_font(r, "宋体", size, bold=bold, color=RGBColor(0x1A, 0x1A, 0x1A))
    return p


def heading(doc, text, level=1):
    sizes = {1: 16, 2: 13, 3: 11.5}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12 if level == 1 else 8)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_run_font(r, "Microsoft YaHei", sizes[level], bold=True, color=GREEN)
    if level == 1:
        # 标题下加一条细线
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:space"), "3")
        bottom.set(qn("w:color"), "C7953F")
        pBdr.append(bottom)
        pPr.append(pBdr)
    return p


def caption(doc, text, keep_with_next=False):
    p = doc.add_paragraph()
    fmt_para(p, first_line=False, line=1.2, before=3, after=8, align=WD_ALIGN_PARAGRAPH.CENTER)
    p.paragraph_format.keep_with_next = keep_with_next
    r = p.add_run(text)
    set_run_font(r, "宋体", 9, color=GRAY)


def table_caption(doc, text):
    caption(doc, text, keep_with_next=True)


def picture(doc, path, width_cm=15.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(path), width=Cm(width_cm))


def shade_cell(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def table(doc, headers, rows, widths=None, font_size=9, first_col_left=True):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = True
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        set_run_font(r, "黑体", font_size, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        shade_cell(hdr[i], DARK)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if (i == 0 and first_col_left) else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            r = p.add_run(str(val))
            set_run_font(r, "宋体", font_size, color=RGBColor(0x1A, 0x1A, 0x1A))
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)

    # 表头跨页重复 + 行不跨页 + 尽量让整张表留在同一页
    for i, row in enumerate(t.rows):
        trPr = row._tr.get_or_add_trPr()
        cantSplit = OxmlElement("w:cantSplit")
        trPr.append(cantSplit)
        if i == 0:
            tblHeader = OxmlElement("w:tblHeader")
            trPr.append(tblHeader)
        if i < len(t.rows) - 1:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True
    return t


def code_block(doc, code):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.right_indent = Cm(0.3)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.keep_together = True
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), LIGHT)
    pPr.append(shd)
    lines = code.strip("\n").split("\n")
    for i, line in enumerate(lines):
        r = p.add_run(line)
        set_run_font(r, "Consolas", 8.2, color=RGBColor(0x1A, 0x1A, 0x1A))
        if i < len(lines) - 1:
            r.add_break()


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    run._r.append(fld1)
    run._r.append(instr)
    run._r.append(fld2)
    set_run_font(run, "宋体", 9, color=GRAY)


def setup_document():
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.3)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)
    section.different_first_page_header_footer = True

    style = doc.styles["Normal"]
    style.font.name = "宋体"
    style.font.size = Pt(11)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = hp.add_run("课程设计报告｜基于 MobileNetV2 的番茄叶片病害识别")
    set_run_font(hr, "宋体", 8.5, color=GRAY)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = fp.add_run("第 ")
    set_run_font(r1, "宋体", 9, color=GRAY)
    add_page_number(fp)
    r2 = fp.add_run(" 页")
    set_run_font(r2, "宋体", 9, color=GRAY)

    doc.core_properties.title = "基于 MobileNetV2 的番茄叶片病害识别"
    doc.core_properties.author = "黄博阳"
    doc.core_properties.subject = "课程设计报告"
    return doc


def cover(doc):
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("课 程 设 计 报 告")
    set_run_font(r, "黑体", 18, bold=True, color=FOREST)
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run("COURSE DESIGN REPORT")
    set_run_font(r2, "Arial", 9, color=GRAY)

    # 装饰线
    line = doc.add_paragraph()
    line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pPr = line._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "12")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "C7953F")
    pBdr.append(bottom)
    pPr.append(pBdr)

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.35
    r = p.add_run("基于 MobileNetV2 的\n番茄叶片病害识别")
    set_run_font(r, "Microsoft YaHei", 26, bold=True, color=GREEN)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("—— 深度学习图像分类全流程实践")
    set_run_font(r, "宋体", 14, color=FOREST)

    for _ in range(4):
        doc.add_paragraph()

    info = [
        ("课程名称", "人工智能 / 深度学习课程设计"),
        ("专业班级", "人工智能专业"),
        ("团队成员", "黄博阳、成员B、成员C、成员D、成员E"),
        ("指导教师", "________________"),
        ("完成日期", "2026 年 11 月"),
    ]
    t = doc.add_table(rows=0, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in info:
        cells = t.add_row().cells
        cells[0].text = ""
        cells[1].text = ""
        p0 = cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r0 = p0.add_run(k + "：")
        set_run_font(r0, "宋体", 11, bold=True, color=GRAY)
        p1 = cells[1].paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r1 = p1.add_run(v)
        set_run_font(r1, "宋体", 11, color=RGBColor(0x1A, 0x1A, 0x1A))
    # 去掉表格边框
    tbl = t._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tblPr.append(borders)

    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("2026 年 11 月")
    set_run_font(r, "宋体", 11, color=GRAY)

    doc.add_page_break()


def abstract(doc):
    heading(doc, "摘  要", 1)
    body(doc,
         "番茄叶片病害种类多、症状相似，传统人工诊断依赖经验且存在滞后。本文以番茄叶片图像为对象，"
         "构建包含细菌性斑点病、早疫病、晚疫病、叶霉病、斑枯病和健康叶片 6 类、共 3000 张图像的数据集，"
         "采用 ImageNet 预训练的 MobileNetV2 作为骨干网络，通过冻结骨干、训练分类头，再解冻最后 20 层并以低学习率微调的"
         "两阶段迁移学习策略完成分类。训练中引入随机裁剪、翻转、亮度/对比度/饱和度扰动和 Dropout，并使用 Adam、"
         "早停与学习率衰减抑制过拟合。在 450 张测试图像上，模型准确率达到 89.11%，Top-3 准确率 99.33%，"
         "宏平均 F1 为 0.8912；健康叶片 F1 达到 0.9737，早疫病因与斑枯病症状相似，F1 相对较低（0.7947）。"
         "混淆矩阵和 Grad-CAM 结果表明，模型主要关注病斑与叶面纹理区域，但也会受到背景和叶片姿态影响。"
         "实验说明，轻量级迁移学习可在 CPU 环境下完成较好的番茄叶片病害分类，可作为智慧农业辅助诊断的原型。",
         indent=True)
    p = doc.add_paragraph()
    fmt_para(p, first_line=False, before=6)
    r = p.add_run("关键词：")
    set_run_font(r, "黑体", 11, bold=True, color=GREEN)
    r2 = p.add_run("番茄叶片病害；卷积神经网络；MobileNetV2；迁移学习；Grad-CAM")
    set_run_font(r2, "宋体", 11, color=RGBColor(0x1A, 0x1A, 0x1A))
    doc.add_page_break()


def section_1(doc):
    heading(doc, "1  应用背景与问题定义", 1)
    heading(doc, "1.1  研究背景", 2)
    body(doc,
         "番茄是我国设施农业和露地栽培中种植面积较大的蔬菜作物之一。番茄叶片病害具有种类多、早期症状不明显、"
         "不同病害之间视觉相似等特点，基层种植户往往依赖经验判断，容易出现漏判、误判和用药不及时的问题。"
         "随着智慧农业和精准植保的推进，利用手机或巡检设备拍摄叶片图像、由模型给出辅助诊断，成为降低识别门槛、"
         "提高植保效率的一种可行路径。")
    body(doc,
         "深度学习，尤其是卷积神经网络（CNN），能够从图像中自动学习纹理、颜色和形状特征，已在植物病害识别中得到广泛研究。"
         "但实际落地仍面临三个问题：一是田间图像背景复杂、光照变化大；二是高质量标注样本有限；三是边缘设备算力有限。"
         "因此，本文不追求在大规模数据集上刷新精度，而是验证一种轻量、可复现、适合课程设计条件的迁移学习方案。")

    heading(doc, "1.2  问题定义", 2)
    body(doc,
         "本文将任务定义为 6 类单标签图像分类：输入一张番茄叶片 RGB 图像，输出其所属类别及置信度。"
         "类别包括番茄细菌性斑点病、番茄早疫病、番茄晚疫病、番茄叶霉病、番茄斑枯病和番茄健康叶片。"
         "评价以测试集准确率、宏平均精确率/召回率/F1、混淆矩阵和 Top-3 准确率为主，并辅以 Grad-CAM 观察模型关注区域。")

    heading(doc, "1.3  研究目标与主要工作", 2)
    body(doc, "本文的主要工作包括：")
    for text in [
        "（1）从 PlantVillage 中筛选 6 类番茄叶片，构建类别均衡的 3000 张图像数据集，并完成分层划分；",
        "（2）以 MobileNetV2 为骨干，设计“冻结—微调”的两阶段迁移学习流程；",
        "（3）引入数据增强、Dropout、早停和学习率衰减，分析训练过程中的过拟合现象；",
        "（4）完成测试集评估、混淆矩阵、预测样例和 Grad-CAM 可视化，分析典型错因；",
        "（5）给出可运行的训练、预测与解释代码，并明确 5 人团队分工。",
    ]:
        body(doc, text, indent=True)

    doc.add_page_break()
    heading(doc, "1.4  任务要求与报告对应关系", 2)
    body(doc, "为方便对照课程设计任务书，表 1 给出了任务要求与本报告章节的对应关系。")
    table_caption(doc, "表 1  课程设计任务要求与报告对应关系")
    table(doc,
          ["任务要求", "本报告对应内容"],
          [
              ["应用背景", "第 1 章：番茄病害识别背景、问题定义与研究目标"],
              ["数据来源", "2.1 节：PlantVillage 数据集及 6 类子集构建"],
              ["算法模型", "第 3 章：CNN 基础、MobileNetV2 与迁移学习"],
              ["学习准则", "4.1 节：稀疏分类交叉熵损失"],
              ["优化算法", "4.2 节：Adam、学习率与早停策略"],
              ["核心代码展示", "第 7 章：数据管道、模型、训练与评估代码及注释"],
              ["结果与分析", "第 6 章：训练曲线、总体指标、混淆矩阵、Grad-CAM"],
              ["团队作战", "第 8 章：5 人分工表与协作机制"],
          ],
          widths=[4.0, 11.8])


def section_2(doc):
    heading(doc, "2  数据来源与预处理", 1)
    heading(doc, "2.1  数据来源", 2)
    body(doc,
         "数据来自公开的 PlantVillage 植物叶片病害数据集。该数据集包含多种作物和病害类别，图像以单叶、"
         "较为干净的背景为主，适合作为课程设计中的方法验证数据。本文从 color 子集中选取番茄的 6 个类别，"
         "每类随机抽取 500 张，共 3000 张，保证类别均衡，避免模型因类别不平衡而偏向多数类。")
    body(doc,
         "需要说明的是，PlantVillage 的图像多为实验室或受控环境拍摄，背景单一、叶片居中，与真实田间的复杂背景、"
         "遮挡和光照变化仍有差距。因此，本文的结果更适合说明方法流程的可行性，而不能直接等同于田间部署性能。")

    heading(doc, "2.2  类别与数据划分", 2)
    body(doc,
         "采用分层抽样按 70% / 15% / 15% 划分训练集、验证集和测试集，得到训练集 2100 张、验证集 450 张、"
         "测试集 450 张，每类在三个子集中的数量分别为 350 / 75 / 75。划分时固定随机种子 42，保证结果可复现。")
    table_caption(doc, "表 2  六类番茄叶片数据及划分")
    rows = []
    for name in CLASS_NAMES_EN:
        rows.append([CLASS_NAMES_ZH[name], 350, 75, 75, 500])
    rows.append(["合计", 2100, 450, 450, 3000])
    table(doc, ["类别", "训练集", "验证集", "测试集", "合计"], rows, widths=[4.6, 2.6, 2.6, 2.6, 2.6])

    heading(doc, "2.3  预处理与数据增强", 2)
    body(doc,
         "所有图像统一解码为 RGB，缩放到 160×160。训练阶段先缩放到 180×180，再随机裁剪到 160×160，"
         "并施加水平翻转、亮度扰动（±0.12）、对比度扰动（0.90—1.10）和饱和度扰动（0.90—1.10）。"
         "验证和测试阶段只做 160×160 缩放，不做随机增强。最后使用 MobileNetV2 的 preprocess_input 将像素值映射到 [-1, 1]。")
    body(doc,
         "这样做的目的有两个：一是通过随机裁剪和颜色扰动模拟拍摄角度、光照和曝光的变化；二是避免增强过强导致病斑形态被破坏。"
         "从训练结果看，增强有效缓解了训练集与验证集之间的过拟合，但仍未完全消除。")

    heading(doc, "2.4  数据样例与分布", 2)
    body(doc, "图 1 展示了 6 类番茄叶片的训练样本。可以看出，不同病害在颜色、斑点形状和叶面纹理上存在差异，"
              "但早疫病与斑枯病、细菌性斑点病与斑枯病之间存在明显的视觉相似性，这也是后续错分的主要来源。")
    picture(doc, FIG_DIR / "dataset_samples.png", 15.2)
    caption(doc, "图 1  六类番茄叶片样例（每类 1 张训练图）")


def section_3(doc):
    heading(doc, "3  算法模型与迁移学习", 1)
    heading(doc, "3.1  卷积神经网络基础", 2)
    body(doc,
         "卷积神经网络通过卷积核在图像上滑动提取局部特征，再通过池化或步长卷积降低空间分辨率，"
         "逐层形成从边缘、纹理到语义部件的层次化表示。一个典型的分类网络包括卷积层、归一化层、激活函数、"
         "池化层和全连接层，最后通过 Softmax 将 logits 转换为类别概率。")
    body(doc,
         "与手工设计特征相比，CNN 的优势在于特征学习与分类器可以联合优化。但 CNN 通常需要较多标注数据；"
         "在样本有限时，迁移学习是一种更现实的选择。")

    heading(doc, "3.2  MobileNetV2 结构", 2)
    body(doc,
         "MobileNetV2 是面向移动端和边缘设备的轻量级 CNN。其核心是深度可分离卷积（depthwise separable convolution）"
         "和倒残差结构（inverted residual）：先通过 1×1 卷积升维，再进行 3×3 深度卷积，最后用 1×1 卷积降维，"
         "并在低维空间使用线性瓶颈，以减少参数量和计算量。相比标准卷积，它在保持较好特征表达能力的同时显著降低了计算成本。")
    body(doc,
         "本文使用在 ImageNet 上预训练的 MobileNetV2（width multiplier 1.0，输入 160×160）作为骨干。"
         "该骨干输出 5×5×1280 的特征图，经过全局平均池化得到 1280 维向量，再接入 Dropout 和 6 类全连接层。"
         "整个模型参数量约 2.27 M，适合 CPU 训练与后续的边缘部署尝试。")

    heading(doc, "3.3  两阶段迁移学习策略", 2)
    body(doc,
         "第一阶段冻结 MobileNetV2 全部卷积层，只训练新增的分类头。这样可以在不破坏预训练特征的前提下，"
         "让分类头快速适应番茄叶片任务。第二阶段解冻骨干的最后 20 层，以 1e-5 的小学习率微调，"
         "同时冻结所有 BatchNormalization 层，避免小批量数据导致统计量漂移。")
    body(doc,
         "这种“先冻结、后微调”的策略比从头训练更稳定：预训练特征提供了良好的初始表示，"
         "而小学习率微调让高层特征逐步贴合病斑纹理，降低了过拟合风险。")

    doc.add_page_break()
    heading(doc, "3.4  模型结构", 2)
    body(doc, "模型整体结构如表 3 所示。")
    table_caption(doc, "表 3  模型主要层与参数量")
    table(doc,
          ["层", "输出尺寸", "参数量"],
          [
              ["输入图像", "160 × 160 × 3", "0"],
              ["MobileNetV2 骨干", "5 × 5 × 1280", "2,257,984"],
              ["全局平均池化", "1280", "0"],
              ["Dropout（0.25）", "1280", "0"],
              ["全连接 + Softmax", "6", "7,686"],
              ["合计", "—", "2,265,670"],
          ],
          widths=[5.2, 5.2, 4.8])


def section_4(doc):
    heading(doc, "4  学习准则与优化算法", 1)
    heading(doc, "4.1  损失函数", 2)
    body(doc,
         "采用稀疏分类交叉熵（Sparse Categorical Cross-Entropy）作为损失函数。对于第 i 个样本，"
         "若真实类别为 y_i，模型输出的第 y_i 类概率为 p_i，则损失为 L_i = -log(p_i)。"
         "该损失函数与 Softmax 配合，能够将模型输出解释为类别概率，并对错误高置信预测施加较大惩罚。")

    heading(doc, "4.2  优化算法", 2)
    body(doc,
         "优化器采用 Adam。Adam 同时维护一阶矩和二阶矩估计，并对学习率进行自适应缩放，"
         "在稀疏梯度和非平稳目标上通常比朴素 SGD 更稳定。第一阶段学习率设为 1e-3，"
         "第二阶段微调设为 1e-5；当验证损失连续 2 个 epoch 不下降时，学习率乘以 0.3。")
    body(doc,
         "此外使用早停：第一阶段最多 12 个 epoch，验证准确率连续 4 个 epoch 不提升则停止；"
         "第二阶段最多 6 个 epoch，耐心值为 3。最终保留验证集表现最好的权重，而不是最后一个 epoch 的权重。")

    heading(doc, "4.3  正则化与训练策略", 2)
    body(doc, "为抑制过拟合，本文使用了以下策略：")
    for text in [
        "（1）数据增强：随机裁剪、水平翻转、亮度/对比度/饱和度扰动；",
        "（2）Dropout：在全连接层前设置 0.25 的丢弃率；",
        "（3）迁移学习与分层学习率：冻结骨干、低学习率微调；",
        "（4）BatchNormalization 冻结：微调阶段不更新 BN 统计量；",
        "（5）早停与学习率衰减：根据验证集表现动态停止或降学习率。",
    ]:
        body(doc, text, indent=True)

    heading(doc, "4.4  评价指标", 2)
    body(doc,
         "采用准确率（Accuracy）、精确率（Precision）、召回率（Recall）、F1 值和 Top-3 准确率。"
         "由于 6 类样本均衡，宏平均与加权平均数值接近；本文同时报告宏平均 F1，以衡量各类别的整体表现。"
         "混淆矩阵用于观察具体错分方向，Grad-CAM 用于定性分析模型关注区域。")

    heading(doc, "4.5  超参数设置", 2)
    table_caption(doc, "表 4  训练超参数")
    table(doc,
          ["项目", "第一阶段（冻结）", "第二阶段（微调）"],
          [
              ["输入尺寸", "160 × 160", "160 × 160"],
              ["Batch size", "32", "32"],
              ["最大 epoch", "12", "6"],
              ["实际 epoch", "9（早停）", "6（早停）"],
              ["优化器", "Adam", "Adam"],
              ["学习率", "1e-3", "1e-5"],
              ["损失函数", "稀疏分类交叉熵", "稀疏分类交叉熵"],
              ["Dropout", "0.25", "0.25"],
              ["可训练范围", "仅分类头", "最后 20 层 + 分类头"],
          ],
          widths=[4.2, 5.6, 5.6])


def section_5(doc):
    heading(doc, "5  实验设置与训练过程", 1)
    heading(doc, "5.1  实验环境", 2)
    body(doc,
         "实验在 Windows 环境下完成，使用 Python 3.13、TensorFlow 2.21.0、Keras 3.14.1，"
         "仅使用 CPU 训练，未使用 GPU。训练数据 2100 张、验证 450 张、测试 450 张，输入分辨率 160×160，"
         "批大小 32。整个训练过程约十余分钟，说明该方案在普通笔记本上具有可复现性。")

    heading(doc, "5.2  训练过程", 2)
    body(doc,
         "第一阶段训练 9 个 epoch 后触发早停，验证准确率最高达到 87.78%；第二阶段微调 6 个 epoch，"
         "验证准确率没有明显提升，最终恢复验证集最佳权重。最终模型在测试集上的准确率为 89.11%，"
         "说明验证集与测试集分布基本一致，模型没有出现明显的测试集偏移。")
    body(doc,
         "从训练曲线看，第一阶段前 3 个 epoch 准确率快速上升，随后进入平台期；训练准确率继续上升至 93% 左右，"
         "而验证准确率在 85%—88% 之间波动，存在约 5—8 个百分点的差距。这说明模型仍有一定过拟合，"
         "但在数据增强、Dropout 和早停的共同作用下，测试集表现仍然稳定。")

    heading(doc, "5.3  复现方式", 2)
    body(doc,
         "项目按“数据准备—训练—预测—解释”拆分为四个脚本，所有脚本位于 src/ 目录，"
         "关键参数可通过 argparse 调整。数据划分文件保存在 data/splits.csv，"
         "模型保存在 outputs/models/tomato_mobilenetv2.h5，训练曲线、混淆矩阵、预测样例和 Grad-CAM 图"
         "保存在 outputs/figures/。具体运行命令见附录 A。")


def section_6(doc):
    heading(doc, "6  结果与分析", 1)
    heading(doc, "6.1  训练曲线", 2)
    body(doc,
         "图 2 给出了训练与验证的准确率、损失曲线，虚线右侧为微调阶段。第一阶段损失快速下降，"
         "验证损失在第 3—5 个 epoch 后趋于平缓；微调阶段训练损失继续下降，但验证损失没有同步改善，"
         "说明解冻过多层或继续训练可能带来过拟合，早停是必要的。")
    picture(doc, FIG_DIR / "training_curves.png", 15.8)
    caption(doc, "图 2  训练与验证的准确率、损失曲线")

    heading(doc, "6.2  总体结果", 2)
    body(doc,
         "表 5 给出了测试集总体指标。模型在 450 张测试图像上取得 89.11% 的准确率，"
         "Top-3 准确率达到 99.33%，说明即使 Top-1 判断错误，正确类别也几乎总在前 3 个候选之中。"
         "宏平均精确率、召回率和 F1 分别为 89.22%、89.11% 和 89.12%，各类别整体较为均衡。")
    table_caption(doc, "表 5  测试集总体指标")
    table(doc,
          ["指标", "数值"],
          [
              ["测试样本数", "450"],
              ["Top-1 准确率", "89.11%"],
              ["Top-3 准确率", "99.33%"],
              ["宏平均精确率", "89.22%"],
              ["宏平均召回率", "89.11%"],
              ["宏平均 F1", "89.12%"],
          ],
          widths=[6.0, 6.0])

    heading(doc, "6.3  分类别结果", 2)
    body(doc,
         "表 6 给出了分类别指标。健康叶片的 F1 最高（0.9737），说明模型对“健康/病害”的边界掌握较好；"
         "叶霉病（0.9324）、晚疫病（0.8980）、细菌性斑点病（0.8767）和斑枯病（0.8718）次之；"
         "早疫病的 F1 最低（0.7947），召回率 0.8000，是后续重点改进的类别。")
    table_caption(doc, "表 6  分类别测试指标")
    rows = [
        ["番茄细菌性斑点病", "0.9014", "0.8533", "0.8767", "75"],
        ["番茄早疫病", "0.7895", "0.8000", "0.7947", "75"],
        ["番茄晚疫病", "0.9167", "0.8800", "0.8980", "75"],
        ["番茄叶霉病", "0.9452", "0.9200", "0.9324", "75"],
        ["番茄斑枯病", "0.8395", "0.9067", "0.8718", "75"],
        ["番茄健康叶片", "0.9610", "0.9867", "0.9737", "75"],
    ]
    table(doc, ["类别", "精确率", "召回率", "F1", "样本数"], rows, widths=[5.4, 3.0, 3.0, 3.0, 2.4])

    heading(doc, "6.4  混淆矩阵与错因分析", 2)
    body(doc,
         "图 3 为测试集混淆矩阵。健康叶片 75 张中正确识别 74 张，仅有 1 张误判为早疫病；"
         "叶霉病正确 69 张，晚疫病 66 张，细菌性斑点病 64 张，斑枯病 68 张，早疫病 60 张。"
         "早疫病的主要错分方向是斑枯病（7 张）、细菌性斑点病（4 张）和晚疫病（2 张）；"
         "细菌性斑点病有 5 张误判为斑枯病。")
    picture(doc, FIG_DIR / "confusion_matrix.png", 13.2)
    caption(doc, "图 3  测试集混淆矩阵")
    body(doc,
         "这些错分并非随机：早疫病与斑枯病在早期都表现为褐色小斑点，斑点边缘和叶面黄化程度相似；"
         "细菌性斑点病与斑枯病在低分辨率下也容易出现纹理混淆。此外，PlantVillage 图像背景单一，"
         "模型可能利用了背景颜色、叶片摆放位置等非病斑线索，这会削弱其田间泛化能力。"
         "从 Grad-CAM 结果看，部分热力图落在叶缘和背景上，也印证了这一点。")

    heading(doc, "6.5  预测样例", 2)
    body(doc,
         "图 4 展示了 12 张测试图像的预测结果。多数样本的置信度较高，正确分类的样例通常伴随 95% 以上的置信度；"
         "错误样例的置信度相对较低（如 72.6%、74.3%），说明模型对不确定样本并非完全“自信”。"
         "这为后续引入置信度阈值、人工复核或拒识机制提供了依据。")
    picture(doc, FIG_DIR / "sample_predictions.png", 14.0)
    caption(doc, "图 4  测试集预测样例（绿色为正确，红色为错误）")

    doc.add_page_break()
    heading(doc, "6.6  Grad-CAM 可解释性分析", 2)
    body(doc,
         "为了观察模型是否关注病斑区域，使用 Grad-CAM 对每类一张正确分类的测试图生成热力图。"
         "图 5 中红色区域表示对当前类别贡献较大的位置。可以看到，模型在多数样本上能聚焦于病斑、叶尖枯斑或叶面纹理，"
         "但也有一部分热量分布在叶片边缘和背景上，说明模型尚未完全学会“只看病斑”。")
    picture(doc, FIG_DIR / "gradcam_grid.png", 15.0)
    caption(doc, "图 5  Grad-CAM：模型关注区域（每类 1 张正确分类样本）")
    body(doc,
         "这一现象有两方面原因：一是数据集中叶片通常居中、背景单一，模型容易把背景当作捷径特征；"
         "二是 160×160 的分辨率会丢失部分细小病斑纹理。后续可以通过叶片分割/裁剪、背景替换、"
         "更高分辨率输入和更强的位置扰动来缓解。")

    doc.add_page_break()
    heading(doc, "6.7  工程迭代对比", 2)
    body(doc,
         "在正式训练前，曾使用每类 300 张、共 1800 张的较小数据集和“解冻最后 30 层”的微调策略，"
         "测试准确率为 84.81%，宏平均 F1 为 0.8438。扩充到每类 500 张、共 3000 张，并把微调范围缩小到"
         "最后 20 层、冻结 BN 后，测试准确率提升到 89.11%，宏平均 F1 提升到 0.8912。"
         "需要说明的是，这一对比同时改变了数据规模和微调策略，属于工程迭代对比，而非严格的单变量消融实验。")
    table_caption(doc, "表 7  工程迭代对比（非严格消融）")
    table(doc,
          ["版本", "数据规模", "微调策略", "测试准确率", "宏平均 F1"],
          [
              ["基线", "300 张/类，共 1800", "解冻最后 30 层", "84.81%", "0.8438"],
              ["最终", "500 张/类，共 3000", "解冻最后 20 层，冻结 BN", "89.11%", "0.8912"],
          ],
          widths=[2.4, 4.6, 4.8, 3.0, 2.8])

    heading(doc, "6.8  改进方向", 2)
    body(doc,
         "结合错因与可视化结果，后续可以从四个方向改进："
         "（1）数据侧：补充田间复杂背景图像，对早疫病/斑枯病困难样本进行针对性采集；"
         "（2）模型侧：尝试 224×224 输入、EfficientNet-B0 或 ConvNeXt-Tiny，并与 MobileNetV2 做对比；"
         "（3）训练侧：引入类别加权、Focal Loss、Cosine Decay、Test-Time Augmentation 和模型集成；"
         "（4）部署侧：模型量化、ONNX 导出、手机端推理，并结合叶片检测/分割先定位病斑。",
         indent=True)


def section_7(doc):
    heading(doc, "7  核心代码展示与说明", 1)
    body(doc,
         "本节只展示关键逻辑，完整代码见 src/ 目录。代码均添加了中文注释，便于复现和答辩讲解。")

    heading(doc, "7.1  数据管道", 2)
    body(doc, "数据管道负责读取图像、缩放、训练增强和 MobileNetV2 预处理。验证/测试阶段不做随机增强，保证评估稳定。")
    code_block(doc, """def decode_image(path, label, training):
    img = tf.io.read_file(path)
    img = tf.image.decode_jpeg(img, channels=3)
    if training:
        img = tf.image.resize(img, [IMG_SIZE + 20, IMG_SIZE + 20])
        img = tf.image.random_crop(img, [IMG_SIZE, IMG_SIZE, 3])
        img = tf.image.random_flip_left_right(img)
        img = tf.image.random_brightness(img, 0.12)
        img = tf.image.random_contrast(img, 0.90, 1.10)
        img = tf.image.random_saturation(img, 0.90, 1.10)
    else:
        img = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
    img = tf.cast(img, tf.float32)
    img = keras.applications.mobilenet_v2.preprocess_input(img)
    return img, label""")

    heading(doc, "7.2  模型构建", 2)
    body(doc, "骨干使用 ImageNet 预训练权重，先冻结全部卷积层；分类头由全局平均池化、Dropout 和 6 类全连接层组成。")
    code_block(doc, """base = keras.applications.MobileNetV2(
    input_shape=(IMG_SIZE, IMG_SIZE, 3),
    include_top=False,
    weights="imagenet",
)
base.trainable = False
inputs = keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3), name="leaf_image")
x = base(inputs, training=False)
x = layers.GlobalAveragePooling2D(name="gap")(x)
x = layers.Dropout(0.25, name="dropout")(x)
outputs = layers.Dense(NUM_CLASSES, activation="softmax", name="predictions")(x)
model = keras.Model(inputs, outputs, name="tomato_mobilenetv2")""")

    heading(doc, "7.3  两阶段训练与微调", 2)
    body(doc, "第一阶段只训练分类头；第二阶段解冻最后 20 层，冻结 BN，并以 1e-5 学习率微调。")
    code_block(doc, """# 第一阶段：冻结骨干
model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=1e-3),
    loss=keras.losses.SparseCategoricalCrossentropy(),
    metrics=["accuracy"],
)
model.fit(train_ds, validation_data=val_ds, epochs=12, callbacks=callbacks1)

# 第二阶段：解冻最后 20 层，冻结 BN
base.trainable = True
for layer in base.layers[:-20]:
    layer.trainable = False
for layer in base.layers:
    if isinstance(layer, layers.BatchNormalization):
        layer.trainable = False
model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=1e-5),
    loss=keras.losses.SparseCategoricalCrossentropy(),
    metrics=["accuracy"],
)
model.fit(train_ds, validation_data=val_ds, epochs=6, callbacks=callbacks2)""")

    doc.add_page_break()
    heading(doc, "7.4  评估与混淆矩阵", 2)
    body(doc, "在测试集上一次性取预测概率，计算准确率、宏平均 F1、Top-3 准确率和混淆矩阵，避免逐张预测带来的顺序错位。")
    code_block(doc, """test_ds = make_dataset(test_df, training=False, shuffle=False)
probs = model.predict(test_ds, verbose=0)
y_pred = probs.argmax(axis=1)
y_true = test_df["label_idx"].values

acc = accuracy_score(y_true, y_pred)
macro_f1 = precision_recall_fscore_support(
    y_true, y_pred, average="macro", zero_division=0
)[2]
cm = confusion_matrix(y_true, y_pred)
sns.heatmap(cm, annot=True, fmt="d", cmap="Greens",
            xticklabels=ZH_NAMES, yticklabels=ZH_NAMES)""")

    heading(doc, "7.5  代码结构", 2)
    body(doc, "项目结构如下：")
    code_block(doc, """src/
  config.py          路径、类别、超参数
  prepare_data.py    扫描数据并做分层切分
  eda.py             类别分布与样例图
  train.py           训练、微调、评估、绘图
  predict.py         单张图片预测
  gradcam.py         Grad-CAM 可视化
  make_diagram.py    模型结构图
data/
  plantvillage_subset/   6 类图片
  splits.csv             训练/验证/测试划分
outputs/
  models/                模型权重
  figures/               图表
  metrics/               指标与报告""")


def section_8(doc):
    heading(doc, "8  团队分工与协作", 1)
    body(doc,
         "本项目由 5 人共同完成，按“数据—模型—训练—评估—交付”拆分任务，每人都参与代码与文档，"
         "并通过交叉复核保证结果可复现。具体分工如表 8 所示。")
    table_caption(doc, "表 8  5 人团队分工")
    table(doc,
          ["成员", "角色", "具体负责内容", "占比"],
          [
              ["黄博阳", "组长 / 数据与训练", "数据筛选与清洗、分层划分、训练主脚本、整体进度协调", "20%"],
              ["成员B", "模型设计", "MobileNetV2 结构、迁移学习策略、模型参数量与结构图", "20%"],
              ["成员C", "训练与调参", "数据增强、学习率与早停、两阶段训练、工程迭代对比", "20%"],
              ["成员D", "评估与可视化", "指标计算、混淆矩阵、预测样例、Grad-CAM、错因分析", "20%"],
              ["成员E", "工程与交付", "推理脚本、代码注释、报告排版、答辩 PPT 与演示", "20%"],
          ],
          widths=[2.4, 4.2, 8.4, 1.8], font_size=8.6)
    body(doc, "注：成员B—E 请替换为实际姓名；如实际分工不同，可按上表结构调整。", indent=False, size=9)
    body(doc,
         "协作机制方面，团队每周进行一次例会，明确本周可交付物；代码统一放在项目目录中，按模块提交；"
         "训练日志、指标 JSON 和图表统一归档到 outputs/，避免“只在某个人电脑上能跑”；"
         "报告与 PPT 由成员E 统稿，其他成员交叉检查数据、指标和结论，确保三者一致。",
         indent=True)


def section_9(doc):
    heading(doc, "9  总结与展望", 1)
    heading(doc, "9.1  工作总结", 2)
    body(doc,
         "本文围绕番茄叶片病害识别，完成了从数据构建、模型设计、训练调参到评估解释的全流程。"
         "在 6 类、3000 张图像上，MobileNetV2 迁移学习取得 89.11% 的测试准确率和 99.33% 的 Top-3 准确率，"
         "宏平均 F1 为 0.8912；模型参数量约 2.27 M，可在 CPU 环境下完成训练与推理。"
         "实验表明，冻结—微调的两阶段策略、适度的数据增强和早停，是小样本条件下较为稳健的组合。")
    body(doc,
         "同时，混淆矩阵和 Grad-CAM 也暴露了模型的不足：早疫病与斑枯病容易混淆，部分注意力落在背景上，"
         "说明数据分布和输入分辨率仍是限制因素。这些问题为后续改进提供了明确方向。")

    heading(doc, "9.2  不足与展望", 2)
    body(doc,
         "本文的不足主要包括：数据以受控环境图像为主，田间泛化能力尚未验证；只做了 6 类分类，"
         "未覆盖更多病害和早期症状；未进行模型量化与端侧部署；未与 ResNet、EfficientNet 等模型做系统对比。"
         "后续计划补充田间数据，尝试目标检测/分割先定位病斑，结合 224×224 输入和模型集成提升困难类别，"
         "并探索 ONNX/手机端部署，使系统更接近真实应用。")

    heading(doc, "参考文献", 1)
    refs = [
        "[1] Hughes D P, Salathé M. An open access repository of images on plant health to enable the development of mobile disease diagnostics[J]. arXiv:1511.08060, 2015.",
        "[2] Sandler M, Howard A, Zhu M, et al. MobileNetV2: Inverted Residuals and Linear Bottlenecks[C]//CVPR, 2018: 4510-4520.",
        "[3] LeCun Y, Bengio Y, Hinton G. Deep learning[J]. Nature, 2015, 521(7553): 436-444.",
        "[4] Selvaraju R R, Cogswell M, Das A, et al. Grad-CAM: Visual Explanations from Deep Networks via Gradient-based Localization[C]//ICCV, 2017: 618-626.",
        "[5] 邱锡鹏. 神经网络与深度学习[M]. 北京: 机械工业出版社, 2020.",
        "[6] TensorFlow/Keras 官方文档. https://www.tensorflow.org/ / https://keras.io/.",
    ]
    for ref in refs:
        p = doc.add_paragraph()
        fmt_para(p, first_line=False, line=1.35, after=3)
        r = p.add_run(ref)
        set_run_font(r, "宋体", 9.5, color=RGBColor(0x1A, 0x1A, 0x1A))


def appendix(doc):
    heading(doc, "附录 A  项目结构与运行说明", 1)
    body(doc, "完整项目位于当前工作目录，核心文件如下：")
    code_block(doc, """report/                  课程设计报告 DOCX/PDF
outputs/models/           tomato_mobilenetv2.h5
outputs/figures/          training_curves.png / confusion_matrix.png
                          sample_predictions.png / gradcam_grid.png
outputs/metrics/          metrics.json / classification_report.txt
src/                      训练、预测、评估、可视化脚本""")
    body(doc, "运行环境：Python 3.13、TensorFlow 2.21.0、Keras 3.14.1；仅 CPU 即可运行。")
    body(doc, "推荐运行顺序：先执行 prepare_data.py 生成 splits.csv，再执行 train.py；预测和 Grad-CAM 依赖训练好的模型。")
    code_block(doc, """python src/prepare_data.py
python src/train.py --stage1-epochs 12 --stage2-epochs 6
python src/predict.py <图片路径>
python src/gradcam.py --grid""")
    body(doc, "如果更换数据集，只需保持“每个类别一个文件夹”的结构，并同步修改 src/config.py 中的类别映射即可。")


def main():
    metrics = json.loads((METRIC_DIR / "metrics.json").read_text(encoding="utf-8"))
    doc = setup_document()
    cover(doc)
    abstract(doc)
    section_1(doc)
    section_2(doc)
    section_3(doc)
    section_4(doc)
    section_5(doc)
    section_6(doc)
    section_7(doc)
    section_8(doc)
    section_9(doc)
    appendix(doc)

    out = REPORT_DIR / "基于MobileNetV2的番茄叶片病害识别-课程设计报告.docx"
    doc.save(out)
    print(f"saved: {out}")
    print(f"test_accuracy={metrics['test_accuracy']:.4f}")


if __name__ == "__main__":
    main()
