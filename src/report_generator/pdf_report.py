"""
Phase 5 PDF report generator.

Attempts to render the HTML audit report into a PDF document using WeasyPrint.
On platforms where underlying C-libraries (Pango/Cairo/GObject) are not installed
(common on Windows without GTK), it provides clear diagnostics and graceful fallbacks.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.report_generator.html_report import render_html_report

logger = logging.getLogger(__name__)


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

    Raises:
        RuntimeError: If WeasyPrint or native libraries are missing.
    """
    is_available, reason = check_weasyprint_available()
    if not is_available:
        logger.warning(reason)
        raise RuntimeError(reason)

    import weasyprint

    html_content = render_html_report(findings)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html = weasyprint.HTML(string=html_content, base_url=base_url)
    html.write_pdf(str(output_path))
    return True
