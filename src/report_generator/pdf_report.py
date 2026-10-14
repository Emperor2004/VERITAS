"""Phase 5 PDF generator using the populated DOCX report template and ReportLab."""
from __future__ import annotations

import logging
from copy import deepcopy
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.report_generator.html_report import summarize

logger = logging.getLogger(__name__)
TEMPLATE_PATH = Path(__file__).parent / "templates" / "report_template.docx"


def check_weasyprint_available() -> tuple[bool, str]:
    """Check if WeasyPrint and its native dependencies (cairo, pango, gobject) are functional."""
    try:
        import weasyprint  # noqa: F401
        return True, "WeasyPrint is available."
    except (ImportError, OSError) as e:
        msg = (
            f"WeasyPrint is not functional: {e}. "
            "On Windows, WeasyPrint requires the GTK3 runtime libraries "
            "(cairo, pango, gobject). Refer to: "
            "https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows"
        )
        return False, msg


def write_pdf_report(
    findings: List[Dict[str, Any]],
    output_path: str | Path,
    base_url: Optional[str] = None,
) -> bool:
    """Render findings into a PDF report at output_path.

    Args:
        findings: List of mapped findings dictionaries.
        output_path: Destination path for the generated PDF.
        base_url: Optional base URL for resolving assets.

    Returns:
        bool: True if PDF was generated successfully, False otherwise.

    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(render_pdf_report(findings, base_url=base_url))
    return True


def render_pdf_report(
    findings: List[Dict[str, Any]],
    base_url: Optional[str] = None,
) -> bytes:
    """Populate the DOCX report template and render its sections to PDF bytes."""
    del base_url
    template_document = _populate_report_template(findings)
    return _render_docx_template_with_reportlab(template_document)


def _populate_report_template(findings: List[Dict[str, Any]]):
    from docx import Document

    document = Document(TEMPLATE_PATH)
    summary = summarize(findings)
    now = datetime.now(timezone.utc)
    generated_at = now.strftime("%Y-%m-%d %H:%M UTC")
    report_id = now.strftime("VERITAS-%Y%m%d-%H%M%S")
    violations = summary["violation_findings"]
    informational = summary["informational_findings"]

    for paragraph in document.paragraphs:
        if paragraph.text.startswith("Generated:"):
            paragraph.text = f"Generated: {generated_at}     |     Findings mapped: {summary['total']}"
        elif paragraph.text.startswith("Use this section to summarize"):
            paragraph.text = (
                f"This automated audit mapped {summary['total']} findings: "
                f"{len(violations)} violation-tier and {len(informational)} informational. "
                "Review the findings and their cited controls before taking action."
            )
        elif paragraph.text.startswith("Findings that meet the configured"):
            paragraph.text = f"{len(violations)} violation-tier findings were identified in this run."
        elif paragraph.text.startswith("Record informational findings here"):
            paragraph.text = (
                f"This section contains {len(informational)} informational findings. "
                "Anomaly findings remain informational-only by design."
            )

    summary_counts = [
        summary["by_severity_tier"].get("violation", 0),
        summary["by_severity_tier"].get("informational", 0),
        summary["by_finding_type"].get("anomaly_finding", 0),
        summary["by_finding_type"].get("fairness_finding", 0),
    ]
    summary_labels = ["Violation-tier findings", "Informational findings", "Anomaly findings", "Fairness findings"]
    for cell, count, label in zip(document.tables[1].rows[0].cells, summary_counts, summary_labels):
        cell.text = f"{count}\n{label}"

    metadata = {
        "Report / run identifier": report_id,
        "Generated at": generated_at,
        "System / model assessed": "Not specified in mapped findings",
        "Assessment period": "Not specified in mapped findings",
        "Report owner": "VERITAS automated audit",
    }
    for row in document.tables[2].rows:
        if row.cells[0].text in metadata:
            row.cells[1].text = metadata[row.cells[0].text]

    def finding_row(finding: Dict[str, Any]) -> list[str]:
        observed = finding.get("observed_value", "Not reported")
        if isinstance(observed, (int, float)):
            observed = f"{observed:.4f}"
        controls = ", ".join(
            str(control.get("control_id", "")) for control in finding.get("controls_applied", [])
        ) or "None"
        return [
            str(finding.get("finding_type", "finding")),
            str(finding.get("metric_name") or "Not applicable"),
            str(observed),
            controls,
            str(finding.get("trigger_explanation", "Not reported")),
        ]

    def replace_body_rows(table, rows: list[list[str]]) -> None:
        prototype = deepcopy(table.rows[1]._tr)
        for row in list(table.rows)[1:]:
            row._tr.getparent().remove(row._tr)
        if not rows:
            rows = [["No findings", "", "", "", ""]]
        for values in rows:
            table._tbl.append(deepcopy(prototype))
            for cell, value in zip(table.rows[-1].cells, values):
                cell.text = value

    replace_body_rows(document.tables[3], [finding_row(finding) for finding in violations])
    replace_body_rows(document.tables[5], [finding_row(finding) for finding in informational])

    detail_finding = (violations or informational or [None])[0]
    detail_values = {
        "Finding ID": detail_finding.get("source_record_id", "Not available") if detail_finding else "Not available",
        "Observed value / threshold": str(detail_finding.get("observed_value", "Not reported")) if detail_finding else "Not available",
        "Evidence reference": ", ".join(
            str(control.get("control_id", ""))
            for control in detail_finding.get("controls_applied", [])
        ) if detail_finding else "Not available",
        "Recommended follow-up": "Review the finding and document an appropriate response." if detail_finding else "No follow-up indicated.",
    }
    for row in document.tables[4].rows:
        if row.cells[0].text in detail_values:
            row.cells[1].text = detail_values[row.cells[0].text]

    recommended_findings = violations[:3]
    recommendation_rows = [
        ["Review", str(finding.get("trigger_explanation", "Review finding and cited evidence.")), "Not assigned", "Not assigned"]
        for finding in recommended_findings
    ] or [["N/A", "No violation-tier findings in this run.", "Not assigned", "Not assigned"]]
    replace_body_rows(document.tables[6], recommendation_rows)

    appendix_values = {
        "Methodology / configuration": "See config/config.yaml and the run manifest.",
        "Data sources": "Mapped phase-4 findings artifact.",
        "Known limitations": "This report is audit evidence, not regulatory certification; thresholds and input quality affect interpretation.",
        "Reviewer / approval": "Not provided.",
    }
    for row in document.tables[8].rows:
        if row.cells[0].text in appendix_values:
            row.cells[1].text = appendix_values[row.cells[0].text]

    return document


def _render_docx_template_with_reportlab(template_document) -> bytes:
    from docx.table import Table as DocxTable
    from docx.text.paragraph import Paragraph as DocxParagraph
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="VERITAS Audit Report",
    )
    base_style = getSampleStyleSheet()["BodyText"]
    body_style = ParagraphStyle("TemplateBody", parent=base_style, fontSize=8.5, leading=11, spaceAfter=4)
    heading_colors = {"Heading 1": "#172b4d", "Heading 2": "#294b9b", "Heading 3": "#4569d4"}
    paragraph_styles = {"Normal": body_style}
    story = []

    def safe_paragraph(text: str, style) -> Paragraph:
        safe_text = escape(str(text).encode("cp1252", errors="replace").decode("cp1252"))
        return Paragraph(safe_text.replace("\n", "<br/>"), style)

    def paragraph_style(word_paragraph):
        style_name = word_paragraph.style.name
        if style_name not in paragraph_styles:
            font_size = {
                "Title": 22,
                "Heading 1": 14,
                "Heading 2": 11,
                "Heading 3": 9.5,
            }.get(style_name, 9)
            paragraph_styles[style_name] = ParagraphStyle(
                f"Template{style_name.replace(' ', '')}",
                parent=body_style,
                fontName="Helvetica-Bold" if style_name != "Normal" else "Helvetica",
                fontSize=font_size,
                leading=font_size * 1.3,
                textColor=colors.HexColor(heading_colors.get(style_name, "#182230")),
                spaceBefore=10 if style_name.startswith("Heading") else 4,
                spaceAfter=6,
                keepWithNext=style_name.startswith("Heading"),
            )
        return paragraph_styles[style_name]

    available_width = letter[0] - 1.2 * inch
    table_index = 0
    for block in template_document.iter_inner_content():
        if isinstance(block, DocxParagraph):
            if block.text.strip():
                story.append(safe_paragraph(block.text, paragraph_style(block)))
            else:
                story.append(Spacer(1, 4))
            continue
        if not isinstance(block, DocxTable):
            continue

        current_table_index = table_index
        table_index += 1
        rows = []
        for row_index, row in enumerate(block.rows):
            cells = []
            for cell in row.cells:
                cell_text = "\n".join(paragraph.text for paragraph in cell.paragraphs).strip()
                style = body_style
                if current_table_index in {3, 5, 6} and row_index == 0:
                    style = ParagraphStyle(
                        "TemplateTableHeader", parent=body_style,
                        fontName="Helvetica-Bold", textColor=colors.white, fontSize=7.5,
                    )
                cells.append(safe_paragraph(cell_text or " ", style))
            rows.append(cells)
        if not rows or all(not cell.getPlainText().strip() for row in rows for cell in row):
            continue

        column_count = len(rows[0])
        table = LongTable(
            rows,
            colWidths=[available_width / column_count] * column_count,
            repeatRows=1 if current_table_index in {3, 5, 6} else 0,
            splitByRow=1,
        )
        table_style = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d8dee8")),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        if current_table_index in {3, 5, 6}:
            table_style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172b4d")))
        elif current_table_index == 1:
            table_style.extend([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#edf2ff")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ])
        elif current_table_index == 7:
            table_style.append(("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef2f8")))
        table.setStyle(TableStyle(table_style))
        story.extend([table, Spacer(1, 6)])

    document.build(story)
    return buffer.getvalue()
