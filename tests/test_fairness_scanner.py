"""
Phase 3 (fairness_scanner) test suite.

Written against the actual modules (thresholds.py, metrics.py,
output_schema.py) after reading their source.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from src.fairness_scanner.thresholds import (
    evaluate_disparate_impact,
    flag_small_groups,
    permutation_significance_test,
)
from src.fairness_scanner.metrics import build_frame, compute_fairness_metrics_for_attribute
from src.fairness_scanner.output_schema import validate_output


# ---- thresholds.py -----------------------------------------------------------

def test_evaluate_disparate_impact_below_threshold_is_violation():
    assert evaluate_disparate_impact(0.71, threshold=0.8) is True


def test_evaluate_disparate_impact_at_threshold_is_not_violation():
    assert evaluate_disparate_impact(0.8, threshold=0.8) is False  # strict '<', not '<='


def test_evaluate_disparate_impact_above_threshold_is_not_violation():
    assert evaluate_disparate_impact(0.95, threshold=0.8) is False


def test_flag_small_groups_flags_only_groups_below_minimum():
    sizes = {"Male": 500, "Female": 15}
    flagged = flag_small_groups(sizes, min_group_size=20)
    assert flagged == ["Female"]


def test_flag_small_groups_returns_empty_when_all_groups_sufficient():
    sizes = {"Male": 500, "Female": 400}
    assert flag_small_groups(sizes, min_group_size=20) == []


# ---- thresholds.py: permutation_significance_test -----------------------------

def _identity_metric(y_true, y_pred, sensitive_features):
    """A metric that ignores sensitive_features entirely -- shuffling it can
    never change the result, so this isolates 'is the null distribution
    degenerate' behavior from any real fairness computation."""
    return float(np.mean(np.asarray(y_true) == np.asarray(y_pred)))


def test_permutation_test_is_deterministic_for_same_seed():
    y_true = np.array([1, 0, 1, 0, 1, 0, 1, 0] * 10)
    y_pred = np.array([1, 0, 1, 1, 1, 0, 0, 0] * 10)
    sensitive = np.array(["A", "B"] * 40)
    r1 = permutation_significance_test(_identity_metric, y_true, y_pred, sensitive, 0.8, random_state=5)
    r2 = permutation_significance_test(_identity_metric, y_true, y_pred, sensitive, 0.8, random_state=5)
    assert r1 == r2


def test_permutation_test_flags_violation_for_real_disparity():
    # Group A: predictions perfectly match true labels (accuracy 1.0).
    # Group B: predictions are the exact inverse (accuracy 0.0).
    # A metric sensitive to sensitive_features membership (here: per-group
    # accuracy gap) should show this as an extreme, non-null result.
    n = 100
    y_true = np.array([1, 0] * n)
    y_pred_a = np.array([1, 0] * n)   # matches
    y_pred_b = np.array([0, 1] * n)   # inverted
    sensitive = np.array(["A"] * (2 * n) + ["B"] * (2 * n))
    y_true_full = np.concatenate([y_true, y_true])
    y_pred_full = np.concatenate([y_pred_a, y_pred_b])

    def group_gap_metric(y_true, y_pred, sensitive_features):
        df = pd.DataFrame({"y_true": y_true, "y_pred": y_pred, "grp": sensitive_features})
        acc_by_group = df.groupby("grp").apply(lambda g: (g.y_true == g.y_pred).mean())
        return float(acc_by_group.max() - acc_by_group.min())

    observed = group_gap_metric(y_true_full, y_pred_full, sensitive)
    result = permutation_significance_test(
        group_gap_metric, y_true_full, y_pred_full, sensitive, observed,
        n_permutations=200, significance_level=0.05, random_state=1,
    )
    assert observed == pytest.approx(1.0)  # max possible gap: 100% vs 0% accuracy
    assert result["violation"] is True
    assert result["p_value"] < 0.05


def test_permutation_test_does_not_flag_when_sensitive_feature_is_irrelevant():
    rng = np.random.default_rng(9)
    y_true = rng.integers(0, 2, 500)
    y_pred = rng.integers(0, 2, 500)   # unrelated to y_true or any group
    sensitive = rng.choice(["A", "B"], 500)

    def group_gap_metric(y_true, y_pred, sensitive_features):
        df = pd.DataFrame({"y_true": y_true, "y_pred": y_pred, "grp": sensitive_features})
        rate_by_group = df.groupby("grp")["y_pred"].mean()
        return float(rate_by_group.max() - rate_by_group.min())

    observed = group_gap_metric(y_true, y_pred, sensitive)
    result = permutation_significance_test(
        group_gap_metric, y_true, y_pred, sensitive, observed,
        n_permutations=500, significance_level=0.05, random_state=2,
    )
    assert result["violation"] is False


def test_permutation_test_reports_monte_carlo_standard_error():
    y_true = np.array([1, 0] * 50)
    y_pred = np.array([1, 0] * 50)
    sensitive = np.array(["A", "B"] * 50)
    result = permutation_significance_test(
        _identity_metric, y_true, y_pred, sensitive, 0.5,
        n_permutations=100, random_state=3,
    )
    assert "p_value_monte_carlo_se" in result
    assert result["p_value_monte_carlo_se"] >= 0


# ---- metrics.py: build_frame fail-loud contract -------------------------------

