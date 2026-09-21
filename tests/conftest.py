"""Shared fixtures for compliance_mapping tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.compliance_mapping.rules_engine import load_lookup_table

LOOKUP_PATH = Path(__file__).parent.parent / "src" / "compliance_mapping" / "nist_control_lookup.yaml"


@pytest.fixture
def lookup():
    return load_lookup_table(LOOKUP_PATH)


@pytest.fixture
def sample_anomaly_finding_informational():
    return {
        "finding_type": "anomaly_finding",
        "metric_name": None,
        "observed_value": -0.12,
        "severity_tier": "informational",
        "source_record_id": "rec_00042",
    }


@pytest.fixture
def sample_fairness_finding_informational():
    return {
        "finding_type": "fairness_finding",
        "metric_name": "demographic_parity_difference",
        "observed_value": 0.03,
        "severity_tier": "informational",
        "source_record_id": "sex",
    }


@pytest.fixture
def sample_fairness_finding_violation():
    return {
        "finding_type": "fairness_finding",
        "metric_name": "disparate_impact_ratio",
        "observed_value": 0.71,
        "severity_tier": "violation",
        "source_record_id": "race",
    }