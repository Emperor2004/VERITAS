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
| 3 | Fairness Scanner — Fairlearn metrics, EEOC four-fifths threshold, permutation-test thresholds for demographic parity/equalized odds, small-group safeguards | ✅ Built & sandbox-tested |
| 4 | Compliance Mapping Engine (core original contribution) | ✅ Built, sandbox-tested, CLI entrypoint added |
| 5 | Report Generator (PDF/HTML) | ✅ Built & sandbox-tested: HTML built, PDF pending |

Phases 1–5 have been run individually against the full UCI Adult Income dataset (~45K records after missing-value cleanup). Phases 1–5 have also been run sequentially as a complete pipeline (ingestion → anomaly detection → fairness scan → compliance mapping → report generation), producing real output artifacts in `outputs/`. No orchestrator-level automated run exists yet — see [§12](#12-known-limitations--open-items).

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
                │ Compliance Mapping  │  ★ core contribution
                │      Engine         │
                └─────────┬───────────┘
                          │  mapped_findings.json
                          ▼
                ┌────────────────────┐
                │  Report Generator   │  HTML built; PDF pending
                └─────────┬───────────┘
                          │
                          ▼
                  audit_report.pdf / .html
```

> **Note on the Compliance Mapping Engine:** this is the only module that is original work. Anomaly detection and fairness scanning use existing, well-established libraries (scikit-learn, Fairlearn) as-is, and run independently of each other. The rules-based translation layer — mapping a raw technical finding to a specific NIST AI RMF control ID with a defensible rationale — is what this project actually contributes. Its core logic (reconciliation, severity resolution, control lookup, explainability trace) is built, unit-tested, and has a CLI entrypoint (`python -m src.compliance_mapping.run_mapping`). Phases 1–5 have been run sequentially against the real dataset; orchestrator wiring is the remaining gap.

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
│   ├── compliance_mapping/         # phase 4 — core original contribution
│   │   ├── __init__.py
│   │   ├── rules_engine.py         # orchestrates lookup + escalation; load_lookup_table() validates the YAML
│   │   ├── input_reconciler.py     # filters is_anomaly=True, unpacks one fairness row into 3 metric findings
│   │   ├── severity_policy.py      # validates severity_tier, resolves MANAGE escalation (does NOT compute severity)
│   │   ├── nist_control_lookup.yaml
│   │   ├── explainability_trace.py # attaches matched NIST action text + per-finding trigger explanation
│   │   ├── output_schema.py        # MappedFinding / ControlCitation dataclasses
│   │   └── run_mapping.py          # phase 4 CLI entrypoint — reads both findings files, writes mapped_findings.json
│   │
│   ├── report_generator/           # phase 5 — HTML report built; PDF pending
│   │   ├── __init__.py
│   │   ├── html_report.py          # loads mapped_findings.json, renders via Jinja2 template
│   │   ├── run_report.py           # phase 5 CLI entrypoint
│   │   ├── pdf_report.py           # placeholder — PDF export not yet implemented
│   │   └── templates/
│   │       └── report_template.html
│   │
│   └── orchestrator.py             # NOT YET BUILT — will run stages 2/3 concurrently, then 4, then 5
│
├── tests/                          # 66 tests across phases 1–5, all passing — see §11
│   ├── conftest.py                 # shared fixtures for compliance_mapping tests
│   ├── test_ingestion.py
│   ├── test_anomaly_detection.py
│   ├── test_fairness_scanner.py
│   ├── test_compliance_mapping.py
│   └── test_report_generator.py    # load/summarize/render/write tests for the HTML report
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
| Fairness Scanning | `Fairlearn` | Demographic parity, equalized odds, disparate impact ratio (via `demographic_parity_ratio`); demographic parity/equalized odds violations resolved via a permutation significance test (custom, `numpy`-based) since neither has an external cited threshold like EEOC's |
| Synthetic Metadata & Anomaly Injection | `Faker` + `numpy` | Timestamps, session IDs, auth methods, with a deliberately injected known-rate operational anomaly for detector evaluation |
| Schema Validation | `pydantic` | Fail-loud validation at every module boundary (ingestion output, anomaly findings, fairness findings) |
| Dataset Access | `ucimlrepo` | Fetches and locally caches UCI Adult Income |
| Compliance Mapping | Custom rules engine (Python, YAML-driven lookup) | Finding → NIST AI RMF control ID translation — core logic built, unit-tested, and CLI-runnable |
| Report Generation | `python-docx`, HTML/CSS, PDF export | Structured audit evidence output — HTML report built; PDF pending |
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
  injection_rate: 0.03           # NOT externally justified — see §12
  random_state: 7
  rare_auth_methods: ["legacy_token", "unverified_device"]
  normal_hour_range: [7, 22]
```

**Threshold justification status:**
- `disparate_impact_ratio_threshold` (0.8) — externally cited (EEOC Uniform Guidelines). Defensible as-is.
- `anomaly_injection.injection_rate` (0.03) — an internal design choice, not sourced from an external benchmark. Flagged, not hidden.
- `fairness.significance_level` (0.05) — a disclosed policy choice controlling the permutation test's false-positive sensitivity, not derived from data. A stricter value (e.g. 0.01) may be warranted for high-stakes decisions; the default has not been specifically justified for this use case.
- IsolationForest's `contamination` parameter is **no longer a config value at all** — phase 2 derives it per-run from the dataset's own score distribution (§9.2). `demographic_parity_difference` / `equalized_odds_difference` are similarly no longer unthresholded — phase 3 now resolves a violation flag for each via a seeded permutation significance test (§9.3), rather than only reporting the raw number.

---

## 8. Running VERITAS

### Run modules independently (current state — no orchestrator yet)

Stages 2 and 3 have no dependency on each other — both only require stage 1's output — so run them concurrently.

```bash
# 1. Ingestion
python -m src.ingestion.log_loader --output data/processed/normalized_log.json

# 2. Anomaly detection (contamination auto-selected — no need to pass it)
python -m src.anomaly_detection.isolation_forest --input data/processed/normalized_log.json --output outputs/logs/anomaly_findings.json

# 3. Fairness scan (runs concurrently with step 2)
python -m src.fairness_scanner.run_scan --input data/processed/normalized_log.json --output outputs/logs/fairness_findings.json

# 4. Compliance mapping

python -m src.compliance_mapping.run_mapping --anomaly-input outputs/logs/anomaly_findings.json --fairness-input outputs/logs/fairness_findings.json --output outputs/logs/mapped_findings.json

# OR - with lookup table

python -m src.compliance_mapping.run_mapping --anomaly-input outputs/logs/anomaly_findings.json --fairness-input outputs/logs/fairness_findings.json --lookup src/compliance_mapping/nist_control_lookup.yaml --output outputs/logs/mapped_findings.json

# 5. Report generation

python -m src.report_generator.run_report --input outputs/logs/mapped_findings.json --output outputs/reports/audit_report.html

wait   # block until both finish
```

### Run the test suite

```bash
# All 66 tests, all five modules with tests:
python -m pytest tests/ -v

# One module at a time:
python -m pytest tests/test_ingestion.py -v
python -m pytest tests/test_anomaly_detection.py -v
python -m pytest tests/test_fairness_scanner.py -v
python -m pytest tests/test_compliance_mapping.py -v
python -m pytest tests/test_report_generator.py -v

# Quiet summary only:
python -m pytest tests/ -q
```

`src/orchestrator.py` does not exist yet. When built, it should run stages 2/3 via `concurrent.futures.ProcessPoolExecutor`, call `.result()` on both futures before invoking compliance mapping, and propagate either exception individually rather than letting one silent failure block the join indefinitely. It will also need to wire in the Compliance Mapping Engine's CLI entrypoint (`run_mapping.py`) and the Report Generator (`run_report.py`).

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
- Violation decisions (`thresholds.py`) are kept separate from metric computation (`metrics.py`). `disparate_impact_ratio` uses the externally cited EEOC four-fifths threshold (0.8). `demographic_parity_difference` and `equalized_odds_difference` — which have no equivalent external number — are each resolved via a **permutation significance test** (`permutation_significance_test()`): protected-attribute labels are shuffled ~1,000 times (seeded, `fairness.permutation_random_state` in config) to build an empirical null distribution, and a finding is flagged a violation if the observed value falls beyond the `(1 - significance_level)` percentile of that null. This is disclosed as data-driven-with-a-policy-parameter, not judgment-free — `significance_level` (0.05 default) is a human choice, not something the data determines.
- Groups below a configurable minimum size are flagged as producing statistically unstable ratios, so a violation is never reported without that caveat attached where relevant.
- This module is pure statistics over already-made predictions, not a learned model.
- Output: `fairness_findings.json` (per-attribute, aggregate — one row per attribute carries all three metrics plus their violation flags and p-values; a structurally different shape than anomaly findings, which the compliance mapping engine must reconcile without force-merging).

### 9.4 Compliance Mapping Engine

The project's original contribution. Everything above uses off-the-shelf libraries (scikit-learn, Fairlearn) as-is; this module is the custom rules-based translation layer from a raw technical finding to a specific, citable NIST AI RMF control ID.

- **`input_reconciler.py`** — joins the two structurally different upstream shapes without force-merging them. Filters `anomaly_findings.json` to genuine findings only (`is_anomaly == True`; `is_anomaly == False` records are normal operation, not findings, and are never mapped). Unpacks each `fairness_findings.json` row — one per attribute, three metrics inline — into three independent per-metric findings, since each metric gets its own severity and control citation.
- **`severity_policy.py`** — deliberately thin: does **not** compute severity (no permutation test, no EEOC comparison — that requires raw per-record data this module doesn't have). It only validates that an incoming `severity_tier` is a known value and resolves what it escalates to.
- **`rules_engine.py`** — orchestrator. `load_lookup_table()` validates `nist_control_lookup.yaml`'s internal consistency at load time (every control ID referenced by `finding_mappings` or `severity_tiers` must exist under `controls`) — fails loudly on a malformed table before any finding is processed, not mid-run. `map_finding()` resolves one finding to its primary/secondary control IDs plus any severity-driven escalation.
- **`explainability_trace.py`** — attaches the *specific* NIST action text matched (not just a bare control ID) and a human-readable trigger explanation per finding, including the anomaly detector's top-contributing-features or the fairness scanner's small-group caveat where relevant. This addresses the explainability-trace gap flagged in CA-1 review (§12).
- **`nist_control_lookup.yaml`** — static, versioned lookup table. Anomaly findings map to **MEASURE 2.4** (production monitoring — its action text names control-limit/ML-based anomaly monitoring almost literally); fairness findings map to **MEASURE 2.11** (fairness and bias evaluated); both carry a secondary citation to **MAP 5.1** (impact characterization). Severity is a property of the *finding*, not the finding type: any `violation`-tier finding of any kind escalates generically to **MANAGE 1.3** (response planned/documented) and **MANAGE 1.4** (residual risk documented), via a `severity_tiers` table keyed only on the tier name — this is what lets the escalation logic generalize to data the current sandbox testing doesn't exercise, without a code change.
- **`run_mapping.py`** — CLI entrypoint matching the convention of phases 1–3. Reads both findings files, calls `reconcile()` → `map_finding()`, writes `mapped_findings.json`.
- **Locked-in design decisions** (see `docs/nist_mapping_reference.md`, not yet written — currently only recorded here and in team notes):
  - Anomaly findings are **informational-only, by design** — they never escalate to MANAGE, because no externally-defensible anomaly-severity cutoff exists (same reasoning as the unjustified injection rate, §12). Manufacturing one just to exercise the MANAGE path would repeat that problem, not solve it.
  - `recalibration_required` is documented directly in the YAML: `protected_attributes`, `fairness.min_group_size_warning`, and `fairness.significance_level` will not transfer correctly to a different (e.g. a sponsoring company's) dataset without human review — this is disclosed proactively, not discovered live during a demo.
- **What this module deliberately does NOT do:** GOVERN-function coverage. NIST's GOVERN function (organizational accountability, training, documented risk tolerance) cannot be evidenced by a tool inspecting model outputs — it's the deploying organization's responsibility. VERITAS automates evidence generation for MEASURE and produces citations into MAP and MANAGE; it does not, and structurally cannot, automate GOVERN.

### 9.5 Report Generator (`src/report_generator/`)
- Reads `mapped_findings.json` (phase 4 output) and renders a self-contained, static HTML audit report via a Jinja2 template — no external CDN assets or JavaScript required, designed to be portable and diffable.
- `html_report.py` loads findings, produces a summary (counts by severity tier and finding type, separated violation/informational lists), and renders via `templates/report_template.html`.
- The report includes an explicit **scope disclosure**: VERITAS covers MEASURE + MAP/MANAGE citations only; GOVERN coverage is the deploying organization's responsibility. This is rendered in every report, not left implicit.
- `run_report.py` is the CLI entrypoint, matching the convention of phases 1–4.
- PDF export (`pdf_report.py`) is a placeholder — not yet implemented.
- Output: `audit_report.html` in `outputs/reports/`.

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

**An automated `pytest` suite exists: 66 tests across all five modules, all passing.**

```bash
python -m pytest tests/ -v      # 66 passed
```

| Module | Test file | What's covered |
|---|---|---|
| Ingestion | `test_ingestion.py` | Schema validation (valid/invalid records, fail-loud on the first bad record in a batch — not a silent drop); anomaly-injection contract (rare auth method + off-hours timestamp for injected records, correct ground-truth label); feature engineering (off-hours/rare-auth flag correctness, zero-mean standardization, zero-std divide-by-zero guard); audit-subject model (predictions returned for every row, not just the held-out split; valid label/confidence ranges) |
| Anomaly Detection | `test_anomaly_detection.py` | Label-leakage guard (`ground_truth_operational_anomaly` / `true_label` must never enter the feature matrix — raises if they do); knee-point threshold determinism and range; grid-search threshold recovery on a manufactured clean separation; evaluation metrics (precision/recall against ground truth); output schema accept/reject |
| Fairness Scanner | `test_fairness_scanner.py` | EEOC threshold boundary behavior (`<` not `<=`); small-group flagging; fail-loud on missing `true_label`; manufactured disparate-impact detection with known expected ratio; **permutation test**: determinism for a fixed seed, correctly flags a manufactured real disparity, correctly does NOT flag an irrelevant/random sensitive feature, reports a Monte Carlo standard error; output schema accept/reject |
| Compliance Mapping | `test_compliance_mapping.py` | Happy-path control mapping for both finding types; informational findings never discarded and never escalate; violation findings correctly escalate to MANAGE 1.3/1.4; anomaly findings never escalate (locks in the informational-only design decision); reconciler filters `is_anomaly=False` records out; reconciler unpacks one fairness row into three independent metric findings with correct per-metric severity; every mapped finding carries non-empty matched NIST action text; fail-loud on an unmapped finding type and on a malformed lookup table |
| Report Generator | `test_report_generator.py` | `load_mapped_findings` fails loudly on wrong JSON key; `summarize` counts by severity tier and finding type correctly; rendered HTML includes both severity sections, GOVERN scope disclosure ("deploying organization"), and handles zero-violation case; end-to-end `write_html_report` file I/O roundtrip |

**What this suite does NOT cover, disclosed rather than assumed away:**
- **No orchestrator-level integration test.** Each module is tested in isolation; nothing currently runs the full five-phase pipeline as one automated sequence and asserts on the final output.
- **No CI wiring.** Tests are run manually (`pytest tests/`), not on push/PR.
- **MEASURE 2.13** (evaluating the TEVV process's own effectiveness — e.g., confirming the fairness scanner actually detects a known injected disparity and does not false-positive on random data at roughly the stated significance rate) is partially covered by the permutation-test unit tests above, but no end-to-end "does this whole pipeline correctly identify a known-bad classifier" test exists yet.

---

## 12. Known Limitations / Open Items

| Issue | Status | Impact |
|---|---|---|
| No explainability trace between the anomaly/fairness threshold gate and the resulting control ID assignment | **Resolved.** `explainability_trace.py` attaches the specific matched NIST action text and a trigger explanation (including top-contributing-features / small-group caveats) to every mapped finding. | Closed — verify against a real dataset run before treating as fully proven at scale |
| Sub-threshold findings silently discarded | **Resolved by design.** `severity_tier` (`informational` / `violation`) is required on every finding; `informational` findings are still mapped and output, never dropped. Enforced by `output_schema.py`'s validation. | Closed |
| No finalized numeric thresholds for `demographic_parity_difference` / `equalized_odds_difference` | **Resolved via permutation significance test**, not a fixed constant. `significance_level` (0.05 default) remains a disclosed human policy choice — do not present the permutation test as removing human judgment entirely, only as removing the arbitrary-constant problem. | Say "data-driven with a disclosed significance threshold," not "fully automatic" |
| Anomaly injection rate (3%) has no external benchmark | **Unresolved.** Chosen as an internal design parameter, not sourced from an industry anomaly base-rate. | Must be either justified or explicitly labeled as an experimental parameter in any report |
| Two threshold-selection methods for IsolationForest contamination can disagree substantially | **Resolved as designed, documented as expected behavior, not a bug.** On test data, unsupervised knee-point selected ~10.5% vs supervised grid search's ~3%. This is diagnostic (real numeric outliers exist beyond the injected ones), not an error — but it means the 10.5%-level flagged set has NOT been manually verified for correctness. | Manually inspect non-ground-truth flagged records before citing detector performance |
| `config/thresholds.yaml` as a separate file (shown in earlier README drafts and repo trees) | **Resolved — was never actually built.** All configuration, including fairness thresholds, lives in a single `config/config.yaml`. | This README previously misrepresented the repo structure; corrected here |
| No automated test suite | **Resolved.** 66 tests across all five modules (§11). Not resolved: no orchestrator-level integration test, no CI wiring — see §11's explicit "not covered" list. | Manual verification no longer needed for unit-level regressions; an end-to-end orchestrator integration test is still an open item |
| Prior tech-stack framing implied an "optional LLM assist" path alongside "deterministic rules engine" | **Resolved.** Architecture is stated as deterministic-only throughout this document. | If an LLM-assist path is ever reintroduced, this document and the module diagram must be updated together |
| Phase 4 was designed against an assumed Phase 2/3 output schema before their real source was reviewed | **Resolved, but worth recording as a process lesson.** `AnomalyFinding` has `is_anomaly: bool`, not a `severity_tier`; Phase 2's findings list includes every record, not just flagged ones; `FairnessFinding` is one row per attribute with all three metrics inline, not per-metric records. `input_reconciler.py` was rewritten against the real schemas after reading the actual source. | Any future module built against an "assumed" contract for an already-built upstream module should be verified against real source before being treated as done |
| Anomaly findings are permanently `informational` — can never trigger a MANAGE-stage response | **Resolved as an explicit design decision, not a gap.** No externally-defensible anomaly-severity cutoff exists (same reasoning as the unbenchmarked injection rate above); manufacturing one to exercise the MANAGE path would repeat that exact problem. Revisit only if an external anomaly-severity standard is identified. | State this as a deliberate scope boundary if asked, not as an oversight |
| GOVERN function has zero representation in the codebase | **By design, not a gap.** GOVERN (organizational accountability, training, documented risk tolerance) cannot be evidenced by a tool inspecting model outputs — it is the deploying organization's responsibility. VERITAS's honest scope claim is "automates MEASURE evidence generation, cites into MAP and MANAGE" — not "implements the AI RMF." | Do not claim full RMF coverage in the report or demo |
| Compliance Mapping Engine has no CLI entrypoint | **Resolved.** `run_mapping.py` provides a CLI entrypoint (`python -m src.compliance_mapping.run_mapping`) matching phases 1–3's conventions. Phases 1–5 have been run sequentially against the real dataset. Orchestrator wiring remains open. | Closed — orchestrator is the remaining gap |
| Permutation test performance at full dataset scale is untested | **Partially resolved.** The pipeline has completed against the full ~45K-row dataset, so the permutation test does finish, but it has not been formally benchmarked or profiled. | Formally benchmark before assuming performance guarantees |

---

## 13. Roadmap

- [x] Run phases 1–5 against the full, real UCI Adult Income dataset
- [ ] Manually inspect the non-ground-truth records flagged by the unsupervised knee-point detector to confirm they're genuine outliers, not noise
- [ ] Source or explicitly label the anomaly injection rate (3%) as an experimental, non-benchmarked parameter
- [x] Decide and implement a numeric threshold approach for `demographic_parity_difference` and `equalized_odds_difference` — done via permutation significance test
- [x] Design and build the Compliance Mapping Engine (phase 4) — core logic and CLI entrypoint built
- [x] Build the explainability trace from threshold gate through to control ID assignment
- [x] Write an actual `pytest` suite — 66 tests across all five modules
- [x] Build a CLI entrypoint for the Compliance Mapping Engine (`python -m src.compliance_mapping.run_mapping`)
- [ ] Build `src/orchestrator.py` with proper concurrent execution and per-job exception handling
- [x] Run phases 1–5 sequentially as one pipeline against the real dataset
- [ ] Benchmark the permutation test's runtime at full dataset scale (formally profile, not just "it completed")
- [ ] Decide whether `fairness.significance_level` (0.05 default) is the right value for this specific use case, or whether a stricter value is warranted
- [x] Build the Report Generator (phase 5) — HTML report implemented; PDF export pending
- [ ] Populate `docs/nist_mapping_reference.md` and `docs/module_contracts.md`, which are referenced but do not yet exist
- [ ] Consider an end-to-end test approximating MEASURE 2.13 (TEVV process effectiveness) — confirm the pipeline detects a known-bad classifier and does not false-positive on a known-fair one, beyond the current unit-level permutation-test coverage

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