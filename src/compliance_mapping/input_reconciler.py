"""
Phase 4 input reconciler.

Joins the two differently-shaped upstream outputs -- per-record anomaly
findings and per-attribute fairness findings -- into one stream the rules
engine can process, WITHOUT force-merging them into a single row shape.

Written against the REAL Phase 2/3 output schemas (read from
anomaly_detection/output_schema.py and fairness_scanner/output_schema.py),
not an assumed API:
  - AnomalyFinding has `is_anomaly: bool`, not a severity_tier -- Phase 4
    filters to genuine findings here and assigns severity per the locked-in
    decision (informational-only; see veritas-capstone.md).
  - FairnessFinding is ONE row per protected attribute carrying all three
    metrics plus their own violation flags -- this unpacks that into three
    independent findings, one per metric, since each metric gets its own
    NIST control mapping and severity in nist_control_lookup.yaml.
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, List

REQUIRED_ANOMALY_FIELDS = {"record_id", "anomaly_score", "is_anomaly"}
REQUIRED_FAIRNESS_FIELDS = {
    "attribute",
    "demographic_parity_difference", "demographic_parity_violation",
    "disparate_impact_ratio", "disparate_impact_violation",
    "equalized_odds_difference", "equalized_odds_violation",
}

# metric_name -> which field in the raw fairness record holds its violation flag
FAIRNESS_METRIC_TO_VIOLATION_FIELD = {
    "disparate_impact_ratio": "disparate_impact_violation",
    "demographic_parity_difference": "demographic_parity_violation",
    "equalized_odds_difference": "equalized_odds_violation",
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

    Anomaly records with is_anomaly=False are normal operation, not
    findings -- they are validated (schema must be well-formed) but
    filtered out here, never mapped to a NIST control. Mapping every row
    in the dataset would produce a compliance citation per normal record,
    which is not what an audit finding is.
    """
    for rec in anomaly_findings:
        _validate_anomaly_record(rec)
        if not rec["is_anomaly"]:
            continue
        yield {
            "finding_type": "anomaly_finding",
            "metric_name": None,
            "observed_value": rec["anomaly_score"],
            # Decision (a), locked in: anomaly findings stay informational-only
            # until an externally-defensible severity cutoff exists -- see
            # veritas-capstone.md, Compliance Mapping Engine decisions.
            "severity_tier": "informational",
            "source_record_id": rec["record_id"],
            "supporting_evidence": rec.get("top_contributing_features", []),
        }

    for rec in fairness_findings:
        _validate_fairness_record(rec)
        for metric_name, violation_field in FAIRNESS_METRIC_TO_VIOLATION_FIELD.items():
            yield {
                "finding_type": "fairness_finding",
                "metric_name": metric_name,
                "observed_value": rec[metric_name],
                "severity_tier": "violation" if rec[violation_field] else "informational",
                "source_record_id": rec["attribute"],
                "supporting_evidence": rec.get("small_group_warning", []),
            }