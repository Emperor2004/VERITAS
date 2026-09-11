"""
Phase 2: Anomaly detection module.

Trains scikit-learn's IsolationForest on the engineered feature set
produced by ingestion (phase 1), scores every record, and evaluates
detection performance against the ground-truth operational anomaly
label injected in phase 1. That evaluation is only possible because
the label exists -- without it there would be no way to validate this
module's output beyond "the algorithm ran and flagged something."

CRITICAL: `ground_truth_operational_anomaly` and `true_label` are
excluded from the feature matrix. They are evaluation-only fields.
Feeding them into the model would be label leakage.
"""
from __future__ import annotations
import argparse
import json
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score

from src.anomaly_detection.output_schema import validate_output
from src.anomaly_detection.threshold_selection import select_threshold_knee, select_threshold_grid_search

EXCLUDED_FROM_FEATURES = {"ground_truth_operational_anomaly", "true_label"}


def load_normalized_log(path: str) -> list:
    with open(path) as f:
        return json.load(f)


def build_feature_matrix(records: list) -> pd.DataFrame:
    df = pd.DataFrame([dict(r["features"]) for r in records])
    # Defensive check -- if a future ingestion change accidentally leaks a
    # label into `features`, fail loudly instead of silently training on it.
    leaked = EXCLUDED_FROM_FEATURES & set(df.columns)
    if leaked:
        raise ValueError(f"Label leakage detected in feature matrix: {leaked}")
    return df


def run_detection(records: list, random_state: int, n_estimators: int,
                   contamination_override: float | None = None):
    X = build_feature_matrix(records)

    # Fit once with contamination="auto" purely to get continuous scores --
    # decision_function/score_samples don't depend on contamination, only
    # the internal predict() threshold does. We derive our own threshold
    # from the score distribution instead of trusting sklearn's default.
    model = IsolationForest(contamination="auto", n_estimators=n_estimators, random_state=random_state)
    model.fit(X)
    anomaly_scores = -model.decision_function(X)  # higher = more anomalous

    y_true = None
    if all("ground_truth_operational_anomaly" in r and r["ground_truth_operational_anomaly"] is not None
           for r in records):
        y_true = np.array([bool(r["ground_truth_operational_anomaly"]) for r in records])

    if contamination_override is not None:
        n = len(anomaly_scores)
        k = max(1, int(round(contamination_override * n)))
        order = np.argsort(-anomaly_scores)
        is_anomaly = np.zeros(n, dtype=bool)
        is_anomaly[order[:k]] = True
        threshold_report = {
            "method": "manual_override",
            "contamination": contamination_override,
            "n_flagged": k,
        }
    else:
        knee_result = select_threshold_knee(anomaly_scores)
        is_anomaly = anomaly_scores >= knee_result["cutoff_score"]

        grid_result = select_threshold_grid_search(anomaly_scores, y_true) if y_true is not None else None

        threshold_report = {
            "unsupervised": knee_result,
            "supervised": grid_result,
        }
        if grid_result and abs(knee_result["contamination"] - grid_result["contamination"]) > 0.03:
            threshold_report["discrepancy_warning"] = (
                f"Unsupervised knee ({knee_result['contamination']}) and supervised grid search "
                f"({grid_result['contamination']}) disagree by more than 3 points -- investigate "
                f"before trusting either value on this dataset."
            )

    return X, anomaly_scores, is_anomaly, threshold_report


def top_contributing_features(x_row: pd.Series, feature_means: pd.Series,
                               feature_stds: pd.Series, top_n: int = 3) -> list:
    """Cheap, transparent local explainability signal: which features deviate
    most from the population mean for this record, in standard-deviation
    units. This is NOT a substitute for the explainability trace still owed
    at the compliance-mapping stage (README section 12) -- it's a partial
    signal at the point of detection, so a finding doesn't arrive at phase 4
    as an unexplained black-box score."""
    z = ((x_row - feature_means) / feature_stds.replace(0, 1)).abs()
    top = z.sort_values(ascending=False).head(top_n)
    return [{"feature": k, "z_score": round(float(v), 3)} for k, v in top.items()]


