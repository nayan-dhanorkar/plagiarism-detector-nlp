# src/report_generator.py
"""
Generates a professional PDF plagiarism report using ReportLab Platypus.

Report structure:
  Page 1 — Cover: title, overall score, timestamp
  Page 2 — Per-source breakdown table + bar chart
  Page 3+ — Sentence-level detail table
"""

import os
from datetime import datetime

from reportlab.lib             import colors
from reportlab.lib.pagesizes   import A4
from reportlab.lib.styles      import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units       import cm
from reportlab.platypus        import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, PageBreak, HRFlowable,
)
from reportlab.graphics.shapes    import Drawing
from reportlab.graphics.charts.barcharts import HorizontalBarChart


# ─────────────────────────────────────────────────────────── #
#  CONFIG
# ─────────────────────────────────────────────────────────── #

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

LABEL_COLORS = {
    "Copied"      : colors.HexColor("#E53E3E"),
    "Paraphrased" : colors.HexColor("#D69E2E"),
    "Original"    : colors.HexColor("#38A169"),
}

BRAND_BLUE  = colors.HexColor("#2B6CB0")
BRAND_DARK  = colors.HexColor("#1A202C")
LIGHT_GREY  = colors.HexColor("#F7FAFC")
MID_GREY    = colors.HexColor("#E2E8F0")


# ─────────────────────────────────────────────────────────── #
#  STYLES
# ─────────────────────────────────────────────────────────── #

def _build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"],
            fontSize=26, textColor=BRAND_DARK, spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle", parent=base["Normal"],
            fontSize=12, textColor=colors.HexColor("#718096"), spaceAfter=4,
        ),
        "heading": ParagraphStyle(
            "SectionHeading", parent=base["Heading2"],
            fontSize=13, textColor=BRAND_BLUE, spaceBefore=14, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontSize=9, leading=13,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["Normal"], fontSize=8, leading=11,
            textColor=colors.HexColor("#4A5568"),
        ),
        "cell": ParagraphStyle(
            "CellText", parent=base["Normal"], fontSize=8,
            leading=11, wordWrap="CJK",
        ),
        "cell_center": ParagraphStyle(
            "CellCenter", parent=base["Normal"], fontSize=8,
            leading=11, alignment=1,
        ),
    }


# ─────────────────────────────────────────────────────────── #
#  COVER PAGE
# ─────────────────────────────────────────────────────────── #

