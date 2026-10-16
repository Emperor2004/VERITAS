import pytest
from unittest.mock import MagicMock

from src.agentic.agents.qa_agent import (
    AuditQAAgent,
    ToolNotAllowedError,
    query_findings,
    get_record_explanation,
    get_anomaly_groups,
)


@pytest.fixture
def mock_audit_state():
    return {
        "run_id": "test-run-123",
        "status": "completed",
        "mapped_findings": [
            {
                "finding_id": "FINDING-FAIR-1",
                "finding_type": "fairness_finding",
                "metric_name": "disparate_impact_ratio",
                "severity_tier": "violation",
                "observed_value": 0.65,
                "threshold": 0.80,
                "source_record_id": "sex",
                "controls_applied": [{"control_id": "MEASURE 2.11"}],
                "plain_explanation": {
                    "what_we_found": "Disparate impact ratio is 0.65 for sex."
                },
            },
            {
                "finding_id": "FINDING-ANOM-1",
                "finding_type": "anomaly_finding",
                "severity_tier": "informational",
                "observed_value": -0.85,
                "source_record_id": "REC-999",
                "controls_applied": [{"control_id": "MEASURE 2.4"}],
                "plain_explanation": {
                    "what_we_found": "Outlier record with score -0.85."
                },
            },
        ],
        "anomaly_groups": [
            {
                "dominant_feature": "capital_gain",
                "record_count": 14,
                "mean_z_score": 3.8,
            }
        ],
    }


def test_qa_agent_answers_summary_with_citation(mock_audit_state):
    agent = AuditQAAgent(llm_client=None)
    response = agent.answer("Can you give me a summary of findings?", mock_audit_state)
    assert "test-run-123" in response
    assert "MEASURE 2.11" in response or "MEASURE 2.4" in response
    assert "2 total mapped findings" in response


def test_qa_agent_record_lookup(mock_audit_state):
    agent = AuditQAAgent(llm_client=None)
    response = agent.answer("What happened to REC-999?", mock_audit_state)
    assert "REC-999" in response
    assert "FINDING-ANOM-1" in response


def test_qa_agent_disallows_mutation_commands(mock_audit_state):
    agent = AuditQAAgent(llm_client=None)
    with pytest.raises(ToolNotAllowedError):
        agent.answer("Please delete the findings table.", mock_audit_state)

    with pytest.raises(ToolNotAllowedError):
        agent.answer("Update configuration to ignore age.", mock_audit_state)


def test_qa_agent_with_mock_llm(mock_audit_state):
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "According to Finding FINDING-FAIR-1, disparate impact ratio was 0.65 under MEASURE 2.11."
    mock_llm.invoke.return_value = mock_response

    agent = AuditQAAgent(llm_client=mock_llm)
    response = agent.answer("What is the fairness status?", mock_audit_state)
    assert "FINDING-FAIR-1" in response
    assert "MEASURE 2.11" in response
