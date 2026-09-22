"""
Schema for fairness_findings.json -- the artifact consumed by the
Compliance Mapping Engine (phase 4). Findings here are per-protected-
attribute (aggregate statistics), NOT per-record, unlike
anomaly_findings.json. Phase 4 must handle both shapes.
"""
from __future__ import annotations
from typing import Dict, List
from pydantic import BaseModel


class FairnessFinding(BaseModel):
    attribute: str
    demographic_parity_difference: float
    demographic_parity_violation: bool
    demographic_parity_p_value: float
    disparate_impact_ratio: float
    disparate_impact_violation: bool
    equalized_odds_difference: float
    equalized_odds_violation: bool
    equalized_odds_p_value: float
    group_selection_rates: Dict[str, float]
    group_sizes: Dict[str, int]
    eeoc_four_fifths_threshold: float
    small_group_warning: List[str]
    permutation_test_config: dict


class FairnessScanOutput(BaseModel):
    findings: List[FairnessFinding]
    config: dict


def validate_output(data: dict) -> FairnessScanOutput:
    return FairnessScanOutput(**data)