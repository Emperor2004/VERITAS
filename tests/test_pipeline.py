"""
Tests for the VeritasPipeline unified modular API.
"""
from __future__ import annotations

import json
import pytest
import numpy as np

from src.pipeline import VeritasPipeline, PipelineArtifacts


def _mock_pipeline_config():
    return {
        "dataset": {
            "local_cache_csv": "data/raw/adult_income.csv",
            "uci_repo_id": 2,
        },
        "anomaly_detection": {
            "random_state": 42,
            "n_estimators": 10,
        },
        "fairness": {
            "disparate_impact_ratio_threshold": 0.8,
            "min_group_size_warning": 5,
            "significance_level": 0.05,
            "permutations": 10,
            "permutation_random_state": 42,
        },
    }


def test_pipeline_instantiation():
    cfg = _mock_pipeline_config()
    pipeline = VeritasPipeline(config=cfg)
    assert pipeline.config == cfg
    assert pipeline.lookup_table is not None
    assert "controls" in pipeline.lookup_table


def test_pipeline_anomaly_detection_uses_nested_config(monkeypatch):
    config = {
        "anomaly_detection": {
            "isolation_forest": {
                "random_state": 17,
                "n_estimators": 23,
            }
        }
    }
    pipeline = VeritasPipeline(config=config)
    captured = {}

    def fake_run_anomaly_detection(**kwargs):
        captured.update(kwargs)
        return {"findings": []}

    monkeypatch.setattr("src.pipeline.run_anomaly_detection", fake_run_anomaly_detection)

    pipeline.run_anomaly_detection(records=[])

    assert captured["random_state"] == 17
    assert captured["n_estimators"] == 23


def test_pipeline_in_memory_flow():
    cfg = _mock_pipeline_config()
    pipeline = VeritasPipeline(config=cfg)

    # Create synthetic normalized log records for quick testing
    records = []
    for i in range(40):
        records.append({
            "record_id": f"REC-{i:04d}",
            "timestamp": "2026-03-01T10:00:00",
            "session_id": f"sess-{i}",
            "auth_method": "password" if i % 10 != 0 else "legacy_token",
            "features": {
                "age": float(i),
                "is_off_hours": 1 if i % 10 == 0 else 0,
                "is_rare_auth_method": 1 if i % 10 == 0 else 0,
            },
            "protected_attributes": {
                "sex": "Female" if i % 2 == 0 else "Male",
            },
            "predicted_label": 1 if i % 3 == 0 else 0,
            "prediction_confidence": 0.8,
            "true_label": 1 if i % 3 == 0 else 0,
            "ground_truth_operational_anomaly": i % 10 == 0,
        })

    ad_output = pipeline.run_anomaly_detection(records)
    assert "findings" in ad_output
    assert len(ad_output["findings"]) == 40

    fairness_output = pipeline.run_fairness_scan(records)
    assert "findings" in fairness_output

    mapped = pipeline.run_compliance_mapping(ad_output, fairness_output)
    assert isinstance(mapped, list)

    html = pipeline.generate_html_report(mapped)
    assert "VERITAS Audit Report" in html


def test_run_all_generates_template_pdf_when_requested(tmp_path, monkeypatch):
    pipeline = VeritasPipeline(config=_mock_pipeline_config())
    monkeypatch.setattr(pipeline, "run_ingestion", lambda limit=None: [])
    monkeypatch.setattr(pipeline, "run_anomaly_detection", lambda records: {})
    monkeypatch.setattr(pipeline, "run_fairness_scan", lambda records: {})
    monkeypatch.setattr(pipeline, "run_compliance_mapping", lambda anomaly, fairness: [])
    monkeypatch.setattr(pipeline, "generate_html_report", lambda findings: "<html></html>")

    artifacts = pipeline.run_all(save_artifacts=True, output_dir=tmp_path, generate_pdf=True)

    pdf_path = tmp_path / "reports" / "audit_report.pdf"
    config_path = tmp_path / "logs" / "effective_run_config.json"
    assert artifacts.report_pdf_generated is True
    assert pdf_path.read_bytes().startswith(b"%PDF-")
    assert artifacts.effective_run_config["schema_version"] == 1
    assert json.loads(config_path.read_text(encoding="utf-8"))["input_mode"] == "adult_income"
