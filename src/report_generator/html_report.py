"""
Phase 5 HTML report generator.

Reads mapped_findings.json (Phase 4 output) and renders a single,
self-contained, static HTML audit report -- no external CDN assets, no JS
required to read it. Deliberately simple: this is an audit artifact meant
to be portable, diffable as plain text, and readable offline.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).parent / "templates"


def load_mapped_findings(path) -> List[Dict[str, Any]]:
    with open(path) as f:
        payload = json.load(f)
    if "mapped_findings" not in payload:
        raise ValueError(f"{path} does not contain a 'mapped_findings' key -- wrong input file?")
    return payload["mapped_findings"]


def summarize(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_tier: Dict[str, int] = {"violation": 0, "informational": 0}
    by_finding_type: Dict[str, int] = {}
    for f in findings:
        tier = f["severity_tier"]
        by_tier[tier] = by_tier.get(tier, 0) + 1
        ft = f["finding_type"]
        by_finding_type[ft] = by_finding_type.get(ft, 0) + 1
    return {
        "total": len(findings),
        "by_severity_tier": by_tier,
        "by_finding_type": by_finding_type,
        "violation_findings": [f for f in findings if f["severity_tier"] == "violation"],
        "informational_findings": [f for f in findings if f["severity_tier"] == "informational"],
    }


def render_html_report(findings: List[Dict[str, Any]], generated_at: datetime = None) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    summary = summarize(findings)
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report_template.html")
    return template.render(
        findings=findings,
        summary=summary,
        generated_at=generated_at.strftime("%Y-%m-%d %H:%M UTC"),
    )


def write_html_report(input_path, output_path) -> None:
    findings = load_mapped_findings(input_path)
    html = render_html_report(findings)
    with open(output_path, "w") as f:
        f.write(html)