def test_build_frame_raises_when_true_label_missing():
    records = [{
        "record_id": "SESS-0000001", "predicted_label": 1, "true_label": None,
        "protected_attributes": {"sex": "Female"},
    }]
    with pytest.raises(ValueError, match="true_label"):
        build_frame(records)


def test_build_frame_builds_expected_columns():
    records = [{
        "record_id": "SESS-0000001", "predicted_label": 1, "true_label": 1,
        "protected_attributes": {"sex": "Female", "race": "White"},
    }]
    df = build_frame(records)
    assert "protected__sex" in df.columns
    assert "protected__race" in df.columns
    assert df.loc[0, "protected__sex"] == "Female"


# ---- metrics.py: manufactured disparity -----------------------------------------

def _manufactured_disparity_df():
    """
    Two groups, deliberately unequal selection rates:
    Group A: 8/10 positive predictions (selection rate 0.8)
    Group B: 2/10 positive predictions (selection rate 0.2)
    disparate_impact_ratio should be min/max = 0.2/0.8 = 0.25 -- a clear violation.
    true_label set equal to predicted_label for every record so equalized_odds
    difference is trivially 0.0 (no prediction errors to create FP/TP rate gaps),
    isolating this test to disparate impact / demographic parity only.
    """
    rows = []
    for i in range(10):
        rows.append({
            "record_id": f"A-{i}", "predicted_label": 1 if i < 8 else 0,
            "true_label": 1 if i < 8 else 0, "protected_attributes": {"sex": "GroupA"},
        })
    for i in range(10):
        rows.append({
            "record_id": f"B-{i}", "predicted_label": 1 if i < 2 else 0,
            "true_label": 1 if i < 2 else 0, "protected_attributes": {"sex": "GroupB"},
        })
    return pd.DataFrame([
        {
            "record_id": r["record_id"],
            "predicted_label": r["predicted_label"],
            "true_label": r["true_label"],
            "protected__sex": r["protected_attributes"]["sex"],
        }
        for r in rows
    ])


def test_compute_fairness_metrics_detects_manufactured_disparate_impact():
    df = _manufactured_disparity_df()
    result = compute_fairness_metrics_for_attribute(
        df, "protected__sex", eeoc_threshold=0.8, min_group_size=20, n_permutations=200
    )
    assert result["disparate_impact_ratio"] == pytest.approx(0.25, abs=0.01)
    assert result["disparate_impact_violation"] is True
    assert result["group_sizes"] == {"GroupA": 10, "GroupB": 10}
    # New fields from the permutation test must be present and internally consistent
    assert "demographic_parity_violation" in result
    assert "demographic_parity_p_value" in result
    assert 0.0 <= result["demographic_parity_p_value"] <= 1.0
    assert result["demographic_parity_violation"] == (result["demographic_parity_p_value"] < 0.05)
    assert result["permutation_test_config"]["n_permutations"] == 200


def test_compute_fairness_metrics_flags_small_group_below_minimum():
    df = _manufactured_disparity_df()
    result = compute_fairness_metrics_for_attribute(
        df, "protected__sex", eeoc_threshold=0.8, min_group_size=20, n_permutations=100
    )
    # both groups are size 10, below min_group_size=20 -- both should be flagged
    assert set(result["small_group_warning"]) == {"GroupA", "GroupB"}


def test_compute_fairness_metrics_equal_selection_rates_is_not_a_violation():
    rows = []
    for group in ("GroupA", "GroupB"):
        for i in range(20):
            rows.append({
                "record_id": f"{group}-{i}", "predicted_label": 1 if i < 10 else 0,
                "true_label": 1 if i < 10 else 0, "protected__sex": group,
            })
    df = pd.DataFrame(rows)
    result = compute_fairness_metrics_for_attribute(
        df, "protected__sex", eeoc_threshold=0.8, min_group_size=20, n_permutations=100
    )
    assert result["disparate_impact_ratio"] == pytest.approx(1.0, abs=0.01)
    assert result["disparate_impact_violation"] is False
    assert result["small_group_warning"] == []  # both groups exactly at min, size 20 not < 20


# ---- output_schema.py -----------------------------------------------------------

def _valid_output():
    return {
        "findings": [{
            "attribute": "sex", "demographic_parity_difference": 0.1,
            "demographic_parity_violation": False, "demographic_parity_p_value": 0.32,
            "disparate_impact_ratio": 0.71, "disparate_impact_violation": True,
            "equalized_odds_difference": 0.05, "equalized_odds_violation": False,
            "equalized_odds_p_value": 0.41,
            "group_selection_rates": {"Male": 0.6, "Female": 0.5},
            "group_sizes": {"Male": 500, "Female": 480},
            "eeoc_four_fifths_threshold": 0.8,
            "small_group_warning": [],
            "permutation_test_config": {"n_permutations": 1000, "significance_level": 0.05, "random_state": 42},
        }],
        "config": {"eeoc_four_fifths_threshold": 0.8, "min_group_size_warning": 20,
                    "protected_attributes_scanned": ["sex"]},
    }


def test_validate_output_accepts_well_formed_output():
    validate_output(_valid_output())  # should not raise


def test_validate_output_rejects_missing_required_field():
    bad = _valid_output()
    del bad["findings"][0]["disparate_impact_ratio"]
    with pytest.raises(ValidationError):
        validate_output(bad)