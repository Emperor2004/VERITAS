"""
Stage G: Golden Equivalence Test for VERITAS.

Proves mathematically that running VERITAS in agentic mode (with approved config
matching the deterministic config) produces IDENTICAL numeric outputs, verdicts,
and control IDs to the deterministic pipeline.
"""
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from src.run_config import RunConfig
from src.agentic.graph import build_audit_graph, make_initial_audit_state
from src.pipeline import VeritasPipeline


def _canonical_json_hash(val: Any) -> str:
    canonical = json.dumps(val, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_golden_equivalence_pipeline_vs_agentic():
    # 1. Run deterministic pipeline with a small sample
    config_path = Path("config/config.yaml")
    pipeline = VeritasPipeline.from_config_file(config_path)
    limit = 60
    artifacts = pipeline.run_all(limit=limit, save_artifacts=False)

    det_anomaly_hash = _canonical_json_hash(artifacts.anomaly_output)
    det_fairness_hash = _canonical_json_hash(artifacts.fairness_output)
    det_mapped_hash = _canonical_json_hash(artifacts.mapped_findings)

    # 2. Run agentic graph on the exact same ingested records
    records = artifacts.normalized_logs
    run_config = pipeline.run_config
    checkpointer = InMemorySaver()
    graph = build_audit_graph(checkpointer)
    initial_state = make_initial_audit_state(records, run_config)
    graph_config = {"configurable": {"thread_id": initial_state.run_id}}

    # Step 1: validate_inputs -> awaiting_approval (interrupt)
    res1 = graph.invoke(initial_state.model_dump(mode="python"), config=graph_config)
    assert res1["status"] == "awaiting_approval"

    # Step 2: Resume with human approval
    res_final = graph.invoke(
        Command(resume={"approved": True, "approved_by": "Compliance Lead"}),
        config=graph_config,
    )
    assert res_final["status"] == "completed"

    agt_anomaly_hash = _canonical_json_hash(res_final["anomaly_output"])
    agt_fairness_hash = _canonical_json_hash(res_final["fairness_output"])
    agt_mapped_hash = _canonical_json_hash(res_final["mapped_findings"])

    # PROOF: Identical SHA-256 hashes across deterministic tools
    assert det_anomaly_hash == agt_anomaly_hash, "Anomaly output hash mismatch!"
    assert det_fairness_hash == agt_fairness_hash, "Fairness output hash mismatch!"
    assert det_mapped_hash == agt_mapped_hash, "Mapped findings hash mismatch!"
