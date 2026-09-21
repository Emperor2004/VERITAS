"""
Phase 4 rules engine -- the Compliance Mapping Engine's orchestrator.

Loads and validates nist_control_lookup.yaml once, then maps each
reconciled finding to its NIST control citation(s), applying severity
escalation and attaching an explainability trace. Fails loudly on any
unmapped finding_type or malformed lookup table.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Union

import yaml

from .explainability_trace import build_controls_applied, build_trigger_explanation
from .output_schema import MappedFinding
from .severity_policy import resolve_escalation


def load_lookup_table(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load nist_control_lookup.yaml and validate internal consistency: every
    control key referenced anywhere (finding_mappings, severity_tiers) must
    exist under `controls`. Deliberately load-time, not lookup-time, so a
    malformed table fails before any finding is processed.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        lookup = yaml.safe_load(f)

    controls = set(lookup.get("controls", {}).keys())

    for finding_type, mapping in lookup.get("finding_mappings", {}).items():
        for key in ("primary_control", "secondary_control"):
            ref = mapping.get(key)
            if ref and ref not in controls:
                raise ValueError(
                    f"finding_mappings.{finding_type}.{key} references unknown "
                    f"control '{ref}'. Known controls: {sorted(controls)}."
                )

    for tier_name, tier_cfg in lookup.get("severity_tiers", {}).items():
        for ref in tier_cfg.get("escalates_to", []):
            if ref not in controls:
                raise ValueError(
                    f"severity_tiers.{tier_name}.escalates_to references unknown "
                    f"control '{ref}'. Known controls: {sorted(controls)}."
                )

    return lookup


def map_finding(finding: Dict[str, Any], lookup: Dict[str, Any]) -> MappedFinding:
    """Map one reconciled finding (see input_reconciler.reconcile) to a MappedFinding."""
    finding_type = finding["finding_type"]
    mappings = lookup.get("finding_mappings", {})

    if finding_type not in mappings:
        raise ValueError(
            f"Unmapped finding_type '{finding_type}'. Every finding_type produced "
            "upstream must have a corresponding entry in nist_control_lookup.yaml's "
            "finding_mappings -- a new finding type implies a new detection module "
            "and requires a code + YAML change, not a silent skip."
        )

    mapping = mappings[finding_type]
    control_keys = [mapping["primary_control"]]
    if mapping.get("secondary_control"):
        control_keys.append(mapping["secondary_control"])

    severity_tier = finding["severity_tier"]
    control_keys.extend(resolve_escalation(severity_tier, lookup))

    return MappedFinding(
        finding_type=finding_type,
        metric_name=finding.get("metric_name"),
        observed_value=finding["observed_value"],
        severity_tier=severity_tier,
        controls_applied=build_controls_applied(control_keys, lookup),
        trigger_explanation=build_trigger_explanation(finding, lookup),
        source_record_id=finding.get("source_record_id"),
    )


def map_all(findings: Iterable[Dict[str, Any]], lookup: Dict[str, Any]) -> Iterator[MappedFinding]:
    for finding in findings:
        yield map_finding(finding, lookup)