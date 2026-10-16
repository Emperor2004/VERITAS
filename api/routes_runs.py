"""
Run lifecycle and audit analysis endpoints for VERITAS.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from langgraph.types import Command

from api.jobs import get_run_lock, submit_job
from api.jsonable import to_jsonable
from api.schemas import (
    ApproveRunRequest,
    AskQuestionRequest,
    AskQuestionResponse,
    CreateRunResponse,
    RejectRunRequest,
    RunDetailResponse,
    ValidateResponse,
)
from api.security import get_current_user
from api.settings import MAX_UPLOAD_SIZE_BYTES, MAX_ROWS, MAX_COLUMNS
from api.store import (
    create_run_record,
    delete_run_record,
    get_run_record,
    list_runs,
    update_run_status,
)
from dashboard.services.agentic_runner import create_uploaded_audit_state
from dashboard.services.veritas_runner import build_summary
from dashboard.utils.data_adapter import (
    _canonicalize_column_name,
    _find_column,
    _resolve_feature_columns,
    _resolve_protected_columns,
    normalize_uploaded_dataframe,
    validate_uploaded_dataframe,
)
from src.agentic.agents.qa_agent import AuditQAAgent, ToolNotAllowedError
from src.report_generator.pdf_report import render_pdf_report
from src.run_config import RunConfig

router = APIRouter(prefix="/api", tags=["runs"])

# Module-level graph instance injected during app lifespan
AUDIT_GRAPH = None


def set_audit_graph(graph: Any) -> None:
    global AUDIT_GRAPH
    AUDIT_GRAPH = graph


def _parse_uploaded_file(file: UploadFile) -> pd.DataFrame:
    """Read CSV or XLSX from upload file stream with size and extension validation."""
    filename = (file.filename or "").lower()
    if not (filename.endswith(".csv") or filename.endswith(".xlsx")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a .csv or .xlsx file.",
        )

    content = file.file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse spreadsheet data: {exc}",
        ) from exc

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file contains no rows.",
        )
    if len(df) > MAX_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file has {len(df)} rows, exceeding maximum allowed {MAX_ROWS} rows.",
        )
    if len(df.columns) > MAX_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file has {len(df.columns)} columns, exceeding maximum allowed {MAX_COLUMNS} columns.",
        )

    return df


@router.post("/validate", response_model=ValidateResponse)
def validate_upload_dry_run(file: UploadFile = File(...)):
    """Dry-run validation: inspects columns and profiles roles without persisting."""
    df = _parse_uploaded_file(file)
    errors: List[str] = []
    try:
        validate_uploaded_dataframe(df)
    except Exception as exc:
        errors.append(str(exc))

    detected_roles = {
        "prediction": _find_column(df, ["predicted_label", "prediction", "predicted", "model_prediction", "decision", "output_label"]),
        "actual": _find_column(df, ["true_label", "actual_label", "ground_truth", "label", "target", "actual", "outcome"]),
        "protected_attributes": _resolve_protected_columns(df),
        "feature_columns": _resolve_feature_columns(df),
        "record_id": _find_column(df, ["record_id", "id", "event_id", "row_id", "sample_id"]),
        "timestamp": _find_column(df, ["timestamp", "event_time", "time", "datetime", "created_at"]),
    }

    preview_records = df.head(10).to_dict(orient="records")
    return ValidateResponse(
        valid=len(errors) == 0,
        total_rows=len(df),
        row_count=len(df),
        columns=[str(c) for c in df.columns],
        detected_roles=detected_roles,
        preview_rows=to_jsonable(preview_records),
        errors=errors,
    )


@router.post("/runs", response_model=CreateRunResponse, status_code=status.HTTP_201_CREATED)
def create_run(file: UploadFile = File(...)):
    """
    Upload a prediction log and run the pipeline up to the human approval gate.
    Returns run_id and configuration proposal for human sign-off.
    """
    if AUDIT_GRAPH is None:
        raise HTTPException(status_code=500, detail="Audit graph is not initialized.")

    df = _parse_uploaded_file(file)
    try:
        records = normalize_uploaded_dataframe(df)
        if not records:
            raise ValueError("No valid records generated after normalization.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    audit_state = create_uploaded_audit_state(records)
    graph_config = {"configurable": {"thread_id": audit_state.run_id}}

    # Execute graph up to human approval interrupt
    try:
        paused_state = AUDIT_GRAPH.invoke(
            audit_state.model_dump(mode="python"),
            config=graph_config,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to initialize audit graph: {exc}") from exc

    interrupt_info = paused_state.get("__interrupt__")
    if not interrupt_info:
        raise HTTPException(status_code=500, detail="Audit graph failed to reach the approval gate.")

    payload = interrupt_info[0].value
    proposed_cfg = payload.get("proposed_run_config", {})
    validation_summary = payload.get("validation_summary", {})
    config_proposal = payload.get("config_proposal")

    # Persist initial run snapshot in SQLite
    create_run_record(
        run_id=audit_state.run_id,
        upload_name=file.filename or "uploaded_data.csv",
        status="awaiting_approval",
        row_count=len(records),
        validation_summary=validation_summary,
        proposed_config=proposed_cfg,
        config_proposal=config_proposal,
        current_stage="awaiting_approval",
    )

    return CreateRunResponse(
        run_id=audit_state.run_id,
        status="awaiting_approval",
        upload_name=file.filename or "uploaded_data.csv",
        row_count=len(records),
        validation_summary=validation_summary,
        config_proposal=config_proposal,
        proposed_run_config=proposed_cfg,
    )


@router.get("/runs", response_model=List[Dict[str, Any]])
def get_all_runs(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    """Retrieve historical audit runs."""
    return list_runs(limit=limit, offset=offset)


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run(run_id: str):
    """Poll run details, approval review payload, or executive summary."""
    run = get_run_record(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    summary = None
    if run.get("results"):
        summary = build_summary(run["results"])

    val_sum = run.get("validation_summary") or {}
    roles = val_sum.get("detected_roles") or {}
    candidates = (
        val_sum.get("protected_attributes")
        or roles.get("protected_attributes")
        or (run.get("proposed_config") or {}).get("protected_attributes")
        or []
    )
    review = {
        "run_id": run["run_id"],
        "row_count": run["row_count"],
        "column_names": val_sum.get("columns", []),
        "detected_protected_candidates": candidates,
        "proposed_config": run.get("proposed_config") or {},
        "rationale": run.get("config_proposal") or {},
        "config_fingerprint": run.get("config_fingerprint"),
    }

    return RunDetailResponse(
        run_id=run["run_id"],
        upload_name=run["upload_name"],
        status=run["status"],
        current_stage=run.get("current_stage"),
        row_count=run["row_count"],
        config_fingerprint=run.get("config_fingerprint"),
        approved_by=run.get("approved_by"),
        created_at=run["created_at"],
        updated_at=run["updated_at"],
        validation_summary=val_sum,
        config_proposal=run.get("config_proposal"),
        proposed_config=run.get("proposed_config"),
        approved_config=run.get("approved_config"),
        summary=summary,
        error_message=run.get("error_message"),
        review=review,
    )


def _execute_approved_run(run_id: str, approved_config_dict: Dict[str, Any], approver: str, fingerprint: str) -> None:
    """Worker task: executes analysis, mapping, and report generation."""
    lock = get_run_lock(run_id)
    if not lock.acquire(blocking=False):
        return

    try:
        update_run_status(run_id=run_id, status="running", current_stage="fairness_and_anomalies")
        graph_config = {"configurable": {"thread_id": run_id}}

        completed_state = AUDIT_GRAPH.invoke(
            Command(resume={
                "approved": True,
                "approved_by": approver,
                "approved_run_config": approved_config_dict,
            }),
            config=graph_config,
        )

        results = {
            "anomaly": completed_state.get("anomaly_output"),
            "fairness": completed_state.get("fairness_output"),
            "mapped_findings": completed_state.get("mapped_findings"),
            "report_html": completed_state.get("report_html"),
            "anomaly_groups": completed_state.get("anomaly_groups", []),
            "effective_run_config": approved_config_dict,
        }

        update_run_status(
            run_id=run_id,
            status="completed",
            current_stage="completed",
            approved_by=approver,
            config_fingerprint=fingerprint,
            approved_config=approved_config_dict,
            results=results,
        )
    except Exception as exc:
        update_run_status(
            run_id=run_id,
            status="failed",
            current_stage="failed",
            error_message=str(exc),
        )
    finally:
        lock.release()


@router.post("/runs/{run_id}/approve", status_code=status.HTTP_202_ACCEPTED)
def approve_run(
    run_id: str,
    payload: ApproveRunRequest,
    current_user: str = Depends(get_current_user),
):
    """
    Approve configuration and resume the audit pipeline in a background worker.
    Returns 202 Accepted immediately; frontend polls /api/runs/{id}.
    """
    run = get_run_record(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run["status"] != "awaiting_approval":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve run with status '{run['status']}'. Run must be awaiting_approval.",
        )

    proposed_dict = run.get("proposed_config") or {}
    config_dict = dict(proposed_dict)
    payload_dict = payload.model_dump(exclude_none=True)
    if "min_group_size" in payload_dict:
        mgs = payload_dict.pop("min_group_size")
        if "min_group_size_warning" not in payload_dict:
            payload_dict["min_group_size_warning"] = mgs
    config_dict.update(payload_dict)

    try:
        validated_config = RunConfig.model_validate(config_dict)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid configuration parameters: {exc}") from exc

    # Compute short SHA-256 fingerprint of approved configuration
    canonical_cfg = json.dumps(validated_config.to_effective_dict(), sort_keys=True)
    fingerprint = hashlib.sha256(canonical_cfg.encode("utf-8")).hexdigest()[:8]

    update_run_status(
        run_id=run_id,
        status="running",
        current_stage="queued",
        approved_by=current_user,
        config_fingerprint=fingerprint,
        approved_config=validated_config.model_dump(mode="json"),
    )

    submit_job(
        _execute_approved_run,
        run_id=run_id,
        approved_config_dict=validated_config.model_dump(mode="json"),
        approver=current_user,
        fingerprint=fingerprint,
    )

    return {"message": "Audit approved and processing started.", "run_id": run_id, "config_fingerprint": fingerprint}


@router.post("/runs/{run_id}/reject", status_code=status.HTTP_200_OK)
def reject_run(
    run_id: str,
    payload: RejectRunRequest,
    current_user: str = Depends(get_current_user),
):
    """Reject run before any analytics execute."""
    run = get_run_record(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run["status"] != "awaiting_approval":
        raise HTTPException(status_code=409, detail="Can only reject runs that are awaiting_approval.")

    graph_config = {"configurable": {"thread_id": run_id}}
    try:
        AUDIT_GRAPH.invoke(
            Command(resume={"approved": False, "approved_by": current_user, "note": payload.note}),
            config=graph_config,
        )
    except Exception:
        pass

    update_run_status(
        run_id=run_id,
        status="rejected",
        current_stage="rejected",
        approved_by=current_user,
        error_message=payload.note,
    )
    return {"message": "Run rejected successfully.", "run_id": run_id}


@router.get("/runs/{run_id}/anomalies")
def get_anomalies(run_id: str, page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=500)):
    """Paginated anomaly detection findings."""
    run = get_run_record(run_id)
    if not run or not run.get("results"):
        raise HTTPException(status_code=404, detail="Results not found for this run.")

    findings = run["results"].get("anomaly", {}).get("findings", [])
    start = (page - 1) * size
    end = start + size
    return {
        "total": len(findings),
        "page": page,
        "size": size,
        "items": findings[start:end],
    }


@router.get("/runs/{run_id}/fairness")
def get_fairness_findings(run_id: str):
    """Fairness scanner findings."""
    run = get_run_record(run_id)
    if not run or not run.get("results"):
        raise HTTPException(status_code=404, detail="Results not found for this run.")
    return run["results"].get("fairness", {})


@router.get("/runs/{run_id}/findings")
def get_mapped_findings(run_id: str, severity_tier: Optional[str] = Query(None)):
    """NIST-mapped findings with optional severity_tier filter (violation | informational)."""
    run = get_run_record(run_id)
    if not run or not run.get("results"):
        raise HTTPException(status_code=404, detail="Results not found for this run.")

    findings = run["results"].get("mapped_findings", [])
    if severity_tier:
        findings = [f for f in findings if f.get("severity_tier") == severity_tier]
    return findings


@router.get("/runs/{run_id}/anomaly-clusters")
def get_anomaly_clusters(run_id: str):
    """Agent-2 outlier feature clusters and statistics."""
    run = get_run_record(run_id)
    if not run or not run.get("results"):
        raise HTTPException(status_code=404, detail="Results not found for this run.")
    return run["results"].get("anomaly_groups", [])


@router.post("/runs/{run_id}/ask", response_model=AskQuestionResponse)
def ask_question(run_id: str, payload: AskQuestionRequest):
    """Agent-6 conversational Q&A over audit results with citation guarantees."""
    run = get_run_record(run_id)
    if not run or not run.get("results"):
        raise HTTPException(status_code=404, detail="Results not available for interrogation.")

    agent = AuditQAAgent(llm_client=None)
    try:
        answer = agent.answer(payload.question, {
            "run_id": run_id,
            "status": run["status"],
            "mapped_findings": run["results"].get("mapped_findings", []),
            "anomaly_groups": run["results"].get("anomaly_groups", []),
        })
        import re
        citations = re.findall(r'(?:GOVERN|MAP|MEASURE|MANAGE|NIST)[-\.\w]+', answer)
        return AskQuestionResponse(answer=answer, run_id=run_id, citations=sorted(set(citations)))
    except ToolNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/runs/{run_id}/report.html")
def get_report_html(run_id: str):
    """Serve standalone HTML audit report with strict sandboxing headers."""
    run = get_run_record(run_id)
    if not run or not run.get("results"):
        raise HTTPException(status_code=404, detail="Report not found.")

    html = run["results"].get("report_html", "<html><body>No report generated</body></html>")
    return HTMLResponse(
        content=html,
        headers={
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:;",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
        },
    )


@router.get("/runs/{run_id}/report.pdf")
def get_report_pdf(run_id: str):
    """Generate and stream PDF report on demand."""
    run = get_run_record(run_id)
    if not run or not run.get("results"):
        raise HTTPException(status_code=404, detail="Results not found.")

    mapped_findings = run["results"].get("mapped_findings", [])
    pdf_bytes = render_pdf_report(mapped_findings)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=veritas_audit_{run_id[:8]}.pdf"},
    )


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: str):
    """Purge run and associated findings from the store."""
    if not delete_run_record(run_id):
        raise HTTPException(status_code=404, detail="Run not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
