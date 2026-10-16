import json
import pandas as pd
import pytest
from unittest.mock import MagicMock

from src.agentic.agents.schema_inference import (
    infer_schema,
    infer_schema_deterministic,
    SchemaInferenceResult,
    _extract_column_profiles,
)


@pytest.fixture
def standard_df():
    return pd.DataFrame({
        "record_id": ["R1", "R2", "R3", "R4"],
        "predicted_label": [0, 1, 1, 0],
        "true_label": [0, 1, 0, 0],
        "sex": ["M", "F", "F", "M"],
        "age": [25, 45, 32, 54],
        "income": [50000, 80000, 62000, 48000],
    })


@pytest.fixture
def unseen_df():
    return pd.DataFrame({
        "id_code": ["U1", "U2", "U3", "U4"],
        "sys_approved": [1, 0, 1, 0],
        "target_default": [0, 1, 0, 0],
        "demographic_sex": ["Male", "Female", "Female", "Male"],
        "num_fico_score": [720, 610, 680, 590],
        "num_debt_ratio": [0.25, 0.45, 0.31, 0.52],
    })


def test_deterministic_alias_resolution(standard_df):
    res = infer_schema(standard_df, llm_client=None)
    assert res.source == "deterministic"
    assert res.confidence == 1.0
    assert not res.needs_human_review
    assert res.mapping["prediction"] == "predicted_label"
    assert res.mapping["actual"] == "true_label"
    assert "sex" in res.protected_attributes
    assert "age" in res.feature_columns or "income" in res.feature_columns


def test_privacy_boundary_column_profiles(unseen_df):
    profiles = _extract_column_profiles(unseen_df)
    for p in profiles:
        assert "column_name" in p
        assert "dtype" in p
        assert "cardinality" in p
        assert len(p["samples"]) <= 5
        # Ensure raw full series is not embedded
        assert "series" not in p


def test_unseen_schema_with_mock_llm(unseen_df):
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "prediction": "sys_approved",
        "actual": "target_default",
        "record_id": "id_code",
        "protected_attributes": ["demographic_sex"],
        "feature_columns": ["num_fico_score", "num_debt_ratio"],
        "confidence": 0.95,
        "rationale": {
            "prediction": "sys_approved is the model binary approval decision",
            "actual": "target_default is the loan default outcome",
            "protected": "demographic_sex represents gender",
        }
    })
    mock_llm.invoke.return_value = mock_response

    res = infer_schema(unseen_df, llm_client=mock_llm)
    assert res.source == "llm"
    assert res.mapping["prediction"] == "sys_approved"
    assert res.mapping["actual"] == "target_default"
    assert "demographic_sex" in res.protected_attributes
    assert not res.needs_human_review


def test_unseen_schema_ambiguous_triggers_review(unseen_df):
    # Non-binary column as prediction should trigger human review
    bad_df = unseen_df.copy()
    bad_df["sys_approved"] = [1, 2, 3, 4]  # non-binary

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "prediction": "sys_approved",
        "actual": "target_default",
        "record_id": "id_code",
        "protected_attributes": ["demographic_sex"],
        "feature_columns": ["num_fico_score", "num_debt_ratio"],
        "confidence": 0.95,
    })
    mock_llm.invoke.return_value = mock_response

    res = infer_schema(bad_df, llm_client=mock_llm)
    assert res.needs_human_review


def test_data_integrity_no_mutation(standard_df):
    original_df = standard_df.copy(deep=True)
    infer_schema(standard_df, llm_client=None)
    pd.testing.assert_frame_equal(standard_df, original_df)
