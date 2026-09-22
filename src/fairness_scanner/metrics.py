"""
Phase 3: Fairness & bias scanning.

Computes three statistical fairness metrics per protected attribute using
Fairlearn: demographic parity difference, disparate impact ratio, and
equalized odds difference. This module performs pure statistical
measurement over the audit-subject model's already-made predictions --
it does not train, tune, or otherwise touch any model.

NOTE on true_label: equalized odds is DEFINED in terms of ground truth
(it measures whether true/false positive rates differ across groups) and
cannot be computed from predictions alone. This is a legitimate and
necessary use of true_label -- unlike anomaly detection, where using it
as an input feature would be label leakage into an unsupervised model,
here nothing is being trained. Real fairness audits use held-out outcome
data (e.g. actual loan repayment, known later) for exactly this purpose.

NOTE on disparate impact ratio: Fairlearn has no function literally named
this. Its `demographic_parity_ratio` -- min(group selection rate) /
max(group selection rate) -- is mathematically the same quantity as the
worst-case pairwise disparate impact ratio across all groups of a
protected attribute, so it is used directly here and compared against
the EEOC four-fifths threshold (0.8).
"""
from __future__ import annotations
import json
import pandas as pd
from fairlearn.metrics import (
    MetricFrame,
    demographic_parity_difference,
    demographic_parity_ratio,
    equalized_odds_difference,
    selection_rate,
    count,
)

from src.fairness_scanner.thresholds import (
    evaluate_disparate_impact,
    flag_small_groups,
    permutation_significance_test,
)

PROTECTED_COL_PREFIX = "protected__"


def load_normalized_log(path: str) -> list:
    with open(path) as f:
        return json.load(f)


def build_frame(records: list) -> pd.DataFrame:
    rows = []
    for r in records:
        if r.get("true_label") is None:
            # Equalized odds cannot be computed without ground truth --
            # fail loudly rather than silently skip, per the project's
            # own stance against silent discards (README section 12).
            raise ValueError(
                f"record {r['record_id']} has no true_label; fairness scanner "
                "requires ground truth for equalized odds and cannot proceed."
            )
        row = {
            "record_id": r["record_id"],
            "predicted_label": r["predicted_label"],
            "true_label": r["true_label"],
        }
        row.update({f"{PROTECTED_COL_PREFIX}{k}": v for k, v in r["protected_attributes"].items()})
        rows.append(row)
    return pd.DataFrame(rows)


def compute_fairness_metrics_for_attribute(
    df: pd.DataFrame,
    attribute_col: str,
    eeoc_threshold: float,
    min_group_size: int,
    significance_level: float = 0.05,
    n_permutations: int = 1000,
    permutation_random_state: int = 42,
) -> dict:
    y_true = df["true_label"]
    y_pred = df["predicted_label"]
    sensitive = df[attribute_col]

    dp_diff = demographic_parity_difference(y_true, y_pred, sensitive_features=sensitive)
    dp_ratio = demographic_parity_ratio(y_true, y_pred, sensitive_features=sensitive)
    eo_diff = equalized_odds_difference(y_true, y_pred, sensitive_features=sensitive)

    # disparate_impact_ratio has an external, cited threshold (EEOC 0.8) --
    # no permutation test needed, it's a direct comparison. demographic
    # parity difference and equalized odds difference have no such external
    # number, so their violation decision comes from a permutation test
    # instead (see thresholds.py for why). Distinct random_state per metric
    # so the two tests don't share a permutation stream.
    dp_test = permutation_significance_test(
        demographic_parity_difference, y_true, y_pred, sensitive, dp_diff,
        n_permutations=n_permutations, significance_level=significance_level,
        random_state=permutation_random_state,
    )
    eo_test = permutation_significance_test(
        equalized_odds_difference, y_true, y_pred, sensitive, eo_diff,
        n_permutations=n_permutations, significance_level=significance_level,
        random_state=permutation_random_state + 1,
    )

    group_frame = MetricFrame(
        metrics={"selection_rate": selection_rate, "count": count},
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=sensitive,
    )

    group_selection_rates = {str(k): round(float(v), 4) for k, v in group_frame.by_group["selection_rate"].items()}
    group_sizes = {str(k): int(v) for k, v in group_frame.by_group["count"].items()}
    small_groups = flag_small_groups(group_sizes, min_group_size)

    return {
        "attribute": attribute_col.replace(PROTECTED_COL_PREFIX, ""),
        "demographic_parity_difference": round(float(dp_diff), 4),
        "demographic_parity_violation": dp_test["violation"],
        "demographic_parity_p_value": dp_test["p_value"],
        "disparate_impact_ratio": round(float(dp_ratio), 4),
        "disparate_impact_violation": evaluate_disparate_impact(dp_ratio, eeoc_threshold),
        "equalized_odds_difference": round(float(eo_diff), 4),
        "equalized_odds_violation": eo_test["violation"],
        "equalized_odds_p_value": eo_test["p_value"],
        "group_selection_rates": group_selection_rates,
        "group_sizes": group_sizes,
        "eeoc_four_fifths_threshold": eeoc_threshold,
        "small_group_warning": small_groups,
        "permutation_test_config": {
            "n_permutations": n_permutations,
            "significance_level": significance_level,
            "random_state": permutation_random_state,
        },
    }