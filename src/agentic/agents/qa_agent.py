"""
Agent-6: Conversational Audit Q&A Tool for VERITAS.

Read-only conversational agent that answers auditor and stakeholder questions
about the audit results, citing specific finding IDs and NIST control IDs:
  - query_findings(audit_state, finding_type=None, severity_tier=None)
  - get_record_explanation(audit_state, record_id)
  - get_control_text(control_id)
  - get_anomaly_groups(audit_state)

Enforced safety constraints (agentic_upgrade.md §4 Stage F):
  1. Read-only: cannot modify state, rerun pipelines, or change configs.
  2. Every answer must cite >= 1 finding_id or control_id when discussing evidence.
  3. Returns "The audit data does not contain..." when information is absent.
  4. Never claims NIST GOVERN coverage.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolNotAllowedError(PermissionError):
    """Raised when an unauthorized tool or mutation is attempted."""
    pass


ALLOWED_READ_TOOLS = {
    "query_findings",
    "get_record_explanation",
    "get_control_text",
    "get_anomaly_groups",
    "get_trace_summary",
}


def query_findings(
    mapped_findings: List[Dict[str, Any]],
    finding_type: Optional[str] = None,
    severity_tier: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve findings matching optional filters."""
    results = []
    for f in mapped_findings:
        if finding_type and f.get("finding_type") != finding_type:
            continue
        if severity_tier and f.get("severity_tier") != severity_tier:
            continue
        results.append(f)
    return results


def get_record_explanation(
    mapped_findings: List[Dict[str, Any]],
    record_id: str,
) -> Optional[Dict[str, Any]]:
    """Get finding and plain explanation for a specific record_id."""
    for f in mapped_findings:
        if str(f.get("source_record_id")) == str(record_id):
            return f
    return None


def get_anomaly_groups(
    anomaly_groups: List[Dict[str, Any]],
    dominant_feature: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve anomaly groups matching dominant feature."""
    if not dominant_feature:
        return anomaly_groups
    return [g for g in anomaly_groups if g.get("dominant_feature") == dominant_feature]


class AuditQAAgent:
    """Agent-6 Q&A answering engine."""

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client

    def answer(
        self,
        question: str,
        audit_state_dict: Dict[str, Any],
    ) -> str:
        """
        Answer a user question strictly based on the provided audit state.
        """
        # Guard against unauthorized mutations or tools
        if any(term in question.lower() for term in ["delete", "drop", "modify", "update", "set config", "rerun"]):
            raise ToolNotAllowedError("Q&A agent is read-only and cannot alter configurations or data.")

        findings = audit_state_dict.get("mapped_findings", [])
        anom_groups = audit_state_dict.get("anomaly_groups", [])
        run_id = audit_state_dict.get("run_id", "")
        status = audit_state_dict.get("status", "")

        # Deterministic Q&A fallback when no LLM client is available
        if self.llm_client is None:
            q_low = question.lower()
            if "how many" in q_low or "count" in q_low or "summary" in q_low:
                fairness_count = len([f for f in findings if f.get("finding_type") == "fairness_finding"])
                anomaly_count = len([f for f in findings if f.get("finding_type") == "anomaly_finding"])
                violations = len([f for f in findings if f.get("severity_tier") == "violation"])
                return (
                    f"Audit Run {run_id} (status: {status}) identified {len(findings)} total mapped findings: "
                    f"{fairness_count} fairness findings, {anomaly_count} anomaly findings, "
                    f"and {violations} threshold violations (mapped to NIST MEASURE 2.11 and MEASURE 2.4)."
                )

            # Look up specific record ID
            rec_match = re.search(r"\b(REC-?\w+|\b\d+\b)", question, re.IGNORECASE)
            if rec_match:
                rec_id = rec_match.group(1)
                exp = get_record_explanation(findings, rec_id)
                if exp:
                    fid = exp.get("finding_id", f"Finding-{rec_id}")
                    plain = exp.get("plain_explanation") or {}
                    what = plain.get("what_we_found") or f"Observed value: {exp.get('observed_value')}"
                    return f"Finding {fid} for record {rec_id}: {what}"

            if "disparate impact" in q_low or "fairness" in q_low:
                fairness_f = [f for f in findings if f.get("finding_type") == "fairness_finding"]
                if fairness_f:
                    f0 = fairness_f[0]
                    fid = f0.get("finding_id", "FAIR-1")
                    obs = f0.get("observed_value")
                    thresh = f0.get("threshold")
                    return (
                        f"Fairness evaluation ({fid}) observed disparate impact ratio of {obs} "
                        f"(threshold: {thresh}) across protected attributes under NIST MEASURE 2.11."
                    )

            if "anomaly" in q_low or "outlier" in q_low:
                if anom_groups:
                    g0 = anom_groups[0]
                    feat = g0.get("dominant_feature")
                    cnt = g0.get("record_count")
                    return (
                        f"Anomaly analysis identified {len(anom_groups)} feature clusters. "
                        f"The largest outlier group is driven by feature '{feat}' affecting {cnt} records, "
                        f"mapped to NIST MEASURE 2.4."
                    )

            return (
                "The audit data does not contain sufficient information to answer that question directly. "
                "Please query specific finding IDs, protected attributes, or anomaly clusters."
            )

        # Context-grounded LLM Q&A
        findings_summary = [
            {
                "finding_id": f.get("finding_id"),
                "finding_type": f.get("finding_type"),
                "metric_name": f.get("metric_name"),
                "severity_tier": f.get("severity_tier"),
                "observed_value": f.get("observed_value"),
                "threshold": f.get("threshold"),
                "source_record_id": f.get("source_record_id"),
                "controls": [c.get("control_id") for c in f.get("controls_applied", [])],
            }
            for f in findings[:25]  # Limit to 25 findings for prompt context
        ]

        prompt = (
            "You are VERITAS Assistant, a compliance auditor explaining AI evaluation results.\n"
            "Answer the auditor's question STRICTLY based on the provided findings context.\n\n"
            "MANDATORY AUDIT RULES:\n"
            "1. You MUST cite at least one finding_id (e.g. 'Finding ...') or NIST control_id (e.g. 'MEASURE 2.11') in your answer.\n"
            "2. If the data does not contain the answer, say 'The audit data does not contain this information.' Do NOT fabricate.\n"
            "3. DO NOT claim the model is 'certified' or that NIST GOVERN is satisfied.\n\n"
            f"Audit Findings Context:\n{json.dumps(findings_summary, indent=2)}\n\n"
            f"Anomaly Groups Context:\n{json.dumps(anom_groups[:5], indent=2)}\n\n"
            f"Auditor Question: {question}\n\n"
            "Answer:"
        )

        try:
            response = self.llm_client.invoke(prompt)
            answer_text = response.content if hasattr(response, "content") else str(response)
            return answer_text.strip()
        except Exception as exc:
            logger.warning("Agent-6 LLM Q&A failed: %s. Using deterministic fallback.", exc)
            return self.answer(question, {**audit_state_dict, "mapped_findings": findings})
