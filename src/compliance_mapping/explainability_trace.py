"""
Phase 4 explainability trace.

Attaches the SPECIFIC NIST control text a finding was matched against, plus
a human-readable trigger explanation, so a mapped finding answers "why this
control ID" without a human re-deriving it from the YAML. This is the piece
flagged as an architecture gap in CA-1 review.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .output_schema import ControlCitation


def _citation_for(control_key: str, lookup: Dict[str, Any]) -> ControlCitation:
    controls = lookup.get("controls", {})
    if control_key not in controls:
        raise ValueError(
            f"Control key '{control_key}' referenced in finding_mappings/"
            "severity_tiers but not defined under 'controls'. "
            "nist_control_lookup.yaml failed internal consistency -- fix the "
            "YAML, do not patch around it here."
        )
    c = controls[control_key]
    return ControlCitation(
        control_id=c["id"],
        title=c["title"],
        citation=c["citation"],
        matched_action_text=c["matched_action_text"].strip(),
    )


def build_controls_applied(control_keys: List[str], lookup: Dict[str, Any]) -> List[ControlCitation]:
    return [_citation_for(k, lookup) for k in control_keys]


def build_trigger_explanation(finding: Dict[str, Any], lookup: Dict[str, Any]) -> str:
    """
    Human-readable, per-finding explanation of what caused the severity tier
    assigned to this finding. Descriptive only -- reads the finding's own
    fields, does not recompute anything.
    """
    finding_type = finding["finding_type"]
    value = finding["observed_value"]
    tier = finding["severity_tier"]
    evidence = finding.get("supporting_evidence") or []

    if finding_type == "anomaly_finding":
        if evidence:
            feature_str = ", ".join(f"{f['feature']} (z={f['z_score']:.2f})" for f in evidence)
        else:
            feature_str = "no contributing-feature detail available"
        return f"anomaly_score={value:.4f}, resolved severity={tier}. Top contributing features: {feature_str}."

    metric = finding.get("metric_name", "<unknown metric>")
    caveat = ""
    if evidence:  # small_group_warning list for fairness findings
        caveat = (
            f" CAVEAT: group(s) {evidence} are below the minimum size threshold -- "
            "this result may be statistically unstable."
        )

    if metric == "disparate_impact_ratio":
        return f"{metric}={value:.4f} against EEOC four-fifths threshold (0.8) -> {tier}.{caveat}"
    if metric in ("demographic_parity_difference", "equalized_odds_difference"):
        return f"{metric}={value:.4f}, resolved via permutation significance test upstream -> {tier}.{caveat}"
    return f"{metric}={value:.4f} -> {tier}.{caveat}"