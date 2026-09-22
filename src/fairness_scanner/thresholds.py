"""
Threshold and violation-decision logic for the fairness scanner.

Deliberately separate from metrics.py: metrics.py computes what the
numbers ARE (demographic parity, disparate impact ratio, equalized odds).
This module decides what counts as a VIOLATION given those numbers. The
same separation exists in the anomaly detection module between
isolation_forest.py (scoring) and threshold_selection.py (choosing a
cutoff) -- conflating computation and judgment in one file makes it
harder to change a threshold's justification without touching the
statistics themselves.
"""
from __future__ import annotations
from typing import Callable, Dict, List

import numpy as np


def evaluate_disparate_impact(disparate_impact_ratio: float, threshold: float) -> bool:
    """EEOC Uniform Guidelines four-fifths rule: a disparate impact ratio
    below `threshold` (canonically 0.8) is treated as a violation. This
    threshold is an external, cited regulatory standard -- unlike the
    anomaly detection contamination rate, it is NOT something this project
    derives or tunes per-dataset."""
    return bool(disparate_impact_ratio < threshold)


def flag_small_groups(group_sizes: Dict[str, int], min_group_size: int) -> List[str]:
    """Groups below min_group_size produce statistically unstable ratio/
    difference metrics. Flagging them means a violation is never reported
    without this caveat attached where relevant."""
    return [g for g, n in group_sizes.items() if n < min_group_size]


def permutation_significance_test(
    metric_fn: Callable,
    y_true,
    y_pred,
    sensitive_features,
    observed_value: float,
    n_permutations: int = 1000,
    significance_level: float = 0.05,
    random_state: int = 42,
) -> dict:
    """
    Generic permutation significance test for a Fairlearn difference metric
    (demographic_parity_difference, equalized_odds_difference, ...).

    Unlike disparate_impact_ratio, these two metrics have no externally
    cited threshold (no EEOC-equivalent number exists for them). Rather
    than picking an arbitrary constant, this shuffles the protected
    attribute's labels -- holding predictions and true labels fixed -- to
    build an empirical null distribution of "what this metric looks like
    with no real relationship to the protected attribute." The observed
    value is flagged a violation if it falls outside that null distribution
    at the given significance level.

    `metric_fn` is injected rather than imported here, keeping this module
    independent of which specific Fairlearn metric is under test --
    consistent with this module's existing separation from metrics.py
    (computation lives there, judgment lives here).

    Both target metrics are non-negative by construction (Fairlearn returns
    the largest group-pair gap), so this is a one-tailed test: p_value is
    the fraction of permutations whose null value is >= the observed value.

    significance_level and random_state are disclosed policy/reproducibility
    choices, not derived from data -- see nist_control_lookup.yaml's
    recalibration_required section. random_state is fixed (not left to
    default RNG state) specifically because an unseeded permutation test
    can flip a boundary-case verdict between identical runs on the same
    data -- a reproducibility failure this project already flagged and
    committed to avoiding.
    """
    rng = np.random.default_rng(random_state)
    sensitive_arr = np.asarray(sensitive_features)
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)

    null_values = np.empty(n_permutations)
    for i in range(n_permutations):
        shuffled = rng.permutation(sensitive_arr)
        null_values[i] = metric_fn(y_true_arr, y_pred_arr, sensitive_features=shuffled)

    p_value = float(np.mean(null_values >= observed_value))
    # Monte Carlo standard error on the p-value estimate itself -- reported
    # so a boundary-case result isn't presented with false precision.
    mc_se = float(np.sqrt(p_value * (1 - p_value) / n_permutations))

    return {
        "violation": bool(p_value < significance_level),
        "p_value": round(p_value, 4),
        "p_value_monte_carlo_se": round(mc_se, 4),
        "n_permutations": n_permutations,
        "significance_level": significance_level,
        "random_state": random_state,
    }