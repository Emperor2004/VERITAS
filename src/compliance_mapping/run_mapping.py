"""
VERITAS Phase 4: compliance mapping CLI entrypoint.

Matches the conventions of phases 1-3's entrypoints (log_loader.py,
isolation_forest.py, run_scan.py): argparse, reads a config file, writes
a JSON output file. This is the piece that was missing -- rules_engine.py
and input_reconciler.py were library functions with no file-based driver
until this file.
"""
from __future__ import annotations

import argparse
import json

from src.compliance_mapping.input_reconciler import reconcile
from src.compliance_mapping.rules_engine import load_lookup_table, map_finding


def run_mapping(anomaly_findings: list, fairness_findings: list, lookup: dict) -> list:
    """Reconcile both finding types and map each to its NIST control(s).
    Returns a list of plain dicts (MappedFinding.to_dict()), ready for
    json.dump -- kept separate from main() so tests can call this directly
    without touching argparse or the filesystem."""
    reconciled = reconcile(anomaly_findings, fairness_findings)
    return [map_finding(finding, lookup).to_dict() for finding in reconciled]


def main():
    parser = argparse.ArgumentParser(description="VERITAS Phase 4: compliance mapping")
    parser.add_argument("--anomaly-input", required=True, help="Path to anomaly_findings.json (phase 2 output)")
    parser.add_argument("--fairness-input", required=True, help="Path to fairness_findings.json (phase 3 output)")
    parser.add_argument(
        "--lookup",
        default="src/compliance_mapping/nist_control_lookup.yaml",
        help="Path to nist_control_lookup.yaml",
    )
    parser.add_argument("--output", required=True, help="Path to write mapped_findings.json")
    args = parser.parse_args()

    with open(args.anomaly_input) as f:
        anomaly_payload = json.load(f)
    with open(args.fairness_input) as f:
        fairness_payload = json.load(f)

    # Phase 2/3 output files wrap their records under a "findings" key
    # (see output_schema.py in each module) -- unwrap here, fail loudly if
    # that key is missing rather than silently mapping an empty list.
    anomaly_findings = anomaly_payload["findings"]
    fairness_findings = fairness_payload["findings"]

    lookup = load_lookup_table(args.lookup)  # validated at load time -- see rules_engine.py

    mapped = run_mapping(anomaly_findings, fairness_findings, lookup)

    with open(args.output, "w") as f:
        json.dump({"mapped_findings": mapped}, f, indent=2, default=str)

    n_violations = sum(1 for m in mapped if m["severity_tier"] == "violation")
    print(f"[phase4] mapped {len(mapped)} findings ({n_violations} violation-tier) -> {args.output}")


if __name__ == "__main__":
    main()
