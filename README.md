# VERITAS

**V**erifiable **E**vidence & **R**isk **I**dentification **T**oolkit for **A**I **S**ystems

> An agentic AI audit platform: ingests prediction logs from a classifier, runs a 6-agent LangGraph pipeline for schema inference, human-in-the-loop governance, anomaly clustering, and plain-English compliance narration, then outputs citable NIST AI RMF control mappings delivered through a luxury Next.js 14 web interface.

**Status:** In development (AY 2026-27) · Final-year B.Tech capstone, AI & ML, SIT Pune · Sponsored by Optywise AI Solutions
**Project ID:** OPT-2

---

## Development Status

| Phase / Component | Description | Status |
|---|---|---|
| 1. Ingestion | Dataset load, audit-subject model, feature engineering, anomaly injection, synthetic metadata | ✅ Built & tested |
| 2. Anomaly Detection | IsolationForest, data-driven threshold selection, explainability, evaluation | ✅ Built & tested |
| 3. Fairness Scanner | Fairlearn metrics, EEOC four-fifths threshold, permutation-test thresholds for demographic parity/equalized odds | ✅ Built & tested |
| 4. Compliance Mapping | Rules-based deterministic NIST AI RMF mapping engine (core original contribution) | ✅ Built & tested |
| 5. Report Generator | Self-contained HTML report + PDF rendered with ReportLab | ✅ Built & tested |
| 6. Agentic AI Upgrade | 6 specialized AI agents (Schema inference, Anomaly clustering, Config proposer, Human-in-the-loop LangGraph orchestrator with durable SQLite checkpointer, Explanation rewriter with verifier, Conversational Q&A) | ✅ Built & tested |
| 7. Full-Stack Web App | High-performance FastAPI backend + Next.js 14 TypeScript frontend with luxury glassmorphism UI, hand-crafted SVG disparity charts, and sandboxed workpaper | ✅ Built & verified |
| 8. Statistical Validation | Formal verification suite — Type I error control, statistical power, EEOC 4/5ths boundary, small-group stability, Isolation Forest knee-point geometry, and deterministic seed invariance | ✅ Built & tested |
| Test Suite | 140 automated unit, integration, golden equivalence, and statistical validation tests passing (100%) | ✅ 140 / 140 Passing |

Each phase has a standalone CLI. Phases 1–5 can also run through the subprocess orchestrator with a SHA-256 manifest, through the in-memory `VeritasPipeline` API, or interactively through the full-stack Next.js web application.

---

## Table of Contents

