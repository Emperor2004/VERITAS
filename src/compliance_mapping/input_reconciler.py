"""
Phase 4 input reconciler.

Joins the two differently-shaped upstream outputs -- per-record anomaly
findings and per-attribute fairness findings -- into one stream the rules
engine can process, WITHOUT force-merging them into a single row shape.
Fabricating a per-record fairness value or a per-attribute anomaly value
would misrepresent data that was never computed at that granularity.
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, List

REQUIRED_ANOMALY_FIELDS = {"record_id", "anomaly_score", "severity_tier"}
REQUIRED_FAIRNESS_FIELDS = {
    "protected_attribute", "metric_name", "observed_value", "severity_tier",
}


def _validate_anomaly_record(rec: Dict[str, Any]) -> None:
    missing = REQUIRED_ANOMALY_FIELDS - rec.keys()
    if missing:
        raise ValueError(f"Anomaly finding missing required field(s): {missing}. Record: {rec}")


def _validate_fairness_record(rec: Dict[str, Any]) -> None:
    missing = REQUIRED_FAIRNESS_FIELDS - rec.keys()
    if missing:
        raise ValueError(f"Fairness finding missing required field(s): {missing}. Record: {rec}")


def reconcile(
    anomaly_findings: List[Dict[str, Any]],
    fairness_findings: List[Dict[str, Any]],
) -> Iterator[Dict[str, Any]]:
    """
    Yield a unified stream of tagged findings for rules_engine.py.

    Each yielded dict carries a `finding_type` key added here; all other
    fields are passed through from whichever section they came from. The
    two input shapes are validated but never coerced into each other.
    """
    for rec in anomaly_findings:
        _validate_anomaly_record(rec)
        yield {
            "finding_type": "anomaly_finding",
            "metric_name": None,
            "observed_value": rec["anomaly_score"],
            "severity_tier": rec["severity_tier"],
            "source_record_id": rec["record_id"],
        }

    for rec in fairness_findings:
        _validate_fairness_record(rec)
        yield {
            "finding_type": "fairness_finding",
            "metric_name": rec["metric_name"],
            "observed_value": rec["observed_value"],
            "severity_tier": rec["severity_tier"],
            "source_record_id": rec["protected_attribute"],
        }