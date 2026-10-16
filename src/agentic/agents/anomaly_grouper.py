"""
Agent-2: Anomaly Grouping Tool for VERITAS.

Groups flagged anomaly records by their dominant contributing feature
(highest absolute z-score in top_contributing_features) to transform
thousands of individual anomaly findings into concise, actionable summaries.

Determinism boundary:
  Grouping, record counting, mean z-scores, and representative records
  are computed 100% deterministically. Optional natural language summaries
  can be generated via LLM behind verification or template formatting.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AnomalyGroup:
    """Group of anomalies clustered by dominant contributing feature."""
    dominant_feature: str
    record_count: int
    record_ids: List[str]
    mean_z_score: float
    representative_record_id: str
    representative_score: float
    deterministic_summary: str
    llm_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dominant_feature": self.dominant_feature,
            "record_count": self.record_count,
            "record_ids": self.record_ids,
            "mean_z_score": round(self.mean_z_score, 4),
            "representative_record_id": self.representative_record_id,
            "representative_score": round(self.representative_score, 4),
            "deterministic_summary": self.deterministic_summary,
            "llm_summary": self.llm_summary,
        }


def group_anomalies(
    findings: List[Dict[str, Any] | Any],
    *,
    ground_truth_records: Optional[List[Dict[str, Any]]] = None,
) -> List[AnomalyGroup]:
    """
    Cluster anomaly findings by dominant contributing feature.

    Parameters
    ----------
    findings:
        List of AnomalyFinding objects or dicts. Only items with is_anomaly=True
        are clustered.
    ground_truth_records:
        Optional raw records with ground_truth_anomaly_type for roadmap breakdown.

    Returns
    -------
    List of AnomalyGroup sorted descending by record_count.
    """
    # 1. Filter to flagged anomalies
    flagged = []
    for f in findings:
        f_dict = f if isinstance(f, dict) else f.model_dump()
        if f_dict.get("is_anomaly"):
            flagged.append(f_dict)

    if not flagged:
        return []

    # 2. Cluster by dominant feature (feature with highest abs z_score)
    clusters: Dict[str, List[Dict[str, Any]]] = {}
    for item in flagged:
        contribs = item.get("top_contributing_features") or []
        if not contribs:
            dom_feat = "unknown_feature"
            z_score = 0.0
        else:
            # contrib can be ContributingFeature object or dict
            best_feat = "unknown_feature"
            best_z = 0.0
            for c in contribs:
                feat = c.get("feature") if isinstance(c, dict) else getattr(c, "feature", "")
                z = c.get("z_score") if isinstance(c, dict) else getattr(c, "z_score", 0.0)
                if abs(float(z)) > abs(best_z):
                    best_feat = feat
                    best_z = float(z)
            dom_feat = best_feat
            z_score = best_z

        item_enriched = dict(item)
        item_enriched["_dominant_z"] = z_score
        clusters.setdefault(dom_feat, []).append(item_enriched)

    # 3. Build AnomalyGroup for each cluster
    groups: List[AnomalyGroup] = []
    for feat, members in clusters.items():
        rec_ids = [m.get("record_id", "") for m in members]
        z_scores = [abs(float(m.get("_dominant_z", 0.0))) for m in members]
        mean_z = sum(z_scores) / len(z_scores) if z_scores else 0.0

        # Representative record is the one with the lowest anomaly_score (most anomalous)
        # or highest z_score
        rep_member = min(members, key=lambda m: float(m.get("anomaly_score", 0.0)))
        rep_id = rep_member.get("record_id", "")
        rep_score = float(rep_member.get("anomaly_score", 0.0))

        summary = (
            f"Feature '{feat}' is the primary outlier driver across {len(members)} records "
            f"(mean |z-score| = {mean_z:.2f}). "
            f"Most anomalous record: {rep_id} (score = {rep_score:.4f})."
        )

        groups.append(
            AnomalyGroup(
                dominant_feature=feat,
                record_count=len(members),
                record_ids=rec_ids,
                mean_z_score=mean_z,
                representative_record_id=rep_id,
                representative_score=rep_score,
                deterministic_summary=summary,
            )
        )

    # 4. Sort clusters by size descending
    groups.sort(key=lambda g: g.record_count, reverse=True)
    return groups


def calculate_per_type_breakdown(
    findings: List[Dict[str, Any] | Any],
    ground_truth_records: List[Dict[str, Any]],
) -> Dict[str, Dict[str, float]]:
    """
    Computes per-type precision and recall breakdown by ground_truth_anomaly_type.
    Closes the open README roadmap item.
    """
    record_truth: Dict[str, str] = {}
    for r in ground_truth_records:
        rid = str(r.get("record_id", ""))
        atype = r.get("ground_truth_anomaly_type")
        if atype:
            record_truth[rid] = str(atype)

    if not record_truth:
        return {}

    # Gather predictions
    flagged_ids = set()
    for f in findings:
        f_dict = f if isinstance(f, dict) else f.model_dump()
        if f_dict.get("is_anomaly"):
            flagged_ids.add(str(f_dict.get("record_id", "")))

    types = set(record_truth.values())
    breakdown = {}
    for t in types:
        truth_ids = {rid for rid, at in record_truth.items() if at == t}
        tp = len(truth_ids & flagged_ids)
        fn = len(truth_ids - flagged_ids)
        fp = len(flagged_ids - truth_ids)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        breakdown[t] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "total_ground_truth": len(truth_ids),
            "detected": tp,
        }

    return breakdown
