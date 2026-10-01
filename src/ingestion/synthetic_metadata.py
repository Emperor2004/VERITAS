"""
Generates the operational metadata (timestamp, session_id, auth_method)
that a real prediction-serving system would emit alongside a prediction,
which UCI Adult Income does not natively contain (HAPI has this structure
natively but lacks user/auth fields -- this module exists to close that
specific gap for our dataset choice).

Operational anomalies are deliberately injected at a known rate rather
than left to uniform random chance. Uniform-random auth_method/timestamp
values carry no real signal for IsolationForest to find -- injecting a
known, labeled anomaly rate gives (a) genuine structure for the detector
to pick up on, and (b) a ground-truth label to evaluate detection
performance against in phase 2. This label is NOT a feature and must
never be passed into the detector's input.
"""
from __future__ import annotations
import numpy as np
from datetime import datetime, time
from typing import List, Dict
from faker import Faker


TYPE_OFF_HOURS_RARE_AUTH = "off_hours_rare_auth"


def assign_anomaly_types(
    n: int, injection_rate: float, type_weights: Dict[str, float], random_state: int
) -> np.ndarray:
    """Decides which records get an injected operational anomaly AND which
    pattern each one gets. Replaces the old boolean compute_anomaly_mask:
    the total injected rate is unchanged (still `injection_rate`, so
    anomaly_detection.contamination in config.yaml needs no change), but
    that budget is now split across named patterns via `type_weights`
    (normalized internally, so weights need not sum to 1).

    Returns an array of length n: None for a normal record, otherwise one
    of the keys in `type_weights`.
    """
    rng = np.random.default_rng(random_state)
    is_anomaly = rng.random(n) < injection_rate
    types = np.full(n, None, dtype=object)

    names = list(type_weights.keys())
    weights = np.array([type_weights[k] for k in names], dtype=float)
    weights = weights / weights.sum()

    anomaly_idx = np.where(is_anomaly)[0]
    if len(anomaly_idx):
        types[anomaly_idx] = rng.choice(names, size=len(anomaly_idx), p=weights)
    return types


def generate_metadata(n: int, config: dict, anomaly_types: np.ndarray, seed: int = 42) -> List[Dict]:
    """`anomaly_types[i]` is None for a normal record, or an anomaly type
    name. Only TYPE_OFF_HOURS_RARE_AUTH changes the generated metadata
    (timestamp/auth_method) -- other anomaly types (feature_outlier,
    duplicate_record) live entirely in the real feature columns, handled
    by feature_anomalies.py, and get normal-looking metadata here so the
    two signal channels stay independent and don't double-count."""
    fake = Faker()
    Faker.seed(seed)

    start = datetime.fromisoformat(config["timestamp_start"])
    end = datetime.fromisoformat(config["timestamp_end"])
    normal_auth_methods = config["auth_methods"]
    rare_auth_methods = config["rare_auth_methods"]
    normal_hour_start, normal_hour_end = config["normal_hour_range"]

    records = []
    for i in range(n):
        anomaly_type = anomaly_types[i]

        if anomaly_type == TYPE_OFF_HOURS_RARE_AUTH:
            # Off-hours timestamp: pick a date, force the hour outside normal range
            base_date = fake.date_between(start_date=start.date(), end_date=end.date())
            off_hour = fake.random_element(
                elements=list(range(0, normal_hour_start)) + list(range(normal_hour_end, 24))
            )
            ts = datetime.combine(base_date, time(hour=off_hour, minute=fake.random_int(0, 59)))
            auth_method = fake.random_element(elements=rare_auth_methods)
        else:
            base_date = fake.date_between(start_date=start.date(), end_date=end.date())
            normal_hour = fake.random_int(normal_hour_start, normal_hour_end - 1)
            ts = datetime.combine(base_date, time(hour=normal_hour, minute=fake.random_int(0, 59)))
            auth_method = fake.random_element(elements=normal_auth_methods)

        records.append({
            "record_id": f"{config['session_id_prefix']}-{i:07d}",
            "timestamp": ts.isoformat(),
            "session_id": fake.uuid4(),
            "auth_method": auth_method,
            "ground_truth_operational_anomaly": anomaly_type is not None,
            "ground_truth_anomaly_type": anomaly_type,
        })
    return records