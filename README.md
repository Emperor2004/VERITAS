# VERITAS

**V**erifiable **E**vidence & **R**isk **I**dentification **T**oolkit for **A**I **S**ystems

> An automated AI-audit pipeline that ingests prediction logs from a classifier, detects anomalies and fairness violations, and translates findings into citable NIST AI RMF control mappings with generated audit evidence.

**Status:** In development (AY 2026-27) · Final-year B.Tech capstone, AI & ML, SIT Pune · Sponsored by Optywise AI Solutions
**Project ID:** OPT-2

---

## Table of Contents

- [1. Overview](#1-overview)
- [2. Scope](#2-scope)
- [3. Architecture](#3-architecture)
- [4. Repository Structure](#4-repository-structure)
- [5. Tech Stack](#5-tech-stack)
- [6. Installation](#6-installation)
- [7. Configuration](#7-configuration)
- [8. Running VERITAS](#8-running-veritas)
- [9. Module Reference](#9-module-reference)
- [10. NIST AI RMF Mapping Approach](#10-nist-ai-rmf-mapping-approach)
- [11. Testing](#11-testing)
- [12. Known Limitations / Open Items](#12-known-limitations--open-items)
- [13. Roadmap](#13-roadmap)
- [14. Team](#14-team)
- [15. Academic Use Notice](#15-academic-use-notice)

---

## 1. Overview

VERITAS treats an AI system — specifically a tabular income/lending classifier — as the **subject of an audit**, not the tool performing one. It ingests a stream of prediction-event logs (synthetic, structured to resemble a bank's income-prediction service), and runs them through four independent stages:

1. Detect operational anomalies in prediction behavior.
2. Scan for statistical fairness violations across protected groups.
3. Translate any findings into specific, citable **NIST AI RMF** control IDs.
4. Generate a structured audit report (PDF/HTML) as evidence output.

The system does not certify compliance and does not interact with a production model. It produces **audit evidence artifacts** for a hypothetical audit exercise.

---

## 2. Scope

**In scope:**
- Synthetic log ingestion (structured prediction-event data)
- Unsupervised anomaly detection over log/prediction behavior
- Statistical fairness scanning (per-batch group metrics)
- Rules-based compliance mapping to NIST AI RMF control IDs
- Automated report generation (PDF/HTML)

**Out of scope:**
- Regulator-accepted certification of any kind
- Live/production model integration
- Multi-framework compliance support (NIST AI RMF only)
- Real user data of any kind

---

## 3. Architecture

VERITAS is built as four decoupled modules connected by fixed, versioned input/output contracts (JSON schemas), so each module can be developed, tested, and demoed independently.

**Dependency graph (not purely sequential):** Anomaly Detection and the Fairness & Bias Scanner both consume `normalized_log.json` directly from ingestion and have no dependency on one another — they run **in parallel**. The Compliance Mapping Engine is the actual join point: it blocks until *both* findings files exist.

```
                ┌────────────────────┐
                │   Log Ingestion     │
                │  & Preprocessing    │
                └─────────┬───────────┘
                          │  normalized_log.json
                          ▼
              ┌───────────┴────────────┐
              │                        │
              ▼                        ▼
   ┌────────────────────┐   ┌────────────────────┐
   │  Anomaly Detection  │   │  Fairness & Bias    │
   │  (IsolationForest)  │   │  Scanner (Fairlearn)│
   └─────────┬───────────┘   └─────────┬───────────┘
             │ anomaly_findings.json    │ fairness_findings.json
             └───────────┬──────────────┘
                         ▼  (join — waits on both)
                ┌────────────────────┐
                │ Compliance Mapping  │  ★ core contribution
                │      Engine         │
                └─────────┬───────────┘
                          │  mapped_findings.json
                          ▼
                ┌────────────────────┐
                │  Report Generator   │
                └─────────┬───────────┘
                          │
                          ▼
                  audit_report.pdf / .html
```

> **Note on the Compliance Mapping Engine:** this is the only module that is original work. Anomaly detection and fairness scanning use existing, well-established libraries (scikit-learn, Fairlearn) as-is, and run independently of each other. The rules-based translation layer — mapping a raw technical finding to a specific NIST AI RMF control ID with a defensible rationale — is what this project actually contributes.

---

## 4. Repository Structure

```
veritas/
├── README.md
├── requirements.txt
├── .env.example
├── config/
│   ├── config.yaml                 # global pipeline config
│   └── thresholds.yaml             # fairness/anomaly thresholds (EEOC 4/5ths etc.)
│
├── data/
│   ├── raw/                        # UCI Adult Income source files
│   ├── synthetic_logs/             # Faker-generated operational metadata, merged
│   └── processed/                  # normalized_log.json outputs
│
├── src/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── log_loader.py           # loads UCI Adult Income predictions
│   │   ├── synthetic_metadata.py   # Faker: timestamps, session IDs, auth methods
│   │   └── schema.py               # normalized_log.json schema + validation
│   │
│   ├── anomaly_detection/
│   │   ├── __init__.py
│   │   ├── isolation_forest.py     # IsolationForest wrapper
│   │   └── output_schema.py        # anomaly_findings.json schema
│   │
│   ├── fairness_scanner/
│   │   ├── __init__.py
│   │   ├── metrics.py              # demographic parity, equalized odds, disparate impact
│   │   ├── thresholds.py           # EEOC four-fifths rule logic
│   │   └── output_schema.py        # fairness_findings.json schema
│   │
│   ├── compliance_mapping/
│   │   ├── __init__.py
│   │   ├── rules_engine.py         # core lookup/translation logic
│   │   ├── nist_control_lookup.yaml # finding-type → NIST AI RMF control ID table
│   │   ├── explainability_trace.py # ⚠ NOT YET IMPLEMENTED — see §12
│   │   └── output_schema.py        # mapped_findings.json schema
│   │
│   ├── report_generator/
│   │   ├── __init__.py
│   │   ├── pdf_report.py
│   │   ├── html_report.py
│   │   └── templates/
│   │       ├── report_template.html
│   │       └── report_template.docx
│   │
│   └── orchestrator.py             # runs full pipeline end-to-end
│
├── tests/
│   ├── test_ingestion.py
│   ├── test_anomaly_detection.py
│   ├── test_fairness_scanner.py
│   ├── test_compliance_mapping.py
│   └── test_report_generator.py
│
├── outputs/
│   ├── logs/
│   └── reports/
│
└── docs/
    ├── architecture.md
    ├── nist_mapping_reference.md
    └── module_contracts.md         # JSON schema contracts between modules
```

Each module directory is independently runnable and independently testable. No module imports directly from another's internals — they communicate only via the JSON contracts in `docs/module_contracts.md`.

---

## 5. Tech Stack

| Layer | Tool / Library | Purpose |
|---|---|---|
| Anomaly Detection | `scikit-learn` (`IsolationForest`) | Unsupervised outlier detection over prediction logs |
| Fairness Scanning | `Fairlearn` | Demographic parity, equalized odds, disparate impact ratio |
| Synthetic Metadata | `Faker` | Timestamps, session IDs, auth methods layered onto real predictions |
| Compliance Mapping | Custom rules engine (Python, YAML-driven lookup) | Finding → NIST AI RMF control ID translation |
| Report Generation | `python-docx`, HTML/CSS, PDF export | Structured audit evidence output |
| Dataset | UCI Adult Income | Real classifier predictions and confidence scores |
| Compliance Reference | NIST AI RMF | Primary framework for control ID mapping |
| Fairness Threshold Standard | EEOC four-fifths rule (0.8 ratio) | External, defensible fairness threshold |

**Deliberately excluded from the core pipeline:** any LLM-based reasoning. The compliance mapping engine is a deterministic rules engine — no optional "LLM assist" path exists in this architecture. (This resolves a framing contradiction flagged in CA-1; see §12.)

---

## 6. Installation

```bash
# Clone repository
git clone <repo-url> veritas
cd veritas

# Create virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

**`requirements.txt` (core):**
```
scikit-learn>=1.4
fairlearn>=0.10
faker>=25.0
pyyaml>=6.0
python-docx>=1.1
jinja2>=3.1
weasyprint>=61.0        # HTML→PDF report rendering
pytest>=8.0
```

---

## 7. Configuration

All thresholds and pipeline parameters live in `config/`, not hardcoded in module logic — this is intentional so thresholds can be cited and changed without touching code.

**`config/thresholds.yaml`**
```yaml
fairness:
  disparate_impact_ratio:
    threshold: 0.8            # EEOC four-fifths rule
    source: "EEOC Uniform Guidelines on Employee Selection Procedures"
  demographic_parity_difference:
    threshold: 0.10           # placeholder — see §12, TC-02 unresolved
  equalized_odds_difference:
    threshold: 0.10           # placeholder — see §12, TC-03 unresolved

anomaly_detection:
  isolation_forest:
    contamination: 0.05
    n_estimators: 100
    random_state: 42
```

> Thresholds marked "placeholder" are flagged, not silently assumed. Do not present these as finalized without resolving TC-02/TC-03 (§12).

---

## 8. Running VERITAS

### Run the full pipeline end-to-end
```bash
python -m src.orchestrator --config config/config.yaml
```

### Run modules independently (for development/demo/grading)

Stages 2 and 3 have no dependency on each other — both only require stage 1's output — so they can be run concurrently. Stage 4 is a join: it will not run until both findings files exist.

```bash
# 1. Ingestion — generates normalized_log.json from UCI Adult Income + Faker metadata
python -m src.ingestion.log_loader --output data/processed/normalized_log.json

# 2a. Anomaly detection — reads normalized log, writes anomaly_findings.json
python -m src.anomaly_detection.isolation_forest \
    --input data/processed/normalized_log.json \
    --output outputs/logs/anomaly_findings.json &

# 2b. Fairness scan — writes fairness_findings.json (runs concurrently with 2a)
python -m src.fairness_scanner.metrics \
    --input data/processed/normalized_log.json \
    --output outputs/logs/fairness_findings.json &

wait   # block until both background jobs finish

# 3. Compliance mapping — joins both findings, writes mapped_findings.json
python -m src.compliance_mapping.rules_engine \
    --anomaly outputs/logs/anomaly_findings.json \
    --fairness outputs/logs/fairness_findings.json \
    --output outputs/logs/mapped_findings.json

# 4. Report generation
python -m src.report_generator.pdf_report \
    --input outputs/logs/mapped_findings.json \
    --output outputs/reports/audit_report.pdf
```

Each stage reads and writes a single, versioned JSON artifact — this is what makes independent module ownership and grading possible without one person's incomplete work blocking another's. The `wait` in step 2 is not cosmetic: it enforces the actual dependency contract (compliance mapping requires both findings files, not just one).

**Orchestrator implementation note:** `src/orchestrator.py` should run stages 2a/2b via `concurrent.futures.ProcessPoolExecutor` (or `multiprocessing.Pool`) rather than shelling out with `&`/`wait` — the shell version above is for manual/demo runs only. The orchestrator should submit both jobs, call `.result()` on both futures before invoking the compliance mapping engine, and propagate either exception individually rather than letting one silent failure block the join indefinitely.

---

## 9. Module Reference

### 9.1 Log Ingestion & Anomaly Detection
- Loads UCI Adult Income predictions and confidence scores.
- Wraps each record with Faker-generated operational metadata (timestamp, session ID, auth method) to simulate a real prediction-event log.
- Runs `IsolationForest` (unsupervised — no labeled anomaly ground truth exists or is assumed).
- Output: `anomaly_findings.json` — flagged records with anomaly scores.

### 9.2 Fairness & Bias Scanner
- Computes per-batch statistical fairness metrics across protected attributes: demographic parity difference, equalized odds difference, disparate impact ratio.
- This is arithmetic over prediction-rate distributions, not a learned model — treat it as a statistics module, not an ML module.
- Output: `fairness_findings.json`.

### 9.3 Compliance Mapping Engine ★
- Ingests both findings files.
- Applies a YAML-defined lookup table (`nist_control_lookup.yaml`) mapping finding types/severities to specific NIST AI RMF control IDs.
- **This is the project's original contribution.** Everything upstream uses off-the-shelf libraries; this module is the deterministic translation layer that makes the output auditable and citable.
- Output: `mapped_findings.json`.

### 9.4 Report Generator
- Renders `mapped_findings.json` into a structured PDF/HTML audit report.
- Templates in `src/report_generator/templates/`.

---

## 10. NIST AI RMF Mapping Approach

The compliance mapping engine uses a static, versioned lookup table (`compliance_mapping/nist_control_lookup.yaml`) rather than any learned or generative mapping — this is a deliberate architecture decision to keep the mapping deterministic, reproducible, and citable in an audit context. Each entry associates:

- a finding type (e.g., `fairness.disparate_impact_below_threshold`)
- a severity tier
- one or more NIST AI RMF control IDs
- a plain-language rationale string included in the final report

See `docs/nist_mapping_reference.md` for the full table and citation sources.

---

## 12. Known Limitations / Open Items

Documented explicitly rather than glossed over, per CA-1 review feedback:

| Issue | Status | Impact |
|---|---|---|
| No explainability trace between the anomaly/fairness threshold gate and the resulting control ID assignment | **Unresolved** | An auditor (or panel member) cannot currently answer "why did finding X map to control Y" — this is the single highest-priority gap |
| Sub-threshold findings are silently discarded rather than logged with rationale | **Unresolved** | Weakens audit defensibility — an audit trail that discards evidence without a logged reason is itself an audit finding |
| No finalized numeric pass/fail thresholds for TC-02 and TC-03 | **Unresolved** | `thresholds.yaml` currently ships placeholder values — do not cite these as final in any report or presentation |
| Prior tech-stack framing implied an "optional LLM assist" path alongside "deterministic rules engine" | **Resolved in this README** | Architecture is now stated as deterministic-only; if an LLM-assist path is reintroduced, this document and the module diagram must be updated together |

---

## 13. Roadmap

- [ ] Design and implement explainability trace logging in `compliance_mapping/explainability_trace.py`
- [ ] Replace silent-discard behavior with a logged-and-flagged low-confidence findings path
- [ ] Finalize TC-02 / TC-03 numeric thresholds with cited external justification (avoid inventing numbers — EEOC four-fifths rule precedent should guide the sourcing standard)
- [ ] Populate `docs/nist_mapping_reference.md` with full control lookup table and citations
- [ ] Insert real test results into CA-2 report placeholders

---

## 14. Team

| Name | PRN | Role |
|---|---|---|
| Om Narayan Pandit | 23070126083 | Compliance Mapping Engine; pipeline orchestration |
| Yash Raj Keshari | 23070126148 | — |
| Vedant Shitole | 23070126143 | — |
| Varun Umang Mate | 23070126142 | — |

**Faculty Guide:** Dr. Sheetal Borhade
**Mentor:** Dr. Rahesha Mulla

---

## 15. Academic Use Notice

This project is a bounded academic capstone exercise. It does not produce regulator-recognized audit certification, does not process real user data, and is not intended for production deployment against a live model. All datasets used are public and synthetic-augmented (UCI Adult Income + Faker-generated metadata).