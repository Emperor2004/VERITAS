from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

import pandas as pd


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_binary_label(value: Any, *, field_name: str) -> int:
    if pd.isna(value):
        raise ValueError(f"{field_name} contains missing values; binary labels must be 0/1 or true/false.")

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if number in {0.0, 1.0}:
            return int(number)
        raise ValueError(f"{field_name} must be binary (0/1 or true/false), but received {value!r}.")

    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"0", "1", "false", "true", "no", "yes", "n", "y", "negative", "positive"}:
            return 0 if cleaned in {"0", "false", "no", "n", "negative"} else 1
        if cleaned in {"0.0", "1.0"}:
            return int(float(cleaned))

    raise ValueError(f"{field_name} must be binary (0/1 or true/false), but received {value!r}.")


def _canonicalize_column_name(name: Any) -> str:
    normalized = str(name).strip().lower()
    normalized = re.sub(r"[\s\-]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def _normalize_uploaded_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    df = df.copy()
    df.columns = [_canonicalize_column_name(col) for col in df.columns]
    return df


def _find_column(df: pd.DataFrame, candidate_names: Iterable[str]) -> str | None:
    lowered = {_canonicalize_column_name(c): c for c in df.columns}
    for name in candidate_names:
        normalized_name = _canonicalize_column_name(name)
        if normalized_name in lowered:
            return lowered[normalized_name]
    return None


def validate_uploaded_dataframe(df: pd.DataFrame) -> None:
    """Reject malformed uploads before the analytics pipeline starts."""
    df = _normalize_uploaded_columns(df)
    if df is None or df.empty:
        raise ValueError("Uploaded file is empty. Please provide a non-empty CSV or XLSX file.")

    if len(df.columns) < 4:
        raise ValueError(
            "Uploaded file has too few columns to run an AI audit. "
            "Please include prediction-related fields and at least a few measurable attributes."
        )

    required_signal = [
        "predicted_label", "prediction", "predicted", "decision", "output_label", "model_prediction",
    ]
    required_truth = [
        "true_label", "actual_label", "ground_truth", "label", "target", "actual", "outcome",
    ]

    prediction_col = _find_column(df, required_signal)
    truth_col = _find_column(df, required_truth)
    has_prediction_signal = prediction_col is not None
    has_truth_signal = truth_col is not None

    if not has_prediction_signal:
        raise ValueError(
            "Missing prediction column. Please include a column like predicted_label, prediction, decision, or output_label."
        )

    if not has_truth_signal:
        raise ValueError(
            "Missing outcome/ground-truth column. Please include a true_label, actual, or target column for fairness evaluation."
        )

    try:
        for col in [prediction_col, truth_col]:
            if col is not None:
                _ = pd.Series(df[col]).map(lambda v: _coerce_binary_label(v, field_name=col))
    except ValueError as exc:
        raise ValueError(
            f"Binary classification columns must use 0/1 or true/false values; {exc}"
        ) from exc

    protected_candidates = [
        "sex", "gender", "race", "demographic_group", "group", "region", "protected_group", "segment",
    ]
    if _find_column(df, protected_candidates) is None:
        raise ValueError(
            "Missing protected-attribute column. Please include a demographic field such as sex, gender, race, or group."
        )

    numeric_feature_count = 0
    excluded_columns = {
        "record_id", "id", "event_id", "row_id", "sample_id",
        "timestamp", "event_time", "time", "datetime", "created_at",
        "session_id", "session", "request_id",
        "auth_method", "authentication_method", "login_method", "auth_type",
        "predicted_label", "prediction", "predicted", "model_prediction", "decision", "output_label",
        "prediction_confidence", "confidence", "score", "probability", "predicted_probability",
        "true_label", "actual_label", "ground_truth", "label", "target", "actual", "outcome",
        "sex", "gender", "race", "demographic_group", "group", "region", "protected_group", "segment",
    }
    for col in df.columns:
        if str(col).lower() in excluded_columns:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric.notna().sum() > 0:
            numeric_feature_count += 1

    if numeric_feature_count == 0:
        raise ValueError(
            "No usable numeric feature columns detected. Please upload a dataset with measurable features such as age, score, hours, income, or similar numeric fields."
        )


def is_already_normalized(df: pd.DataFrame) -> bool:
    return {"record_id", "timestamp", "features", "protected_attributes"}.issubset(set(df.columns))


PROTECTED_CANDIDATES = [
    "sex", "gender", "race", "ethnicity", "demographic_group", "group", "region",
    "age_group", "department", "country", "protected_group", "segment", "marital_status",
]

EXCLUDED_FEATURE_COLUMNS = {
    "record_id", "id", "event_id", "row_id", "sample_id",
    "timestamp", "event_time", "time", "datetime", "created_at",
    "session_id", "session", "request_id",
    "auth_method", "authentication_method", "login_method", "auth_type",
    "predicted_label", "prediction", "predicted", "model_prediction", "decision", "output_label",
    "prediction_confidence", "confidence", "score", "probability", "predicted_probability",
    "true_label", "actual_label", "ground_truth", "label", "target", "actual", "outcome",
    "sex", "gender", "race", "ethnicity", "demographic_group", "group", "region",
    "age_group", "department", "country", "protected_group", "segment", "marital_status",
}


def _normalize_timestamp(value: Any, default_iso: str) -> str:
    if pd.isna(value):
        return default_iso
    try:
        ts = pd.to_datetime(value)
        return ts.isoformat(timespec="seconds")
    except Exception:
        return default_iso


def _resolve_feature_columns(df: pd.DataFrame) -> List[str]:
    feature_cols: List[str] = []
    for col in df.columns:
        if str(col).lower() in EXCLUDED_FEATURE_COLUMNS:
            continue
        try:
            numeric = pd.to_numeric(df[col], errors="coerce")
            if numeric.notna().any():
                feature_cols.append(str(col))
        except Exception:
            pass
    return feature_cols


def _resolve_protected_columns(df: pd.DataFrame) -> List[str]:
    found_cols: List[str] = []
    for candidate in PROTECTED_CANDIDATES:
        col = _find_column(df, [candidate])
        if col is not None and col not in found_cols:
            found_cols.append(col)
    if not found_cols:
        for col in df.columns:
            if str(col).lower() in EXCLUDED_FEATURE_COLUMNS:
                continue
            if df[col].dtype == object or df[col].nunique() <= min(10, len(df)):
                found_cols.append(str(col))
                if len(found_cols) >= 2:
                    break
    return found_cols


def normalize_uploaded_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    df = _normalize_uploaded_columns(df)
    validate_uploaded_dataframe(df)

    if is_already_normalized(df):
        normalized = []
        for _, row in df.iterrows():
            record = dict(row)
            if not isinstance(record.get("features"), dict):
                record["features"] = json.loads(str(record["features"])) if isinstance(record["features"], str) else {}
            if not isinstance(record.get("protected_attributes"), dict):
                record["protected_attributes"] = json.loads(str(record["protected_attributes"])) if isinstance(record["protected_attributes"], str) else {}
            normalized.append(record)
        return normalized

    # Resolve columns once upfront
    record_id_col = _find_column(df, ["record_id", "id", "event_id", "row_id", "sample_id"])
    timestamp_col = _find_column(df, ["timestamp", "event_time", "time", "datetime", "created_at"])
    session_col = _find_column(df, ["session_id", "session", "request_id"])
    auth_col = _find_column(df, ["auth_method", "authentication_method", "login_method", "auth_type"])
    predicted_label_col = _find_column(df, ["predicted_label", "prediction", "predicted", "model_prediction", "decision", "output_label"])
    confidence_col = _find_column(df, ["prediction_confidence", "confidence", "score", "probability", "predicted_probability"])
    true_label_col = _find_column(df, ["true_label", "actual_label", "ground_truth", "label", "target", "actual", "outcome"])

    feature_columns = _resolve_feature_columns(df)
    if not feature_columns:
        feature_columns = [
            c for c in df.columns
            if c not in {record_id_col, timestamp_col, session_col, auth_col, predicted_label_col, confidence_col, true_label_col}
        ]

    protected_columns = _resolve_protected_columns(df)
    upload_now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    records: List[Dict[str, Any]] = []
    for index, row in df.iterrows():
        predicted_value = row[predicted_label_col] if predicted_label_col else None
        if predicted_value is None:
            if confidence_col and confidence_col in df.columns:
                predicted_value = 1 if _safe_float(row[confidence_col]) >= 0.5 else 0
            else:
                predicted_value = 0

        predicted_label = _coerce_binary_label(predicted_value, field_name="prediction")

        confidence_value = row[confidence_col] if confidence_col else None
        prediction_confidence = _safe_float(confidence_value, 0.5)
        if not 0.0 <= prediction_confidence <= 1.0:
            prediction_confidence = 0.5

        true_label_value = row[true_label_col] if true_label_col else predicted_label
        true_label = _coerce_binary_label(true_label_value, field_name="ground_truth")

        protected: Dict[str, str] = {}
        for pcol in protected_columns:
            val = row[pcol]
            protected[pcol] = str(val).strip() if not pd.isna(val) else "unknown"
        if not protected:
            protected = {"group": "unknown"}

        features: Dict[str, float] = {}
        for fcol in feature_columns:
            features[fcol] = _safe_float(row[fcol])
        if "prediction_confidence" not in features:
            features["prediction_confidence"] = float(prediction_confidence)
        if "predicted_label" not in features:
            features["predicted_label"] = float(predicted_label)

        normalized_record = {
            "record_id": str(row[record_id_col]) if record_id_col else f"UPLOAD-{index:06d}",
            "timestamp": _normalize_timestamp(row[timestamp_col], upload_now_iso) if timestamp_col else upload_now_iso,
            "session_id": str(row[session_col]) if session_col else str(uuid.uuid4()),
            "auth_method": str(row[auth_col]).strip() if auth_col and not pd.isna(row[auth_col]) else "password",
            "features": features,
            "protected_attributes": protected,
            "predicted_label": int(predicted_label),
            "prediction_confidence": float(prediction_confidence),
            "true_label": int(true_label),
            "ground_truth_operational_anomaly": False,
            "ground_truth_anomaly_type": None,
        }
        records.append(normalized_record)

    return records