- [1. Overview](#1-overview)
- [2. Scope](#2-scope)
- [3. Architecture](#3-architecture)
- [3a. Agentic AI Upgrade (6 Agents)](#3a-agentic-ai-upgrade-6-agents)
- [3b. Full-Stack Web Application](#3b-full-stack-web-application)
- [3c. Statistical Validation Suite](#3c-statistical-validation-suite)
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

VERITAS treats an AI system as the **subject of an audit**, not the tool performing one. It ingests prediction-event logs and runs a complete agentic AI-powered audit pipeline:

1. **Schema Discovery (Agent-1):** Automatically infers column roles, protected attributes, and privacy-safe feature candidates.
2. **Human-in-the-Loop Governance (Agent-3 + LangGraph, Agent-4):** Pauses for mandatory auditor approval with AI-generated configuration rationales before any statistical computation begins.
3. **Anomaly Detection & Clustering (Agent-2):** Isolation Forest detection grouped by dominant z-score signatures with precision/recall estimates.
4. **Fairness & Disparity Scanning:** EEOC 4/5ths Rule (disparate impact ratio ≥ 0.80), demographic parity difference, and equalized odds via seeded permutation testing.
5. **NIST AI RMF Compliance Mapping (Agent-5):** Deterministic, rules-based mapping to NIST AI 100-1 (Govern, Map, Measure, Manage) with plain-English explanations verified for number traceability.
6. **Report Generation:** SHA-256 sealed, board-ready HTML workpaper and PDF report.
7. **Conversational Audit Interrogation (Agent-6):** Immutable read-only Q&A assistant over case findings.

The **Deterministic Statistical Boundary** is a core architectural guarantee: no AI agent ever calculates or modifies metrics, z-scores, p-values, or compliance outcomes. All numerical computation is 100% deterministic.

---

## 2. Scope

**In scope:**
- Log ingestion combining real classifier predictions with synthetic operational metadata
- Unsupervised anomaly detection over log/prediction behavior, with data-driven threshold selection
- Statistical fairness scanning (per-attribute group metrics)
- Rules-based compliance mapping to NIST AI RMF control IDs
- Automated report generation (PDF/HTML)

**Out of scope:**
- Regulator-accepted certification of any kind
- Live/production model integration
- Multi-framework compliance support (NIST AI RMF only)
- Real user data of any kind

---

## 3. Architecture

VERITAS is organized into **seven phases** — five deterministic statistical phases (Phases 1–5) backed by an agentic AI layer (Phase 6) and delivered through a full-stack web application (Phase 7). Phases 1–5 are connected by JSON artifact contracts and can run independently, in parallel, or end-to-end via the orchestrator or web API.

**Dependency graph (not purely sequential):** Anomaly Detection and the Fairness & Bias Scanner both consume `normalized_log.json` directly from ingestion and have no dependency on one another — they run **in parallel**. The Compliance Mapping Engine is the actual join point: it blocks until *both* findings files exist, and must reconcile two structurally different artifact shapes (anomaly findings are per-record; fairness findings are per-protected-attribute aggregates).

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
             │ (per-record)             │ (per-attribute, aggregate)
             └───────────┬──────────────┘
                         ▼  (join — waits on both)
                ┌────────────────────┐
                │ Compliance Mapping  │  ★ core contribution
                │      Engine         │
                └─────────┬───────────┘
                          │  mapped_findings.json
                          ▼
                ┌────────────────────┐
                │  Report Generator   │  HTML + optional PDF
                └─────────┬───────────┘
                          │
                          ▼
                  audit_report.pdf / .html
```

> **Note on originality:** The **Compliance Mapping Engine** (Phase 4) is the core original contribution in the deterministic pipeline — anomaly detection and fairness scanning use established libraries (scikit-learn, Fairlearn) as-is. The **Agentic AI layer** (6 agents, LangGraph graph, human-in-the-loop gate, explainability verifier) and the **Full-Stack Web Application** (FastAPI API + Next.js 14 frontend) are additional original contributions built on top of Phases 1–5. All phases can be run individually via CLI, through the subprocess orchestrator with SHA-256 manifest, in-memory via `VeritasPipeline`, or interactively through the web application.

---

## 3a. Agentic AI Upgrade (6 Agents)

VERITAS now ships a **multi-agent AI layer** built on LangGraph + LangChain, operating strictly inside a *Deterministic Statistical Boundary*: every metric, z-score, p-value, and compliance verdict is computed by the deterministic pipeline; agents only read, reason over, and narrate those results.

| Agent | Role | Location |
|---|---|---|
| **Agent-1 — Schema Inference** | Analyses uploaded CSV headers and sample rows; infers column roles (prediction, ground-truth, protected attribute, feature) and proposes a validated audit config | `src/agentic/agents/schema_agent.py` |
| **Agent-2 — Anomaly Grouper** | Clusters flagged anomalies by dominant z-score signature and writes a human-readable cluster breakdown narrative | `src/agentic/agents/anomaly_grouper.py` |
| **Agent-3 — Config Proposer** | Drafts an auditor-facing rationale for the proposed audit configuration (protected attributes, thresholds, fairness metrics) before the pipeline runs | `src/agentic/agents/config_proposer.py` |
| **Agent-4 — Approval Gate** | LangGraph conditional edge: blocks pipeline execution until the auditor explicitly confirms or rejects Agent-3's proposed config. Pipeline never proceeds without human sign-off | `src/agentic/graph.py` |
| **Agent-5 — Explanation Rewriter + Verifier** | Rewrites compliance-mapping findings into board-readable plain English; a second verifier pass checks every cited number against the deterministic output to block hallucinated statistics | `src/agentic/agents/explainer.py` |
| **Agent-6 — Q&A Assistant** | Immutable, read-only conversational assistant over the sealed case file. Cannot modify findings; cites only numbers already present in the deterministic audit output | `src/agentic/agents/qa_agent.py` |

**LangGraph Execution Graph:**
```
[Upload] → Agent-1 (Schema) → Agent-3 (Config Rationale)
                                        │
                              Agent-4 (Human Approval Gate)
                                        │ APPROVED
                             Deterministic Pipeline (Phases 1–5)
                                        │
                    ┌───────────────────┴───────────────────┐
              Agent-2 (Anomaly Grouper)            Agent-5 (Explainer + Verifier)
                    └───────────────────┬───────────────────┘
                                        │
                              Agent-6 (Q&A Assistant)
```

The graph is persisted via `SqliteSaver` checkpointing, so interrupted runs can be resumed from the last completed node.

---

## 3c. Statistical Validation Suite

VERITAS includes a **formal statistical validation engine** (`src/statistical_validation.py`) that independently verifies the mathematical correctness of the pipeline's statistical machinery. This is not a functional test — it is a protocol-level verification that the statistical claims made by Phases 2–4 are defensible.

| Protocol | What It Verifies | Method |
|---|---|---|
| **Type I Error Control** | Under a true null hypothesis (H₀), the permutation test rejects at most α (5%) of the time | 200 Monte Carlo trials with shuffled labels; observed false-positive rate must be ≤ α + tolerance |
| **Statistical Power** | Under a true disparity (H₁), the permutation test detects the violation with ≥ 80% power | 200 Monte Carlo trials with manufactured 30-point disparity gap; observed detection rate must be ≥ 0.80 |
| **EEOC 4/5ths Boundary** | The disparate impact ratio threshold correctly classifies boundary cases | Ratios at 0.79 (violation) and 0.81 (compliant) verified against the 0.80 EEOC threshold |
| **Small-Group Stability** | Groups with N < 30 are flagged as statistically unstable | Synthetic small groups verified to trigger the instability warning |
| **Knee-Point Geometry** | Isolation Forest's data-driven contamination selection produces geometrically valid curvature | Curvature at the selected knee must exceed both neighbors; threshold must be in (0, 1) |
| **Seed Invariance** | Deterministic seeding produces identical results across runs | Two independent pipeline executions with the same seed must yield bit-identical outputs |

The suite also includes a **UCI Adult Income live benchmark** that runs the full pipeline against the real dataset and validates end-to-end output structure.

```bash
# Run statistical validation tests:
python -m pytest tests/test_statistical_validation.py -v
```

---

## 3b. Full-Stack Web Application

VERITAS ships a production-ready **Next.js 14 + FastAPI** full-stack web application, designed for live executive demonstrations.

### Architecture
```
┌──────────────────────────────────────────────┐
│            Next.js 14 (Port 3000)            │  ← App Router, TypeScript, Tailwind CSS
│  ┌──────────────┐  ┌───────────────────────┐ │
│  │  Dropzone /  │  │  Results Case-File    │ │
│  │  Pre-flight  │  │  Workspace (tabs)     │ │
│  │  Review UI   │  │  Summary / Charts /   │ │
│  │  (Agent-3)   │  │  NIST Table / Q&A     │ │
│  └──────┬───────┘  └──────────┬────────────┘ │
└─────────┼────────────────────┼──────────────┘
          │ REST /api/*         │
┌─────────▼────────────────────▼──────────────┐
│           FastAPI Backend (Port 8000)        │
│  routes_runs.py  │  schemas.py              │
│  SQLite runs DB  │  LangGraph (6 agents)    │
└──────────────────────────────────────────────┘
```

### Frontend Pages
| Route | Page | Description |
|---|---|---|
| `/` | Landing | Executive hero, three-pillar value proposition |
| `/runs/new` | Upload | Glassmorphism dropzone + Agent-1 schema inspection card |
| `/runs/[id]/review` | Pre-flight Approval | Agent-3 config rationale + auditor sign-off (Agent-4 gate) |
| `/runs/[id]/summary` | Executive Summary | Outlier stats, Agent-2 cluster breakdown |
| `/runs/[id]/disparity` | Disparity Charts | SVG bar chart with EEOC 0.80 threshold line, per-attribute |
| `/runs/[id]/anomalies` | Anomaly Findings | Anomaly detection results with z-score explanations |
| `/runs/[id]/findings` | NIST Table | Paginated findings with Agent-5 plain-English explanations |
| `/runs/[id]/controls` | Control Mappings | NIST AI RMF control ID assignments with severity badges |
| `/runs/[id]/qa` | Q&A Chat | Agent-6 conversational assistant with citation chips |
| `/runs/[id]/report` | Audit Workpaper | Sandboxed HTML Case Dossier with executive summary KPIs, SHA-256 seal, and expandable findings |

---

## 4. Repository Structure

```
veritas/
├── README.md
├── pyproject.toml                  # Packaging specification and CLI entrypoints
├── requirements.txt               # Python backend dependencies
├── .gitignore
│
├── api/                            # ★ FastAPI backend (Port 8000)
│   ├── main.py                     # FastAPI application entrypoint
│   ├── routes_runs.py              # Run lifecycle endpoints (/api/runs/*)
│   └── schemas.py                  # Pydantic request/response schemas
│
├── frontend/                       # ★ Next.js 14 frontend (Port 3000)
│   ├── app/
│   │   ├── layout.tsx              # Root layout with Navbar and global styles
│   │   ├── page.tsx                # Executive landing page
│   │   └── runs/[id]/
│   │       ├── review/page.tsx     # Pre-flight human approval (Agent-3 + Agent-4)
│   │       └── (results)/
│   │           ├── layout.tsx      # Results tab shell with stat strip
│   │           ├── summary/        # Executive summary + Agent-2 cluster breakdown
│   │           ├── disparity/      # SVG disparity charts (EEOC 4/5ths)
│   │           ├── findings/       # NIST AI RMF table + Agent-5 explanations
│   │           └── qa/             # Agent-6 Q&A chat interface
│   ├── components/
│   │   ├── Navbar.tsx              # Luxury glass navigation bar
│   │   ├── Dropzone.tsx            # Glassmorphism CSV upload with validation
│   │   ├── ColumnCheck.tsx         # Agent-1 schema inspection card
│   │   ├── RunStepper.tsx          # Animated audit progress stepper
│   │   ├── DisparityChart.tsx      # Handcrafted SVG bar chart with 0.80 threshold
│   │   ├── FindingsTable.tsx       # Paginated NIST table with expandable Agent-5 narratives
│   │   ├── ReportFrame.tsx         # Sandboxed iframe for Case Dossier HTML workpaper
│   │   └── SeverityMark.tsx        # Neon severity badges (CRITICAL / HIGH / INFO)
│   ├── styles/tokens.css           # Design tokens + glassmorphism utilities
│   ├── tailwind.config.ts          # Tailwind design system config
│   ├── next.config.js              # API proxy rewrites
│   └── package.json
│
├── src/                            # Python audit pipeline (Phases 1–5)
│   ├── agentic/                    # ★ LangGraph multi-agent layer
│   │   ├── graph.py                # LangGraph state machine + SqliteSaver checkpointer
│   │   └── agents/
│   │       ├── schema_agent.py     # Agent-1: Schema inference
│   │       ├── anomaly_grouper.py  # Agent-2: Anomaly cluster narrative
│   │       ├── config_proposer.py  # Agent-3: Config rationale
│   │       ├── explainer.py        # Agent-5: Plain-English rewriter + verifier
│   │       └── qa_agent.py         # Agent-6: Read-only Q&A assistant
│   ├── __init__.py
│   ├── pipeline.py
│   ├── run_config.py
│   ├── orchestrator.py
│   ├── ingestion/
│   ├── anomaly_detection/
│   ├── fairness_scanner/
│   ├── compliance_mapping/
│   ├── report_generator/
│   └── statistical_validation.py  # ★ Formal statistical verification (6 protocols)
│
├── config/
│   └── config.yaml
├── data/
│   ├── demo_audit_dataset.csv      # ★ Pre-built CEO demonstration dataset
│   └── processed/
├── tests/                          # 140 tests — see §11
├── outputs/
└── docs/
```

Each module is independently runnable via CLI and callable programmatically via Python functions. No module imports directly from another module's internal state — they can communicate via JSON artifacts or in-memory through `VeritasPipeline`.

---

## 5. Tech Stack

| Layer | Tool / Library | Purpose |
|---|---|---|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS, TanStack Query | Full-stack web UI — interactive audit workspace |
| **Backend API** | FastAPI, Uvicorn, Pydantic v2, SQLite | REST API serving run lifecycle and LangGraph-backed agentic endpoints |
| **Agentic AI** | LangGraph, LangChain, OpenAI GPT-4o, SqliteSaver | 6-agent directed graph with durable checkpointing and human-in-the-loop approval gate |
| Audit-Subject Model | `scikit-learn` (`LogisticRegression`) | Stand-in classifier simulating the bank's income-prediction model; produces the predictions VERITAS actually audits |
| Anomaly Detection | `scikit-learn` (`IsolationForest`) | Unsupervised outlier detection over prediction logs |
| Threshold Selection | Custom (knee-point geometry + grid search) | Data-driven contamination selection, replacing an arbitrary constant |
| Fairness Scanning | `Fairlearn` | Demographic parity, equalized odds, disparate impact ratio (via `demographic_parity_ratio`); demographic parity/equalized odds violations resolved via a permutation significance test (custom, `numpy`-based) since neither has an external cited threshold like EEOC's |
| Synthetic Metadata & Anomaly Injection | `Faker` + `numpy` | Timestamps, session IDs, auth methods, plus three deliberately injected, known-rate operational anomaly patterns for detector evaluation — see §9.1 |
| Schema Validation | `pydantic` | Fail-loud validation at every module boundary (ingestion output, anomaly findings, fairness findings) |
| Dataset Access | `ucimlrepo` | Fetches and locally caches UCI Adult Income |
| Compliance Mapping | Custom rules engine (Python, YAML-driven lookup) | Finding → NIST AI RMF control ID translation — core logic built, unit-tested, and CLI-runnable |
| Report Generation | Jinja2, python-docx, ReportLab | Self-contained HTML view plus a PDF rendered from the existing DOCX report template |
| Dataset | UCI Adult Income | Real classifier predictions and confidence scores |
| Compliance Reference | NIST AI RMF | Primary framework for control ID mapping |
| Fairness Threshold Standard | EEOC four-fifths rule (0.8 ratio) | External, defensible fairness threshold — the only threshold in this project with an external citation so far |

**Deterministic Statistical Boundary:** No AI agent ever calculates or modifies a metric, z-score, p-value, or compliance verdict. All numerical computation uses the deterministic Python pipeline above; agents only read and narrate those results.

---

## 6. Installation

```bash
git clone <repo-url> veritas
cd veritas

# --- Python Backend ---
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

python -m pip install -r requirements.txt

# --- Next.js Frontend ---
cd frontend
npm install
cd ..
```

**`requirements.txt` (Python backend core):**
```
# Core data stack
pandas>=2.0
numpy>=1.26

# Phases 1-5 (deterministic pipeline)
ucimlrepo>=0.0.7
faker>=25.0
pyyaml>=6.0
scikit-learn>=1.4
fairlearn>=0.10
jinja2>=3.1
python-docx>=1.1
reportlab>=4.0
pydantic>=2.6

# Phase 6 — Agentic AI layer
langgraph>=1.2,<2.0
langchain>=0.2
langchain-core>=0.2
# LLM provider (pick one): langchain-google-genai>=1.0  OR  langchain-ollama>=0.1

# Phase 7 — FastAPI backend
fastapi>=0.111
uvicorn[standard]>=0.29
python-multipart>=0.0.9
python-dotenv>=1.0
httpx>=0.27

# Testing
pytest>=8.0
pytest-asyncio>=0.23
```

> **Frontend:** `cd frontend && npm install` installs Next.js 14, Tailwind CSS, TanStack Query, and all TypeScript dependencies from `frontend/package.json` automatically.

---

## 7. Configuration

All thresholds and pipeline parameters live in a single `config/config.yaml` — not hardcoded in module logic — so they can be cited, changed, and audited without touching code.

```yaml
paths:
  raw_dir: data/raw
  processed_dir: data/processed
  synthetic_dir: data/synthetic_logs

dataset:
  source: uci_adult_income
  uci_repo_id: 2
  local_cache_csv: data/raw/adult_income.csv

audit_subject_model:
  algorithm: logistic_regression
  test_size: 0.2
  random_state: 42

protected_attributes:
  - sex
  - race

fairness:
  disparate_impact_ratio_threshold: 0.8   # EEOC Uniform Guidelines — four-fifths rule
  min_group_size_warning: 20              # groups smaller than this get flagged as statistically unstable
  significance_level: 0.05                # policy choice, not derived from data — see §12
  permutations: 1000                      # null-distribution size for the permutation significance test
  permutation_random_state: 42            # fixed — an unseeded permutation test can flip a boundary-case
                                           # verdict between identical runs on the same data

synthetic_metadata:
  session_id_prefix: "SESS"
  auth_methods: ["password", "sso", "mfa_token", "biometric"]
  timestamp_start: "2026-01-01T00:00:00"
  timestamp_end: "2026-06-30T23:59:59"

anomaly_injection:
  injection_rate: 0.03           # total rate across ALL patterns below — NOT externally justified, see §12
  random_state: 7
  rare_auth_methods: ["legacy_token", "unverified_device"]
  normal_hour_range: [7, 22]

  type_weights:                  # normalized internally — need not sum to 1
    off_hours_rare_auth: 0.4     # original pattern: off-hours timestamp + rare auth method together
    feature_outlier: 0.3         # implausible combination of real UCI feature columns
    duplicate_record: 0.3        # exact copy of another clean record's full feature row

  feature_outlier:
    age_range: [12, 17]
    hours_per_week_range: [90, 99]
    capital_gain_min: 90000
```

**Threshold justification status:**
- `disparate_impact_ratio_threshold` (0.8) — externally cited (EEOC Uniform Guidelines). Defensible as-is.
- `anomaly_injection.injection_rate` (0.03) — an internal design choice, not sourced from an external benchmark. Flagged, not hidden. Unchanged by the type split below: `type_weights` divides this one rate across three patterns, it does not add to it, so `anomaly_detection.isolation_forest.contamination` still only needs to match this single number.
- `anomaly_injection.type_weights` — relative frequency of each injected pattern, not individually benchmarked against any real-world anomaly mix; same unresolved-benchmark caveat as the rate itself applies per-type, not just in aggregate.
- `fairness.significance_level` (0.05) — a disclosed policy choice controlling the permutation test's false-positive sensitivity, not derived from data. A stricter value (e.g. 0.01) may be warranted for high-stakes decisions; the default has not been specifically justified for this use case.
- IsolationForest's `contamination` parameter is **no longer a config value at all** — phase 2 derives it per-run from the dataset's own score distribution (§9.2). `demographic_parity_difference` / `equalized_odds_difference` are similarly no longer unthresholded — phase 3 now resolves a violation flag for each via a seeded permutation significance test (§9.3), rather than only reporting the raw number.

---

## 8. Running VERITAS

### 8.1 Automated Pipeline Orchestration (`src/orchestrator.py`)

The pipeline orchestrator coordinates Phases 1 through 5, supports dry runs and phase selection, and logs execution evidence into `outputs/logs/run/run_manifest.json`, including the versioned effective analysis config and SHA-256 hashes. Both subprocess and `--in-memory` runs generate `outputs/reports/audit_report.html` and `outputs/reports/audit_report.pdf`.

```bash
# 1. Full pipeline run (subprocesses with SHA-256 integrity validation)
python src/orchestrator.py

# 2. In-memory pipeline run (avoids intermediate JSON serialization)
python src/orchestrator.py --in-memory --limit 1000

# 3. Dry-run: inspect execution plan without executing
python src/orchestrator.py --dry-run

# 4. Run specific phase(s)
python src/orchestrator.py --from-phase 2 --to-phase 3
python src/orchestrator.py --only 4
```

### 8.2 Programmatic Python API (`VeritasPipeline`)

VERITAS can be imported and executed directly in Python scripts, Jupyter notebooks, or backend services:

```python
from src import VeritasPipeline

# Initialize from YAML configuration
pipeline = VeritasPipeline.from_config_file("config/config.yaml")

# Run all phases end-to-end in-memory, optionally writing artifacts to disk
artifacts = pipeline.run_all(limit=500, save_artifacts=True, output_dir="outputs")

print(f"Mapped findings count: {len(artifacts.mapped_findings)}")
```

### 8.3 Run Modules Independently (CLI)

Stages 2 and 3 have no dependency on each other — both only require stage 1's output — and can be executed concurrently:

```bash
# 1. Ingestion
python -m src.ingestion.log_loader --output data/processed/normalized_log.json

# 2. Anomaly detection (contamination auto-selected)
python -m src.anomaly_detection.isolation_forest --input data/processed/normalized_log.json --output outputs/logs/anomaly_findings.json

# 3. Fairness scan (runs concurrently with step 2)
python -m src.fairness_scanner.run_scan --input data/processed/normalized_log.json --output outputs/logs/fairness_findings.json

# 4. Compliance mapping
python -m src.compliance_mapping.run_mapping --anomaly-input outputs/logs/anomaly_findings.json --fairness-input outputs/logs/fairness_findings.json --output outputs/logs/mapped_findings.json

# 5. Report generation
python -m src.report_generator.run_report --input outputs/logs/mapped_findings.json --output outputs/reports/audit_report.html --pdf-output outputs/reports/audit_report.pdf
```

### 8.4 Streamlit Dashboard (Legacy)

> **Note:** The Streamlit dashboard is the original upload-and-audit interface. It has been superseded by the full-stack Next.js web application (§8.5), which provides the full agentic AI pipeline, pre-flight governance, interactive disparity charts, and Agent-6 Q&A. The Streamlit dashboard remains functional for quick local CSV inspection without the agentic layer.

Install the optional dashboard dependencies, then run from the repository root:

```bash
python -m pip install -r dashboard/requirements.txt
python -m streamlit run dashboard/app.py
```

The dashboard accepts CSV and Excel (`.xlsx`/`.xls`) prediction logs. It requires a binary prediction column, a binary actual/ground-truth column, at least one protected-attribute column, and at least one numeric feature. Column names are normalized for case, spaces, and hyphens; common aliases such as `prediction`/`predicted_label`, `actual`/`true_label`, and `gender`/`sex` are accepted. Labels must use supported binary values such as `0`/`1`, true/false, or yes/no. Invalid or missing labels are rejected before analysis. The sidebar provides a downloadable CSV example.

### 8.5 Full-Stack Web Application (FastAPI + Next.js)

This is the recommended interface for live demonstrations. Run both servers simultaneously in separate terminals:

**Terminal 1 — FastAPI Backend**
```bash
# From the repository root, with .venv activated
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Next.js Frontend**
```bash
# From the repository root
cd frontend
npm run dev
```

Open **`http://localhost:3000`** in your browser.

> **Environment variables:** Create a `.env` file in the repository root with your chosen LLM provider key before running:
> ```
> # Google Gemini (recommended)
> GOOGLE_API_KEY=AIza...
> VERITAS_LLM_PROVIDER=gemini
> VERITAS_LLM_MODEL=gemini-3.8-flash     # optional, this is the default
>
> # --- OR --- Ollama (local, no API key required)
> VERITAS_LLM_PROVIDER=ollama
> OLLAMA_BASE_URL=http://localhost:11434  # optional
> VERITAS_LLM_MODEL=llama3.2             # optional
> ```
> If neither is configured, VERITAS runs in **deterministic mode** — all 5 statistical pipeline phases execute normally; only the agentic narration steps are skipped.

**Demo dataset:** Upload `data/demo_audit_dataset.csv` — a pre-built 500-record CSV with deliberate fairness and anomaly signals — on the Upload page. Full demonstration script: [`VERITAS_CEO_Demonstration_Guide.md`](./VERITAS_CEO_Demonstration_Guide.md).

---

## 9. Module Reference

### 9.1 Log Ingestion (`src/ingestion/`)
- Loads UCI Adult Income (cached locally after first fetch via `ucimlrepo`), explicitly handling the dataset's `" ?"` missing-value convention before dropping incomplete rows (pandas does not treat this as `NaN` by default — this was a real bug caught and fixed during development).
- Trains a stand-in classifier (`LogisticRegression`) on the data — this produces the predictions and confidence scores VERITAS actually audits, since UCI Adult Income ships ground-truth labels only, not model predictions.
- Builds an anomaly-detection feature set (`feature_engineering.py`) separate from the audit-subject model's own preprocessing, so anomaly detection examines prediction *behavior* rather than re-deriving the model's own decision boundary.
- Generates synthetic operational metadata (timestamp, session ID, auth method) via Faker, with a **deliberately injected, known-rate operational anomaly** rather than uniform random noise — this gives the anomaly detector genuine signal to find and a ground-truth label to evaluate against. The injected rate (`anomaly_injection.injection_rate`) is split across three independent patterns (`anomaly_injection.type_weights`), so evaluation isn't resting on a single easy-to-separate signal:
  - **`off_hours_rare_auth`** (original) — off-hours timestamp + rare auth method, injected into the synthetic metadata only.
  - **`feature_outlier`** (`feature_anomalies.py`) — an internally implausible combination of real UCI feature columns (e.g. a teenage age together with very high hours-per-week and capital-gain). This is the only pattern that tests the detector against the audit subject's actual inputs rather than synthetic wrapper fields.
  - **`duplicate_record`** (`feature_anomalies.py`) — an exact copy of another, non-anomalous record's full feature row. Deliberately left undetectable by `IsolationForest` on purpose: a density-based detector treats an exact repeat of a common point as *more* typical, not less, so this pattern documents a real blind spot in the evaluation rather than hiding it (see §12).
  - The two feature-level patterns mutate the real UCI columns **before** the audit-subject model is trained, and injected rows are excluded from that training split (`audit_subject_model.train_audit_subject`'s `trainable_mask`) while still receiving a prediction. Training on a deliberately-injected outlier would partially teach the model to treat it as normal, undermining both this evaluation and the fairness scanner's.
- Output: `normalized_log.json`, validated against a `pydantic` schema that fails loudly on malformed records rather than silently dropping them. Each record carries both `ground_truth_operational_anomaly` (bool) and `ground_truth_anomaly_type` (which of the three patterns, or `null`) — the type field is evaluation-only, like the bool it extends, and must never be fed into `IsolationForest` as an input feature.

### 9.2 Anomaly Detection (`src/anomaly_detection/`)
- Runs `IsolationForest` over the engineered feature set (numeric UCI features + prediction confidence + the injected operational-anomaly flags).
- **Contamination is not a guessed constant.** `threshold_selection.py` derives it two ways: an unsupervised knee-point detector (usable on real, unlabeled data — this is the production-realistic method) and a supervised grid search that only works because of the injected ground-truth label (validation-only, explicitly flagged as not generalizable). Both are reported; a discrepancy warning fires if they disagree by more than 3 points.
- Each finding includes a lightweight explainability signal — the top contributing features by z-score deviation from the population mean — so a flagged record isn't an unexplained black-box score by the time it would reach the compliance mapping engine.
- Evaluates precision/recall/F1 against the injected ground truth, with an explicit caveat in the output that this only measures the injected operational-anomaly category, not genuine unlabeled statistical outliers the detector also flags.
- Output: `anomaly_findings.json` (per-record).

### 9.3 Fairness & Bias Scanner (`src/fairness_scanner/`)
- Computes, per protected attribute (`sex`, `race`): demographic parity difference, disparate impact ratio (via Fairlearn's `demographic_parity_ratio`, mathematically equivalent to the worst-case pairwise EEOC ratio), and equalized odds difference.
- Equalized odds requires ground-truth labels by definition — the module fails loudly if `true_label` is missing rather than silently skipping the metric.
- Violation decisions (`thresholds.py`) are kept separate from metric computation (`metrics.py`). `disparate_impact_ratio` uses the externally cited EEOC four-fifths threshold (0.8). `demographic_parity_difference` and `equalized_odds_difference` — which have no equivalent external number — are each resolved via a **permutation significance test** (`permutation_significance_test()`): protected-attribute labels are shuffled ~1,000 times (seeded, `fairness.permutation_random_state` in config) to build an empirical null distribution, and a finding is flagged a violation if the observed value falls beyond the `(1 - significance_level)` percentile of that null. This is disclosed as data-driven-with-a-policy-parameter, not judgment-free — `significance_level` (0.05 default) is a human choice, not something the data determines.
- Groups below a configurable minimum size are flagged as producing statistically unstable ratios, so a violation is never reported without that caveat attached where relevant.
- This module is pure statistics over already-made predictions, not a learned model.
- Output: `fairness_findings.json` (per-attribute, aggregate — one row per attribute carries all three metrics plus their violation flags and p-values; a structurally different shape than anomaly findings, which the compliance mapping engine must reconcile without force-merging).

### 9.4 Compliance Mapping Engine

The project's core original contribution in the deterministic pipeline. Anomaly detection and fairness scanning use off-the-shelf libraries (scikit-learn, Fairlearn) as-is; this module is the custom rules-based translation layer from a raw technical finding to a specific, citable NIST AI RMF control ID. The **Agentic AI layer** (§3a) and **Full-Stack Web Application** (§3b) are separate original contributions layered on top.

- **`input_reconciler.py`** — joins the two structurally different upstream shapes without force-merging them. Filters `anomaly_findings.json` to genuine findings only (`is_anomaly == True`; `is_anomaly == False` records are normal operation, not findings, and are never mapped). Unpacks each `fairness_findings.json` row — one per attribute, three metrics inline — into three independent per-metric findings, since each metric gets its own severity and control citation.
- **`severity_policy.py`** — deliberately thin: does **not** compute severity (no permutation test, no EEOC comparison — that requires raw per-record data this module doesn't have). It only validates that an incoming `severity_tier` is a known value and resolves what it escalates to.
- **`rules_engine.py`** — orchestrator. `load_lookup_table()` validates `nist_control_lookup.yaml`'s internal consistency at load time (every control ID referenced by `finding_mappings` or `severity_tiers` must exist under `controls`) — fails loudly on a malformed table before any finding is processed, not mid-run. `map_finding()` resolves one finding to its primary/secondary control IDs plus any severity-driven escalation.
- **`explainability_trace.py`** — attaches the *specific* NIST action text matched (not just a bare control ID) and a human-readable trigger explanation per finding, including the anomaly detector's top-contributing-features or the fairness scanner's small-group caveat where relevant. This addresses the explainability-trace gap flagged in CA-1 review (§12).
- **`nist_control_lookup.yaml`** — static, versioned lookup table. Anomaly findings map to **MEASURE 2.4** (production monitoring — its action text names control-limit/ML-based anomaly monitoring almost literally); fairness findings map to **MEASURE 2.11** (fairness and bias evaluated); both carry a secondary citation to **MAP 5.1** (impact characterization). Severity is a property of the *finding*, not the finding type: any `violation`-tier finding of any kind escalates generically to **MANAGE 1.3** (response planned/documented) and **MANAGE 1.4** (residual risk documented), via a `severity_tiers` table keyed only on the tier name — this is what lets the escalation logic generalize to data the current sandbox testing doesn't exercise, without a code change.
- **`run_mapping.py`** — CLI entrypoint matching the convention of phases 1–3. Reads both findings files, calls `reconcile()` → `map_finding()`, writes `mapped_findings.json`.
- **Locked-in design decisions** (see `docs/nist_mapping_reference.md` — fully written and populated):
  - Anomaly findings are **informational-only, by design** — they never escalate to MANAGE, because no externally-defensible anomaly-severity cutoff exists (same reasoning as the unjustified injection rate, §12). Manufacturing one just to exercise the MANAGE path would repeat that problem, not solve it.
  - `recalibration_required` is documented directly in the YAML: `protected_attributes`, `fairness.min_group_size_warning`, and `fairness.significance_level` will not transfer correctly to a different (e.g. a sponsoring company's) dataset without human review — this is disclosed proactively, not discovered live during a demo.
- **What this module deliberately does NOT do:** GOVERN-function coverage. NIST's GOVERN function (organizational accountability, training, documented risk tolerance) cannot be evidenced by a tool inspecting model outputs — it's the deploying organization's responsibility. VERITAS automates evidence generation for MEASURE and produces citations into MAP and MANAGE; it does not, and structurally cannot, automate GOVERN.

### 9.5 Report Generator (`src/report_generator/`)
- Reads `mapped_findings.json` (phase 4 output) and renders a self-contained HTML audit report via a Jinja2 template. CSS and JavaScript are embedded; there are no external CDN dependencies. JavaScript enables the findings-table “See More” control. Reports are written as UTF-8.
- `html_report.py` loads findings, produces a summary (counts by severity tier and finding type, separated violation/informational lists), and renders via `templates/report_template.html`.
- `pdf_report.py` populates `templates/report_template.docx` with run metadata, summary counts, and finding rows, then renders the template's ordered sections into PDF with ReportLab. The dashboard displays HTML and offers a PDF download; both orchestrator modes write HTML and PDF.
- The report includes an explicit **scope disclosure**: VERITAS covers MEASURE + MAP/MANAGE citations only; GOVERN coverage is the deploying organization's responsibility. This is rendered in every report, not left implicit.
- `run_report.py` is the CLI entrypoint, matching the convention of phases 1–4.
- Output: the orchestrator writes `audit_report.html` and `audit_report.pdf` in `outputs/reports/`; the dashboard generates its template-based PDF download in memory.

---

## 10. NIST AI RMF Mapping Approach

A static, versioned lookup table (`src/compliance_mapping/nist_control_lookup.yaml`) rather than any learned or generative mapping, to keep the mapping deterministic, reproducible, and citable in an audit context. Implemented, not just planned:

- **Deterministic control IDs.** Anomaly findings → MEASURE 2.4; fairness findings → MEASURE 2.11; both → MAP 5.1 as a secondary citation. No LLM or learned component is in this path — see §5.
- **Severity-tier-based escalation**, not per-metric hardcoding. A `violation`-tier finding of any type escalates to MANAGE 1.3 and MANAGE 1.4 generically, via a `severity_tiers` table keyed only on the tier name.
- **Explainability trace**, not just a control ID. Every mapped finding carries the specific NIST action text it was matched against (`matched_action_text`) and a human-readable trigger explanation citing the actual observed value, threshold, or p-value.
- **Scope is explicitly MEASURE + citations into MAP/MANAGE — not GOVERN.** GOVERN (organizational accountability, training, documented risk tolerance) is not something an automated tool inspecting model outputs can produce evidence for; it remains the deploying organization's responsibility, by design, not by omission. If asked whether VERITAS "implements the AI RMF": it automates evidence generation for MEASURE and produces citations into MAP and MANAGE — that is the honest, defensible scope claim, not "full RMF coverage."
- **Load-time validation, not lookup-time failure.** A malformed YAML (a control ID referenced but not defined) is caught when the lookup table loads, before any finding is processed.
- **Disclosed, not hidden, remaining human judgment.** `fairness.significance_level` (0.05) governs the fairness permutation test's sensitivity and is a policy choice, not a data-derived value. This is documented in the YAML's `recalibration_required` section, not left implicit.

Everything above is verified by `tests/test_compliance_mapping.py` (see §11) against the module's actual behavior — not asserted here without a corresponding test.

---

## 11. Testing

**An automated `pytest` suite exists: 140 tests across all modules, 100% passing.**

```bash
# Run all tests:
python -m pytest tests/ -v

# Run one module at a time:
python -m pytest tests/test_pipeline.py -v
python -m pytest tests/test_ingestion.py -v
python -m pytest tests/test_anomaly_detection.py -v
python -m pytest tests/test_fairness_scanner.py -v
python -m pytest tests/test_compliance_mapping.py -v
python -m pytest tests/test_report_generator.py -v
python -m pytest tests/test_statistical_validation.py -v

# Quiet summary only:
python -m pytest tests/ -q
```

| Module | Test file | What's covered |
|---|---|---|
| Pipeline | `test_pipeline.py` | Full in-memory end-to-end execution; `VeritasPipeline` instantiation from config dict and file; verification of record flow across all five phases without disk I/O bottlenecks |
| Ingestion | `test_ingestion.py` | Schema validation (valid/invalid records, fail-loud on the first bad record in a batch — not a silent drop); anomaly-injection contract (rare auth method + off-hours timestamp, `assign_anomaly_types` multi-pattern weight split, correct ground-truth label); feature engineering (off-hours/rare-auth flag correctness, zero-mean standardization, zero-std divide-by-zero guard); audit-subject model (predictions returned for every row, not just the held-out split; valid label/confidence ranges) |
| Anomaly Detection | `test_anomaly_detection.py` | Label-leakage guard (`ground_truth_operational_anomaly` / `true_label` must never enter the feature matrix — raises if they do); knee-point threshold determinism and range; grid-search threshold recovery on a manufactured clean separation; evaluation metrics (precision/recall against ground truth); output schema accept/reject |
| Fairness Scanner | `test_fairness_scanner.py` | EEOC threshold boundaries; small-group and missing-label safeguards; manufactured disparate-impact detection; seeded permutation behavior and fast-path equivalence with Fairlearn for demographic parity and equalized odds; output schema validation |
| Compliance Mapping | `test_compliance_mapping.py` | Happy-path control mapping for both finding types; informational findings never discarded and never escalate; violation findings correctly escalate to MANAGE 1.3/1.4; anomaly findings never escalate (locks in the informational-only design decision); reconciler filters `is_anomaly=False` records out; reconciler unpacks one fairness row into three independent metric findings with correct per-metric severity; every mapped finding carries non-empty matched NIST action text; fail-loud on an unmapped finding type and on a malformed lookup table |
| Report Generator | `test_report_generator.py` | Input-key validation; summary counts; rendered severity sections and scope disclosure; zero-violation behavior; end-to-end UTF-8 HTML output; PDF signature/output verification |
| Statistical Validation | `test_statistical_validation.py` | Type I error control (false-positive rate ≤ α under H₀); statistical power (≥ 80% detection under H₁); EEOC 4/5ths boundary accuracy; small-group stability screening; Isolation Forest knee-point curvature geometry; deterministic seed invariance across runs |

**What this suite does NOT cover, disclosed rather than assumed away:**
- **No CI wiring.** Tests are currently run locally via pytest, not yet on automated GitHub Actions pull request triggers.
- **MEASURE 2.13** (evaluating the TEVV process's own effectiveness — e.g., confirming the fairness scanner actually detects a known injected disparity and does not false-positive on random data at roughly the stated significance rate) is partially covered by the permutation-test unit tests above, but no end-to-end "does this whole pipeline correctly identify a known-bad classifier" test exists yet.

---

## 12. Known Limitations / Open Items

| Issue | Status | Impact |
|---|---|---|
| No explainability trace between the anomaly/fairness threshold gate and the resulting control ID assignment | **Resolved.** `explainability_trace.py` attaches the specific matched NIST action text and a trigger explanation (including top-contributing-features / small-group caveats) to every mapped finding. | Closed — verify against a real dataset run before treating as fully proven at scale |
| Sub-threshold findings silently discarded | **Resolved by design.** `severity_tier` (`informational` / `violation`) is required on every finding; `informational` findings are still mapped and output, never dropped. Enforced by `output_schema.py`'s validation. | Closed |
| No finalized numeric thresholds for `demographic_parity_difference` / `equalized_odds_difference` | **Resolved via permutation significance test**, not a fixed constant. `significance_level` (0.05 default) remains a disclosed human policy choice — do not present the permutation test as removing human judgment entirely, only as removing the arbitrary-constant problem. | Say "data-driven with a disclosed significance threshold," not "fully automatic" |
| Anomaly injection rate (3%) has no external benchmark | **Unresolved.** Chosen as an internal design parameter, not sourced from an industry anomaly base-rate. Now split across three patterns via `type_weights` (§7, §9.1); the per-type split is an additional internal design choice on top of the already-unbenchmarked total. | Must be either justified or explicitly labeled as an experimental parameter in any report |
| `duplicate_record` anomaly pattern is structurally undetectable by `IsolationForest` | **By design, not a gap.** A density-based detector treats an exact repeat of a common feature vector as more typical, not less — this pattern exists specifically to make that blind spot visible in the evaluation instead of silently absent from it. | State this as a deliberate limitation of the chosen detector family if asked, not as a missed anomaly type |
| Phase 2's precision/recall evaluation does not yet break down by anomaly type | **Open.** `ground_truth_anomaly_type` is written by phase 1 and validated by the schema, but `isolation_forest.py`'s evaluation still reports a single aggregate precision/recall against the overall `ground_truth_operational_anomaly` bool. | Wire a per-type breakdown before citing detection performance on any individual pattern (especially `duplicate_record`, which should show near-zero recall and is expected to) |
| Two threshold-selection methods for IsolationForest contamination can disagree substantially | **Open for interpretation.** The unsupervised knee and supervised grid search can produce very different rates; the pipeline emits a warning, but the discrepancy alone does not establish which threshold is appropriate. | Inspect flagged records and justify the operating threshold before citing detector performance |
| `config/thresholds.yaml` as a separate file (shown in earlier README drafts and repo trees) | **Resolved — was never actually built.** All configuration, including fairness thresholds, lives in a single `config/config.yaml`. | This README previously misrepresented the repo structure; corrected here |
| No automated test suite | **Resolved.** 140 tests across all modules (§11). No CI wiring is currently documented. | Continue running the full suite locally; add CI before relying on automated pull-request checks |
| Prior tech-stack framing implied an "optional LLM assist" path alongside "deterministic rules engine" | **Resolved.** Architecture is stated as deterministic-only throughout this document. | If an LLM-assist path is ever reintroduced, this document and the module diagram must be updated together |
| Phase 4 was designed against an assumed Phase 2/3 output schema before their real source was reviewed | **Resolved, but worth recording as a process lesson.** `AnomalyFinding` has `is_anomaly: bool`, not a `severity_tier`; Phase 2's findings list includes every record, not just flagged ones; `FairnessFinding` is one row per attribute with all three metrics inline, not per-metric records. `input_reconciler.py` was rewritten against the real schemas after reading the actual source. | Any future module built against an "assumed" contract for an already-built upstream module should be verified against real source before being treated as done |
| Anomaly findings are permanently `informational` — can never trigger a MANAGE-stage response | **Resolved as an explicit design decision, not a gap.** No externally-defensible anomaly-severity cutoff exists (same reasoning as the unbenchmarked injection rate above); manufacturing one to exercise the MANAGE path would repeat that exact problem. Revisit only if an external anomaly-severity standard is identified. | State this as a deliberate scope boundary if asked, not as an oversight |
| GOVERN function has zero representation in the codebase | **By design, not a gap.** GOVERN (organizational accountability, training, documented risk tolerance) cannot be evidenced by a tool inspecting model outputs — it is the deploying organization's responsibility. VERITAS's honest scope claim is "automates MEASURE evidence generation, cites into MAP and MANAGE" — not "implements the AI RMF." | Do not claim full RMF coverage in the report or demo |
| Compliance Mapping Engine has no CLI entrypoint | **Resolved.** `run_mapping.py` provides a CLI entrypoint (`python -m src.compliance_mapping.run_mapping`) matching phases 1–3's conventions. | Closed |
| Automated Pipeline Orchestrator | **Resolved.** `src/orchestrator.py` provides concurrent subprocess execution with SHA-256 manifests, while `src/pipeline.py` provides the in-memory `VeritasPipeline` for zero-disk-I/O execution. | Closed |
| PDF Report Generation | **Resolved.** `src/report_generator/pdf_report.py` populates `report_template.docx` and renders its sections and findings to PDF with ReportLab, without requiring native conversion tools. | Closed |
| Module Documentation & Reference Contracts | **Resolved.** `docs/architecture.md`, `docs/module_contracts.md`, and `docs/nist_mapping_reference.md` are fully written and populated. | Closed |
| Permutation test performance at full dataset scale | **Optimized and benchmarked.** Fairlearn's repeated metric-frame construction is replaced by a batched NumPy path for binary demographic-parity and equalized-odds permutations, preserving seeded results. On 45,222 rows, a 100-permutation benchmark measured roughly 115x speedup for demographic parity and 155x for equalized odds. | This is an isolated metric-kernel comparison, not an end-to-end service-level guarantee |

---

## 13. Roadmap

- [x] Run phases 1–5 against the full, real UCI Adult Income dataset
- [x] Add additional injected anomaly patterns beyond off-hours-timestamp + rare-auth-method — `feature_outlier` and `duplicate_record` added, splitting the same total `injection_rate`
- [ ] Break down phase 2's precision/recall by `ground_truth_anomaly_type` instead of only the aggregate bool — needed to show `duplicate_record`'s expected near-zero recall as a documented result, not an unexplained gap
- [ ] Manually inspect the non-ground-truth records flagged by the unsupervised knee-point detector to confirm they're genuine outliers, not noise
- [ ] Source or explicitly label the anomaly injection rate (3%) as an experimental, non-benchmarked parameter
- [x] Decide and implement a numeric threshold approach for `demographic_parity_difference` and `equalized_odds_difference` — done via permutation significance test
- [x] Design and build the Compliance Mapping Engine (phase 4) — core logic and CLI entrypoint built
- [x] Build the explainability trace from threshold gate through to control ID assignment
- [x] Write an actual `pytest` suite — **140 tests across all modules**, 100% passing
- [x] Build a CLI entrypoint for the Compliance Mapping Engine (`python -m src.compliance_mapping.run_mapping`)
- [x] Build `src/orchestrator.py` with concurrent execution, SHA-256 manifests, and in-memory execution mode
- [x] Build modular `VeritasPipeline` in `src/pipeline.py` for programmatic invocation
- [x] Run phases 1–5 sequentially as one pipeline against the real dataset
- [x] Benchmark the optimized permutation metric path on the full 45,222-row normalized dataset (isolated metric-kernel benchmark; see §12)
- [ ] Decide whether `fairness.significance_level` (0.05 default) is the right value for this specific use case, or whether a stricter value is warranted
- [x] Build the Report Generator (phase 5) — HTML report and PDF rendered from the DOCX template
- [x] Populate `docs/nist_mapping_reference.md`, `docs/module_contracts.md`, and `docs/architecture.md`
- [ ] Consider an end-to-end test approximating MEASURE 2.13 (TEVV process effectiveness) — confirm the pipeline detects a known-bad classifier and does not false-positive on a known-fair one, beyond the current unit-level permutation-test coverage
- [x] **Phase 6 — Agentic AI Upgrade:** 6 LangGraph agents (Schema Inference, Anomaly Grouper, Config Proposer, Human-in-the-Loop Approval Gate, Explanation Rewriter + Verifier, Q&A Assistant) with durable SqliteSaver checkpointing — built and tested
- [x] **Phase 7 — Full-Stack Web Application:** FastAPI backend + Next.js 14 TypeScript frontend with luxury glassmorphism UI, hand-crafted SVG disparity charts, pre-flight governance review screen, and Agent-6 conversational assistant — built and verified
- [x] **Phase 8 — Statistical Validation:** Formal verification suite covering Type I error control, statistical power, EEOC boundary accuracy, small-group stability, knee-point geometry, and seed invariance — built and tested
- [x] **Audit Workpaper Case Dossier:** Dynamic HTML report with run metadata injection, executive summary KPIs, SHA-256 config fingerprint, and sandboxed iframe viewer — built and verified
- [x] **CEO Demonstration Guide:** end-to-end demonstration script with sample dataset, act-by-act walkthrough, and answers to tough executive questions — written and ready

---

## 14. Team

| Name | PRN | Role |
|---|---|---|
| Vedant Shitole | 23070126143 | Anomaly Detection |
| Varun Umang Mate | 23070126142 | Fairness Scanner |
| Om Narayan Pandit | 23070126083 | Compliance Mapping Engine |
| Yash Raj Keshari | 23070126148 | Report Generation |

**Faculty Guide:** Dr. Sheetal Borhade
**Mentor:** Dr. Aishwarya Mishra

---

## 15. Academic Use Notice

This project is a bounded academic capstone exercise. It does not produce regulator-recognized audit certification, does not process real user data, and is not intended for production deployment against a live model. All datasets used are public; operational metadata is synthetically generated with deliberately injected, labeled anomalies for detector evaluation purposes.