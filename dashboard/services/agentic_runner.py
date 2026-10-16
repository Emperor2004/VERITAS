from __future__ import annotations

from typing import Any, Dict, List

from src.agentic.graph import make_initial_audit_state
from src.agentic.state import AuditState
from src.run_config import RunConfig

from dashboard.services.veritas_runner import load_project_config


def create_uploaded_audit_state(records: List[Dict[str, Any]]) -> AuditState:
    """Build a validated uploaded-data run state from approved project defaults."""
    protected_attributes = tuple(dict.fromkeys(
        attribute
        for record in records
        for attribute in record.get("protected_attributes", {})
    ))
    run_config = RunConfig.from_project_config(
        load_project_config(),
        input_mode="uploaded_predictions",
        protected_attributes=protected_attributes,
    )
    return make_initial_audit_state(records, run_config)