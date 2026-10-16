import pytest
from src.agentic.agents.anomaly_grouper import (
    group_anomalies,
    calculate_per_type_breakdown,
    AnomalyGroup,
)


@pytest.fixture
def sample_anomaly_findings():
    return [
        {
            "record_id": "REC-1",
            "anomaly_score": -0.85,
            "is_anomaly": True,
            "top_contributing_features": [
                {"feature": "capital_gain", "z_score": 4.5},
                {"feature": "age", "z_score": 1.2},
            ],
        },
        {
            "record_id": "REC-2",
            "anomaly_score": -0.72,
            "is_anomaly": True,
            "top_contributing_features": [
                {"feature": "capital_gain", "z_score": 3.8},
                {"feature": "hours_per_week", "z_score": 2.1},
            ],
        },
        {
            "record_id": "REC-3",
            "anomaly_score": -0.65,
            "is_anomaly": True,
            "top_contributing_features": [
                {"feature": "hours_per_week", "z_score": 5.0},
                {"feature": "capital_gain", "z_score": 1.1},
            ],
        },
        {
            "record_id": "REC-4",
            "anomaly_score": 0.12,
            "is_anomaly": False,
            "top_contributing_features": [
                {"feature": "age", "z_score": 0.5},
            ],
        },
    ]


def test_group_anomalies_clusters_by_dominant_feature(sample_anomaly_findings):
    groups = group_anomalies(sample_anomaly_findings)
    assert len(groups) == 2
    # Group 1 should be capital_gain (2 members)
    assert groups[0].dominant_feature == "capital_gain"
    assert groups[0].record_count == 2
    assert "REC-1" in groups[0].record_ids
    assert "REC-2" in groups[0].record_ids
    assert groups[0].representative_record_id == "REC-1"
    assert "capital_gain" in groups[0].deterministic_summary

    # Group 2 should be hours_per_week (1 member)
    assert groups[1].dominant_feature == "hours_per_week"
    assert groups[1].record_count == 1
    assert "REC-3" in groups[1].record_ids


def test_group_anomalies_empty_list():
    assert group_anomalies([]) == []


def test_per_type_breakdown():
    findings = [
        {"record_id": "R1", "is_anomaly": True},
        {"record_id": "R2", "is_anomaly": False},
        {"record_id": "R3", "is_anomaly": True},
    ]
    ground_truth = [
        {"record_id": "R1", "ground_truth_anomaly_type": "point_outlier"},
        {"record_id": "R2", "ground_truth_anomaly_type": "point_outlier"},
        {"record_id": "R3", "ground_truth_anomaly_type": "contextual_outlier"},
    ]
    breakdown = calculate_per_type_breakdown(findings, ground_truth)
    assert "point_outlier" in breakdown
    assert "contextual_outlier" in breakdown
    assert breakdown["point_outlier"]["detected"] == 1
    assert breakdown["point_outlier"]["total_ground_truth"] == 2
    assert breakdown["contextual_outlier"]["detected"] == 1
