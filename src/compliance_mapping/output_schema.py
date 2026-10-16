"""
Output schema for the Compliance Mapping Engine (Phase 4).

Defines the shape of a single entry in mapped_findings.json and validates
it on construction. Kept separate from rules_engine.py so report_generator.py
can import the schema without importing the mapping logic.

Schema changes are additive-only: any new field must be Optional with a
default value so the existing 95-test suite passes without modification.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .plain_explanation import PlainExplanation
VALID_FINDING_TYPES = {"anomaly_finding", "fairness_finding"}
VALID_SEVERITY_TIERS = {"informational", "violation"}


def build_finding_id(
    finding_type: str,
    source_record_id: Optional[str],
    metric_name: Optional[str],
) -> str:
    """Return a stable opaque ID for one source finding and metric."""
    identity = json.dumps(
        [finding_type, source_record_id or "", metric_name or ""],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return f"F-{digest}"


@dataclass(frozen=True)
class ControlCitation:
    """One NIST control cited for a finding, with the specific text matched."""
    control_id: str          # e.g. "MEASURE 2.4"
    title: str
    citation: str
    matched_action_text: str


@dataclass(frozen=True)
class MappedFinding:
    """One row of mapped_findings.json -- one input finding, fully traced.

    New fields (Stage A agentic upgrade):
      plain_explanation -- Optional[PlainExplanation] built by
                           compliance_mapping.plain_explanation; None until
                           the explanation layer runs.  Optional so all
                           pre-existing tests remain unaffected.
      remediation_ids   -- Stable catalog IDs from the remediation_catalog;
                           populated alongside plain_explanation.
    """
    finding_type: str                       # "anomaly_finding" | "fairness_finding"
    metric_name: Optional[str]              # None for anomaly_finding
    observed_value: float
    severity_tier: str                      # "informational" | "violation"
    controls_applied: List[ControlCitation] = field(default_factory=list)
    trigger_explanation: str = ""           # e.g. "ratio 0.71 < EEOC threshold 0.8"
    source_record_id: Optional[str] = None  # links back to the raw finding for audit trail
    supporting_evidence: Any = None         # e.g. top_contributing_features, small_group_warning
    plain_explanation: Optional[Any] = None # Optional[PlainExplanation] — Any avoids circular import
    remediation_ids: List[str] = field(default_factory=list)
    finding_id: str = field(init=False)

    def __post_init__(self) -> None:
        if self.finding_type not in VALID_FINDING_TYPES:
            raise ValueError(
                f"Unknown finding_type '{self.finding_type}'. Expected one of "
                f"{sorted(VALID_FINDING_TYPES)}. A genuinely new finding type "
                "requires a new nist_control_lookup.yaml entry AND a code change "
                "here -- it must not silently pass through."
            )
        if self.severity_tier not in VALID_SEVERITY_TIERS:
            raise ValueError(
                f"Unknown severity_tier '{self.severity_tier}' for finding_type "
                f"'{self.finding_type}'. Upstream (fairness_scanner / "
                "anomaly_detection) must resolve severity to a concrete tier "
                "before this stage -- 'dynamic' is a YAML documentation "
                "placeholder, not a runtime value."
            )
        object.__setattr__(
            self,
            "finding_id",
            build_finding_id(self.finding_type, self.source_record_id, self.metric_name),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)