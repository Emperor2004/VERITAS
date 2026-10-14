from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
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


def _normalize_timestamp(value: Any) -> str:
    if pd.isna(value):
        return datetime.utcnow().isoformat(timespec="seconds")
    try:
        ts = pd.to_datetime(value)
        return ts.isoformat(timespec="seconds")
    except Exception:
        return datetime.utcnow().isoformat(timespec="seconds")


def _build_feature_dict(row: pd.Series, feature_columns: List[str]) -> Dict[str, float]:
    features: Dict[str, float] = {}
    for col in feature_columns:
        if col in row.index:
            features[col] = _safe_float(row[col])
    if not features:
        # fallback: use all non-label, non-protected fields
        for col in row.index:
            if col.lower() in {"record_id", "timestamp", "session_id", "auth_method", "prediction_confidence", "predicted_label", "true_label", "actual_label", "label", "target", "gender", "sex", "race", "group"}:
                continue
            features[col] = _safe_float(row[col])
    return features


def _extract_protected_attributes(row: pd.Series) -> Dict[str, str]:
    candidates = [
        "sex", "gender", "race", "demographic_group", "group", "region",
        "age_group", "department", "country", "protected_group",
    ]
    protected: Dict[str, str] = {}
    for name in candidates:
        col = _find_column(row.to_frame().T, [name])
        if col is not None:
            protected[name] = str(row[col]).strip() if not pd.isna(row[col]) else "unknown"
    if not protected:
        for col in row.index:
            lower = col.lower()
            if lower in {"record_id", "timestamp", "session_id", "auth_method", "prediction_confidence", "predicted_label", "true_label", "actual_label", "output", "probability", "score", "label", "target"}:
                continue
            if row[col].dtype == object or row[col].nunique() <= min(10, len(row)):
                protected[col] = str(row[col]).strip() if not pd.isna(row[col]) else "unknown"
                if len(protected) >= 2:
                    break
    return protected or {"group": "unknown"}


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

    records: List[Dict[str, Any]] = []
    record_id_col = _find_column(df, ["record_id", "id", "event_id", "row_id", "sample_id"])
    timestamp_col = _find_column(df, ["timestamp", "event_time", "time", "datetime", "created_at"])
    session_col = _find_column(df, ["session_id", "session", "request_id"])
    auth_col = _find_column(df, ["auth_method", "authentication_method", "login_method", "auth_type"])
    predicted_label_col = _find_column(df, ["predicted_label", "prediction", "predicted", "model_prediction", "decision", "output_label"])
    confidence_col = _find_column(df, ["prediction_confidence", "confidence", "score", "probability", "predicted_probability"])
    true_label_col = _find_column(df, ["true_label", "actual_label", "ground_truth", "label", "target", "actual", "outcome"])

    for index, row in df.iterrows():
        feature_columns = []
        feature_exclusions = {
            "record_id", "id", "event_id", "row_id", "sample_id",
            "timestamp", "event_time", "time", "datetime", "created_at",
            "session_id", "session", "request_id",
            "auth_method", "authentication_method", "login_method", "auth_type",
            "predicted_label", "prediction", "predicted", "model_prediction", "decision", "output_label",
            "prediction_confidence", "confidence", "score", "probability", "predicted_probability",
            "true_label", "actual_label", "ground_truth", "label", "target", "actual", "outcome",
            "sex", "gender", "race", "demographic_group", "group", "region", "age_group", "country", "protected_group",
        }
        for col in df.columns:
            lower = str(col).lower()
            if lower in feature_exclusions:
                continue
            try:
                sampled = pd.to_numeric(df[col], errors="coerce")
                if sampled.notna().any():
                    feature_columns.append(col)
            except Exception:
                pass

        if not feature_columns:
            feature_columns = [c for c in df.columns if c not in {record_id_col, timestamp_col, session_col, auth_col, predicted_label_col, confidence_col, true_label_col}]

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

        protected = _extract_protected_attributes(row)

        normalized_record = {
            "record_id": str(row[record_id_col]) if record_id_col else f"UPLOAD-{index:06d}",
            "timestamp": _normalize_timestamp(row[timestamp_col]) if timestamp_col else datetime.utcnow().isoformat(timespec="seconds"),
            "session_id": str(row[session_col]) if session_col else str(uuid.uuid4()),
            "auth_method": str(row[auth_col]).strip() if auth_col and not pd.isna(row[auth_col]) else "password",
            "features": _build_feature_dict(row, feature_columns),
            "protected_attributes": protected,
            "predicted_label": int(predicted_label),
            "prediction_confidence": float(prediction_confidence),
            "true_label": int(true_label),
            "ground_truth_operational_anomaly": False,
            "ground_truth_anomaly_type": None,
        }

        if "prediction_confidence" not in normalized_record["features"]:
            normalized_record["features"]["prediction_confidence"] = float(prediction_confidence)
        if "predicted_label" not in normalized_record["features"]:
            normalized_record["features"]["predicted_label"] = float(predicted_label)

        records.append(normalized_record)

    return records
