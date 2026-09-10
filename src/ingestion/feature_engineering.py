"""
Builds the `features` dict used by the anomaly detection module.

Deliberately separate from `audit_subject_model.py`: the audit-subject
model's preprocessing simulates what the bank's model does internally,
while THIS preprocessing produces the feature representation VERITAS
itself uses to look for anomalous prediction behavior. Conflating the
two would mean anomaly detection is just re-discovering the audit
subject's own decision boundary instead of examining its behavior.
"""
from __future__ import annotations
import pandas as pd
from datetime import datetime

NUMERIC_COLS = ["age", "education-num", "hours-per-week", "capital-gain", "capital-loss"]


def engineer_features(
    df: pd.DataFrame,
    predicted_label,
    confidence,
    metadata: list,
    rare_auth_methods: list,
    normal_hour_range: tuple,
) -> pd.DataFrame:
    feats = pd.DataFrame(index=df.index)

    # Normalize numeric columns to comparable scale for IsolationForest
    for col in NUMERIC_COLS:
        col_std = df[col].std()
        feats[col] = (df[col] - df[col].mean()) / col_std if col_std > 0 else 0.0

    # Behavioral signal: how confident the model was on this record
    feats["prediction_confidence"] = confidence
    feats["predicted_label"] = predicted_label

    # A cheap but real anomaly-relevant signal: capital-gain/loss extremity
    feats["capital_activity_ratio"] = (
        (df["capital-gain"] - df["capital-loss"])
        / (df["capital-gain"] + df["capital-loss"] + 1)
    )

    # Operational anomaly signals -- meaningful ONLY because anomalies were
    # deliberately injected into the metadata generator with a known rate
    # (see synthetic_metadata.py). Uniform-random categorical/timestamp
    # values would carry no real structure for IsolationForest to use;
    # these binary flags convert the injected pattern into usable signal.
    normal_start, normal_end = normal_hour_range
    is_off_hours = []
    is_rare_auth = []
    for m in metadata:
        hour = datetime.fromisoformat(m["timestamp"]).hour
        is_off_hours.append(0 if normal_start <= hour < normal_end else 1)
        is_rare_auth.append(1 if m["auth_method"] in rare_auth_methods else 0)

    feats["is_off_hours"] = is_off_hours
    feats["is_rare_auth_method"] = is_rare_auth

    return feats