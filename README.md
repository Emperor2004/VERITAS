# VERITAS

**V**erifiable **E**vidence & **R**isk **I**dentification **T**oolkit for **A**I **S**ystems

> An automated AI-audit pipeline that ingests prediction logs from a classifier, detects anomalies and fairness violations, and translates findings into citable NIST AI RMF control mappings with generated audit evidence.

**Status:** In development (AY 2026-27) · Final-year B.Tech capstone, AI & ML, SIT Pune · Sponsored by Optywise AI Solutions
**Project ID:** OPT-2

---

## Development Status

| Phase | Description | Status |
|---|---|---|
| 1 | Ingestion — dataset load, audit-subject model, feature engineering, anomaly injection, synthetic metadata | ✅ Built & sandbox-tested |
| 2 | Anomaly Detection — IsolationForest, data-driven threshold selection, explainability, evaluation | ✅ Built & sandbox-tested |
| 3 | Fairness Scanner — Fairlearn metrics, EEOC four-fifths threshold, small-group safeguards | ✅ Built & sandbox-tested |
| 4 | Compliance Mapping Engine (core original contribution) | ⬜ Not started |
| 5 | Report Generator (PDF/HTML) | ⬜ Not started |

Phases 1–3 have been tested against small synthetic stand-in data during development. **None have yet been run against the real, full UCI Adult Income dataset.** Do not treat sandbox-passing as equivalent to a validated run — see [§12](#12-known-limitations--open-items).

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

VERITAS treats an AI system — specifically a tabular income/lending classifier — as the **subject of an audit**, not the tool performing one. It ingests a stream of prediction-event logs (real UCI Adult Income predictions, wrapped with synthetic operational metadata to resemble a bank's income-prediction service), and runs them through four stages:

1. Detect operational and statistical anomalies in prediction behavior.
2. Scan for statistical fairness violations across protected groups.
3. Translate any findings into specific, citable **NIST AI RMF** control IDs.
4. Generate a structured audit report (PDF/HTML) as evidence output.

The system does not certify compliance and does not interact with a production model. It produces **audit evidence artifacts** for a hypothetical audit exercise.

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

VERITAS is built as four decoupled modules connected by fixed, versioned input/output contracts (JSON schemas), so each module can be developed, tested, and demoed independently.

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
                │ Compliance Mapping  │  ★ core contribution — NOT YET BUILT
                │      Engine         │
                └─────────┬───────────┘
                          │  mapped_findings.json
                          ▼
                ┌────────────────────┐
                │  Report Generator   │  NOT YET BUILT
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
├── .gitignore
│
├── config/
│   └── config.yaml                 # single global config — dataset, audit-subject model,
│                                    # anomaly injection, protected attributes, fairness
│                                    # thresholds. (No separate thresholds.yaml — consolidated
│                                    # here deliberately; earlier drafts of this README
│                                    # incorrectly showed a two-file split that was never built.)
│
├── data/
│   ├── raw/                        # UCI Adult Income source CSV (cached after first download)
│   ├── synthetic_logs/             # reserved, currently unused
│   └── processed/                  # normalized_log.json output
│
├── src/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── log_loader.py           # phase 1 CLI entrypoint — loads data, orchestrates the rest
│   │   ├── audit_subject_model.py  # trains the stand-in "bank" classifier (LogisticRegression)
│   │   ├── feature_engineering.py  # builds IsolationForest's feature set
│   │   ├── synthetic_metadata.py   # Faker metadata + deliberate anomaly injection
│   │   └── schema.py               # normalized_log.json schema + validation
│   │
│   ├── anomaly_detection/
│   │   ├── __init__.py
│   │   ├── isolation_forest.py     # phase 2 CLI entrypoint — detection, scoring, explainability
│   │   ├── threshold_selection.py  # knee-point (unsupervised) + grid search (supervised, validation-only)
│   │   └── output_schema.py        # anomaly_findings.json schema
│   │
│   ├── fairness_scanner/
│   │   ├── __init__.py
│   │   ├── run_scan.py             # phase 3 CLI entrypoint
│   │   ├── metrics.py              # Fairlearn metric computation
│   │   ├── thresholds.py           # EEOC four-fifths violation decision, small-group flagging
│   │   └── output_schema.py        # fairness_findings.json schema
│   │
│   ├── compliance_mapping/         # NOT YET BUILT (phase 4)
│   │   ├── __init__.py
│   │   ├── rules_engine.py
│   │   ├── nist_control_lookup.yaml
│   │   ├── explainability_trace.py # addresses the open explainability-trace gap, see §12
│   │   └── output_schema.py
│   │
│   ├── report_generator/           # NOT YET BUILT (phase 5)
│   │   ├── __init__.py
│   │   ├── pdf_report.py
│   │   ├── html_report.py
│   │   └── templates/
│   │
│   └── orchestrator.py             # NOT YET BUILT — will run stages 2/3 concurrently, then 4, then 5
│
├── tests/                          # currently empty — no automated test suite yet, see §11
│   ├── test_ingestion.py
│   ├── test_anomaly_detection.py
│   ├── test_fairness_scanner.py
│   ├── test_compliance_mapping.py
│   └── test_report_generator.py
│
├── outputs/
│   ├── logs/                       # anomaly_findings.json, fairness_findings.json land here
│   └── reports/
│
└── docs/
    ├── architecture.md
    ├── nist_mapping_reference.md
    └── module_contracts.md         # JSON schema contracts between modules — not yet written
```

Each module directory is independently runnable and independently testable. No module imports directly from another's internals — they communicate only via the JSON artifacts described in §9.

---

## 5. Tech Stack

| Layer | Tool / Library | Purpose |
|---|---|---|
| Audit-Subject Model | `scikit-learn` (`LogisticRegression`) | Stand-in classifier simulating the bank's income-prediction model; produces the predictions VERITAS actually audits |
| Anomaly Detection | `scikit-learn` (`IsolationForest`) | Unsupervised outlier detection over prediction logs |
| Threshold Selection | Custom (knee-point geometry + grid search) | Data-driven contamination selection, replacing an arbitrary constant |
| Fairness Scanning | `Fairlearn` | Demographic parity, equalized odds, disparate impact ratio (via `demographic_parity_ratio`) |
| Synthetic Metadata & Anomaly Injection | `Faker` + `numpy` | Timestamps, session IDs, auth methods, with a deliberately injected known-rate operational anomaly for detector evaluation |
| Schema Validation | `pydantic` | Fail-loud validation at every module boundary (ingestion output, anomaly findings, fairness findings) |
| Dataset Access | `ucimlrepo` | Fetches and locally caches UCI Adult Income |
| Compliance Mapping | Custom rules engine (Python, YAML-driven lookup) | Finding → NIST AI RMF control ID translation — not yet built |
| Report Generation | `python-docx`, HTML/CSS, PDF export | Structured audit evidence output — not yet built |
| Dataset | UCI Adult Income | Real classifier predictions and confidence scores |
| Compliance Reference | NIST AI RMF | Primary framework for control ID mapping |
| Fairness Threshold Standard | EEOC four-fifths rule (0.8 ratio) | External, defensible fairness threshold — the only threshold in this project with an external citation so far |

**Deliberately excluded from the core pipeline:** any LLM-based reasoning. The compliance mapping engine is planned as a deterministic rules engine with no "LLM assist" path.

---

## 6. Installation

```bash
git clone <repo-url> veritas
cd veritas

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

**`requirements.txt`:**
```
pandas>=2.0
scikit-learn>=1.4
fairlearn>=0.10
faker>=25.0
pyyaml>=6.0
pydantic>=2.6
ucimlrepo>=0.0.7
python-docx>=1.1
jinja2>=3.1
weasyprint>=61.0
pytest>=8.0
```

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

synthetic_metadata:
  session_id_prefix: "SESS"
  auth_methods: ["password", "sso", "mfa_token", "biometric"]
  timestamp_start: "2026-01-01T00:00:00"
  timestamp_end: "2026-06-30T23:59:59"

anomaly_injection:
  injection_rate: 0.03           # NOT externally justified — see §12
  random_state: 7
  rare_auth_methods: ["legacy_token", "unverified_device"]
  normal_hour_range: [7, 22]
```

**Threshold justification status:**
- `disparate_impact_ratio_threshold` (0.8) — externally cited (EEOC Uniform Guidelines). Defensible as-is.
- `anomaly_injection.injection_rate` (0.03) — an internal design choice, not sourced from an external benchmark. Flagged, not hidden.
- IsolationForest's `contamination` parameter is **no longer a config value at all** — phase 2 derives it per-run from the dataset's own score distribution (§9.2). This resolves the original TC-02/TC-03-style "unjustified constant" problem for anomaly detection specifically, though the fairness scanner does not yet threshold on `demographic_parity_difference` or `equalized_odds_difference` individually (see §12).

---

## 8. Running VERITAS

### Run modules independently (current state — no orchestrator yet)

Stages 2 and 3 have no dependency on each other — both only require stage 1's output — so run them concurrently.

```bash
# 1. Ingestion
python -m src.ingestion.log_loader --output data/processed/normalized_log.json

# 2. Anomaly detection (contamination auto-selected — no need to pass it)
python -m src.anomaly_detection.isolation_forest \
    --input data/processed/normalized_log.json \
    --output outputs/logs/anomaly_findings.json &

# 3. Fairness scan (runs concurrently with step 2)
python -m src.fairness_scanner.run_scan \
    --input data/processed/normalized_log.json \
    --output outputs/logs/fairness_findings.json &

wait   # block until both finish

# 4. Compliance mapping — NOT YET BUILT
# 5. Report generation — NOT YET BUILT
```

`src/orchestrator.py` does not exist yet. When built, it should run stages 2/3 via `concurrent.futures.ProcessPoolExecutor`, call `.result()` on both futures before invoking compliance mapping, and propagate either exception individually rather than letting one silent failure block the join indefinitely.

---

## 9. Module Reference

### 9.1 Log Ingestion (`src/ingestion/`)
- Loads UCI Adult Income (cached locally after first fetch via `ucimlrepo`), explicitly handling the dataset's `" ?"` missing-value convention before dropping incomplete rows (pandas does not treat this as `NaN` by default — this was a real bug caught and fixed during development).
- Trains a stand-in classifier (`LogisticRegression`) on the data — this produces the predictions and confidence scores VERITAS actually audits, since UCI Adult Income ships ground-truth labels only, not model predictions.
- Builds an anomaly-detection feature set (`feature_engineering.py`) separate from the audit-subject model's own preprocessing, so anomaly detection examines prediction *behavior* rather than re-deriving the model's own decision boundary.
- Generates synthetic operational metadata (timestamp, session ID, auth method) via Faker, with a **deliberately injected, known-rate operational anomaly** (off-hours timestamp + rare auth method) rather than uniform random noise — this gives the anomaly detector genuine signal to find and a ground-truth label to evaluate against.
- Output: `normalized_log.json`, validated against a `pydantic` schema that fails loudly on malformed records rather than silently dropping them.

### 9.2 Anomaly Detection (`src/anomaly_detection/`)
- Runs `IsolationForest` over the engineered feature set (numeric UCI features + prediction confidence + the injected operational-anomaly flags).
- **Contamination is not a guessed constant.** `threshold_selection.py` derives it two ways: an unsupervised knee-point detector (usable on real, unlabeled data — this is the production-realistic method) and a supervised grid search that only works because of the injected ground-truth label (validation-only, explicitly flagged as not generalizable). Both are reported; a discrepancy warning fires if they disagree by more than 3 points.
- Each finding includes a lightweight explainability signal — the top contributing features by z-score deviation from the population mean — so a flagged record isn't an unexplained black-box score by the time it would reach the compliance mapping engine.
- Evaluates precision/recall/F1 against the injected ground truth, with an explicit caveat in the output that this only measures the injected operational-anomaly category, not genuine unlabeled statistical outliers the detector also flags.
- Output: `anomaly_findings.json` (per-record).

### 9.3 Fairness & Bias Scanner (`src/fairness_scanner/`)
- Computes, per protected attribute (`sex`, `race`): demographic parity difference, disparate impact ratio (via Fairlearn's `demographic_parity_ratio`, mathematically equivalent to the worst-case pairwise EEOC ratio), and equalized odds difference.
- Equalized odds requires ground-truth labels by definition — the module fails loudly if `true_label` is missing rather than silently skipping the metric.
- Violation decisions (`thresholds.py`) are kept separate from metric computation (`metrics.py`) — the EEOC four-fifths threshold (0.8) is externally cited, unlike the anomaly injection rate.
- Groups below a configurable minimum size are flagged as producing statistically unstable ratios, so a violation is never reported without that caveat attached where relevant.
- This module is pure statistics over already-made predictions, not a learned model.
- Output: `fairness_findings.json` (per-attribute, aggregate — a structurally different shape than anomaly findings; the compliance mapping engine must reconcile both).

### 9.4 Compliance Mapping Engine ★ — NOT YET BUILT
- Will ingest both findings files and apply a YAML-defined lookup table mapping finding types/severities to NIST AI RMF control IDs.
- This is the project's original contribution; everything above uses off-the-shelf libraries.
- Must resolve the explainability-trace gap (§12) and the two-different-input-shapes problem noted in §3/§9.3.

### 9.5 Report Generator — NOT YET BUILT
- Will render `mapped_findings.json` into a structured PDF/HTML audit report.

---

## 10. NIST AI RMF Mapping Approach

Planned, not yet implemented: a static, versioned lookup table (`compliance_mapping/nist_control_lookup.yaml`) rather than any learned or generative mapping, to keep the mapping deterministic, reproducible, and citable in an audit context.

---

## 11. Testing

**No automated test suite exists yet.** The `tests/` directory contains placeholder filenames only. What exists instead is manual, ad hoc verification performed during development:

- Phase 1 was run against a small synthetic stand-in CSV (matching UCI Adult Income's schema) to catch import/logic errors before running against real data.
- Phase 1's `" ?"` missing-value fix was verified by deliberately injecting `" ?"` values into test data and confirming they were caught and logged.
- Phase 1's anomaly injection was verified by manually inspecting one injected and one normal record's timestamp/auth_method/derived feature flags.
- Phase 2 was verified by inspecting a sample flagged finding's `top_contributing_features` for plausibility, and by checking that unsupervised/supervised contamination estimates were both reported with a discrepancy warning where relevant.
- Phase 3 was verified by inspecting full per-attribute output including group sizes, to confirm a reported violation wasn't an artifact of a tiny group.

**None of this constitutes automated regression testing.** Writing real `pytest` coverage for each module (schema validation failures, label-leakage guards, threshold edge cases) is an open item — see §13.

**None of phases 1–3 have yet been run against the full real UCI Adult Income dataset** — only small synthetic stand-ins so far. Do this before treating any phase as complete.

---

## 12. Known Limitations / Open Items

| Issue | Status | Impact |
|---|---|---|
| No explainability trace between the anomaly/fairness threshold gate and the resulting control ID assignment | **Partially addressed, not resolved.** Phase 2 now attaches top-contributing-feature z-scores to each anomaly finding. Phase 3 attaches group sizes and small-group warnings to each fairness finding. Neither is wired into a control-ID assignment yet, since phase 4 doesn't exist. | Still the single highest-priority gap once phase 4 begins |
| Sub-threshold findings silently discarded | **Not yet applicable / open for phase 4.** Phases 1–3 do not discard records — every record gets a finding entry regardless of whether it crosses a threshold. This remains an open design question specifically for how the compliance mapping engine will handle low-severity findings. | Must be resolved before phase 4 is built, not after |
| No finalized numeric thresholds for `demographic_parity_difference` / `equalized_odds_difference` (formerly tracked as TC-02/TC-03) | **Unresolved.** Only `disparate_impact_ratio` has an enforced, externally-cited threshold (EEOC 0.8). The other two Fairlearn metrics are computed and reported but nothing currently flags a violation based on them. | Do not present demographic parity / equalized odds as "checked" against a pass/fail bar — only reported |
| Anomaly injection rate (3%) has no external benchmark | **Unresolved, newly identified.** Chosen as an internal design parameter, not sourced from an industry anomaly base-rate. | Must be either justified or explicitly labeled as an experimental parameter in any report |
| Two threshold-selection methods for IsolationForest contamination can disagree substantially | **Resolved as designed, documented as expected behavior, not a bug.** On test data, unsupervised knee-point selected ~10.5% vs supervised grid search's ~3%. This is diagnostic (real numeric outliers exist beyond the injected ones), not an error — but it means the 10.5%-level flagged set has NOT been manually verified for correctness. | Manually inspect non-ground-truth flagged records before citing detector performance |
| `config/thresholds.yaml` as a separate file (shown in earlier README drafts and repo trees) | **Resolved — was never actually built.** All configuration, including fairness thresholds, lives in a single `config/config.yaml`. | This README previously misrepresented the repo structure; corrected here |
| No automated test suite | **Unresolved, newly identified.** See §11. | Manual verification does not scale past the current three modules and won't catch regressions |
| Prior tech-stack framing implied an "optional LLM assist" path alongside "deterministic rules engine" | **Resolved.** Architecture is stated as deterministic-only throughout this document. | If an LLM-assist path is ever reintroduced, this document and the module diagram must be updated together |

---

## 13. Roadmap

- [ ] Run phases 1–3 against the full, real UCI Adult Income dataset (only synthetic stand-in data used so far)
- [ ] Manually inspect the non-ground-truth records flagged by the unsupervised knee-point detector to confirm they're genuine outliers, not noise
- [ ] Source or explicitly label the anomaly injection rate (3%) as an experimental, non-benchmarked parameter
- [ ] Decide and implement a numeric threshold approach for `demographic_parity_difference` and `equalized_odds_difference`, or explicitly scope them out as report-only metrics
- [ ] Design and build the Compliance Mapping Engine (phase 4), resolving how it joins two differently-shaped findings files and how it handles low-severity/sub-threshold findings without silent discard
- [ ] Build the explainability trace from threshold gate through to control ID assignment
- [ ] Build `src/orchestrator.py` with proper concurrent execution and per-job exception handling
- [ ] Write an actual `pytest` suite covering schema validation failures, label-leakage guards, and threshold edge cases
- [ ] Build the Report Generator (phase 5)
- [ ] Populate `docs/nist_mapping_reference.md` and `docs/module_contracts.md`, which are referenced but do not yet exist

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

This project is a bounded academic capstone exercise. It does not produce regulator-recognized audit certification, does not process real user data, and is not intended for production deployment against a live model. All datasets used are public; operational metadata is synthetically generated with deliberately injected, labeled anomalies for detector evaluation purposes.