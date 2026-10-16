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
from typing import Mapping
import yaml

from src.fairness_scanner.metrics import (
    load_normalized_log,
    build_frame,
    compute_fairness_metrics_for_attribute,
    PROTECTED_COL_PREFIX,
)
from src.fairness_scanner.output_schema import validate_output
from src.run_config import RunConfig


def run_fairness_scan(records: list, config: Mapping | RunConfig) -> dict:
    """Run fairness scan across all protected attributes present in records.

    Args:
        records: List of normalized log record dicts.
        config: Parsed configuration dictionary containing fairness settings.

    Returns:
        dict: Findings dictionary matching output_schema.py.
    """
    run_config = (
        config
        if isinstance(config, RunConfig)
        else RunConfig.from_project_config(config)
    )
    eeoc_threshold = run_config.disparate_impact_ratio_threshold
    min_group_size = run_config.min_group_size_warning
    significance_level = run_config.significance_level
    n_permutations = run_config.permutations
    permutation_random_state = run_config.permutation_random_state

    df = build_frame(records)
    available_attributes = [
        c.replace(PROTECTED_COL_PREFIX, "")
        for c in df.columns
        if c.startswith(PROTECTED_COL_PREFIX)
    ]
    if run_config.protected_attributes:
        missing_attributes = set(run_config.protected_attributes) - set(available_attributes)
        if missing_attributes:
            raise ValueError(
                "Configured protected attribute(s) missing from records: "
                f"{sorted(missing_attributes)}. Available attributes: {available_attributes}."
            )
        protected_cols = [
            f"{PROTECTED_COL_PREFIX}{attribute}"
            for attribute in run_config.protected_attributes
        ]
    else:
        protected_cols = [
            c for c in df.columns if c.startswith(PROTECTED_COL_PREFIX)
        ]

    findings = []
    for col in protected_cols:
        finding = compute_fairness_metrics_for_attribute(
            df, col, eeoc_threshold, min_group_size,
            significance_level=significance_level,
            n_permutations=n_permutations,
            permutation_random_state=permutation_random_state,
        )
        findings.append(finding)

    output = {
        "findings": findings,
        "config": {
            "eeoc_four_fifths_threshold": eeoc_threshold,
            "min_group_size_warning": min_group_size,
            "protected_attributes_scanned": [c.replace(PROTECTED_COL_PREFIX, "") for c in protected_cols],
        },
    }
    validate_output(output)
    return output


def main():
    parser = argparse.ArgumentParser(description="VERITAS Phase 3: fairness scanning")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = RunConfig.from_project_config(yaml.safe_load(f))

    print("[phase3] loading normalized log...")
    records = load_normalized_log(args.input)

    print("[phase3] scanning protected attributes...")
    output = run_fairness_scan(records, config)
    findings = output["findings"]
    eeoc_threshold = output["config"]["eeoc_four_fifths_threshold"]
    min_group_size = output["config"]["min_group_size_warning"]

    for finding in findings:
        status = "VIOLATION" if finding["disparate_impact_violation"] else "within threshold"
        print(f"[phase3]   {finding['attribute']}: disparate_impact_ratio="
              f"{finding['disparate_impact_ratio']} ({status}, threshold={eeoc_threshold})")
        print(f"[phase3]   {finding['attribute']}: demographic_parity_difference="
              f"{finding['demographic_parity_difference']} "
              f"({'VIOLATION' if finding['demographic_parity_violation'] else 'not significant'}, "
              f"p={finding['demographic_parity_p_value']})")
        print(f"[phase3]   {finding['attribute']}: equalized_odds_difference="
              f"{finding['equalized_odds_difference']} "
              f"({'VIOLATION' if finding['equalized_odds_violation'] else 'not significant'}, "
              f"p={finding['equalized_odds_p_value']})")
        if finding["small_group_warning"]:
            print(f"[phase3]   WARNING: small group(s) for {finding['attribute']}: "
                  f"{finding['small_group_warning']} (n < {min_group_size}) -- "
                  f"ratio/difference metrics for this attribute may be statistically unstable")

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[phase3] wrote {len(findings)} attribute findings to {args.output}")


if __name__ == "__main__":
    main()