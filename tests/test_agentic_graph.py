from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from src.agentic.graph import build_audit_graph, make_initial_audit_state
from src.run_config import RunConfig


def _records():
    return [
        {
            "record_id": f"r{index}",
            "features": {"feature_a": float(index), "predicted_label": float(index % 2)},
            "protected_attributes": {"sex": "A" if index % 2 else "B"},
            "predicted_label": index % 2,
            "true_label": (index // 2) % 2,
            "prediction_confidence": 0.7,
            "ground_truth_operational_anomaly": False,
        }
        for index in range(24)
    ]


def _run_config():
    return RunConfig(
        input_mode="uploaded_predictions",
        protected_attributes=("sex",),
        permutations=4,
        isolation_forest_n_estimators=5,
    )


def _start_run():
    checkpointer = InMemorySaver()
    graph = build_audit_graph(checkpointer)
    initial_state = make_initial_audit_state(_records(), _run_config())
    graph_config = {"configurable": {"thread_id": initial_state.run_id}}
    paused = graph.invoke(initial_state.model_dump(mode="python"), config=graph_config)
    return graph, graph_config, paused


def test_graph_pauses_for_approval_before_analysis_or_mapping():
    _, _, paused = _start_run()

    assert paused["status"] == "awaiting_approval"
    assert len(paused["__interrupt__"]) == 1
    assert paused["anomaly_output"] is None
    assert paused["fairness_output"] is None
    assert paused["mapped_findings"] == []
    assert "records" not in paused["__interrupt__"][0].value


def test_approval_runs_analysis_mapping_report_and_trace():
    graph, config, paused = _start_run()

    completed = graph.invoke(
        Command(resume={"approved": True, "approved_by": "reviewer"}),
        config=config,
    )

    assert paused["status"] == "awaiting_approval"
    assert completed["status"] == "completed"
    assert completed["approval_record"]["approved_by"] == "reviewer"
    assert completed["anomaly_output"] is not None
    assert completed["fairness_output"] is not None
    assert completed["mapped_findings"]
    assert "VERITAS Audit Report" in completed["report_html"]
    assert {event["agent"] for event in completed["trace"]} >= {
        "master", "anomaly", "fairness", "compliance_mapping", "report_generation"
    }
    assert all(len(event["input_hash"]) == 64 for event in completed["trace"])


def test_rejection_stops_before_analysis_and_mapping():
    graph, config, _ = _start_run()

    rejected = graph.invoke(
        Command(resume={"approved": False, "approved_by": "reviewer", "note": "not approved"}),
        config=config,
    )

    assert rejected["status"] == "rejected"
    assert rejected["approval_record"]["note"] == "not approved"
    assert rejected["anomaly_output"] is None
    assert rejected["fairness_output"] is None
    assert rejected["mapped_findings"] == []
    assert rejected["report_html"] is None


def test_approved_run_config_is_the_config_used_by_fairness():
    graph, config, paused = _start_run()
    approved_config = dict(paused["proposed_run_config"])
    approved_config["permutations"] = 7

    completed = graph.invoke(
        Command(resume={
            "approved": True,
            "approved_by": "reviewer",
            "approved_run_config": approved_config,
        }),
        config=config,
    )

    assert completed["approved_run_config"]["permutations"] == 7
    assert completed["fairness_output"]["findings"][0]["permutation_test_config"]["n_permutations"] == 7


def test_approval_rejects_protected_attributes_missing_from_upload():
    graph, config, paused = _start_run()
    approved_config = dict(paused["proposed_run_config"])
    approved_config["protected_attributes"] = ["race"]

    with pytest.raises(ValueError, match="missing from uploaded records"):
        graph.invoke(
            Command(resume={
                "approved": True,
                "approved_by": "reviewer",
                "approved_run_config": approved_config,
            }),
            config=config,
        )