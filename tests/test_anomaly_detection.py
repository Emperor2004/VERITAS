"""
Phase 2 (anomaly_detection) test suite.

Written against the actual modules (isolation_forest.py,
threshold_selection.py, output_schema.py) after reading their source.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from src.anomaly_detection.isolation_forest import (
    build_feature_matrix,
    run_detection,
    evaluate_against_ground_truth,
)
from src.anomaly_detection.threshold_selection import (
    select_threshold_knee,
    select_threshold_grid_search,
)
from src.anomaly_detection.output_schema import validate_output


# ---- label leakage guard (isolation_forest.py) --------------------------------

def test_build_feature_matrix_raises_on_leaked_ground_truth_field():
    records = [{"features": {"age": 0.1, "ground_truth_operational_anomaly": True}}]
    with pytest.raises(ValueError, match="Label leakage"):
        build_feature_matrix(records)


def test_build_feature_matrix_raises_on_leaked_true_label_field():
    records = [{"features": {"age": 0.1, "true_label": 1}}]
    with pytest.raises(ValueError, match="Label leakage"):
        build_feature_matrix(records)


def test_build_feature_matrix_passes_clean_records():
    records = [{"features": {"age": 0.1, "hours-per-week": -0.3}}]
    df = build_feature_matrix(records)
    assert list(df.columns) == ["age", "hours-per-week"]


# ---- threshold_selection.py -----------------------------------------------------

def test_select_threshold_knee_returns_cutoff_within_score_range():
    scores = np.concatenate([np.random.normal(0, 0.1, 950), np.random.normal(2, 0.1, 50)])
    result = select_threshold_knee(scores)
    assert scores.min() <= result["cutoff_score"] <= scores.max()
    assert 0 < result["contamination"] < 1
    assert result["n_flagged"] == int(round(result["contamination"] * len(scores)))


def test_select_threshold_knee_is_deterministic_given_same_scores():
    scores = np.concatenate([np.random.default_rng(1).normal(0, 0.1, 950),
                              np.random.default_rng(1).normal(2, 0.1, 50)])
    r1 = select_threshold_knee(scores)
    r2 = select_threshold_knee(scores)
    assert r1 == r2  # no hidden randomness in the knee method itself


def test_select_threshold_grid_search_recovers_a_clean_separation():
    # Construct scores where the top 5% are unambiguously the true anomalies --
    # grid search should land near contamination=0.05 with a high F1.
    n = 1000
    scores = np.zeros(n)
    ground_truth = np.zeros(n, dtype=bool)
    scores[:50] = np.random.default_rng(2).normal(5, 0.01, 50)   # clearly anomalous
    ground_truth[:50] = True
    scores[50:] = np.random.default_rng(3).normal(0, 0.01, 950)  # clearly normal

    result = select_threshold_grid_search(scores, ground_truth)
    assert abs(result["contamination"] - 0.05) <= 0.005
    assert result["f1"] > 0.95


def test_select_threshold_grid_search_warning_present():
    scores = np.random.default_rng(4).normal(0, 1, 200)
    ground_truth = np.zeros(200, dtype=bool)
    ground_truth[:10] = True
    result = select_threshold_grid_search(scores, ground_truth)
    assert "warning" in result
    assert "not a production threshold" in result["warning"] or "validation check" in result["warning"]


# ---- run_detection (contamination override path) -------------------------------

def test_run_detection_manual_override_flags_expected_count():
    records = [{"features": {"age": float(i)}} for i in range(200)]
    X, scores, is_anomaly, report = run_detection(
        records, random_state=42, n_estimators=50, contamination_override=0.1
    )
    assert is_anomaly.sum() == 20  # 10% of 200
    assert report["method"] == "manual_override"


# ---- evaluate_against_ground_truth ------------------------------------------------

def test_evaluate_against_ground_truth_computes_correct_precision_recall():
    records = [
        {"ground_truth_operational_anomaly": True},   # true positive if flagged
        {"ground_truth_operational_anomaly": True},   # false negative (not flagged)
        {"ground_truth_operational_anomaly": False},  # false positive (flagged)
        {"ground_truth_operational_anomaly": False},  # true negative
    ]
    is_anomaly = np.array([True, False, True, False])
    result = evaluate_against_ground_truth(records, is_anomaly)
    assert result["precision"] == 0.5   # 1 TP / (1 TP + 1 FP)
    assert result["recall"] == 0.5      # 1 TP / (1 TP + 1 FN)
    assert result["n_ground_truth_anomalies"] == 2
    assert result["n_flagged"] == 2


def test_evaluate_against_ground_truth_returns_none_without_labels():
    records = [{"ground_truth_operational_anomaly": None}]
    result = evaluate_against_ground_truth(records, np.array([False]))
    assert result is None


# ---- output_schema.py -----------------------------------------------------------

def _valid_output():
    return {
        "findings": [{
            "record_id": "SESS-0000001", "anomaly_score": 0.42, "is_anomaly": True,
            "top_contributing_features": [{"feature": "age", "z_score": 2.1}],
        }],
        "evaluation": None,
        "threshold_selection": {"method": "knee"},
        "config": {"n_estimators": 100, "random_state": 42, "manual_contamination_override": None},
    }


def test_validate_output_accepts_well_formed_output():
    validate_output(_valid_output())  # should not raise


def test_validate_output_rejects_missing_required_field():
    bad = _valid_output()
    del bad["findings"][0]["anomaly_score"]
    with pytest.raises(ValidationError):
        validate_output(bad)