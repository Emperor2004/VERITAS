"""
Phase 4 severity policy.

Deliberately thin: this module does NOT compute severity (no permutation
test, no EEOC comparison -- that happens upstream in fairness_scanner /
anomaly_detection, which have access to the raw per-record data required).
Its only job: (a) validate the severity_tier a finding already carries is a
known tier, and (b) resolve which additional controls that tier escalates
to, per nist_control_lookup.yaml's `severity_tiers` block.
"""
from __future__ import annotations

from typing import Any, Dict, List


def resolve_escalation(severity_tier: str, lookup: Dict[str, Any]) -> List[str]:
    """
    Return the control keys (into lookup['controls']) that this severity
    tier escalates to. Raises if the tier is unknown -- this is the guard
    against 'dynamic' or an upstream typo reaching this layer unresolved.
    """
    tiers = lookup.get("severity_tiers", {})
    if severity_tier not in tiers:
        raise ValueError(
            f"Unknown severity_tier '{severity_tier}'. Known tiers: "
            f"{sorted(tiers.keys())}. This finding was not fully resolved "
            "upstream before reaching the Compliance Mapping Engine."
        )
    return list(tiers[severity_tier].get("escalates_to", []))