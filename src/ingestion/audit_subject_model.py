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
):
    """Trains the stand-in classifier and returns predictions + confidence
    for the FULL dataset (train and test alike) -- VERITAS audits prediction
    logs, so predictions are needed for every record shipped downstream,
    not just a held-out test split."""
    X = df[NUMERIC_COLS + CATEGORICAL_COLS]
    y = (df[target_col].astype(str).str.strip().str.rstrip(".") == ">50K").astype(int)

    X_train, _, y_train, _ = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    pipeline = build_pipeline(random_state=random_state)
    pipeline.fit(X_train, y_train)

    predicted_label = pipeline.predict(X)
    predicted_proba = pipeline.predict_proba(X)
    confidence = predicted_proba.max(axis=1)

    return predicted_label, confidence, y.values