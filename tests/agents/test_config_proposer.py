import json
import pytest
from unittest.mock import MagicMock

from src.agentic.agents.config_proposer import (
    propose_config,
    propose_config_deterministic,
    ConfigProposal,
)


@pytest.fixture
def sample_records():
    records = []
    for i in range(150):
        records.append({
            "record_id": f"REC-{i}",
            "prediction": 1 if i % 2 == 0 else 0,
            "actual": 1 if i % 3 == 0 else 0,
            "protected_attributes": {
                "sex": "Female" if i % 2 == 0 else "Male",
                "race": "GroupA" if i % 4 == 0 else "GroupB",
            },
            "zip_code": f"9021{i % 10}",
            "score": 500 + i * 2,
        })
    return records


def test_propose_config_deterministic(sample_records):
    proposal = propose_config(sample_records, llm_client=None)
    assert isinstance(proposal, ConfigProposal)
    assert proposal.source == "deterministic"
    assert "sex" in proposal.proposed_protected_attributes
    assert "race" in proposal.proposed_protected_attributes
    assert proposal.proposed_min_group_size >= 30
    assert any("zip_code" in w for w in proposal.proxy_feature_warnings)
    assert "0.05" in proposal.significance_level_recommendation


def test_propose_config_with_mock_llm(sample_records):
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "proposed_protected_attributes": ["sex", "race"],
        "proposed_min_group_size": 35,
        "proxy_feature_warnings": ["zip_code correlates with demographics"],
        "attribute_rationales": {
            "sex": "Binary gender class",
            "race": "Protected racial groups",
        },
        "group_size_rationale": "35 records ensures statistical stability.",
        "significance_level_recommendation": "Use α=0.05 per federal guidelines."
    })
    mock_llm.invoke.return_value = mock_response

    proposal = propose_config(sample_records, llm_client=mock_llm)
    assert proposal.source == "llm"
    assert proposal.proposed_min_group_size == 35
    assert "35 records" in proposal.group_size_rationale


def test_propose_config_empty_records():
    proposal = propose_config([], llm_client=None)
    assert proposal.proposed_protected_attributes == []
    assert proposal.proposed_min_group_size == 30
