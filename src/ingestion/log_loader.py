"""
Phase 1 entrypoint: dataset load -> audit-subject prediction -> feature
engineering -> synthetic metadata merge -> schema validation ->
normalized_log.json

Usage:
    python -m src.ingestion.log_loader --output data/processed/normalized_log.json
"""
from __future__ import annotations
import argparse
import json
import os
import pandas as pd
import yaml

from src.ingestion.audit_subject_model import train_audit_subject
from src.ingestion.feature_engineering import engineer_features
from src.ingestion.synthetic_metadata import generate_metadata, compute_anomaly_mask
from src.ingestion.schema import validate_records

ADULT_COLUMNS = [
    "age", "workclass", "fnlwgt", "education", "education-num",
    "marital-status", "occupation", "relationship", "race", "sex",
    "capital-gain", "capital-loss", "hours-per-week", "native-country", "income",
]


def load_raw_dataset(config: dict) -> pd.DataFrame:
    """Loads UCI Adult Income, preferring a local cache to avoid re-downloading.
    Falls back to `ucimlrepo` if no local cache exists."""
    cache_path = config["dataset"]["local_cache_csv"]

    if os.path.exists(cache_path):
        return pd.read_csv(cache_path)

    try:
        from ucimlrepo import fetch_ucirepo
    except ImportError as e:
        raise RuntimeError(
            "No local dataset cache found and `ucimlrepo` is not installed. "
            "Run: pip install ucimlrepo -- or manually place the Adult Income "
            f"CSV at {cache_path} with columns: {ADULT_COLUMNS}"
        ) from e

    dataset = fetch_ucirepo(id=config["dataset"]["uci_repo_id"])
    df = pd.concat([dataset.data.features, dataset.data.targets], axis=1)
    df.columns = ADULT_COLUMNS[: len(df.columns)]

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    df.to_csv(cache_path, index=False)
    return df


def build_normalized_log(df: pd.DataFrame, config: dict) -> list:
    # UCI Adult Income encodes missing values as the literal string " ?" (with
    # a leading space) rather than NaN. dropna() alone silently misses these --
    # replace first, or unknown-category rows pass through undetected.
    df = df.replace(r"^\s*\?\s*$", pd.NA, regex=True)
    n_before = len(df)
    df = df.dropna().reset_index(drop=True)
    n_dropped = n_before - len(df)
    if n_dropped:
        print(f"[phase1] dropped {n_dropped} rows with missing/'?' values "
              f"({n_dropped / n_before:.1%} of raw data)")

    predicted_label, confidence, true_label = train_audit_subject(
        df,
        test_size=config["audit_subject_model"]["test_size"],
        random_state=config["audit_subject_model"]["random_state"],
    )

    inj_cfg = config["anomaly_injection"]
    anomaly_mask = compute_anomaly_mask(
        len(df), inj_cfg["injection_rate"], inj_cfg["random_state"]
    )
    metadata = generate_metadata(len(df), config["synthetic_metadata"] | {
        "rare_auth_methods": inj_cfg["rare_auth_methods"],
        "normal_hour_range": inj_cfg["normal_hour_range"],
    }, anomaly_mask)

    features_df = engineer_features(
        df, predicted_label, confidence, metadata,
        rare_auth_methods=inj_cfg["rare_auth_methods"],
        normal_hour_range=tuple(inj_cfg["normal_hour_range"]),
    )

    protected_cols = config["protected_attributes"]

    records = []
    for i in range(len(df)):
        record = {
            **metadata[i],
            "features": features_df.iloc[i].to_dict(),
            "protected_attributes": {
                col: str(df.iloc[i][col]).strip() for col in protected_cols
            },
            "predicted_label": int(predicted_label[i]),
            "prediction_confidence": float(confidence[i]),
            "true_label": int(true_label[i]),
        }
        records.append(record)

    n_injected = int(anomaly_mask.sum())
    print(f"[phase1] injected {n_injected} operational anomalies "
          f"({n_injected / len(df):.1%} of records)")

    return records


def main():
    parser = argparse.ArgumentParser(description="VERITAS Phase 1: ingestion pipeline")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=None,
                         help="Optional row limit, useful for a fast dev run")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    print("[phase1] loading raw dataset...")
    df = load_raw_dataset(config)
    if args.limit:
        df = df.sample(n=args.limit, random_state=42).reset_index(drop=True)

    print(f"[phase1] {len(df)} records loaded, training audit-subject model and building log...")
    raw_records = build_normalized_log(df, config)

    print("[phase1] validating against schema...")
    validated = validate_records(raw_records)  # raises loudly on malformed records

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump([r.model_dump(mode="json") for r in validated], f, indent=2, default=str)

    print(f"[phase1] wrote {len(validated)} records to {args.output}")


if __name__ == "__main__":
    main()