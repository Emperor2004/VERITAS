"""
VERITAS Unified Modular Pipeline.

Provides the programmatic, in-memory pipeline interface for VERITAS,
allowing all five phases to be executed either sequentially or individually
without requiring subprocess boundaries or intermediate JSON disk serialization.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from src.ingestion.log_loader import run_ingestion
from src.anomaly_detection.isolation_forest import run_anomaly_detection
from src.fairness_scanner.run_scan import run_fairness_scan
from src.compliance_mapping.run_mapping import run_mapping
from src.compliance_mapping.rules_engine import load_lookup_table
from src.report_generator.html_report import render_html_report, write_html_report
from src.report_generator.pdf_report import write_pdf_report


@dataclass
class PipelineArtifacts:
    """Holds data artifacts produced during pipeline execution."""
    normalized_logs: Optional[List[Dict[str, Any]]] = None
    anomaly_output: Optional[Dict[str, Any]] = None
    fairness_output: Optional[Dict[str, Any]] = None
    mapped_findings: Optional[List[Dict[str, Any]]] = None
    report_html: Optional[str] = None
    report_pdf_generated: bool = False


class VeritasPipeline:
    """Modular, programmatic interface for running the VERITAS audit pipeline."""

    def __init__(
        self,
        config: Dict[str, Any],
        lookup_path: str | Path = "src/compliance_mapping/nist_control_lookup.yaml",
    ):
        self.config = config
        self.lookup_path = Path(lookup_path)
        self._lookup_table = None

    @classmethod
    def from_config_file(
        cls,
        config_path: str | Path = "config/config.yaml",
        lookup_path: str | Path = "src/compliance_mapping/nist_control_lookup.yaml",
    ) -> VeritasPipeline:
        """Instantiate pipeline from a YAML configuration file path."""
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cls(config=cfg, lookup_path=lookup_path)

    @property
    def lookup_table(self) -> Dict[str, Any]:
        """Lazy-loaded, validated NIST control lookup table."""
        if self._lookup_table is None:
            self._lookup_table = load_lookup_table(self.lookup_path)
        return self._lookup_table

    def run_ingestion(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Phase 1: Ingest dataset, engineer features, inject anomalies, return normalized logs."""
        return run_ingestion(self.config, limit=limit)

    def run_anomaly_detection(
        self,
        records: List[Dict[str, Any]],
        contamination_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Phase 2: Detect operational and statistical anomalies via IsolationForest."""
        ad_cfg = self.config.get("anomaly_detection", {})
        random_state = ad_cfg.get("random_state", 42)
        n_estimators = ad_cfg.get("n_estimators", 100)
        return run_anomaly_detection(
            records=records,
            random_state=random_state,
            n_estimators=n_estimators,
            contamination_override=contamination_override,
        )

    def run_fairness_scan(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Phase 3: Compute disparate impact, parity difference, and equalized odds."""
        return run_fairness_scan(records, self.config)

    def run_compliance_mapping(
        self,
        anomaly_output: Dict[str, Any],
        fairness_output: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Phase 4: Reconcile findings and map them to NIST AI RMF controls."""
        anomaly_findings = anomaly_output.get("findings", [])
        fairness_findings = fairness_output.get("findings", [])
        return run_mapping(anomaly_findings, fairness_findings, self.lookup_table)

    def generate_html_report(self, mapped_findings: List[Dict[str, Any]]) -> str:
        """Phase 5: Render standalone HTML audit report."""
        return render_html_report(mapped_findings)

    def run_all(
        self,
        limit: Optional[int] = None,
        save_artifacts: bool = False,
        output_dir: str | Path = "outputs",
        generate_pdf: bool = False,
    ) -> PipelineArtifacts:
        """Execute all phases in sequence in-memory.

        Args:
            limit: Optional record count limit for Phase 1.
            save_artifacts: If True, writes JSON logs and report files to output_dir.
            output_dir: Base directory for output artifacts.
            generate_pdf: If True, renders a PDF from the DOCX report template.

        Returns:
            PipelineArtifacts: Container with all generated in-memory artifacts.
        """
        artifacts = PipelineArtifacts()

        # Phase 1: Ingestion
        artifacts.normalized_logs = self.run_ingestion(limit=limit)

        # Phase 2 & 3: Anomaly detection & Fairness scan
        artifacts.anomaly_output = self.run_anomaly_detection(artifacts.normalized_logs)
        artifacts.fairness_output = self.run_fairness_scan(artifacts.normalized_logs)

        # Phase 4: Compliance mapping
        artifacts.mapped_findings = self.run_compliance_mapping(
            artifacts.anomaly_output, artifacts.fairness_output
        )

        # Phase 5: Report generation
        artifacts.report_html = self.generate_html_report(artifacts.mapped_findings)

        out_path = Path(output_dir)
        logs_dir = out_path / "logs"
        reports_dir = out_path / "reports"

        if save_artifacts:
            logs_dir.mkdir(parents=True, exist_ok=True)
            reports_dir.mkdir(parents=True, exist_ok=True)

            with open(logs_dir / "anomaly_findings.json", "w", encoding="utf-8") as f:
                json.dump(artifacts.anomaly_output, f, indent=2)

            with open(logs_dir / "fairness_findings.json", "w", encoding="utf-8") as f:
                json.dump(artifacts.fairness_output, f, indent=2)

            with open(logs_dir / "mapped_findings.json", "w", encoding="utf-8") as f:
                json.dump({"mapped_findings": artifacts.mapped_findings}, f, indent=2, default=str)

            html_dest = reports_dir / "audit_report.html"
            html_dest.write_text(artifacts.report_html, encoding="utf-8")

        if generate_pdf:
            pdf_dest = reports_dir / "audit_report.pdf"
            artifacts.report_pdf_generated = write_pdf_report(artifacts.mapped_findings, pdf_dest)

        return artifacts
