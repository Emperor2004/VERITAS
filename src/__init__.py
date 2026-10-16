"""
VERITAS: Verifiable Evidence & Risk Identification Toolkit for AI Systems.

An automated AI-audit pipeline that ingests prediction logs from a classifier,
detects anomalies and fairness violations, and translates findings into citable
NIST AI RMF control mappings with generated audit evidence.
"""
from __future__ import annotations

from src.pipeline import PipelineArtifacts, VeritasPipeline
from src.run_config import RunConfig
from src.ingestion.log_loader import run_ingestion
from src.anomaly_detection.isolation_forest import run_anomaly_detection
from src.fairness_scanner.run_scan import run_fairness_scan
from src.compliance_mapping.run_mapping import run_mapping
from src.report_generator.html_report import render_html_report, write_html_report
from src.report_generator.pdf_report import check_weasyprint_available, write_pdf_report

__version__ = "0.2.0"

__all__ = [
    "VeritasPipeline",
    "PipelineArtifacts",
    "RunConfig",
    "run_ingestion",
    "run_anomaly_detection",
    "run_fairness_scan",
    "run_compliance_mapping",
    "render_html_report",
    "write_html_report",
    "write_pdf_report",
    "check_weasyprint_available",
]
