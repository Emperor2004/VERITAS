"""
Phase 1 (ingestion) test suite.

Written against the actual modules (schema.py, synthetic_metadata.py,
feature_engineering.py, audit_subject_model.py) after reading their source
-- not against an assumed API.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from src.ingestion.schema import NormalizedLogRecord, validate_records
from src.ingestion.synthetic_metadata import compute_anomaly_mask, generate_metadata
from src.ingestion.feature_engineering import engineer_features
from src.ingestion.audit_subject_model import train_audit_subject


# ---- schema.py --------------------------------------------------------------

def _valid_record_kwargs(**overrides):
    base = dict(
        record_id="SESS-0000001",
        timestamp=datetime(2026, 3, 1, 10, 0, 0),
        session_id="abc-123",
        auth_method="password",
        features={"age": 0.5},
        protected_attributes={"sex": "Female", "race": "White"},
        predicted_label=1,
        prediction_confidence=0.87,
    )
    base.update(overrides)
    return base


def test_valid_record_passes_schema():
    rec = NormalizedLogRecord(**_valid_record_kwargs())
    assert rec.predicted_label == 1


def test_empty_protected_attributes_raises():
    with pytest.raises(ValidationError):
        NormalizedLogRecord(**_valid_record_kwargs(protected_attributes={}))


def test_predicted_label_out_of_range_raises():
    with pytest.raises(ValidationError):
        NormalizedLogRecord(**_valid_record_kwargs(predicted_label=2))


def test_prediction_confidence_out_of_range_raises():
    with pytest.raises(ValidationError):
        NormalizedLogRecord(**_valid_record_kwargs(prediction_confidence=1.5))


def test_true_label_and_ground_truth_are_optional():
    rec = NormalizedLogRecord(**_valid_record_kwargs())
    assert rec.true_label is None
    assert rec.ground_truth_operational_anomaly is None


def test_validate_records_fails_loud_on_first_bad_record_not_silently_dropped():
    good = _valid_record_kwargs()
    bad = _valid_record_kwargs(record_id="SESS-0000002", protected_attributes={})
    with pytest.raises(ValidationError):
        validate_records([good, bad])


# ---- synthetic_metadata.py ----------------------------------------------------

def test_compute_anomaly_mask_is_deterministic_for_same_seed():
    m1 = compute_anomaly_mask(1000, injection_rate=0.03, random_state=7)
    m2 = compute_anomaly_mask(1000, injection_rate=0.03, random_state=7)
    assert np.array_equal(m1, m2)


def test_compute_anomaly_mask_rate_is_approximately_correct():
    n = 20000
    mask = compute_anomaly_mask(n, injection_rate=0.03, random_state=7)
    observed_rate = mask.sum() / n
    assert abs(observed_rate - 0.03) < 0.005  # generous tolerance for a random draw


_METADATA_CONFIG = {
    "session_id_prefix": "SESS",
    "auth_methods": ["password", "sso", "mfa_token", "biometric"],
    "timestamp_start": "2026-01-01T00:00:00",
    "timestamp_end": "2026-06-30T23:59:59",
    "rare_auth_methods": ["legacy_token", "unverified_device"],
    "normal_hour_range": [7, 22],
}


def test_anomaly_flagged_records_use_rare_auth_method_and_off_hours():
    n = 500
    mask = np.zeros(n, dtype=bool)
    mask[:50] = True  # force first 50 to be anomalies, deterministic to inspect
    records = generate_metadata(n, _METADATA_CONFIG, mask, seed=42)

    for r in records[:50]:
        assert r["auth_method"] in _METADATA_CONFIG["rare_auth_methods"]
        hour = datetime.fromisoformat(r["timestamp"]).hour
        assert hour < 7 or hour >= 22

    for r in records[50:]:
        assert r["auth_method"] in _METADATA_CONFIG["auth_methods"]
        hour = datetime.fromisoformat(r["timestamp"]).hour
        assert 7 <= hour < 22


def test_generate_metadata_ground_truth_label_matches_injected_mask():
    n = 100
    mask = compute_anomaly_mask(n, injection_rate=0.1, random_state=1)
    records = generate_metadata(n, _METADATA_CONFIG, mask, seed=1)
    for r, injected in zip(records, mask):
        assert r["ground_truth_operational_anomaly"] == bool(injected)


# ---- feature_engineering.py ---------------------------------------------------

def test_engineer_features_flags_off_hours_and_rare_auth_correctly():
    df = pd.DataFrame({
        "age": [30, 40], "education-num": [10, 12], "hours-per-week": [40, 35],
        "capital-gain": [0, 5000], "capital-loss": [0, 0],
    })
    predicted_label = np.array([0, 1])
    confidence = np.array([0.6, 0.9])
    metadata = [
        {"timestamp": "2026-01-01T03:00:00", "auth_method": "legacy_token"},   # off-hours + rare
        {"timestamp": "2026-01-01T10:00:00", "auth_method": "password"},       # normal
    ]
    feats = engineer_features(
        df, predicted_label, confidence, metadata,
        rare_auth_methods=["legacy_token", "unverified_device"],
        normal_hour_range=(7, 22),
    )
    assert feats.loc[0, "is_off_hours"] == 1
    assert feats.loc[0, "is_rare_auth_method"] == 1
    assert feats.loc[1, "is_off_hours"] == 0
    assert feats.loc[1, "is_rare_auth_method"] == 0


def test_engineer_features_standardizes_numeric_columns_to_zero_mean():
    df = pd.DataFrame({
        "age": [20, 30, 40, 50], "education-num": [8, 9, 10, 11],
        "hours-per-week": [30, 40, 50, 60], "capital-gain": [0, 0, 0, 0],
        "capital-loss": [0, 0, 0, 0],
    })
    metadata = [{"timestamp": "2026-01-01T10:00:00", "auth_method": "password"}] * 4
    feats = engineer_features(
        df, np.zeros(4), np.full(4, 0.5), metadata,
        rare_auth_methods=[], normal_hour_range=(7, 22),
    )
    assert abs(feats["age"].mean()) < 1e-9


def test_engineer_features_zero_std_column_does_not_divide_by_zero():
    df = pd.DataFrame({
        "age": [30, 30, 30], "education-num": [10, 10, 10],
        "hours-per-week": [40, 40, 40], "capital-gain": [0, 0, 0], "capital-loss": [0, 0, 0],
    })
    metadata = [{"timestamp": "2026-01-01T10:00:00", "auth_method": "password"}] * 3
    feats = engineer_features(
        df, np.zeros(3), np.full(3, 0.5), metadata,
        rare_auth_methods=[], normal_hour_range=(7, 22),
    )
    assert not feats["age"].isna().any()  # would be NaN if the zero-std guard were missing


# ---- audit_subject_model.py ---------------------------------------------------

def _tiny_adult_like_df(n=60, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "age": rng.integers(20, 60, n),
        "education-num": rng.integers(5, 16, n),
        "hours-per-week": rng.integers(20, 60, n),
        "capital-gain": rng.integers(0, 5000, n),
        "capital-loss": np.zeros(n),
        "workclass": rng.choice(["Private", "Self-emp"], n),
        "education": rng.choice(["Bachelors", "HS-grad"], n),
        "marital-status": rng.choice(["Married", "Never-married"], n),
        "occupation": rng.choice(["Tech-support", "Sales"], n),
        "relationship": rng.choice(["Husband", "Not-in-family"], n),
        "race": rng.choice(["White", "Black"], n),
        "sex": rng.choice(["Male", "Female"], n),
        "native-country": ["United-States"] * n,
        "income": rng.choice(["<=50K", ">50K"], n),
    })


def test_train_audit_subject_returns_predictions_for_every_row_not_just_test_split():
    df = _tiny_adult_like_df(n=60)
    predicted_label, confidence, true_label = train_audit_subject(df, test_size=0.2, random_state=42)
    assert len(predicted_label) == len(df)  # full dataset, not held-out test split only
    assert len(confidence) == len(df)
    assert len(true_label) == len(df)


def test_train_audit_subject_outputs_are_valid_ranges():
    df = _tiny_adult_like_df(n=60)
    predicted_label, confidence, _ = train_audit_subject(df, test_size=0.2, random_state=42)
    assert set(np.unique(predicted_label)).issubset({0, 1})
    assert (confidence >= 0.5).all()  # max class probability is always >= 0.5 for binary
    assert (confidence <= 1.0).all()