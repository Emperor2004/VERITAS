"""
Deterministic plain-English explanation builder for VERITAS.

Reads explanation_templates.yaml and remediation_catalog.yaml to produce
a structured PlainExplanation for each MappedFinding.  This is the
deterministic draft.  Agent-5 may optionally improve the wording via LLM
rewrite, but only if the rewrite passes explanation_verifier.py.

Design constraints (from agentic_upgrade.md §2 and §8):
- Never calls an LLM.
- Only reads values that exist in the source MappedFinding dict.
- Returns a fully valid PlainExplanation even when optional fields
  (p_value, minority_group, etc.) are missing -- falls back to safe defaults.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

_TEMPLATE_PATH = Path(__file__).with_name("explanation_templates.yaml")
_CATALOG_PATH = Path(__file__).with_name("remediation_catalog.yaml")

# Forbidden phrases that must never appear in a finding explanation.
# The verifier checks these; we also avoid them here as a belt-and-suspenders.
FORBIDDEN_PHRASES: List[str] = [
    "certif",
    "guarantee of fairness",
    "guarantee of compliance",
    "fully compliant",
    "fully audit",
    "govern",        # NIST GOVERN function — out of scope by design
]


@dataclass
class RemediationStep:
    """One actionable fix step from the remediation catalog."""
    id: str
    text: str
    effort: str     # "low" | "medium" | "high"
    source: str


@dataclass
class PlainExplanation:
    """
    Structured plain-English explanation for one MappedFinding.

    Fields:
      what_we_found     -- 1-2 sentences describing the finding with numbers.
      why_it_matters    -- Risk in plain language.
      how_to_fix_it     -- Ordered list of rendered step texts.
      remediation_ids   -- Stable catalog IDs for the steps above.
      remediation_steps -- Full step objects (for downstream rendering).
      control_summary   -- e.g. "MEASURE 2.11; escalates to MANAGE 1.3, 1.4"
      small_group_caveat-- Emitted when the finding carries a small-group warning.
      source            -- "deterministic" always here; overwritten to "llm"
                           by Agent-5 if the verifier accepts the rewrite.
    """
    what_we_found: str
    why_it_matters: str
    how_to_fix_it: List[str]
    remediation_ids: List[str]
    remediation_steps: List[RemediationStep]
    control_summary: str
    small_group_caveat: Optional[str] = None
    source: str = "deterministic"


# ---------------------------------------------------------------------------
# Loader helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_templates() -> Dict[str, Any]:
    return _load_yaml(_TEMPLATE_PATH)


def _load_catalog() -> Dict[str, Any]:
    return _load_yaml(_CATALOG_PATH)


# Module-level cache so pipelines that process many findings don't reload.
_TEMPLATES: Optional[Dict[str, Any]] = None
_CATALOG: Optional[Dict[str, Any]] = None


def _templates() -> Dict[str, Any]:
    global _TEMPLATES
    if _TEMPLATES is None:
        _TEMPLATES = _load_templates()
    return _TEMPLATES


def _catalog() -> Dict[str, Any]:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = _load_catalog()
    return _CATALOG


# ---------------------------------------------------------------------------
# Template context builders
# ---------------------------------------------------------------------------

def _fairness_context(finding: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the format-map context for a fairness finding.

    Safe defaults are used for any field that may not be present so the
    template never raises KeyError on an unusual finding shape.
    """
    metric = finding.get("metric_name", "")
    observed = float(finding.get("observed_value", 0.0))
    evidence = finding.get("supporting_evidence") or []

    # Derive minority / majority from supporting_evidence if possible.
    # supporting_evidence for fairness findings is a list of small-group
    # warning strings (see explainability_trace.py).  Group selection rates
    # live on the original FairnessFinding but are NOT on MappedFinding;
    # we use safe placeholders so the text is still meaningful.
    group_selection_rates: Dict[str, float] = finding.get("group_selection_rates", {})
    if group_selection_rates:
        sorted_groups = sorted(group_selection_rates.items(), key=lambda kv: kv[1])
        minority_group = sorted_groups[0][0] if sorted_groups else "minority group"
        majority_group = sorted_groups[-1][0] if len(sorted_groups) > 1 else "reference group"
        minority_pct = sorted_groups[0][1] if sorted_groups else observed
        majority_pct = sorted_groups[-1][1] if len(sorted_groups) > 1 else 1.0
    else:
        minority_group = "the lower-rate group"
        majority_group = "the reference group"
        minority_pct = observed
        majority_pct = 1.0

    # p-value is stored as a top-level field on the MappedFinding dict when
    # the input_reconciler adds it; fall back gracefully.
    p_value = float(finding.get("p_value", finding.get("observed_p_value", 0.0)))
    significance_level = float(finding.get("significance_level", 0.05))
    attribute = finding.get("source_record_id", finding.get("attribute", "the protected attribute"))

    return {
        "attribute": attribute,
        "metric": metric,
        "observed_value": observed,
        "threshold": float(finding.get("threshold", 0.8)),
        "minority_group": minority_group,
        "majority_group": majority_group,
        "minority_pct": minority_pct,
        "majority_pct": majority_pct,
        "p_value": p_value,
        "significance_level": significance_level,
    }


