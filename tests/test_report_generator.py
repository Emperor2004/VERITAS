"""
Phase 5 (report_generator) test suite.
"""
from __future__ import annotations

import json

import pytest

from src.report_generator.html_report import (
    load_mapped_findings,
    summarize,
    render_html_report,
    write_html_report,
)


def _sample_findings():
    return [
        {
            "finding_type": "fairness_finding", "metric_name": "disparate_impact_ratio",
            "observed_value": 0.37, "severity_tier": "violation",
            "controls_applied": [{"control_id": "MEASURE 2.11", "title": "t", "citation": "c", "matched_action_text": "m"}],
            "trigger_explanation": "0.37 < 0.8 -> violation", "source_record_id": "sex",
            "supporting_evidence": [],
        },
        {
            "finding_type": "anomaly_finding", "metric_name": None,
            "observed_value": -0.6, "severity_tier": "informational",
            "controls_applied": [{"control_id": "MEASURE 2.4", "title": "t", "citation": "c", "matched_action_text": "m"}],
            "trigger_explanation": "anomaly_score=-0.6000, resolved severity=informational.",
            "source_record_id": "SESS-0000012", "supporting_evidence": [],
        },
    ]


# ---- load_mapped_findings ------------------------------------------------------

def test_load_mapped_findings_raises_on_wrong_key(tmp_path):
    bad_path = tmp_path / "wrong.json"
    bad_path.write_text(json.dumps({"findings": []}))  # wrong key name
    with pytest.raises(ValueError, match="mapped_findings"):
        load_mapped_findings(bad_path)


def test_load_mapped_findings_reads_valid_file(tmp_path):
    path = tmp_path / "mapped_findings.json"
    path.write_text(json.dumps({"mapped_findings": _sample_findings()}))
    result = load_mapped_findings(path)
    assert len(result) == 2


# ---- summarize --------------------------------------------------------------

def test_summarize_counts_by_severity_tier_correctly():
    summary = summarize(_sample_findings())
    assert summary["by_severity_tier"]["violation"] == 1
    assert summary["by_severity_tier"]["informational"] == 1
    assert summary["total"] == 2


def test_summarize_separates_violation_and_informational_lists():
    summary = summarize(_sample_findings())
    assert len(summary["violation_findings"]) == 1
    assert summary["violation_findings"][0]["metric_name"] == "disparate_impact_ratio"
    assert len(summary["informational_findings"]) == 1


# ---- render_html_report -------------------------------------------------------

def test_render_html_report_includes_both_severity_sections():
    html = render_html_report(_sample_findings())
    assert "disparate_impact_ratio" in html
    assert "MEASURE 2.11" in html
    assert "MEASURE 2.4" in html


def test_render_html_report_includes_govern_scope_disclosure():
    # Locks in the scope claim agreed on earlier in the project: the report
    # must not silently imply full RMF coverage.
    html = render_html_report(_sample_findings())
    assert "GOVERN" in html
    assert "deploying organization" in html


def test_render_html_report_handles_zero_violations():
    only_informational = [f for f in _sample_findings() if f["severity_tier"] == "informational"]
    html = render_html_report(only_informational)
    assert "No violation-tier findings" in html


# ---- write_html_report (end-to-end file I/O) -----------------------------------

def test_write_html_report_end_to_end(tmp_path):
    input_path = tmp_path / "mapped_findings.json"
    input_path.write_text(json.dumps({"mapped_findings": _sample_findings()}))
    output_path = tmp_path / "audit_report.html"

    write_html_report(input_path, output_path)

    assert output_path.exists()
    content = output_path.read_text()
    assert "VERITAS Audit Report" in content
    assert "disparate_impact_ratio" in content