def build_findings(records: list, X: pd.DataFrame, anomaly_scores, is_anomaly,
                    top_n_features: int = 3) -> list:
    feature_means = X.mean()
    feature_stds = X.std()

    findings = []
    for i, r in enumerate(records):
        findings.append({
            "record_id": r["record_id"],
            "anomaly_score": round(float(anomaly_scores[i]), 6),
            "is_anomaly": bool(is_anomaly[i]),
            "top_contributing_features": top_contributing_features(
                X.iloc[i], feature_means, feature_stds, top_n_features
            ),
        })
    return findings


def evaluate_against_ground_truth(records: list, is_anomaly) -> dict | None:
    has_labels = all(
        "ground_truth_operational_anomaly" in r and r["ground_truth_operational_anomaly"] is not None
        for r in records
    )
    if not has_labels:
        return None

    y_true = np.array([bool(r["ground_truth_operational_anomaly"]) for r in records])
    y_pred = np.asarray(is_anomaly)

    return {
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "n_ground_truth_anomalies": int(y_true.sum()),
        "n_flagged": int(y_pred.sum()),
        "note": (
            "Ground truth here covers ONLY the deliberately injected operational "
            "anomalies (off-hours timestamp + rare auth method). It does NOT cover "
            "genuine statistical outliers in the numeric features (e.g. extreme "
            "capital-gain), which have no ground-truth label and are excluded from "
            "this score. Do not present this precision/recall as full detector "
            "performance -- it measures one anomaly category only."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="VERITAS Phase 2: anomaly detection")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--contamination", type=float, default=None,
        help="Manual contamination override. If omitted (default), the threshold is "
             "derived automatically from this dataset's own score distribution via "
             "knee-point detection, cross-validated against ground truth via grid "
             "search when available. Only set this manually if you have an external, "
             "cited justification -- an unjustified manual number reintroduces the "
             "exact problem this auto-selection replaces."
    )
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    print("[phase2] loading normalized log...")
    records = load_normalized_log(args.input)

    print("[phase2] running IsolationForest and deriving threshold...")
    X, anomaly_scores, is_anomaly, threshold_report = run_detection(
        records, args.random_state, args.n_estimators, contamination_override=args.contamination
    )

    if args.contamination is not None:
        print(f"[phase2] using manual override contamination={args.contamination}")
    else:
        knee = threshold_report["unsupervised"]
        print(f"[phase2] unsupervised knee-point contamination={knee['contamination']} "
              f"(cutoff_score={knee['cutoff_score']:.6f})")
        if threshold_report.get("supervised"):
            sup = threshold_report["supervised"]
            print(f"[phase2] supervised grid-search contamination={sup['contamination']} "
                  f"(f1={sup['f1']}, validation-only, not generalizable)")
        if "discrepancy_warning" in threshold_report:
            print(f"[phase2] WARNING: {threshold_report['discrepancy_warning']}")

    print("[phase2] building findings...")
    findings = build_findings(records, X, anomaly_scores, is_anomaly)

    eval_result = evaluate_against_ground_truth(records, is_anomaly)
    if eval_result:
        print(f"[phase2] evaluation vs injected ground truth: "
              f"precision={eval_result['precision']} recall={eval_result['recall']} "
              f"f1={eval_result['f1']} ({eval_result['n_flagged']} flagged, "
              f"{eval_result['n_ground_truth_anomalies']} true injected)")
    else:
        print("[phase2] no ground truth available -- skipping evaluation")

    output = {
        "findings": findings,
        "evaluation": eval_result,
        "threshold_selection": threshold_report,
        "config": {
            "n_estimators": args.n_estimators,
            "random_state": args.random_state,
            "manual_contamination_override": args.contamination,
        },
    }

    print("[phase2] validating output against schema...")
    validate_output(output)  # raises loudly on malformed output, same discipline as phase 1

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    n_flagged = int(np.asarray(is_anomaly).sum())
    print(f"[phase2] flagged {n_flagged}/{len(records)} records "
          f"({n_flagged/len(records):.1%}), wrote {args.output}")


if __name__ == "__main__":
    main()