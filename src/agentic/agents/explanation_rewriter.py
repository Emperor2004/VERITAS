"""
Agent-5: Explanation Rewriter Tool for VERITAS.

Optionally improves the readability and narrative flow of deterministic PlainExplanation
drafts using an LLM, strictly bound by the ExplanationVerifier:
  1. Starts with the deterministic PlainExplanation draft (from Stage A).
  2. If llm_client is configured, asks LLM to polish wording only.
  3. Validates the rewrite with explanation_verifier.py:
     - All numbers must trace back to the source finding.
     - All NIST control IDs must match controls_applied.
     - All remediation IDs must exist in the catalog.
     - No forbidden phrases (certifications, bias-free claims, GOVERN scope).
  4. On verification pass: returns rewritten PlainExplanation with source="llm".
  5. On verification failure or error: falls back 100% safely to deterministic draft.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import replace
from typing import Any, Dict, Optional, Tuple

from src.compliance_mapping.plain_explanation import PlainExplanation
from src.compliance_mapping.explanation_verifier import verify_plain_explanation

logger = logging.getLogger(__name__)


def rewrite_explanation(
    finding: Dict[str, Any],
    deterministic_draft: PlainExplanation,
    llm_client: Optional[Any] = None,
) -> Tuple[PlainExplanation, str]:
    """
    Attempt to polish an explanation using LLM behind the verifier gate.

    Returns
    -------
    (PlainExplanation, source_str) where source_str is "llm" or "deterministic".
    """
    if llm_client is None:
        return deterministic_draft, "deterministic"

    prompt = (
        "You are an expert AI auditor improving the clarity of an audit finding summary for executive leadership.\n"
        "Rewrite the 'what_we_found' and 'why_it_matters' sections of the finding draft below.\n\n"
        "STRICT CONSTRAINTS (Violations will cause automatic rejection):\n"
        "1. DO NOT change, add, or round any numbers or percentages. Use the EXACT numbers from the draft.\n"
        "2. DO NOT mention any NIST control IDs that are not already present in the draft.\n"
        "3. DO NOT claim the system is 'certified', 'fully compliant', 'bias-free', or 'guarantees fairness'.\n"
        "4. DO NOT reference the NIST GOVERN function.\n"
        "5. Keep the narrative concise, objective, and clear.\n\n"
        f"Original Draft:\n"
        f"what_we_found: {deterministic_draft.what_we_found}\n"
        f"why_it_matters: {deterministic_draft.why_it_matters}\n\n"
        "Respond ONLY with a valid JSON object matching:\n"
        "{\n"
        '  "what_we_found": "...",\n'
        '  "why_it_matters": "..."\n'
        "}"
    )

    try:
        from src.agentic.llm_client import extract_text_from_response

        response = llm_client.invoke(prompt)
        text = extract_text_from_response(response)
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            logger.info("Agent-5 rewrite did not return valid JSON; using deterministic draft.")
            return deterministic_draft, "deterministic"

        data = json.loads(json_match.group(0))
        new_what = data.get("what_we_found", "").strip()
        new_why = data.get("why_it_matters", "").strip()

        if not new_what or not new_why:
            return deterministic_draft, "deterministic"

        candidate = replace(
            deterministic_draft,
            what_we_found=new_what,
            why_it_matters=new_why,
            source="llm",
        )

        # Run strict verifier
        verification = verify_plain_explanation(candidate, finding)
        if verification.passed:
            return candidate, "llm"
        else:
            logger.info(
                "Agent-5 LLM rewrite rejected by verifier: %s. Using deterministic draft.",
                verification.violations,
            )
            return deterministic_draft, "deterministic"
    except Exception as exc:
        logger.warning("Agent-5 explanation rewrite encountered error: %s", exc)
        return deterministic_draft, "deterministic"
