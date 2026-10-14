"""
VERITAS Phase 5: report generation CLI entrypoint.

Matches the conventions of phases 1-4's entrypoints: argparse, reads a
JSON input, writes an output file.
"""
from __future__ import annotations

import argparse

from src.report_generator.html_report import load_mapped_findings, write_html_report
from src.report_generator.pdf_report import write_pdf_report


def main():
    parser = argparse.ArgumentParser(description="VERITAS Phase 5: report generation")
    parser.add_argument("--input", required=True, help="Path to mapped_findings.json (phase 4 output)")
    parser.add_argument("--output", required=True, help="Path to write the HTML report")
    parser.add_argument("--pdf-output", help="Optional path to write a PDF report")
    args = parser.parse_args()

    write_html_report(args.input, args.output)
    print(f"[phase5] report written -> {args.output}")
    if args.pdf_output:
        findings = load_mapped_findings(args.input)
        write_pdf_report(findings, args.pdf_output)
        print(f"[phase5] PDF report written -> {args.pdf_output}")


if __name__ == "__main__":
    main()
