import json
import pytest
from unittest.mock import MagicMock

from src.compliance_mapping.plain_explanation import PlainExplanation, build_plain_explanation
from src.agentic.agents.explanation_rewriter import rewrite_explanation


@pytest.fixture
def sample_finding():
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
        "supporting_evidence": [],
    }


def test_rewrite_explanation_none_client_returns_deterministic(sample_finding):
    draft = build_plain_explanation(sample_finding)
    result, source = rewrite_explanation(sample_finding, draft, llm_client=None)
    assert source == "deterministic"
    assert result == draft


def test_rewrite_explanation_verifier_accepts_clean_rewrite(sample_finding):
    draft = build_plain_explanation(sample_finding)
    mock_llm = MagicMock()
    mock_response = MagicMock()
    # Contains valid exact numbers (0.65, 0.80) and no forbidden phrases
    mock_response.content = json.dumps({
        "what_we_found": "A disparate impact ratio of 0.65 was observed for gender.",
        "why_it_matters": "This metric falls below the 0.80 threshold, indicating potential group disparity.",
    })
    mock_llm.invoke.return_value = mock_response

    result, source = rewrite_explanation(sample_finding, draft, llm_client=mock_llm)
    assert source == "llm"
    assert "0.65" in result.what_we_found
    assert result.source == "llm"


def test_rewrite_explanation_verifier_rejects_forbidden_claims(sample_finding):
    draft = build_plain_explanation(sample_finding)
    mock_llm = MagicMock()
    mock_response = MagicMock()
    # Hallucinates compliance guarantee
    mock_response.content = json.dumps({
        "what_we_found": "The ratio is 0.65.",
        "why_it_matters": "This guarantees fairness and certifies the model.",
    })
    mock_llm.invoke.return_value = mock_response

    result, source = rewrite_explanation(sample_finding, draft, llm_client=mock_llm)
    # Must reject and fall back to deterministic draft
    assert source == "deterministic"
    assert result.what_we_found == draft.what_we_found


def test_rewrite_explanation_verifier_rejects_hallucinated_numbers(sample_finding):
    draft = build_plain_explanation(sample_finding)
    mock_llm = MagicMock()
    mock_response = MagicMock()
    # Hallucinates 0.42 not in source finding
    mock_response.content = json.dumps({
        "what_we_found": "The ratio dropped to 0.42 unexpectedly.",
        "why_it_matters": "This violates the 0.80 threshold.",
    })
    mock_llm.invoke.return_value = mock_response

    result, source = rewrite_explanation(sample_finding, draft, llm_client=mock_llm)
    assert source == "deterministic"
    assert result.what_we_found == draft.what_we_found
