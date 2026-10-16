from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.run_config import RunConfig


def test_run_config_captures_nested_project_settings():
    config = {
        "protected_attributes": ["sex", "race"],
        "fairness": {
            "disparate_impact_ratio_threshold": 0.78,
            "min_group_size_warning": 24,
            "significance_level": 0.01,
            "permutations": 321,
            "permutation_random_state": 19,
        },
        "anomaly_detection": {
            "isolation_forest": {"random_state": 7, "n_estimators": 31}
        },
    }

    effective = RunConfig.from_project_config(config)

    assert effective.protected_attributes == ("sex", "race")
    assert effective.disparate_impact_ratio_threshold == 0.78
    assert effective.min_group_size_warning == 24
    assert effective.significance_level == 0.01
    assert effective.permutations == 321
    assert effective.permutation_random_state == 19
    assert effective.isolation_forest_random_state == 7
    assert effective.isolation_forest_n_estimators == 31
    assert effective.anomaly_threshold_method == "knee_point"
    assert effective.to_effective_dict()["schema_version"] == 1


def test_run_config_can_scope_uploaded_protected_attributes():
    effective = RunConfig.from_project_config(
        {"protected_attributes": ["sex", "race"]},
        input_mode="uploaded_predictions",
        protected_attributes=["gender"],
    )

    assert effective.input_mode == "uploaded_predictions"
    assert effective.protected_attributes == ("gender",)


def test_run_config_accepts_legacy_flat_anomaly_settings():
    effective = RunConfig.from_project_config(
        {"anomaly_detection": {"random_state": 13, "n_estimators": 17}}
    )

    assert effective.isolation_forest_random_state == 13
    assert effective.isolation_forest_n_estimators == 17


def test_run_config_rejects_invalid_fairness_settings():
    with pytest.raises(ValidationError):
        RunConfig.from_project_config(
            {"fairness": {"significance_level": 1.0}}
        )


def test_fixed_contamination_requires_a_valid_override():
    with pytest.raises(ValidationError):
        RunConfig(anomaly_threshold_method="fixed_contamination")

    with pytest.raises(ValidationError):
        RunConfig(
            anomaly_threshold_method="fixed_contamination",
            contamination_override=1.0,
        )