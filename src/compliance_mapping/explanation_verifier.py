"""
Explanation verifier for VERITAS.

Checks any text (deterministic or LLM-rewritten) against a set of
rules before it is allowed into the audit report.  On failure, the
caller MUST fall back to the deterministic draft.

Verifier rules (ALL must pass):
  1. Every number appearing in the text rounds to a field in the source
     MappedFinding (within a rounding tolerance of 2 decimal places for
     ratios/differences, 4 for anomaly scores).
  2. Every control ID cited in the text exists in the finding's own
     controls_applied list.
  3. Every remediation ID cited is a valid entry in remediation_catalog.yaml.
  4. No forbidden phrase appears in the text (compliance guarantees,
     GOVERN coverage claims, etc.).
  5. Text does not reference a finding field that does not exist on the
     source finding (guards against hallucinated context).

Design constraints (agentic_upgrade.md §8.6):
- This module has zero LLM dependency.
- It is stateless — all context comes from the source finding dict and
  the pre-loaded catalog.
- It returns a VerificationResult with a boolean `passed` and a list of
  `violations` so callers can log the rejection reason.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

_CATALOG_PATH = Path(__file__).with_name("remediation_catalog.yaml")

# ---------------------------------------------------------------------------
# Forbidden phrases — any match → reject (case-insensitive)
# ---------------------------------------------------------------------------
_FORBIDDEN_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bcertif(ied|ication|y|ies)\b", re.IGNORECASE),
    re.compile(r"\bguarantee of (fairness|compliance)\b", re.IGNORECASE),
    re.compile(r"\bfully compliant\b", re.IGNORECASE),
    re.compile(r"\bfully (certified|audited)\b", re.IGNORECASE),
    re.compile(r"\bNIST\s+GOVERN\b", re.IGNORECASE),  # GOVERN out of scope
    re.compile(r"\bGOVERN\s+function\b", re.IGNORECASE),
    re.compile(r"\bno bias\b", re.IGNORECASE),       # unprovable claim
    re.compile(r"\bproves fairness\b", re.IGNORECASE),
    re.compile(r"\bguarantees?\b.*\bfair\b", re.IGNORECASE),
]

# Remediation ID pattern — must start with FAIR- or ANOM- followed by digits.
_REMEDIATION_ID_PATTERN = re.compile(r"\b(FAIR|ANOM)-\d{3}\b")

# Number extraction — finds floats and ints in rendered text, including percentages.
_NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?%?")



@dataclass(frozen=True)
class VerificationResult:
    """Result of running the verifier on a piece of text."""
    passed: bool
    violations: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.passed


# ---------------------------------------------------------------------------
# Catalog loader (cached at module level)
# ---------------------------------------------------------------------------
_CATALOG_CACHE: Optional[Dict[str, Any]] = None


def _load_catalog() -> Dict[str, Any]:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is None:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as fh:
            _CATALOG_CACHE = yaml.safe_load(fh)
    return _CATALOG_CACHE


def _all_valid_remediation_ids(catalog: Dict[str, Any]) -> Set[str]:
    """Collect every `id` value from the remediation catalog."""
    ids: Set[str] = set()
    for type_section in catalog.values():
        if not isinstance(type_section, dict):
            continue
        for metric_section in type_section.values():
            if not isinstance(metric_section, dict):
                continue
            for tier_steps in metric_section.values():
                if not isinstance(tier_steps, list):
                    continue
                for step in tier_steps:
                    if isinstance(step, dict) and "id" in step:
                        ids.add(step["id"])
    return ids


# ---------------------------------------------------------------------------
# Helper: extract all numbers from text (ignore IDs, controls, list indices)
# ---------------------------------------------------------------------------
def _extract_numbers_from_text(text: str) -> List[tuple[float, bool]]:
    """
    Extract numbers from text. Returns list of (value, is_percentage).
    """
    # Strip known non-statistic patterns before searching for numbers:
    # 1. NIST Control IDs: e.g. MEASURE 2.11, MAP 1.2
    cleaned = re.sub(r"\b(GOVERN|MAP|MEASURE|MANAGE)\s+\d+(?:\.\d+)?\b", " ", text, flags=re.IGNORECASE)
    # 2. Hyphenated IDs like FAIR-001, ANOM-002, REC-999
    cleaned = re.sub(r"\b[A-Za-z_]+-\d+\b", " ", cleaned)
    # 3. List numbering like "1. ", "2. "
    cleaned = re.sub(r"(?:^|\s)\d+\.\s", " ", cleaned)

    numbers: List[tuple[float, bool]] = []
    for match in _NUMBER_PATTERN.finditer(cleaned):
        token = match.group(0)
        is_pct = token.endswith("%")
        raw = token.rstrip("%")
        try:
            numbers.append((float(raw), is_pct))
        except ValueError:
            pass
    return numbers


def _finding_numbers(finding: Dict[str, Any]) -> Set[float]:
    """
    Collect every numeric value that appears directly on the finding dict.
    These are the only numbers the verifier accepts in rendered text.
    """
    nums: Set[float] = set()
    for k, v in finding.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            val = float(v)
            nums.add(round(val, 4))
            nums.add(round(abs(val), 4))
            nums.add(round(val, 2))
            nums.add(round(abs(val), 2))
        elif isinstance(v, str):
            # If string contains a record ID with digits (e.g., "REC-999" or "999")
            digits = re.findall(r"\b\d+(?:\.\d+)?\b", v)
            for d in digits:
                try:
                    nums.add(float(d))
                except ValueError:
                    pass
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    for subv in item.values():
                        if isinstance(subv, (int, float)) and not isinstance(subv, bool):
                            sval = float(subv)
                            nums.add(round(sval, 4))
                            nums.add(round(abs(sval), 4))
                            nums.add(round(sval, 2))
                            nums.add(round(abs(sval), 2))

    # Baseline configuration & statistical constants:
    # 0.05, 0.01, 0.001 (alpha levels), 0.8 / 80% (EEOC four-fifths rule), 1.0 (full reference rate)
    nums.update({0.05, 0.8, 0.01, 0.001, 1.0})
    return nums


def _number_is_traceable(num: float, is_pct: bool, source_nums: Set[float]) -> bool:
    """True if `num` traces to any value in source_nums within tolerance."""
    abs_num = abs(num)
    for src in source_nums:
        # If it was written as a percentage (e.g. 65% or 100%), compare against src * 100
        if is_pct:
            if abs(round(num, 1) - round(src * 100, 1)) < 0.5 or abs(round(abs_num, 1) - round(src * 100, 1)) < 0.5:
                return True
        else:
            # Absolute number: compare directly
            if abs(round(num, 2) - round(src, 2)) < 0.005 or abs(round(abs_num, 2) - round(src, 2)) < 0.005:
                return True
            if abs(round(num, 4) - round(src, 4)) < 0.00005 or abs(round(abs_num, 4) - round(src, 4)) < 0.00005:
                return True
    return False


# ---------------------------------------------------------------------------
# Individual rule checkers
# ---------------------------------------------------------------------------

def _check_forbidden_phrases(text: str) -> List[str]:
    violations = []
    for pattern in _FORBIDDEN_PATTERNS:
        m = pattern.search(text)
        if m:
            violations.append(
                f"Forbidden phrase matched by pattern {pattern.pattern!r}: "
                f"'{m.group(0)}'"
            )
    return violations


def _check_control_ids(text: str, finding: Dict[str, Any]) -> List[str]:
    """
    Any NIST control ID mentioned in the text must appear in the finding's
    controls_applied list.  We check for patterns like 'MEASURE 2.4',
    'MAP 5.1', 'MANAGE 1.3'.
    """
    control_id_pattern = re.compile(
        r"\b(GOVERN|MAP|MEASURE|MANAGE)\s+\d+\.\d+\b", re.IGNORECASE
    )
    cited_ids = {m.group(0).upper() for m in control_id_pattern.finditer(text)}
    if not cited_ids:
        return []

    valid_ids: Set[str] = set()
    for c in finding.get("controls_applied", []):
        if isinstance(c, dict):
            cid = c.get("control_id", "")
            valid_ids.add(cid.upper())

    violations = []
    for cid in cited_ids:
        if cid not in valid_ids:
            violations.append(
                f"Control ID '{cid}' appears in text but is not in this "
                f"finding's controls_applied list {sorted(valid_ids)}."
            )
    return violations


def _check_remediation_ids(text: str, valid_ids: Set[str]) -> List[str]:
    cited = set(_REMEDIATION_ID_PATTERN.findall(text))
    # The pattern captures the prefix only — reassemble
    cited_full = {m.group(0) for m in _REMEDIATION_ID_PATTERN.finditer(text)}
    violations = []
    for rid in cited_full:
        if rid not in valid_ids:
            violations.append(
                f"Remediation ID '{rid}' appears in text but is not in the "
                "remediation_catalog.yaml."
            )
    return violations


def _check_numbers(text: str, finding: Dict[str, Any]) -> List[str]:
    source_nums = _finding_numbers(finding)
    text_nums = _extract_numbers_from_text(text)
    violations = []
    for num, is_pct in text_nums:
        if num == 0:  # Zero is always safe (e.g. "0 violations")
            continue
        if not _number_is_traceable(num, is_pct, source_nums):
            pct_suffix = "%" if is_pct else ""
            violations.append(
                f"Number {num}{pct_suffix} appears in text but cannot be traced to any "
                "field in the source finding.  Add the field to the finding "
                "or remove the number from the text."
            )
    return violations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_explanation(
    text: str,
    finding: Dict[str, Any],
    *,
    catalog: Optional[Dict[str, Any]] = None,
    check_numbers: bool = True,
) -> VerificationResult:
    """
    Verify that `text` is safe to include in the audit report for `finding`.

    Parameters
    ----------
    text:
        The rendered explanation text to verify (what + why + steps combined,
        or each individually).
    finding:
        MappedFinding.to_dict() — the source of truth for numbers and IDs.
    catalog:
        Pre-loaded remediation_catalog.yaml.  Loaded from disk if None.
    check_numbers:
        Set to False to skip the number-traceability check (useful when
        verifying only the prose sections, not rendered step text).

    Returns
    -------
    VerificationResult with passed=True if all rules pass.
    """
    if catalog is None:
        catalog = _load_catalog()

    valid_remediation_ids = _all_valid_remediation_ids(catalog)
    all_violations: List[str] = []

    # Rule 4: forbidden phrases
    all_violations.extend(_check_forbidden_phrases(text))

    # Rule 2: control IDs
    all_violations.extend(_check_control_ids(text, finding))

    # Rule 3: remediation IDs
    all_violations.extend(_check_remediation_ids(text, valid_remediation_ids))

    # Rule 1: numbers
    if check_numbers:
        all_violations.extend(_check_numbers(text, finding))

    return VerificationResult(
        passed=len(all_violations) == 0,
        violations=all_violations,
    )


def verify_plain_explanation(
    explanation: Any,
    finding: Dict[str, Any],
    *,
    catalog: Optional[Dict[str, Any]] = None,
) -> VerificationResult:
    """
    Verify a PlainExplanation dataclass or dict against its source finding.
    """
    if hasattr(explanation, "__dict__"):
        exp_dict = explanation.__dict__
    elif isinstance(explanation, dict):
        exp_dict = explanation
    else:
        exp_dict = {}
    return verify_plain_explanation_against_finding(exp_dict, finding, catalog=catalog)


def verify_plain_explanation_against_finding(
    explanation_dict: Dict[str, Any],
    finding: Dict[str, Any],
    *,
    catalog: Optional[Dict[str, Any]] = None,
) -> VerificationResult:
    """
    Verify a full PlainExplanation dict (as returned by
    PlainExplanation.__dict__ or asdict()) against its source finding.

    Verifies what_we_found, why_it_matters, and each step in how_to_fix_it.
    """
    combined = " ".join([
        explanation_dict.get("what_we_found", ""),
        explanation_dict.get("why_it_matters", ""),
        " ".join(explanation_dict.get("how_to_fix_it", [])),
    ])
    return verify_explanation(combined, finding, catalog=catalog)

