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
    anomaly = [{"record_id": "r1", "anomaly_score": -0.5, "severity_tier": "informational"}]
    fairness = [{
        "protected_attribute": "sex", "metric_name": "disparate_impact_ratio",
        "observed_value": 0.9, "severity_tier": "informational",
    }]
    results = list(reconcile(anomaly, fairness))
    assert len(results) == 2
    assert results[0]["finding_type"] == "anomaly_finding"
    assert results[0]["metric_name"] is None
    assert results[1]["finding_type"] == "fairness_finding"
    assert results[1]["metric_name"] == "disparate_impact_ratio"


def test_reconciler_fails_loud_on_missing_field():
    anomaly = [{"record_id": "r1", "anomaly_score": -0.5}]  # missing severity_tier
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