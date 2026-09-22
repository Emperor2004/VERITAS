"""
Compliance Mapping Engine (Phase 4) -- MVP test suite.

Grouped so each group can be named and defended independently:
happy path, sub-threshold/no-silent-discard, severity escalation,
reconciliation, explainability trace, fail-loud on unmapped/malformed.
"""
from __future__ import annotations

import yaml
import pytest

from src.compliance_mapping.input_reconciler import reconcile
from src.compliance_mapping.rules_engine import load_lookup_table, map_finding
from src.compliance_mapping.severity_policy import resolve_escalation


# ---- Happy path ------------------------------------------------------------

def test_anomaly_finding_maps_to_measure_2_4(lookup, sample_anomaly_finding_informational):
    result = map_finding(sample_anomaly_finding_informational, lookup)
    control_ids = [c.control_id for c in result.controls_applied]
    assert "MEASURE 2.4" in control_ids
    assert "MAP 5.1" in control_ids


def test_fairness_finding_maps_to_measure_2_11(lookup, sample_fairness_finding_informational):
    result = map_finding(sample_fairness_finding_informational, lookup)
    control_ids = [c.control_id for c in result.controls_applied]
    assert "MEASURE 2.11" in control_ids


# ---- Sub-threshold / no-silent-discard --------------------------------------

def test_informational_finding_still_produces_output(lookup, sample_fairness_finding_informational):
    result = map_finding(sample_fairness_finding_informational, lookup)
    assert result.severity_tier == "informational"
    assert result is not None


def test_informational_finding_does_not_escalate(lookup, sample_fairness_finding_informational):
    result = map_finding(sample_fairness_finding_informational, lookup)
    control_ids = [c.control_id for c in result.controls_applied]
    assert "MANAGE 1.3" not in control_ids
    assert "MANAGE 1.4" not in control_ids


# ---- Severity escalation -----------------------------------------------------

def test_violation_finding_escalates_to_manage(lookup, sample_fairness_finding_violation):
    result = map_finding(sample_fairness_finding_violation, lookup)
    control_ids = [c.control_id for c in result.controls_applied]
    assert "MANAGE 1.3" in control_ids
    assert "MANAGE 1.4" in control_ids


def test_anomaly_findings_never_escalate_by_design(lookup, sample_anomaly_finding_informational):
    # Locks in the (a) decision: anomaly severity is always informational,
    # no auto-escalation, until an externally-defensible cutoff exists.
    result = map_finding(sample_anomaly_finding_informational, lookup)
    control_ids = [c.control_id for c in result.controls_applied]
    assert "MANAGE 1.3" not in control_ids


def test_resolve_escalation_rejects_unresolved_dynamic_tier(lookup):
    # 'dynamic' is a YAML documentation placeholder -- it must never reach
    # this layer as a literal runtime value.
    with pytest.raises(ValueError):
        resolve_escalation("dynamic", lookup)


# ---- Reconciliation -----------------------------------------------------------

def test_reconciler_preserves_two_shapes_without_force_merge():
    anomaly = [{
        "record_id": "r1", "anomaly_score": -0.5, "is_anomaly": True,
        "top_contributing_features": [{"feature": "hour", "z_score": 3.1}],
    }]
    fairness = [{
        "attribute": "sex",
        "demographic_parity_difference": 0.02, "demographic_parity_violation": False,
        "disparate_impact_ratio": 0.9, "disparate_impact_violation": False,
        "equalized_odds_difference": 0.01, "equalized_odds_violation": False,
        "small_group_warning": [],
    }]
    results = list(reconcile(anomaly, fairness))
    assert results[0]["finding_type"] == "anomaly_finding"
    assert results[0]["metric_name"] is None          # per-record shape preserved
    fairness_results = [r for r in results if r["finding_type"] == "fairness_finding"]
    assert {r["metric_name"] for r in fairness_results} == {
        "disparate_impact_ratio", "demographic_parity_difference", "equalized_odds_difference"
    }


def test_reconciler_filters_out_non_anomalous_records():
    anomaly = [
        {"record_id": "r1", "anomaly_score": -0.1, "is_anomaly": False},
        {"record_id": "r2", "anomaly_score": 2.4, "is_anomaly": True},
    ]
    results = list(reconcile(anomaly, []))
    assert len(results) == 1
    assert results[0]["source_record_id"] == "r2"


def test_reconciler_unpacks_one_fairness_row_into_three_metric_findings():
    fairness = [{
        "attribute": "race",
        "demographic_parity_difference": 0.15, "demographic_parity_violation": True,
        "disparate_impact_ratio": 0.71, "disparate_impact_violation": True,
        "equalized_odds_difference": 0.03, "equalized_odds_violation": False,
        "small_group_warning": ["Amer-Indian-Eskimo"],
    }]
    results = list(reconcile([], fairness))
    assert len(results) == 3
    severities = {r["metric_name"]: r["severity_tier"] for r in results}
    assert severities["demographic_parity_difference"] == "violation"
    assert severities["disparate_impact_ratio"] == "violation"
    assert severities["equalized_odds_difference"] == "informational"
    assert all(r["supporting_evidence"] == ["Amer-Indian-Eskimo"] for r in results)


def test_reconciler_fails_loud_on_missing_field():
    anomaly = [{"record_id": "r1", "anomaly_score": -0.5}]  # missing is_anomaly
    with pytest.raises(ValueError):
        list(reconcile(anomaly, []))


# ---- Explainability trace -----------------------------------------------------

def test_every_mapped_finding_carries_matched_action_text(lookup, sample_fairness_finding_violation):
    result = map_finding(sample_fairness_finding_violation, lookup)
    for citation in result.controls_applied:
        assert citation.matched_action_text  # non-empty: specific text, not a bare ID


def test_trigger_explanation_names_the_specific_threshold(lookup, sample_fairness_finding_violation):
    result = map_finding(sample_fairness_finding_violation, lookup)
    assert "0.8" in result.trigger_explanation


# ---- Fail-loud on unmapped / malformed -----------------------------------------

def test_unmapped_finding_type_raises(lookup):
    bad = {"finding_type": "privacy_finding", "observed_value": 1, "severity_tier": "informational"}
    with pytest.raises(ValueError):
        map_finding(bad, lookup)


def test_malformed_lookup_table_fails_at_load_time(tmp_path, lookup):
    broken = dict(lookup)
    broken["finding_mappings"] = dict(broken["finding_mappings"])
    broken["finding_mappings"]["anomaly_finding"] = dict(broken["finding_mappings"]["anomaly_finding"])
    broken["finding_mappings"]["anomaly_finding"]["primary_control"] = "MEASURE_9_9"
    bad_path = tmp_path / "broken_lookup.yaml"
    bad_path.write_text(yaml.safe_dump(broken))
    with pytest.raises(ValueError):
        load_lookup_table(bad_path)