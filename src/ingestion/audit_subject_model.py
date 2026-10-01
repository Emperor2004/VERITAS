"""
Trains a stand-in classifier to simulate the "hypothetical bank's
income-prediction model" that VERITAS audits. This is NOT part of the
audit pipeline itself -- it exists only to produce realistic predictions
and confidence scores for the ingestion module to log, since VERITAS
audits prediction behavior, not model training. UCI Adult Income ships
ground-truth labels only; without this step there is no "prediction"
for the downstream modules to audit.
"""
from __future__ import annotations
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

NUMERIC_COLS = ["age", "education-num", "hours-per-week", "capital-gain", "capital-loss"]
CATEGORICAL_COLS = [
    "workclass", "education", "marital-status", "occupation",
    "relationship", "race", "sex", "native-country",
]


def build_pipeline(random_state: int = 42) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_COLS),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS),
        ]
    )
    return Pipeline(steps=[
        ("preprocess", preprocessor),
        ("clf", LogisticRegression(max_iter=1000, random_state=random_state)),
    ])


def train_audit_subject(
    df: pd.DataFrame,
    target_col: str = "income",
    test_size: float = 0.2,
    random_state: int = 42,
    trainable_mask=None,
):
    """Trains the stand-in classifier and returns predictions + confidence
    for the FULL dataset (train and test alike) -- VERITAS audits prediction
    logs, so predictions are needed for every record shipped downstream,
    not just a held-out test split.

    `trainable_mask`: optional boolean array, same length as `df`. Rows
    where it is False are excluded from training (but still get a
    prediction from the fitted model). Required when `df` contains
    deliberately-injected anomaly rows (see feature_anomalies.py) -- without
    this, the model partially learns to treat injected outliers as normal,
    which would make both anomaly-detection and fairness evaluation
    unreliable. Defaults to None (train on everything) to keep this
    function's old behavior for any other caller."""
    X = df[NUMERIC_COLS + CATEGORICAL_COLS]
    y = (df[target_col].astype(str).str.strip().str.rstrip(".") == ">50K").astype(int)

    if trainable_mask is not None:
        X_pool, y_pool = X[trainable_mask], y[trainable_mask]
    else:
        X_pool, y_pool = X, y

    X_train, _, y_train, _ = train_test_split(
        X_pool, y_pool, test_size=test_size, random_state=random_state, stratify=y_pool
    )

    pipeline = build_pipeline(random_state=random_state)
    pipeline.fit(X_train, y_train)

    predicted_label = pipeline.predict(X)
    predicted_proba = pipeline.predict_proba(X)
    confidence = predicted_proba.max(axis=1)

    return predicted_label, confidence, y.values