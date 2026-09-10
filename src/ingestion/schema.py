"""
Schema definition and validation for the ingestion module's output artifact:
normalized_log.json

This is the single contract consumed by BOTH the anomaly detection module
and the fairness scanner (see README section 3 -- they run in parallel off
this same file). Any change here must be reflected in docs/module_contracts.md.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, field_validator


class NormalizedLogRecord(BaseModel):
    record_id: str = Field(..., description="Unique identifier for this prediction event")
    timestamp: datetime
    session_id: str
    auth_method: str

    # Features consumed by anomaly detection (numeric, engineered/encoded)
    features: Dict[str, float]

    # Raw protected attributes -- MUST remain human-readable categorical values.
    # Anomaly detection may use encoded versions inside `features`, but the
    # fairness scanner requires these raw labels to compute group metrics.
    protected_attributes: Dict[str, str]

    # What the audit-subject model actually predicted
    predicted_label: int = Field(..., ge=0, le=1)
    prediction_confidence: float = Field(..., ge=0.0, le=1.0)

    # Ground truth, retained for evaluation/debugging only --
    # NOT to be used by anomaly detection or fairness scanner logic,
    # since a real deployed audit subject would not expose this.
    true_label: Optional[int] = Field(default=None, ge=0, le=1)

    # Ground truth for the DELIBERATELY INJECTED operational anomaly
    # (see synthetic_metadata.py). Evaluation-only -- phase 2's
    # IsolationForest must never see this field as an input feature,
    # only use it afterward to score precision/recall.
    ground_truth_operational_anomaly: Optional[bool] = Field(default=None)

    @field_validator("protected_attributes")
    @classmethod
    def must_include_configured_attributes(cls, v: Dict[str, str]) -> Dict[str, str]:
        if not v:
            raise ValueError(
                "protected_attributes cannot be empty -- fairness scanner has nothing to group on"
            )
        return v


def validate_records(records: List[dict]) -> List[NormalizedLogRecord]:
    """Validate a list of raw dicts against the schema. Raises on first failure --
    a corrupt/malformed record here should stop the pipeline, not be silently
    dropped (see README section 12 -- silent discard is a known audit-defensibility
    problem; we do not want to repeat that mistake at the ingestion boundary)."""
    return [NormalizedLogRecord(**r) for r in records]