import pytest
from src.compliance_mapping.explanation_verifier import (
    verify_explanation,
    verify_plain_explanation,
    VerificationResult,
)
from src.compliance_mapping.plain_explanation import PlainExplanation


@pytest.fixture
def base_finding():
    return {
        "finding_type": "fairness_finding",
        "metric_name": "disparate_impact_ratio",
        "severity_tier": "violation",
        "attribute": "gender",
        "observed_value": 0.65,
        "threshold": 0.80,
        "controls_applied": [
            {"control_id": "MEASURE 2.11", "title": "Fairness evaluated"}
        ],
    }


def test_verifier_rejects_forbidden_phrases(base_finding):
    forbidden_examples = [
        "This model is certified compliant.",
        "We provide a guarantee of fairness.",
        "The system has no bias.",
        "This fully complies with the NIST GOVERN framework.",
    ]
    for text in forbidden_examples:
        res = verify_explanation(text, base_finding, check_numbers=False)
        assert not res.passed
        assert any("Forbidden phrase" in v for v in res.violations)


def test_verifier_rejects_hallucinated_numbers(base_finding):
    # base finding has 0.65 and 0.80. Number 99.99 is not traceable.
    text = "The model disparate impact ratio was 99.99 which is unusual."
    res = verify_explanation(text, base_finding)
    assert not res.passed
    assert any("Number 99.99" in v for v in res.violations)


def test_verifier_accepts_traceable_numbers(base_finding):
    text = "The model disparate impact ratio was 0.65 below the 0.80 threshold."
    res = verify_explanation(text, base_finding)
    assert res.passed, f"Failed with: {res.violations}"


def test_verifier_rejects_invalid_control_ids(base_finding):
    # base_finding has MEASURE 2.11. Citing MANAGE 1.3 should fail if not in controls_applied.
    text = "This triggers MANAGE 1.3 for mitigation."
    res = verify_explanation(text, base_finding, check_numbers=False)
    assert not res.passed
    assert any("Control ID 'MANAGE 1.3'" in v for v in res.violations)


def test_verifier_rejects_invalid_remediation_ids(base_finding):
    text = "Apply step FAIR-999 to mitigate."
    res = verify_explanation(text, base_finding, check_numbers=False)
    assert not res.passed
    assert any("Remediation ID 'FAIR-999'" in v for v in res.violations)
