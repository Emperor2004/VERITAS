# VERITAS System Architecture

**VERITAS** (**V**erifiable **E**vidence & **R**isk **I**dentification **T**oolkit for **A**I **S**ystems) is an automated audit pipeline that treats machine learning models as the *subject* of an audit rather than the auditor. It evaluates prediction event logs, identifies statistical anomalies and algorithmic fairness violations, maps them to citable **NIST AI RMF 1.0** controls, and generates verifiable audit artifacts.

---

## 1. High-Level Architecture & Pipeline Topology

VERITAS follows an event-driven, decoupled pipeline where modules communicate through strict, versioned JSON data contracts.

```
                    ┌────────────────────────┐
                    │      Raw Dataset       │
                    │   (UCI Adult Income)   │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ Phase 1: Ingestion &   │
                    │ Synthetic Logging      │
                    └───────────┬────────────┘
                                │ normalized_log.json
                    ┌───────────┴────────────┐
                    │                        │
                    ▼                        ▼
        ┌────────────────────────┐  ┌────────────────────────┐
        │   Phase 2: Anomaly     │  │   Phase 3: Fairness    │
        │      Detection         │  │       Scanner          │
        │   (IsolationForest)    │  │      (Fairlearn)       │
        └───────────┬────────────┘  └───────────┬────────────┘
                    │ anomaly_findings.json  │ fairness_findings.json
                    │ (per-record)           │ (aggregate per-attribute)
                    └───────────┬────────────┘
                                │
                                ▼ [Join / Reconciliation]
                    ┌────────────────────────┐
                    │ Phase 4: Compliance    │ ★ Core Novel Contribution
                    │     Mapping Engine     │   (NIST AI RMF Lookup)
                    └───────────┬────────────┘
                                │ mapped_findings.json
                                ▼
                    ┌────────────────────────┐
                    │ Phase 5: Report        │
                    │       Generator        │
                    └───────────┬────────────┘
                                │
                        ┌───────┴───────┐
                        ▼               ▼
                 audit_report.html  audit_report.pdf
```

### Dependency Graph & Parallelism
* **Phase 1 (Ingestion)** loads raw features, trains a stand-in prediction model (the audit subject), injects labeled operational anomalies, merges realistic synthetic operational metadata, and validates every record against `NormalizedLogRecord` schema.
* **Phase 2 (Anomaly Detection)** and **Phase 3 (Fairness Scanner)** run **in parallel**. Neither depends on the other; both independently consume the immutable `normalized_log.json`.
* **Phase 4 (Compliance Mapping)** serves as the formal **join barrier**. It blocks until both Phase 2 and Phase 3 produce outputs, reconciles their differing granularities (per-record vs per-group), evaluates severity tiers (`violation` vs `informational`), attaches verifiable audit evidence traces, and links findings to citable NIST controls.
* **Phase 5 (Report Generation)** ingests reconciled compliance mappings and generates human-auditable, self-contained HTML and PDF reports.

---

## 2. Core Architectural Principles

1. **Zero Label Leakage in Audit Subject**:
   The audit subject model simulates a black-box lending/income classification service. The operational anomaly ground truth (`ground_truth_operational_anomaly`) and the true ground-truth label (`true_label`) are strictly isolated and never fed into feature matrices during anomaly scoring or fairness evaluation.

2. **Strict Schema Boundaries (Fail Loudly)**:
   Every inter-module boundary is validated with Pydantic (`validate_records`, `validate_output`). Ill-formed records or missing keys fail loudly on record 0 rather than silently dropping data or producing partial audits.

3. **Dual Execution Models**:
   * **In-Memory Programmatic Pipeline (`VeritasPipeline`)**: Enables zero-copy, high-speed execution in memory (useful for unit tests, notebooks, and automated microservices) without reading/writing tens of megabytes of JSON between phases.
   * **Subprocess CLI Orchestration (`orchestrator.py`)**: Runs each phase as an isolated Python subprocess, capturing stdout/stderr and generating a cryptographically verifiable `run_manifest.json` containing SHA-256 hashes of all inputs, outputs, and configuration files.

4. **Transparent Explainability Over Black-Box Scoring**:
   Anomaly findings are enriched with z-score feature contribution vectors (`top_contributing_features`) at the point of detection, giving human auditors clear rationale for why a transaction was flagged.

5. **Defensible Statistical Testing**:
   Fairness violations are not judged by arbitrary heuristics alone; they combine the regulatory EEOC 80% (four-fifths) rule with non-parametric permutation significance testing ($N \ge 1000$) to guarantee statistical significance while flagging small sample cohorts ($N < 30$).
