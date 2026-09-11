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
from typing import Dict, List


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