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
    disparate_impact_ratio: float
    equalized_odds_difference: float
    group_selection_rates: Dict[str, float]
    group_sizes: Dict[str, int]
    eeoc_four_fifths_threshold: float
    disparate_impact_violation: bool
    small_group_warning: List[str]


class FairnessScanOutput(BaseModel):
    findings: List[FairnessFinding]
    config: dict


def validate_output(data: dict) -> FairnessScanOutput:
    return FairnessScanOutput(**data)