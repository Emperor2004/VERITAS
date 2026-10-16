"""Validated state and audit trace models for agentic VERITAS runs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Annotated, Literal
from uuid import uuid4
import operator

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import TypedDict

from src.run_config import RunConfig

RunStatus = Literal[
    "ready",
    "awaiting_approval",
    "approved",
    "analyzing",
    "mapping",
    "reporting",
    "rejected",
    "completed",
    "failed",
]


class TraceEvent(BaseModel):
    """Hash-linked record of a deterministic stage or approval decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent: str
    tool: str
    input_hash: str
    output_hash: str
    config_hash: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: Literal["ok", "rejected", "failed"] = "ok"
    rationale: str | None = None


class ApprovalRecord(BaseModel):
    """Human decision on the effective configuration before analytics run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    approved: bool
    approved_by: str = Field(min_length=1)
    approved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    config_hash: str
    note: str | None = None

    @field_validator("approved_by")
    @classmethod
    def validate_approver(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("approved_by must not be blank")
        return cleaned


class AuditState(BaseModel):
    """Validated run snapshot shared between graph nodes and Streamlit."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    run_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    input_mode: Literal["adult_income", "uploaded_predictions"]
    input_hash: str = ""
    records: list[dict[str, Any]] = Field(default_factory=list)
    proposed_run_config: RunConfig
    approved_run_config: RunConfig | None = None
    status: RunStatus = "ready"
    validation_summary: dict[str, Any] = Field(default_factory=dict)
    approval_record: ApprovalRecord | None = None
    anomaly_output: dict[str, Any] | None = None
    fairness_output: dict[str, Any] | None = None
    mapped_findings: list[dict[str, Any]] = Field(default_factory=list)
    report_html: str | None = None
    trace: list[TraceEvent] = Field(default_factory=list)
    failure: str | None = None
    schema_mapping: dict[str, str] = Field(default_factory=dict)
    schema_confidence: float | None = None
    schema_needs_review: bool = False
    config_proposal: dict[str, Any] | None = None
    anomaly_groups: list[dict[str, Any]] = Field(default_factory=list)


class AgenticGraphState(TypedDict, total=False):
    schema_version: int
    run_id: str
    input_mode: str
    input_hash: str
    records: list[dict[str, Any]]
    proposed_run_config: dict[str, Any]
    approved_run_config: dict[str, Any] | None
    status: str
    validation_summary: dict[str, Any]
    approval_record: dict[str, Any] | None
    anomaly_output: dict[str, Any] | None
    fairness_output: dict[str, Any] | None
    mapped_findings: list[dict[str, Any]]
    report_html: str | None
    trace: Annotated[list[dict[str, Any]], operator.add]
    failure: str | None
    schema_mapping: dict[str, str]
    schema_confidence: float | None
    schema_needs_review: bool
    config_proposal: dict[str, Any] | None
    anomaly_groups: list[dict[str, Any]]