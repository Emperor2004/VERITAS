import pytest
from src.compliance_mapping.plain_explanation import (
    build_plain_explanation,
    PlainExplanation,
    RemediationStep,
)
from src.compliance_mapping.explanation_verifier import (
    verify_plain_explanation,
    verify_explanation,
)


def test_build_plain_explanation_fairness_disparate_impact():
    finding = {
        "finding_type": "fairness_finding",
        "metric_name": "disparate_impact_ratio",
        "severity_tier": "violation",
        "attribute": "gender",
        "observed_value": 0.65,
        "threshold": 0.80,
        "controls_applied": [
            {"control_id": "MEASURE 2.11", "title": "Fairness evaluated"}
        ],
        "supporting_evidence": [],
    }

    explanation = build_plain_explanation(finding)
    assert isinstance(explanation, PlainExplanation)
    assert "0.65" in explanation.what_we_found or "65" in explanation.what_we_found
    assert len(explanation.how_to_fix_it) > 0
    assert len(explanation.remediation_ids) > 0
    assert explanation.source == "deterministic"

    # Deterministic explanations should pass verifier
    result = verify_plain_explanation(explanation, finding)
    assert result.passed, f"Verifier failed with violations: {result.violations}"


def test_build_plain_explanation_fairness_with_small_group():
    finding = {
        "finding_type": "fairness_finding",
        "metric_name": "demographic_parity_difference",
        "severity_tier": "violation",
        "attribute": "race",
        "observed_value": 0.15,
        "threshold": 0.10,
        "p_value": 0.002,
        "controls_applied": [
            {"control_id": "MEASURE 2.11", "title": "Fairness evaluated"}
        ],
        "supporting_evidence": ["group_small"],
    }

    explanation = build_plain_explanation(finding)
    assert explanation.small_group_caveat is not None
    assert "group_small" in explanation.small_group_caveat
    assert explanation.source == "deterministic"


def test_build_plain_explanation_anomaly():
    finding = {
        "finding_type": "anomaly_finding",
        "severity_tier": "informational",
        "source_record_id": "REC-999",
        "observed_value": -0.725,
        "top_contributing_features": ["amount", "age"],
        "controls_applied": [
            {"control_id": "MEASURE 2.4", "title": "Input integrity"}
        ],
    }

    explanation = build_plain_explanation(finding)
    assert "REC-999" in explanation.what_we_found
    assert len(explanation.remediation_ids) > 0
    assert explanation.source == "deterministic"

    result = verify_plain_explanation(explanation, finding)
    assert result.passed, f"Verifier failed with violations: {result.violations}"