def _anomaly_context(finding: Dict[str, Any]) -> Dict[str, Any]:
    evidence = finding.get("supporting_evidence") or []
    if evidence:
        feature_str = ", ".join(
            f"{f['feature']} (z={f['z_score']:.2f})"
            for f in evidence
            if isinstance(f, dict) and "feature" in f
        )
    else:
        feature_str = "no feature-level detail available"

    return {
        "source_record_id": finding.get("source_record_id", "unknown"),
        "observed_value": float(finding.get("observed_value", 0.0)),
        "top_features_str": feature_str,
    }


# ---------------------------------------------------------------------------
# Remediation step builders
# ---------------------------------------------------------------------------

def _get_catalog_steps(
    finding_type: str,
    metric_name: Optional[str],
    severity_tier: str,
    catalog: Dict[str, Any],
) -> List[RemediationStep]:
    """Look up catalog steps for this finding type × metric × tier."""
    if finding_type == "fairness_finding" and metric_name:
        bucket = catalog.get("fairness", {}).get(metric_name, {})
    elif finding_type == "anomaly_finding":
        bucket = catalog.get("anomaly", {}).get("is_anomaly", {})
    else:
        return []

    raw_steps = bucket.get(severity_tier, [])
    return [
        RemediationStep(
            id=s["id"],
            text=s["text"],
            effort=s.get("effort", "medium"),
            source=s.get("source", "internal_design_choice"),
        )
        for s in raw_steps
    ]


def _render_step(step: RemediationStep, ctx: Dict[str, Any]) -> str:
    """Fill placeholders in a catalog step's text using the finding context."""
    try:
        return step.text.format_map(ctx)
    except (KeyError, ValueError):
        return step.text  # Return template text unchanged if context is incomplete


# ---------------------------------------------------------------------------
# Control summary
# ---------------------------------------------------------------------------

def _build_control_summary(finding: Dict[str, Any]) -> str:
    """
    Build a one-line string listing control IDs and their function.
    e.g. "MEASURE 2.11 (Fairness evaluated); MAP 5.1; escalates to MANAGE 1.3, MANAGE 1.4"
    """
    controls = finding.get("controls_applied", [])
    if not controls:
        return "No NIST AI RMF controls mapped."

    parts = []
    for c in controls:
        cid = c.get("control_id", "")
        title = c.get("title", "")
        if title:
            parts.append(f"{cid} ({title})")
        else:
            parts.append(cid)
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Small-group caveat
# ---------------------------------------------------------------------------

