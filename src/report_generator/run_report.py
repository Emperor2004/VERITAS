"""
VERITAS Phase 5: report generation CLI entrypoint.

Matches the conventions of phases 1-4's entrypoints: argparse, reads a
JSON input, writes an output file.
"""
from __future__ import annotations

import argparse

from src.report_generator.html_report import write_html_report


def main():
    parser = argparse.ArgumentParser(description="VERITAS Phase 5: report generation")
    parser.add_argument("--input", required=True, help="Path to mapped_findings.json (phase 4 output)")
    parser.add_argument("--output", required=True, help="Path to write the HTML report")
    args = parser.parse_args()

    write_html_report(args.input, args.output)
    print(f"[phase5] report written -> {args.output}")


if __name__ == "__main__":
    main()
