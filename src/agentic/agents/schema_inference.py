"""
Agent-1: Schema Inference Tool for VERITAS.

Maps unseen tabular columns to VERITAS canonical roles:
  - prediction (required): binary 0/1, bool, or decision output
  - actual (required): ground-truth binary label
  - protected (required): categorical/demographic attributes (e.g. sex, race, age_group)
  - features (required): numeric/continuous features for anomaly detection
  - record_id (optional): unique row identifier
  - timestamp (optional): event timestamp

Privacy boundary (agentic_upgrade.md §2 & §5):
  ONLY column names, dtypes, cardinality counts, and up to 5 sample values
  are sent to the LLM. Raw records or rows are NEVER sent.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import pandas as pd

logger = logging.getLogger(__name__)

# Known aliases for deterministic first-pass matching
ALIAS_TABLE: Dict[str, List[str]] = {
    "prediction": [
        "predicted_label", "prediction", "predicted", "decision",
        "output_label", "model_prediction", "pred", "y_pred", "score_binary"
    ],
    "actual": [
        "true_label", "actual_label", "ground_truth", "label",
        "target", "actual", "outcome", "y_true", "groundtruth"
    ],
    "record_id": [
        "record_id", "id", "row_id", "user_id", "applicant_id", "index"
    ],
    "timestamp": [
        "timestamp", "time", "date", "created_at", "logged_at", "event_time"
    ],
}

KNOWN_PROTECTED_CANDIDATES: Set[str] = {
    "sex", "gender", "race", "ethnicity", "age", "age_group", "marital_status",
    "nationality", "religion", "disability", "veteran_status"
}


@dataclass
class SchemaInferenceResult:
    """Result of schema inference."""
    mapping: Dict[str, str]                 # canonical_role -> column_name
    protected_attributes: List[str]         # list of protected column names
    feature_columns: List[str]              # list of numeric feature column names
    confidence: float                       # mean confidence (0.0 to 1.0)
    needs_human_review: bool                # True when confidence < threshold or ambiguous
    rationale: Dict[str, str]               # explanation per role
    source: str = "deterministic"           # "deterministic" | "llm"


def _canonicalize_col(col: Any) -> str:
    normalized = str(col).strip().lower()
    normalized = re.sub(r"[\s\-]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def _is_binary_column(series: pd.Series) -> bool:
    """Check if series has at most 2 distinct non-null values compatible with binary."""
    dropped = series.dropna()
    if dropped.empty:
        return False
    unique_vals = set(dropped.unique())
    if len(unique_vals) > 2:
        return False
    # Check if values are binary-like
    binary_tokens = {0, 1, 0.0, 1.0, True, False, "0", "1", "true", "false", "yes", "no", "positive", "negative", "y", "n"}
    normalized_vals = {str(v).strip().lower() if isinstance(v, str) else v for v in unique_vals}
    return normalized_vals.issubset(binary_tokens)


def _extract_column_profiles(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Extract privacy-safe summary for each column.
    Never includes raw rows; only metadata and up to 5 unique stringified samples.
    """
    profiles = []
    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        unique_vals = non_null.unique()
        cardinality = int(len(unique_vals))
        
        # Up to 5 sample values stringified safely
        samples = [str(x) for x in unique_vals[:5]]
        
        dtype_str = str(series.dtype)
        is_num = pd.api.types.is_numeric_dtype(series)
        
        profiles.append({
            "column_name": str(col),
            "dtype": dtype_str,
            "is_numeric": bool(is_num),
            "cardinality": cardinality,
            "is_binary": _is_binary_column(series),
            "samples": samples,
        })
    return profiles


def infer_schema_deterministic(df: pd.DataFrame) -> Optional[SchemaInferenceResult]:
    """
    Fast deterministic alias-table lookup.
    Returns SchemaInferenceResult if all required roles are unambiguously identified.
    """
    if df is None or df.empty:
        return None

    col_map = {_canonicalize_col(c): c for c in df.columns}
    mapping: Dict[str, str] = {}
    rationale: Dict[str, str] = {}

    # 1. Match prediction
    for alias in ALIAS_TABLE["prediction"]:
        if alias in col_map:
            actual_col = col_map[alias]
            if _is_binary_column(df[actual_col]):
                mapping["prediction"] = actual_col
                rationale["prediction"] = f"Matched alias '{alias}' with binary distribution."
                break

    # 2. Match actual
    for alias in ALIAS_TABLE["actual"]:
        if alias in col_map:
            actual_col = col_map[alias]
            if actual_col != mapping.get("prediction") and _is_binary_column(df[actual_col]):
                mapping["actual"] = actual_col
                rationale["actual"] = f"Matched alias '{alias}' with binary distribution."
                break

    # 3. Match record_id and timestamp (optional)
    for alias in ALIAS_TABLE["record_id"]:
        if alias in col_map and col_map[alias] not in mapping.values():
            mapping["record_id"] = col_map[alias]
            rationale["record_id"] = f"Matched identifier alias '{alias}'."
            break

    for alias in ALIAS_TABLE["timestamp"]:
        if alias in col_map and col_map[alias] not in mapping.values():
            mapping["timestamp"] = col_map[alias]
            rationale["timestamp"] = f"Matched timestamp alias '{alias}'."
            break

    # 4. Identify protected attributes
    protected_cols: List[str] = []
    for col in df.columns:
        if col in mapping.values():
            continue
        canon = _canonicalize_col(col)
        if canon in KNOWN_PROTECTED_CANDIDATES or any(cand in canon for cand in KNOWN_PROTECTED_CANDIDATES):
            protected_cols.append(str(col))

    # 5. Identify numeric features
    feature_cols: List[str] = []
    for col in df.columns:
        if col in mapping.values() or col in protected_cols:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            feature_cols.append(str(col))

    # If both prediction and actual found, and at least one protected attribute and feature:
    if "prediction" in mapping and "actual" in mapping and protected_cols and feature_cols:
        return SchemaInferenceResult(
            mapping=mapping,
            protected_attributes=protected_cols,
            feature_columns=feature_cols,
            confidence=1.0,
            needs_human_review=False,
            rationale=rationale,
            source="deterministic",
        )

    return None