def _build_small_group_caveat(finding: Dict[str, Any]) -> Optional[str]:
    evidence = finding.get("supporting_evidence") or []
    if finding.get("finding_type") == "fairness_finding" and evidence:
        group_list = ", ".join(str(g) for g in evidence)
        return (
            f"CAVEAT: group(s) {group_list} have fewer records than the minimum "
            "group-size threshold.  This result may be statistically unstable; "
            "a larger sample is needed before taking corrective action."
        )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_plain_explanation(
    finding: Dict[str, Any],
    *,
    templates: Optional[Dict[str, Any]] = None,
    catalog: Optional[Dict[str, Any]] = None,
) -> PlainExplanation:
    """
    Build the deterministic plain-English explanation for one MappedFinding.

    Parameters
    ----------
    finding:
        MappedFinding.to_dict() -- all fields are read-only; nothing is mutated.
    templates:
        Pre-loaded explanation_templates.yaml dict.  Loaded from disk if None.
    catalog:
        Pre-loaded remediation_catalog.yaml dict.  Loaded from disk if None.

    Returns
    -------
    PlainExplanation with source="deterministic".
    """
    if templates is None:
        templates = _templates()
    if catalog is None:
        catalog = _catalog()

    finding_type: str = finding.get("finding_type", "")
    metric_name: Optional[str] = finding.get("metric_name")
    severity_tier: str = finding.get("severity_tier", "informational")

    # ------------------------------------------------------------------
    # Build context for placeholder substitution
    # ------------------------------------------------------------------
    if finding_type == "fairness_finding":
        ctx = _fairness_context(finding)
        template_key = metric_name or "disparate_impact_ratio"
        type_templates = templates.get("fairness_finding", {})
    else:
        ctx = _anomaly_context(finding)
        template_key = "is_anomaly"
        type_templates = templates.get("anomaly_finding", {})

    metric_templates = type_templates.get(template_key, {})
    tier_templates = metric_templates.get(severity_tier, metric_templates.get("informational", {}))

    # ------------------------------------------------------------------
    # Fill what / why
    # ------------------------------------------------------------------
    raw_what = tier_templates.get("what", f"Finding: {finding_type} — {metric_name or 'anomaly'}")
    raw_why = tier_templates.get("why", "See the NIST AI RMF control citations for context.")

    try:
        what_we_found = raw_what.format_map(ctx)
    except (KeyError, ValueError):
        what_we_found = raw_what

    try:
        why_it_matters = raw_why.format_map(ctx)
    except (KeyError, ValueError):
        why_it_matters = raw_why

    # ------------------------------------------------------------------
    # Remediation steps
    # ------------------------------------------------------------------
    steps = _get_catalog_steps(finding_type, metric_name, severity_tier, catalog)
    rendered_steps = [_render_step(s, ctx) for s in steps]
    step_ids = [s.id for s in steps]

    # ------------------------------------------------------------------
    # Control summary
    # ------------------------------------------------------------------
    control_summary = _build_control_summary(finding)

    # ------------------------------------------------------------------
    # Small-group caveat
    # ------------------------------------------------------------------
    small_group_caveat = _build_small_group_caveat(finding)

    return PlainExplanation(
        what_we_found=what_we_found,
        why_it_matters=why_it_matters,
        how_to_fix_it=rendered_steps,
        remediation_ids=step_ids,
        remediation_steps=steps,
        control_summary=control_summary,
        small_group_caveat=small_group_caveat,
        source="deterministic",
    )


def build_plain_explanations_batch(
    findings: List[Dict[str, Any]],
) -> List[PlainExplanation]:
    """
    Build explanations for a list of MappedFinding dicts.

    Loads YAML files once and reuses them across the batch.
    """
    tmpl = _templates()
    cat = _catalog()
    return [build_plain_explanation(f, templates=tmpl, catalog=cat) for f in findings]


def attach_plain_explanations(
    findings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Attach plain_explanation dict and remediation_ids to a list of finding dicts.
    """
    tmpl = _templates()
    cat = _catalog()
    enriched = []
    for f in findings:
        exp = build_plain_explanation(f, templates=tmpl, catalog=cat)
        f_copy = dict(f)
        f_copy["plain_explanation"] = exp.__dict__
        f_copy["remediation_ids"] = exp.remediation_ids
        enriched.append(f_copy)
    return enriched

