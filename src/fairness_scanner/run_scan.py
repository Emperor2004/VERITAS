"""
Phase 3 entrypoint: fairness scanning over the normalized log.

Usage:
    python -m src.fairness_scanner.run_scan \
        --input data/processed/normalized_log.json \
        --output outputs/logs/fairness_findings.json
"""
from __future__ import annotations
import argparse
import json
import os
import yaml

from src.fairness_scanner.metrics import (
    load_normalized_log,
    build_frame,
    compute_fairness_metrics_for_attribute,
    PROTECTED_COL_PREFIX,
)
from src.fairness_scanner.output_schema import validate_output


def main():
    parser = argparse.ArgumentParser(description="VERITAS Phase 3: fairness scanning")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    eeoc_threshold = config["fairness"]["disparate_impact_ratio_threshold"]
    min_group_size = config["fairness"]["min_group_size_warning"]

    print("[phase3] loading normalized log...")
    records = load_normalized_log(args.input)

    print("[phase3] building analysis frame...")
    df = build_frame(records)

    protected_cols = [c for c in df.columns if c.startswith(PROTECTED_COL_PREFIX)]
    print(f"[phase3] scanning protected attributes: "
          f"{[c.replace(PROTECTED_COL_PREFIX, '') for c in protected_cols]}")

    findings = []
    for col in protected_cols:
        finding = compute_fairness_metrics_for_attribute(df, col, eeoc_threshold, min_group_size)
        findings.append(finding)

        status = "VIOLATION" if finding["disparate_impact_violation"] else "within threshold"
        print(f"[phase3]   {finding['attribute']}: disparate_impact_ratio="
              f"{finding['disparate_impact_ratio']} ({status}, threshold={eeoc_threshold})")
        if finding["small_group_warning"]:
            print(f"[phase3]   WARNING: small group(s) for {finding['attribute']}: "
                  f"{finding['small_group_warning']} (n < {min_group_size}) -- "
                  f"ratio/difference metrics for this attribute may be statistically unstable")

    output = {
        "findings": findings,
        "config": {
            "eeoc_four_fifths_threshold": eeoc_threshold,
            "min_group_size_warning": min_group_size,
            "protected_attributes_scanned": [c.replace(PROTECTED_COL_PREFIX, "") for c in protected_cols],
        },
    }

    print("[phase3] validating output against schema...")
    validate_output(output)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[phase3] wrote {len(findings)} attribute findings to {args.output}")


if __name__ == "__main__":
    main()
