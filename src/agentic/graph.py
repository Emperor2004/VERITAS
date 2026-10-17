"""Deterministic Master graph around the existing VERITAS analysis tools."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from src.anomaly_detection.isolation_forest import run_anomaly_detection
from src.compliance_mapping.run_mapping import run_mapping
from src.compliance_mapping.rules_engine import load_lookup_table
from src.fairness_scanner.run_scan import run_fairness_scan
from src.report_generator.html_report import render_html_report
from src.run_config import RunConfig
from src.agentic.agents.config_proposer import propose_config
from src.agentic.agents.anomaly_grouper import group_anomalies

from .state import ApprovalRecord, AuditState, AgenticGraphState, TraceEvent

DEFAULT_LOOKUP_PATH = Path(__file__).resolve().parents[1] / "compliance_mapping" / "nist_control_lookup.yaml"


def _canonical_hash(value: Any) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    """Convert NumPy scalars and nested values to checkpoint-safe primitives."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported audit state value: {type(value).__name__}")


def _audit_state(state: AgenticGraphState) -> AuditState:
    return AuditState.model_validate(state)


def _trace_event(
    *,
    agent: str,
    tool: str,
    input_value: Any,
    output_value: Any,
    config: RunConfig,
    rationale: str | None = None,
    status: str = "ok",
) -> dict[str, Any]:
    return TraceEvent(
        agent=agent,
        tool=tool,
        input_hash=_canonical_hash(input_value),
        output_hash=_canonical_hash(output_value),
        config_hash=_canonical_hash(config.to_effective_dict()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=status,
        rationale=rationale,
    ).model_dump(mode="json")


def make_initial_audit_state(
    records: list[dict[str, Any]],
    run_config: RunConfig,
    *,
    run_id: str | None = None,
) -> AuditState:
    """Create a validated, session-local run snapshot from normalized records."""
    return AuditState(
        run_id=run_id or str(uuid4()),
        input_mode=run_config.input_mode,
        records=_json_safe(records),
        proposed_run_config=run_config,
    )


def build_audit_graph(
    checkpointer: BaseCheckpointSaver | None = None,
    *,
    lookup_path: str | Path = DEFAULT_LOOKUP_PATH,
):
    """Compile the fixed-edge workflow with a human approval interrupt.

    The default checkpointer is process-memory only. Callers handling uploaded
    rows should provide a session-scoped in-memory checkpointer and a unique
    `thread_id` for each run.
    """
    lookup_path = Path(lookup_path)

    def validate_inputs(state: AgenticGraphState) -> dict[str, Any]:
        audit = _audit_state(state)
        if not audit.records:
            raise ValueError("An audit run requires at least one normalized record.")

        available_attributes = {
            attribute
            for record in audit.records
            for attribute in record.get("protected_attributes", {})
        }
        missing_attributes = set(audit.proposed_run_config.protected_attributes) - available_attributes
        if missing_attributes:
            raise ValueError(
                "Configured protected attribute(s) missing from records: "
                f"{sorted(missing_attributes)}. Available attributes: {sorted(available_attributes)}."
            )

        input_hash = _canonical_hash(audit.records)
        proposal = propose_config(audit.records)
        validation_summary = {
            "rows": len(audit.records),
            "protected_attributes": sorted(available_attributes),
            "selected_protected_attributes": list(audit.proposed_run_config.protected_attributes),
        }
        return {
            "input_hash": input_hash,
            "status": "awaiting_approval",
            "validation_summary": validation_summary,
            "config_proposal": proposal.to_dict(),
            "trace": [
                _trace_event(
                    agent="ingest_validate",
                    tool="validate_normalized_records",
                    input_value=input_hash,
                    output_value=validation_summary,
                    config=audit.proposed_run_config,
                    rationale="Validate the normalized upload and profile available protected attributes.",
                )
            ],
        }

    def request_approval(state: AgenticGraphState) -> dict[str, Any]:
        audit = _audit_state(state)
        approval_payload = {
            "run_id": audit.run_id,
            "validation_summary": audit.validation_summary,
            "proposed_run_config": audit.proposed_run_config.to_effective_dict(),
            "config_proposal": audit.config_proposal,
            "input_hash": audit.input_hash,
        }
        response = interrupt(approval_payload)
        if not isinstance(response, dict):
            raise ValueError("Approval response must be an object.")

        approved = response.get("approved")
        if not isinstance(approved, bool):
            raise ValueError("Approval response must include a boolean 'approved' value.")

        config_data = response.get(
            "approved_run_config",
            audit.proposed_run_config.to_effective_dict(),
        )
        approved_config = RunConfig.model_validate(config_data) if approved else None
        if approved_config is not None and approved_config.input_mode != audit.input_mode:
            raise ValueError("Approval cannot change the run's input mode.")
        if approved_config is not None:
            available_attributes = set(audit.validation_summary["protected_attributes"])
            missing_attributes = set(approved_config.protected_attributes) - available_attributes
            if missing_attributes:
                raise ValueError(
                    "Approved protected attribute(s) missing from uploaded records: "
                    f"{sorted(missing_attributes)}. Available attributes: "
                    f"{sorted(available_attributes)}."
                )

        config_for_record = approved_config or audit.proposed_run_config
        approval_record = ApprovalRecord(
            approved=approved,
            approved_by=response.get("approved_by", ""),
            config_hash=_canonical_hash(config_for_record.to_effective_dict()),
            note=response.get("note"),
        )
        return {
            "approved_run_config": (
                approved_config.model_dump(mode="json") if approved_config else None
            ),
            "approval_record": approval_record.model_dump(mode="json"),
            "status": "approved" if approved else "rejected",
            "trace": [
                _trace_event(
                    agent="master",
                    tool="human_approval",
                    input_value=approval_payload,
                    output_value=approval_record.model_dump(mode="json"),
                    config=config_for_record,
                    rationale="Require a human decision before analysis and control mapping.",
                    status="ok" if approved else "rejected",
                )
            ],
        }

    def route_after_approval(state: AgenticGraphState) -> str:
        return "approved" if state.get("status") == "approved" else "rejected"

    def start_analysis(state: AgenticGraphState) -> dict[str, Any]:
        audit = _audit_state(state)
        return {
            "status": "analyzing",
            "trace": [
                _trace_event(
                    agent="master",
                    tool="start_deterministic_analysis",
                    input_value=audit.approval_record.model_dump(mode="json"),
                    output_value={"status": "analyzing"},
                    config=audit.approved_run_config,
                    rationale="Run the approved deterministic analysis tools in parallel.",
                )
            ],
        }

    def anomaly_agent(state: AgenticGraphState) -> dict[str, Any]:
        audit = _audit_state(state)
        config = audit.approved_run_config
        if config is None:
            raise ValueError("Anomaly Agent requires an approved RunConfig.")
        output = run_anomaly_detection(
            audit.records,
            random_state=config.isolation_forest_random_state,
            n_estimators=config.isolation_forest_n_estimators,
            contamination_override=config.contamination_override,
        )
        groups = group_anomalies(output.get("findings", []))
        return {
            "anomaly_output": _json_safe(output),
            "anomaly_groups": [g.to_dict() for g in groups],
            "trace": [
                _trace_event(
                    agent="anomaly",
                    tool="run_anomaly_detection",
                    input_value={"input_hash": audit.input_hash, "config": config.to_effective_dict()},
                    output_value=output,
                    config=config,
                )
            ],
        }

    def fairness_agent(state: AgenticGraphState) -> dict[str, Any]:
        audit = _audit_state(state)
        config = audit.approved_run_config
        if config is None:
            raise ValueError("Fairness Agent requires an approved RunConfig.")
        output = run_fairness_scan(audit.records, config)
        return {
            "fairness_output": _json_safe(output),
            "trace": [
                _trace_event(
                    agent="fairness",
                    tool="run_fairness_scan",
                    input_value={"input_hash": audit.input_hash, "config": config.to_effective_dict()},
                    output_value=output,
                    config=config,
                )
            ],
        }

    def compliance_agent(state: AgenticGraphState) -> dict[str, Any]:
        audit = _audit_state(state)
        if audit.approval_record is None or not audit.approval_record.approved:
            raise ValueError("Compliance mapping is blocked until a human approves the run.")
        if audit.anomaly_output is None or audit.fairness_output is None:
            raise ValueError("Compliance mapping requires both analysis outputs.")
        mapped = run_mapping(
            audit.anomaly_output["findings"],
            audit.fairness_output["findings"],
            load_lookup_table(lookup_path),
        )
        config = audit.approved_run_config
        return {
            "status": "mapping",
            "mapped_findings": _json_safe(mapped),
            "trace": [
                _trace_event(
                    agent="compliance_mapping",
                    tool="run_mapping",
                    input_value={
                        "anomaly_findings": audit.anomaly_output["findings"],
                        "fairness_findings": audit.fairness_output["findings"],
                    },
                    output_value=mapped,
                    config=config,
                )
            ],
        }

    def report_agent(state: AgenticGraphState) -> dict[str, Any]:
        audit = _audit_state(state)
        metadata = {
            "run_id": audit.run_id,
            "upload_name": audit.validation_summary.get("filename") or "audit_dataset.csv",
            "row_count": len(audit.records),
            "approved_by": audit.approval_record.approved_by if audit.approval_record else None,
            "config_fingerprint": audit.approval_record.config_hash[:8] if (audit.approval_record and audit.approval_record.config_hash) else None,
        }
        html = render_html_report(audit.mapped_findings, run_metadata=metadata)
        return {
            "status": "reporting",
            "report_html": html,
            "trace": [
                _trace_event(
                    agent="report_generation",
                    tool="render_html_report",
                    input_value=audit.mapped_findings,
                    output_value=html,
                    config=audit.approved_run_config,
                )
            ],
        }

    def finish_run(state: AgenticGraphState) -> dict[str, Any]:
        audit = _audit_state(state)
        return {
            "status": "completed",
            "trace": [
                _trace_event(
                    agent="master",
                    tool="finish_audit_run",
                    input_value={"run_id": audit.run_id, "status": audit.status},
                    output_value={"status": "completed"},
                    config=audit.approved_run_config,
                )
            ],
        }

    builder = StateGraph(AgenticGraphState)
    builder.add_node("validate", validate_inputs)
    builder.add_node("approval", request_approval)
    builder.add_node("start_analysis", start_analysis)
    builder.add_node("anomaly", anomaly_agent)
    builder.add_node("fairness", fairness_agent)
    builder.add_node("mapping", compliance_agent)
    builder.add_node("report", report_agent)
    builder.add_node("complete", finish_run)

    builder.add_edge(START, "validate")
    builder.add_edge("validate", "approval")
    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {"approved": "start_analysis", "rejected": END},
    )
    builder.add_edge("start_analysis", "anomaly")
    builder.add_edge("start_analysis", "fairness")
    builder.add_edge(["anomaly", "fairness"], "mapping")
    builder.add_edge("mapping", "report")
    builder.add_edge("report", "complete")
    builder.add_edge("complete", END)

    return builder.compile(checkpointer=checkpointer or InMemorySaver())


def make_initial_audit_state(
    records: list[dict[str, Any]],
    run_config: RunConfig,
    *,
    run_id: str | None = None,
) -> AuditState:
    """Build the validated input state for one audit graph invocation."""
    return AuditState(
        run_id=run_id or str(__import__("uuid").uuid4()),
        input_mode=run_config.input_mode,
        records=records,
        proposed_run_config=run_config,
    )