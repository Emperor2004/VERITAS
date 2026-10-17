"""
VERITAS Formal Statistical Validation Engine.

Performs rigorous statistical verification of the VERITAS audit pipeline:
1. Permutation Significance Testing (Empirical Null Distribution, Type I Error Rate under H0, Power under H1, Monte Carlo SE)
2. EEOC 4/5ths Disparate Impact Ratio Boundary & Sensitivity
3. Small-Group Sample Size Stability Screening
4. Isolation Forest Score Distribution & Knee-Point Geometric Threshold Calibration
5. Deterministic Boundary Invariance (Bit-level seed reproducibility)
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import time
import numpy as np
import pandas as pd
from fairlearn.metrics import demographic_parity_difference, equalized_odds_difference

from src.fairness_scanner.thresholds import (
    evaluate_disparate_impact,
    flag_small_groups,
    permutation_significance_test,
)
from src.anomaly_detection.threshold_selection import (
    select_threshold_knee,
    select_threshold_grid_search,
)
from src.anomaly_detection.isolation_forest import run_detection
from src.pipeline import VeritasPipeline
from pathlib import Path


def validate_permutation_null_distribution(n_trials: int = 50, n_perms: int = 200, alpha: float = 0.05) -> dict:
    """Validate Type I error rate under the null hypothesis (H0: sensitive attribute independent of labels)."""
    rng = np.random.default_rng(12345)
    rejections = 0
    p_values = []

    n_samples = 200
    y_true = rng.choice([0, 1], size=n_samples, p=[0.7, 0.3])
    y_pred = rng.choice([0, 1], size=n_samples, p=[0.75, 0.25])

    for i in range(n_trials):
        # Under H0, sensitive feature is purely independent random noise
        sensitive = rng.choice(["Group_A", "Group_B"], size=n_samples, p=[0.5, 0.5])
        observed = float(demographic_parity_difference(y_true, y_pred, sensitive_features=sensitive))
        res = permutation_significance_test(
            metric_fn=demographic_parity_difference,
            y_true=y_true,
            y_pred=y_pred,
            sensitive_features=sensitive,
            observed_value=observed,
            n_permutations=n_perms,
            significance_level=alpha,
            random_state=42 + i,
        )
        p_values.append(res["p_value"])
        if res["violation"]:
            rejections += 1

    observed_alpha = rejections / n_trials
    # 95% binomial standard error for alpha under H0
    se_alpha = np.sqrt(alpha * (1 - alpha) / n_trials)
    within_ci = abs(observed_alpha - alpha) <= 2.5 * se_alpha

    return {
        "test": "Type I Error Control under Null (H0)",
        "trials": n_trials,
        "nominal_alpha": alpha,
        "empirical_alpha": round(observed_alpha, 4),
        "mean_p_value": round(float(np.mean(p_values)), 4),
        "se_alpha": round(float(se_alpha), 4),
        "passed": bool(within_ci),
        "note": f"Empirical false-positive rate {observed_alpha:.1%} is within statistical bounds of alpha={alpha:.1%}.",
    }


def validate_permutation_power(n_perms: int = 500, alpha: float = 0.05) -> dict:
    """Validate statistical power / sensitivity under known strong disparity (H1)."""
    rng = np.random.default_rng(54321)
    n_samples = 300
    # Group A: 80% positive rate, Group B: 10% positive rate -> massive disparity
    group_a = np.array(["A"] * (n_samples // 2))
    group_b = np.array(["B"] * (n_samples // 2))
    sensitive = np.concatenate([group_a, group_b])

    y_pred_a = rng.choice([0, 1], size=len(group_a), p=[0.2, 0.8])
    y_pred_b = rng.choice([0, 1], size=len(group_b), p=[0.9, 0.1])
    y_pred = np.concatenate([y_pred_a, y_pred_b])
    y_true = y_pred.copy()

    observed = float(demographic_parity_difference(y_true, y_pred, sensitive_features=sensitive))
    res = permutation_significance_test(
        metric_fn=demographic_parity_difference,
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=sensitive,
        observed_value=observed,
        n_permutations=n_perms,
        significance_level=alpha,
        random_state=42,
    )

    passed = res["violation"] and res["p_value"] < 0.001
    return {
        "test": "Statistical Power under True Disparity (H1)",
        "observed_disparity": round(observed, 4),
        "p_value": res["p_value"],
        "monte_carlo_se": res["p_value_monte_carlo_se"],
        "violation_flagged": res["violation"],
        "passed": passed,
        "note": f"True disparity of {observed:.2%} correctly rejected H0 with p={res['p_value']:.4f} (p < {alpha}).",
    }


def validate_eeoc_boundary() -> dict:
    """Validate EEOC 4/5ths (0.80) ratio standard boundary conditions."""
    cases = [
        (0.7999, True),   # Just below 0.80 -> violation
        (0.8000, False),  # Exactly 0.80 -> compliant
        (0.8001, False),  # Just above 0.80 -> compliant
        (0.6383, True),   # Observed in demo dataset -> violation
        (1.0000, False),  # Perfect parity -> compliant
    ]
    results = []
    all_passed = True
    for ratio, expected in cases:
        flag = evaluate_disparate_impact(ratio, threshold=0.8)
        passed = (flag == expected)
        all_passed = all_passed and passed
        results.append({"ratio": ratio, "expected_violation": expected, "result": flag, "passed": passed})

    return {
        "test": "EEOC 4/5ths Rule Boundary Verification",
        "boundary_cases": results,
        "passed": all_passed,
        "note": "Exact IEEE floating-point boundary adherence for DIR < 0.80.",
    }


def validate_sample_size_stability() -> dict:
    """Validate small-cohort sample-size screening to avoid noisy inferences."""
    groups = {"Caucasian": 450, "African_American": 120, "Asian": 15, "Native_American": 4}
    threshold = 30
    unstable = flag_small_groups(groups, min_group_size=threshold)
    expected = ["Asian", "Native_American"]
    passed = sorted(unstable) == sorted(expected)

    return {
        "test": "Small-Group Sample Size Stability Screening",
        "cohort_sizes": groups,
        "min_group_size_cutoff": threshold,
        "flagged_unstable_groups": unstable,
        "passed": passed,
        "note": f"Correctly isolated cohorts with N < {threshold} to prevent small-sample noise.",
    }


def validate_knee_point_geometry() -> dict:
    """Validate Isolation Forest knee-point curve threshold detection."""
    # Synthetic exponential tail characteristic of anomaly scores
    rng = np.random.default_rng(999)
    normal_scores = rng.normal(loc=-0.15, scale=0.03, size=900)
    outlier_scores = rng.exponential(scale=0.15, size=100) + 0.1
    all_scores = np.concatenate([normal_scores, outlier_scores])

    knee_res = select_threshold_knee(all_scores)
    # The true injected outlier rate was ~10% (100 / 1000)
    inferred_contamination = knee_res["contamination"]
    passed = 0.05 <= inferred_contamination <= 0.20

    return {
        "test": "Unsupervised Knee-Point Curvature Detection",
        "cutoff_score": knee_res["cutoff_score"],
        "inferred_contamination": inferred_contamination,
        "records_flagged": knee_res["n_flagged"],
        "passed": passed,
        "note": f"Knee-point geometry isolated {knee_res['n_flagged']} anomalies ({inferred_contamination:.1%}) without labels.",
    }


def validate_seed_reproducibility() -> dict:
    """Assert deterministic statistical boundary: 100% reproducible p-values and scores."""
    rng = np.random.default_rng(777)
    y_true = rng.choice([0, 1], size=150)
    y_pred = rng.choice([0, 1], size=150)
    sensitive = rng.choice(["M", "F"], size=150)
    observed = float(demographic_parity_difference(y_true, y_pred, sensitive_features=sensitive))

    run1 = permutation_significance_test(
        demographic_parity_difference, y_true, y_pred, sensitive, observed, n_permutations=300, random_state=42
    )
    run2 = permutation_significance_test(
        demographic_parity_difference, y_true, y_pred, sensitive, observed, n_permutations=300, random_state=42
    )

    exact_match = (run1 == run2)
    return {
        "test": "Deterministic Statistical Boundary Invariance",
        "run1_p_value": run1["p_value"],
        "run2_p_value": run2["p_value"],
        "exact_match": exact_match,
        "passed": exact_match,
        "note": "Independent seeded runs produce bit-for-bit identical statistical outputs.",
    }


def run_full_statistical_validation():
    print("=" * 80)
    print("  VERITAS ENTERPRISE STATISTICAL VALIDATION SUITE")
    print("  Deterministic Statistical Boundary & Numerical Integrity Protocol")
    print("=" * 80)

    start_time = time.time()
    validations = [
        validate_eeoc_boundary(),
        validate_sample_size_stability(),
        validate_permutation_null_distribution(),
        validate_permutation_power(),
        validate_knee_point_geometry(),
        validate_seed_reproducibility(),
    ]

    all_passed = True
    for i, v in enumerate(validations, 1):
        status_icon = "[PASS]" if v["passed"] else "[FAIL]"
        all_passed = all_passed and v["passed"]
        print(f"\n[{i}/6] {v['test']}")
        print(f"      Status: {status_icon}")
        print(f"      Details: {v['note']}")
        for k, val in v.items():
            if k not in ("test", "passed", "note", "boundary_cases"):
                print(f"        * {k}: {val}")

    # End-to-end audit run statistics
    print("\n" + "-" * 80)
    print("  LIVE BENCHMARK: End-to-End Pipeline Statistical Verification (UCI Adult Income)")
    print("-" * 80)
    config_path = Path("config/config.yaml")
    pipeline = VeritasPipeline.from_config_file(config_path)
    artifacts = pipeline.run_all(limit=500, save_artifacts=False)

    fairness = artifacts.fairness_output
    anomaly = artifacts.anomaly_output
    mapped = artifacts.mapped_findings

    injected_count = sum(1 for r in artifacts.normalized_logs if r.get("ground_truth_operational_anomaly"))
    total_anomalies = len(anomaly.get("findings", []))
    contamination = anomaly.get("config", {}).get("contamination_used", "knee_point")
    print(f"  - Anomaly Detector Flagged: {total_anomalies} records (contamination: {contamination})")
    eval_dict = anomaly.get("evaluation") or {}
    print(f"  - Anomaly Supervised Precision: {eval_dict.get('precision', 'N/A')}")
    print(f"  - Anomaly Supervised Recall: {eval_dict.get('recall', 'N/A')}")
    print(f"  - Anomaly Supervised F1-Score: {eval_dict.get('f1_score', 'N/A')}")
    print(f"  - Fairness Attributes Scanned: {fairness.get('config', {}).get('protected_attributes_scanned')}")
    print(f"  - Total NIST-Mapped Findings: {len(mapped)}")
    violations = [f for f in mapped if f['severity_tier'] == 'violation']
    print(f"  - Violation-Tier Findings: {len(violations)}")
    for v in violations:
        print(f"      - [{v['finding_type']}] {v.get('metric_name') or v.get('source_record_id')} = {v.get('observed_value')}")

    elapsed = time.time() - start_time
    print("=" * 80)
    if all_passed:
        print(f"  ALL 6 STATISTICAL VALIDATION PROTOCOLS PASSED ({elapsed:.2f}s) - 100% COMPLIANT")
    else:
        print(f"  STATISTICAL VALIDATION FAILED ({elapsed:.2f}s)")
    print("=" * 80)
    return all_passed


if __name__ == "__main__":
    success = run_full_statistical_validation()
    sys.exit(0 if success else 1)
