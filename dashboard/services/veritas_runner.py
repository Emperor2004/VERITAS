from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.anomaly_detection.isolation_forest import run_anomaly_detection
from src.compliance_mapping.run_mapping import run_mapping
from src.compliance_mapping.rules_engine import load_lookup_table
from src.compliance_mapping.plain_explanation import attach_plain_explanations
from src.agentic.agents.anomaly_grouper import group_anomalies
from src.fairness_scanner.run_scan import run_fairness_scan
from src.report_generator.html_report import render_html_report
from src.run_config import RunConfig

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
LOOKUP_PATH = PROJECT_ROOT / "src" / "compliance_mapping" / "nist_control_lookup.yaml"


def load_project_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def run_veritas_on_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    config = load_project_config()
    protected_attributes = tuple(dict.fromkeys(
        attribute
        for record in records
        for attribute in record.get("protected_attributes", {})
    ))
    run_config = RunConfig.from_project_config(
        config,
        input_mode="uploaded_predictions",
        protected_attributes=protected_attributes,
    )
    anomaly_output = run_anomaly_detection(
        records,
        random_state=run_config.isolation_forest_random_state,
        n_estimators=run_config.isolation_forest_n_estimators,
        contamination_override=run_config.contamination_override,
    )
    fairness_output = run_fairness_scan(records, run_config)
    lookup = load_lookup_table(LOOKUP_PATH)
    mapped_findings = run_mapping(anomaly_output["findings"], fairness_output["findings"], lookup)
    mapped_findings = attach_plain_explanations(mapped_findings)
    anomaly_groups = group_anomalies(anomaly_output.get("findings", []))
    report_html = render_html_report(mapped_findings)

    return {
        "anomaly": anomaly_output,
        "fairness": fairness_output,
        "mapped_findings": mapped_findings,
        "anomaly_groups": [g.to_dict() for g in anomaly_groups],
        "report_html": report_html,
        "effective_run_config": run_config.to_effective_dict(),
    }


def build_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    anomaly_findings = results["anomaly"]["findings"]
    fairness_findings = results["fairness"]["findings"]
    mapped_findings = results["mapped_findings"]

    anomaly_total = sum(1 for item in anomaly_findings if item["is_anomaly"])
    fairness_violations = sum(
        1 for item in fairness_findings if item["disparate_impact_violation"] or item["demographic_parity_violation"] or item["equalized_odds_violation"]
    )
    violation_count = sum(1 for item in mapped_findings if item["severity_tier"] == "violation")
    informational_count = sum(1 for item in mapped_findings if item["severity_tier"] == "informational")

    return {
        "anomaly_total": anomaly_total,
        "fairness_violations": fairness_violations,
        "mapped_violation_count": violation_count,
        "mapped_informational_count": informational_count,
        "total_findings": len(mapped_findings),
    }