def _cover_page(story, summary, styles):
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("Plagiarism Detection Report", styles["title"]))
    story.append(HRFlowable(width="100%", thickness=2,
                             color=BRAND_BLUE, spaceAfter=10))

    generated_at = datetime.now().strftime("%d %B %Y, %H:%M")
    story.append(Paragraph(f"Generated: {generated_at}", styles["subtitle"]))
    story.append(Spacer(1, 1.5 * cm))

    pct   = summary.get("plagiarism_percent", 0)
    color = (colors.HexColor("#E53E3E") if pct >= 40
             else colors.HexColor("#D69E2E") if pct >= 20
             else colors.HexColor("#38A169"))

    score_data = [[Paragraph(
        f'<font size="36"><b>{pct}%</b></font><br/>'
        f'<font size="11" color="#718096">Overall Plagiarism</font>',
        ParagraphStyle("Score", alignment=1, leading=44),
    )]]
    score_table = Table(score_data, colWidths=[8 * cm], rowHeights=[5 * cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("TEXTCOLOR",  (0, 0), (-1, -1), colors.white),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 1 * cm))

    total     = summary.get("total_sentences", 0)
    plagiarised = summary.get("plagiarized_sentences", 0)
    original  = total - plagiarised

    stats_data = [
        ["Total Chunks",  str(total)],
        ["Plagiarised",   str(plagiarised)],
        ["Original",      str(original)],
    ]
    stats_table = Table(stats_data, colWidths=[5 * cm, 3 * cm])
    stats_table.setStyle(TableStyle([
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",   (0, 0), (0, -1), colors.HexColor("#718096")),
        ("TEXTCOLOR",   (1, 0), (1, -1), BRAND_DARK),
        ("FONTNAME",    (1, 0), (1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(stats_table)
    story.append(PageBreak())


# ─────────────────────────────────────────────────────────── #
#  SOURCE BREAKDOWN PAGE
# ─────────────────────────────────────────────────────────── #

def _source_breakdown(story, summary, styles):
    source_breakdown = summary.get("source_breakdown", {})

    story.append(Paragraph("Per-Source Similarity Breakdown", styles["heading"]))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=MID_GREY, spaceAfter=8))

    if not source_breakdown:
        story.append(Paragraph("No plagiarism detected from any source.", styles["body"]))
        story.append(Spacer(1, 0.5 * cm))
        return

    # ── Summary table ─────────────────────────────────────── #
    header = [
        Paragraph("<b>Source File</b>",    styles["cell"]),
        Paragraph("<b>Similarity %</b>",   styles["cell"]),
        Paragraph("<b>Risk Level</b>",     styles["cell"]),
    ]
    rows = [header]

    sorted_sources = sorted(source_breakdown.items(), key=lambda x: x[1], reverse=True)

    for src, pct in sorted_sources:
        risk = "HIGH" if pct >= 40 else "MEDIUM" if pct >= 20 else "LOW"
        risk_color = (colors.HexColor("#E53E3E") if risk == "HIGH"
                      else colors.HexColor("#D69E2E") if risk == "MEDIUM"
                      else colors.HexColor("#38A169"))
        rows.append([
            Paragraph(src,       styles["cell"]),
            Paragraph(f"{pct}%", styles["cell"]),
            Paragraph(
                f'<font color="{risk_color.hexval()}"><b>{risk}</b></font>',
                styles["cell_center"],
            ),
        ])

    tbl = Table(rows, colWidths=[10 * cm, 3.5 * cm, 3.5 * cm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  BRAND_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ("GRID",          (0, 0), (-1, -1), 0.5, MID_GREY),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("ALIGN",         (1, 0), (2, -1),  "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.8 * cm))

    # ── Horizontal bar chart ──────────────────────────────── #
    if len(sorted_sources) > 0:
        story.append(Paragraph("Visual Breakdown", styles["heading"]))

        chart_height = max(3 * cm, len(sorted_sources) * 1.2 * cm)
        drawing      = Drawing(16 * cm, chart_height + 1.5 * cm)

        bc = HorizontalBarChart()
        bc.x      = 4 * cm
        bc.y      = 0.5 * cm
        bc.height = chart_height
        bc.width  = 11 * cm

        pct_values = [pct for _, pct in sorted_sources]
        bc.data    = [pct_values]

        bc.valueAxis.valueMin  = 0
        bc.valueAxis.valueMax  = max(100, max(pct_values) + 10)
        bc.valueAxis.valueStep = 20

        bc.categoryAxis.categoryNames = [src for src, _ in sorted_sources]
        bc.categoryAxis.labels.fontSize = 8
        bc.bars[0].fillColor = BRAND_BLUE

        drawing.add(bc)
        story.append(drawing)

    story.append(Spacer(1, 0.5 * cm))


# ─────────────────────────────────────────────────────────── #
#  DETAIL TABLE
# ─────────────────────────────────────────────────────────── #

def _detail_table(story, results, styles):
    story.append(PageBreak())
    story.append(Paragraph("Sentence-Level Analysis", styles["heading"]))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=MID_GREY, spaceAfter=8))

    if not results:
        story.append(Paragraph("No results to display.", styles["body"]))
        return

    header = [
        Paragraph("<b>#</b>",                   styles["cell"]),
        Paragraph("<b>Student Chunk</b>",        styles["cell"]),
        Paragraph("<b>Best Match (Source)</b>",  styles["cell"]),
        Paragraph("<b>Source File</b>",          styles["cell"]),
        Paragraph("<b>Score</b>",                styles["cell"]),
        Paragraph("<b>Label</b>",                styles["cell"]),
    ]
    rows = [header]

    for idx, item in enumerate(results, start=1):
        label       = item.get("Category", "Original")
        label_color = LABEL_COLORS.get(label, colors.black)
        score       = item.get("Similarity Score", 0)
        source_file = item.get("Source File", "—")

        rows.append([
            Paragraph(str(idx),                              styles["small"]),
            Paragraph(item.get("Student Sentence", "")[:300], styles["cell"]),
            Paragraph(item.get("Matched Source",   "")[:300], styles["cell"]),
            Paragraph(source_file,                           styles["small"]),
            Paragraph(str(score),                            styles["small"]),
            Paragraph(
                f'<font color="{label_color.hexval()}"><b>{label}</b></font>',
                styles["cell_center"],
            ),
        ])

    col_widths = [0.7*cm, 5.5*cm, 5.5*cm, 2.8*cm, 1.2*cm, 2.3*cm]
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  BRAND_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ("GRID",          (0, 0), (-1, -1), 0.4, MID_GREY),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(tbl)


# ─────────────────────────────────────────────────────────── #
#  PUBLIC FUNCTIONS
# ─────────────────────────────────────────────────────────── #

def generate_pdf_report(results: list, summary: dict, output_path: str = None) -> str:
    """
    Generates a PDF report and saves it to disk.

    Called automatically by detector.py after every detection run.

    Args:
        results     (list): The "results" list from _run_detection().
        summary     (dict): Full summary dict from _run_detection().
        output_path (str) : Override save path. Defaults to reports/plagiarism_report_<ts>.pdf

    Returns:
        str: Path to the saved PDF.
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if output_path is None:
        ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(REPORTS_DIR, f"plagiarism_report_{ts}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize     = A4,
        leftMargin   = 2 * cm,
        rightMargin  = 2 * cm,
        topMargin    = 2 * cm,
        bottomMargin = 2 * cm,
        title        = "Plagiarism Detection Report",
    )

    styles = _build_styles()
    story  = []

    _cover_page(story, summary, styles)
    _source_breakdown(story, summary, styles)
    _detail_table(story, results, styles)

    doc.build(story)
    print(f"PDF report saved at:\n  {output_path}")
    return output_path


def generate_pdf_report_bytes(results: list, summary: dict) -> bytes:
    """
    Generates the PDF entirely in memory and returns raw bytes.
    Used by API endpoints that stream the PDF to the browser.
    """
    import io

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize     = A4,
        leftMargin   = 2 * cm,
        rightMargin  = 2 * cm,
        topMargin    = 2 * cm,
        bottomMargin = 2 * cm,
        title        = "Plagiarism Detection Report",
    )

    styles = _build_styles()
    story  = []

    _cover_page(story, summary, styles)
    _source_breakdown(story, summary, styles)
    _detail_table(story, results, styles)

    doc.build(story)
    buffer.seek(0)
    return buffer.read()