def infer_schema_llm(
    df: pd.DataFrame,
    llm_client: Any,
) -> SchemaInferenceResult:
    """
    Use LLM to infer schema mapping from column profiles.
    Adheres strictly to the privacy boundary: only metadata is sent.
    """
    profiles = _extract_column_profiles(df)
    
    prompt = (
        "You are an expert AI auditor configuring the VERITAS compliance pipeline.\n"
        "Given the following table column metadata (names, dtypes, cardinality, binary status, and sample values), "
        "identify the canonical roles:\n"
        "1. 'prediction': the model's predicted binary outcome (required, must be binary)\n"
        "2. 'actual': the true/ground-truth binary outcome (required, must be binary)\n"
        "3. 'protected_attributes': list of demographic or sensitive attributes (e.g. sex, gender, race, age)\n"
        "4. 'feature_columns': list of numeric columns for anomaly detection\n"
        "5. 'record_id': optional unique ID column\n\n"
        f"Column Metadata:\n{json.dumps(profiles, indent=2)}\n\n"
        "Respond ONLY with a valid JSON object with the following schema:\n"
        "{\n"
        '  "prediction": "column_name",\n'
        '  "actual": "column_name",\n'
        '  "record_id": "column_name_or_null",\n'
        '  "protected_attributes": ["col1", "col2"],\n'
        '  "feature_columns": ["col3", "col4"],\n'
        '  "confidence": 0.95,\n'
        '  "rationale": {"prediction": "...", "actual": "...", "protected": "..."}\n'
        "}"
    )

    try:
        from src.agentic.llm_client import extract_text_from_response

        response = llm_client.invoke(prompt)
        text = extract_text_from_response(response)
        
        # Parse JSON from response
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            raise ValueError(f"No JSON found in LLM response: {text[:200]}")
        data = json.loads(json_match.group(0))

        pred_col = data.get("prediction")
        actual_col = data.get("actual")
        rec_id = data.get("record_id")
        prot_cols = [c for c in data.get("protected_attributes", []) if c in df.columns]
        feat_cols = [c for c in data.get("feature_columns", []) if c in df.columns]
        confidence = float(data.get("confidence", 0.7))
        rationale = data.get("rationale", {})

        # Validation: check that assigned columns actually exist in df
        valid_pred = pred_col in df.columns and _is_binary_column(df[pred_col])
        valid_act = actual_col in df.columns and _is_binary_column(df[actual_col])

        mapping = {}
        if valid_pred:
            mapping["prediction"] = pred_col
        if valid_act:
            mapping["actual"] = actual_col
        if rec_id and rec_id in df.columns:
            mapping["record_id"] = rec_id

        needs_review = (
            not valid_pred or
            not valid_act or
            not prot_cols or
            not feat_cols or
            confidence < 0.8
        )

        return SchemaInferenceResult(
            mapping=mapping,
            protected_attributes=prot_cols,
            feature_columns=feat_cols,
            confidence=confidence if (valid_pred and valid_act) else 0.4,
            needs_human_review=needs_review,
            rationale=rationale if isinstance(rationale, dict) else {},
            source="llm",
        )
    except Exception as exc:
        logger.warning("LLM schema inference failed: %s. Using heuristic fallback.", exc)
        return _heuristic_fallback(df)


def _heuristic_fallback(df: pd.DataFrame) -> SchemaInferenceResult:
    """Best-effort heuristic fallback when LLM is unavailable or fails."""
    binary_cols = [c for c in df.columns if _is_binary_column(df[c])]
    mapping: Dict[str, str] = {}
    rationale: Dict[str, str] = {}

    if len(binary_cols) >= 2:
        mapping["prediction"] = str(binary_cols[0])
        mapping["actual"] = str(binary_cols[1])
        rationale["prediction"] = "Heuristic: first detected binary column"
        rationale["actual"] = "Heuristic: second detected binary column"
    elif len(binary_cols) == 1:
        mapping["prediction"] = str(binary_cols[0])
        rationale["prediction"] = "Heuristic: only binary column detected"

    protected = [
        str(c) for c in df.columns
        if c not in mapping.values() and any(k in _canonicalize_col(c) for k in KNOWN_PROTECTED_CANDIDATES)
    ]
    numeric = [
        str(c) for c in df.columns
        if c not in mapping.values() and c not in protected and pd.api.types.is_numeric_dtype(df[c])
    ]

    return SchemaInferenceResult(
        mapping=mapping,
        protected_attributes=protected,
        feature_columns=numeric,
        confidence=0.5,
        needs_human_review=True,
        rationale=rationale,
        source="deterministic",
    )


def infer_schema(
    df: pd.DataFrame,
    llm_client: Optional[Any] = None,
) -> SchemaInferenceResult:
    """
    Main entrypoint for Agent-1 Schema Inference.
    
    1. Deterministic alias lookup runs first (zero cost, zero latency).
    2. If aliases fail to resolve all roles:
       - Uses LLM if llm_client is provided.
       - Falls back to heuristic inference if llm_client is None.
    """
    # 1. Deterministic alias lookup first
    det_result = infer_schema_deterministic(df)
    if det_result is not None:
        return det_result

    # 2. LLM inference if available
    if llm_client is not None:
        return infer_schema_llm(df, llm_client)

    # 3. Fallback
    return _heuristic_fallback(df)
