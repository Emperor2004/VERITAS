"""
Phase 1 anomaly injection -- feature-space outlier and duplicate-record
patterns.

Separate from synthetic_metadata.py: that module injects anomalies into the
Faker-generated OPERATIONAL metadata (timestamp, auth_method). This module
injects anomalies into the REAL UCI Adult Income feature columns themselves,
so the anomaly detector is also tested on the audit subject's actual inputs,
not only on synthetic wrapper fields.

Both functions mutate `df` in place and MUST run before `train_audit_subject`.
This ordering is required, not incidental: the audit-subject model must never
be trained on a deliberately-injected outlier row, or it partially "learns"
to treat the pattern as normal, which would make both the anomaly-detection
evaluation and the fairness evaluation unreliable. The caller is responsible
for excluding these indices from the training split (see log_loader.py).
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def inject_feature_space_outliers(
    df: pd.DataFrame, indices: np.ndarray, config: dict, random_state: int
) -> None:
    """Overwrites rows at `indices` with an internally-implausible combination
    of real feature values (in place): a young age together with a very high
    hours-per-week and capital-gain. Each value alone is within the dataset's
    normal range -- it is the *combination* that is unlikely, which is what
    makes this a genuine density-based anomaly rather than a single-column
    extreme value a one-sided check could catch.

    `education-num` is deliberately left untouched: a young record paired
    with a high existing education-num is itself part of the implausible
    combination; forcing it down here would erase the pattern instead of
    creating it.
    """
    if len(indices) == 0:
        return
    rng = np.random.default_rng(random_state)
    age_lo, age_hi = config["age_range"]
    hrs_lo, hrs_hi = config["hours_per_week_range"]
    gain_min = config["capital_gain_min"]

    for idx in indices:
        df.at[idx, "age"] = int(rng.integers(age_lo, age_hi + 1))
        df.at[idx, "hours-per-week"] = int(rng.integers(hrs_lo, hrs_hi + 1))
        df.at[idx, "capital-gain"] = int(rng.integers(gain_min, gain_min + 10_000))


def inject_duplicate_records(
    df: pd.DataFrame, indices: np.ndarray, source_pool: np.ndarray, random_state: int
) -> dict:
    """Overwrites rows at `indices` with an exact copy of another record's
    full feature columns (including the target), drawn from `source_pool`.
    `source_pool` must exclude every injected index (feature_outlier and
    duplicate_record alike), so a duplicate is never copied from another
    anomaly.

    This pattern is deliberately left undetectable by IsolationForest, which
    is density-based and treats an exact repeat of a common point as *more*
    typical, not less. It is included so the detector's blind spot is
    documented in the evaluation rather than silently absent from it -- see
    README known-limitations.

    Returns {duplicated_index: source_index} for logging only; not written
    to the schema, since it is an injection-time artifact, not an
    audit-relevant field.
    """
    if len(indices) == 0:
        return {}
    rng = np.random.default_rng(random_state)
    sources = rng.choice(source_pool, size=len(indices), replace=True)
    for dup_idx, src_idx in zip(indices, sources):
        df.loc[dup_idx, df.columns] = df.loc[src_idx, df.columns].values
    return {int(d): int(s) for d, s in zip(indices, sources)}
