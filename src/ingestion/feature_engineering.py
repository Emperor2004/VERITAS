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

NUMERIC_COLS = ["age", "education-num", "hours-per-week", "capital-gain", "capital-loss"]


def engineer_features(df: pd.DataFrame, predicted_label, confidence) -> pd.DataFrame:
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

    return feats