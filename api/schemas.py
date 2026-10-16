"""
Pydantic API request and response schemas for VERITAS.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ValidateResponse(BaseModel):
    valid: bool
    total_rows: int
    row_count: Optional[int] = None
    columns: List[str]
    detected_roles: Dict[str, Any]
    preview_rows: List[Dict[str, Any]]
    errors: List[str] = Field(default_factory=list)


class CreateRunResponse(BaseModel):
    run_id: str
    status: str
    upload_name: str
    row_count: int
    validation_summary: Dict[str, Any]
    config_proposal: Optional[Dict[str, Any]] = None
    proposed_run_config: Dict[str, Any]


class ApproveRunRequest(BaseModel):
    protected_attributes: List[str] = Field(min_length=1)
    significance_level: float = Field(gt=0.0, lt=1.0)
    min_group_size_warning: Optional[int] = Field(default=None, ge=1)
    min_group_size: Optional[int] = Field(default=None, ge=1)
    permutations: int = Field(ge=1, le=100_000)


class RejectRunRequest(BaseModel):
    note: Optional[str] = "Rejected by reviewer"


class AskQuestionRequest(BaseModel):
    question: str = Field(min_length=2)


class AskQuestionResponse(BaseModel):
    answer: str
    run_id: str
    citations: List[str] = Field(default_factory=list)


class ConfigBoundsResponse(BaseModel):
    significance_level: Dict[str, float]
    min_group_size: Dict[str, int]
    permutations: Dict[str, int]
    default_protected_candidates: List[str]


class RunDetailResponse(BaseModel):
    run_id: str
    upload_name: str
    status: str
    current_stage: Optional[str] = None
    row_count: int
    config_fingerprint: Optional[str] = None
    approved_by: Optional[str] = None
    created_at: str
    updated_at: str
    validation_summary: Optional[Dict[str, Any]] = None
    config_proposal: Optional[Dict[str, Any]] = None
    proposed_config: Optional[Dict[str, Any]] = None
    approved_config: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    review: Optional[Dict[str, Any]] = None
