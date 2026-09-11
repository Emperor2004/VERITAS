"""
Schema for anomaly_findings.json -- the artifact consumed by the
Compliance Mapping Engine (phase 4). The fairness scanner produces a
separate findings file with its own schema; the two are joined only
at the compliance-mapping stage, per README section 3 (parallel execution).
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class ContributingFeature(BaseModel):
    feature: str
    z_score: float


class AnomalyFinding(BaseModel):
    record_id: str
    anomaly_score: float
    is_anomaly: bool
    top_contributing_features: List[ContributingFeature]


class EvaluationResult(BaseModel):
    precision: float
    recall: float
    f1: float
    n_ground_truth_anomalies: int
    n_flagged: int
    note: str


class AnomalyDetectionOutput(BaseModel):
    findings: List[AnomalyFinding]
    evaluation: Optional[EvaluationResult] = None
    threshold_selection: dict
    config: dict


def validate_output(data: dict) -> AnomalyDetectionOutput:
    return AnomalyDetectionOutput(**data)