"""
Generates the operational metadata (timestamp, session_id, auth_method)
that a real prediction-serving system would emit alongside a prediction,
which UCI Adult Income does not natively contain (HAPI has this structure
natively but lacks user/auth fields -- this module exists to close that
specific gap for our dataset choice).
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Dict
from faker import Faker


def generate_metadata(n: int, config: dict, seed: int = 42) -> List[Dict]:
    fake = Faker()
    Faker.seed(seed)

    start = datetime.fromisoformat(config["timestamp_start"])
    end = datetime.fromisoformat(config["timestamp_end"])
    auth_methods = config["auth_methods"]

    records = []
    for i in range(n):
        records.append({
            "record_id": f"{config['session_id_prefix']}-{i:07d}",
            "timestamp": fake.date_time_between(start_date=start, end_date=end).isoformat(),
            "session_id": fake.uuid4(),
            "auth_method": fake.random_element(elements=auth_methods),
        })
    return records