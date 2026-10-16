# VERITAS — Agentic Upgrade Specification (v2)

**Project:** VERITAS (OPT-2) — Verifiable Evidence & Risk Identification Toolkit for AI Systems
**Sponsor:** Optywise AI Solutions
**Place in repo:** `docs/agentic_upgrade.md` (referenced from README §3.1)
**Status:** Design. Nothing in this document is implemented yet. Items tagged `[VERIFY]` must be checked against a source or the real code before being stated as fact.

---

## 0. What changed from v1

v1 was written from stale notes. This version is aligned to the current README.

| v1 said | Reality (README) | v2 change |
|---|---|---|
| No automated tests exist | 84 pytest tests across all modules | Agent layer extends the suite; adds a golden-equivalence test |
| PDF deferred | HTML and PDF both generated | No PDF work planned |
| Plain pipeline | `orchestrator.py`, `VeritasPipeline`, SHA-256 manifests, Streamlit dashboard exist | Agents wrap these as tools; nothing is rewritten |
| Agent-2 chooses between knee-point and grid search | Grid search needs injected ground-truth labels, so it is validation-only | On uploaded real logs Agent-2 uses knee-point only |
| Agent-1 "proposes fixes for malformed rows" | Invalid labels are rejected before analysis | Agent-1 may map columns, never alter values |
| Agent-3 may set `significance_level` | It is a disclosed human policy choice | Agent may only recommend; the human sets it |
| Agent trace maps to NIST GOVERN/MANAGE | README: GOVERN cannot be evidenced by a tool inspecting model outputs | Claim removed. The trace is provenance only |

---

## 1. Goals and non-goals

### Goals
1. Wrap the existing five phases in a multi-agent system (Master + six agents) that adapts to unseen log schemas and datasets.
2. Replace report explanations that restate finding values with plain-English problem statements and concrete fixes.
3. Keep every metric, verdict, and NIST control ID reproducible and traceable.
4. Demonstrate with measurements that the agentic mode is better than the deterministic mode, not just different.

### Non-goals
- Regulator-accepted certification, live production integration, multi-framework support, real user data in development (unchanged scope exclusions).
- Claiming GOVERN coverage.
- Letting any LLM output become evidence without a deterministic check.

---

## 2. Core design principle: the determinism boundary

> Agents decide **what to run and how to configure it**. Deterministic tools compute **every number, verdict, and control ID**.

| Decision | LLM allowed? | Notes |
|---|---|---|
| Column-name mapping for an uploaded log | Yes, as a *proposal* | Pydantic validation and the existing label checks accept or reject |
| Candidate `protected_attributes`, proxy-feature flags, `min_group_size_warning` suggestions | Yes, as a *proposal* | Human approves before the run |
| `significance_level` | **No** (recommendation text only) | Policy choice per README §7 and §12 |
| Anomaly scores, contamination (knee-point), fairness metrics, permutation tests, EEOC check | **No** | Existing code, fixed seeds |
| `severity_tier`, MANAGE escalation | **No** | `severity_policy.py` and `nist_control_lookup.yaml` |
| NIST control IDs | **No** | Lookup table only. Unknown finding type becomes `unmapped` for a human |
| Wording of explanations, executive summary, dashboard Q&A | Yes, behind the verifier (Section 8) | Deterministic draft always exists as fallback |

---

## 3. Architecture

```
                         ┌────────────────────────────┐
                         │        Master Agent         │
                         │   (LangGraph supervisor)    │
                         └─────────────┬──────────────┘
                                       │ AuditState (Pydantic)
 Agent-1 Ingest & Validate ──▶ Agent-2 Anomaly ──┐  (parallel, join at gate)
                           └─▶ Agent-3 Fairness ─┘
                                       ▼
                         [ Human approval gate: config ]
                                       ▼
                    Agent-4 Compliance Mapping (rules-only core)
                                       ▼
                    Agent-5 Report (template → rewrite → verifier)
                                       ▼
                    Agent-6 Dashboard Q&A (read-only)

 Cross-cutting: Trace logger (hashed tool calls) → extends run_manifest.json
```

### 3.1 How agents attach to existing code

Agents call the existing entrypoints as tools. They do not reimplement them.

| Tool | Wraps (from README) | Note |
|---|---|---|
| `ingest_log` | dashboard validation path; `run_ingestion()` for the UCI path | Two ingestion paths exist today (UCI synthetic and user upload). `[VERIFY]` how the dashboard normalizes uploads in `dashboard/services/` |
| `run_anomaly` | `run_anomaly_detection()` | Knee-point contamination on real uploads |
| `run_fairness` | `run_fairness_scan()` | Takes the approved `RunConfig` |
| `run_mapping` | `run_mapping()` → `reconcile()` → `map_finding()` | Unchanged |
| `run_report` | `src/report_generator/run_report.py` | `[VERIFY]` function names |
| `read_findings` | JSON readers for `outputs/logs/*.json` | Read-only, used by Agent-6 |

### 3.2 Two execution modes (both permanent)

- **Deterministic mode:** agents off, fixed config from `config/config.yaml`. This is today's behaviour and the baseline for every experiment.
- **Agentic mode:** the graph in this document.

The golden-equivalence test (Section 10) proves the two modes produce identical numbers and control IDs for the same config.

---

## 4. Shared state (sketch)

```python
from pydantic import BaseModel
from typing import Literal, Optional

class RunConfig(BaseModel):
    protected_attributes: list[str]
    min_group_size_warning: int
    significance_level: float          # human-set only
    permutations: int = 1000
    permutation_random_state: int = 42
    source: Literal["config_yaml", "agent_proposed"] = "config_yaml"
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

class TraceEvent(BaseModel):
    seq: int
    agent: str
    tool: str
    input_hash: str                    # SHA-256, same scheme as run_manifest.json
    output_hash: str
    timestamp: str
    rationale: Optional[str] = None    # LLM's stated reason, clearly labelled as such

class AuditState(BaseModel):
    run_id: str
    mode: Literal["deterministic", "agentic"]
    upload_path: Optional[str] = None
    schema_mapping: dict[str, str] = {}
    schema_confidence: Optional[float] = None
    config: Optional[RunConfig] = None
    artifact_paths: dict[str, str] = {}    # normalized_log, anomaly, fairness, mapped, report
    unmapped_findings: list[str] = []
    trace: list[TraceEvent] = []
    status: Literal["running", "awaiting_approval", "failed", "done"] = "running"
```

---

## 5. Agent specifications

### Master Agent
- LangGraph `StateGraph` with fixed edges, not free-form agent chat. Bounded retries (default 2). On repeated failure the run stops with a clear message and never skips a phase silently. `[VERIFY: LangGraph checkpointer and interrupt API for the installed version]`
- Enforces the approval gate before Agent-4.

### Agent-1 — Ingestion & Validation
- **Decides:** which uploaded column plays which role (prediction, actual, protected attribute, features), using column names plus value profiles. Extends the dashboard's current alias table (`prediction`/`predicted_label`, `actual`/`true_label`, `gender`/`sex`).
- **Asks the user** when confidence is below a threshold, showing the proposed mapping.
- **Never:** changes cell values, imputes labels, or "repairs" rows. Invalid or missing labels are rejected exactly as today.
- **Acceptance:** the existing validation path, not the LLM.

### Agent-2 — Anomaly Detection
- **Decides:** nothing numeric. It runs the existing detector with knee-point contamination, reads the discrepancy warning, and reviews flagged records for the open README item "manually inspect the non-ground-truth records flagged."
- **Adds value by:** grouping flagged records by dominant contributing feature and summarising likely causes for the report.
- Grid search and per-type precision/recall run only on the synthetic UCI path, where ground truth exists.
- Anomaly findings stay `informational` (README design decision). The agent cannot change that.

### Agent-3 — Fairness Scanner
- **Proposes:** `protected_attributes`, likely proxy features, and a `min_group_size_warning` suited to the dataset size. This addresses the documented `recalibration_required` items for a sponsor dataset.
- **Recommends, does not set:** `significance_level`. It may explain the trade-off (for example 0.05 vs 0.01); the human chooses.
- **Hard rule:** metrics and verdicts come only from the existing scanner.

### Agent-4 — Compliance Mapping
- Orchestration only. Calls `run_mapping`. If any finding is `unmapped`, it pauses and surfaces it to a human. It never authors or guesses a control ID.

### Agent-5 — Report Generation
- Builds the report using the explanation layer (Section 8). LLM rewriting is optional and sits behind the verifier.
- HTML and PDF paths are the existing ones.

### Agent-6 — Dashboard Q&A
- Conversational layer inside Streamlit. Not a UI generator.
- Read-only tools: `query_findings`, `get_record_explanation`, `get_control_text`, `get_trace`.
- Every answer cites finding IDs. If the data does not contain the answer, it says so.

---

## 6. Approval gate

Shown on the dashboard before Agent-4:
- Proposed `RunConfig` with each agent's rationale, next to the current `config.yaml` values.
- Agent-1's schema mapping and validation summary.
- A required field for `significance_level` (pre-filled with 0.05, editable).

The user can approve, edit, or reject. Approval is recorded in `RunConfig` and the trace.

**Implementation choice:** run the graph in two stages (propose → wait → execute) instead of relying on a mid-graph interrupt, because Streamlit reruns the script on every interaction and a stage boundary is easier to keep correct than a paused graph. `[VERIFY: test both approaches in a small spike before committing]`

---

## 7. Guardrails and trace

1. **Trace logger:** each tool call records agent, tool, input hash, output hash, timestamp, rationale. Reuse the SHA-256 scheme from `run_manifest.json`. The trace is provenance, not a NIST claim.
2. **Allowlists:** each agent can call only its listed tools.
3. **Typed hand-offs:** agents pass `AuditState` only, never free text between phases.
4. **Reproducibility:** LLM temperature 0 where supported, existing seeds (42 for permutations) untouched, final `RunConfig` saved with the report.
5. **Data privacy:** raw rows never go to an external LLM API. Send column names, dtypes, and summary statistics only, or use a local SLM. Decision needed (Section 12).
6. **No silent discard:** sub-threshold findings stay in the report as `informational`, as today.
7. **Honest scope text:** the report keeps its existing MEASURE + MAP/MANAGE scope disclosure.

---

## 8. Plain-English explanations with fixes

### 8.1 Problem
Report explanations restate values from anomaly, fairness, and mapping findings. The reader still has to work out what is wrong and what to do.

### 8.2 Required content per finding
1. **What we found:** one or two simple sentences with the key numbers filled in.
2. **Why it matters:** the risk in plain language.
3. **How to fix it:** 2 to 4 ordered steps.
4. **Where it maps:** control ID plus a one-line description from `nist_control_lookup.yaml`.

### 8.3 Where it plugs in
`explainability_trace.py` already attaches `matched_action_text` and a trigger explanation to each `MappedFinding`. `[VERIFY: read the file; likely the source of the copied-values problem]`

Add **optional, backward-compatible** fields to `MappedFinding` in `compliance_mapping/output_schema.py`:
- `plain_explanation: Optional[PlainExplanation]` (what / why / steps / control text)
- `remediation_ids: list[str]`

Optional fields keep existing tests passing. Update `docs/module_contracts.md` in the same change.

### 8.4 Pipeline

```
MappedFinding (existing fields)
   ├─▶ explanation_templates.yaml   what / why with {placeholders}
   ├─▶ remediation_catalog.yaml     steps keyed by type + metric + tier
   └─▶ nist_control_lookup.yaml     control ID + description
          ▼
   deterministic draft ──▶ (optional) Agent-5 rewrite for readability
          ▼
   verifier ──pass──▶ report      └─fail──▶ keep deterministic draft + log rejection
```

The deterministic draft is complete on its own. The LLM may only improve wording and grouping.

### 8.5 Examples (illustrative numbers, not real results)

**Fairness violation**
> **What we found:** The model gives the positive outcome to about 18% of women but 31% of men, a ratio of 0.58.
> **Why it matters:** The four-fifths rule expects at least 0.80. At 0.58 the model may be treating women unfairly, which creates legal and reputational risk.
> **How to fix it:** 1) Check whether women are under-represented or labelled differently in the training data. 2) Review features that may act as stand-ins for sex. 3) Retrain with a fairness mitigation method and re-run this audit. 4) Document the decision and keep monitoring this ratio.
> **Mapped to:** MEASURE 2.11, secondary MAP 5.1; escalates to MANAGE 1.3 and 1.4 because this is a violation.

**Anomaly group**
> **What we found:** 14 records have unusually high values for hours per week, far above most records.
> **Why it matters:** Outliers can come from data-entry errors, system faults, or tampering, and can distort audit results.
> **How to fix it:** 1) Check the source system for these records. 2) Confirm each value is real or a logging error. 3) Correct or exclude errors and record the reason. 4) If real, investigate the cause and add monitoring.
> **Mapped to:** MEASURE 2.4. This finding is informational by design and does not trigger a MANAGE response.

**Small group caveat:** when a group is below `min_group_size_warning`, the text must say the ratio may be unstable and that a larger sample is needed before acting.

### 8.6 Verifier rules
- Every number in the text matches a field in the source finding (rounding rules defined in code).
- Every control ID exists in `nist_control_lookup.yaml` and equals the finding's assigned mapping.
- Every fix step is a `remediation_id` from the catalog; free-form advice is rejected.
- No wording that claims compliance, certification, or a guarantee of fairness.
- On failure, use the deterministic draft and log the rejection.

### 8.7 Remediation catalog format

```yaml
fairness:
  disparate_impact_ratio:
    violation:
      - id: FAIR-001
        text: "Check whether the affected group is under-represented or labelled differently in the training data."
        effort: low
        source: "Mehrabi et al., A Survey on Bias and Fairness in Machine Learning, ACM Computing Surveys 2021"   # [VERIFY]
      - id: FAIR-002
        text: "Review features that may act as stand-ins for the protected attribute."
        effort: medium
        source: "Mehrabi et al. 2021"                                                                              # [VERIFY]
      - id: FAIR-003
        text: "Retrain with a fairness mitigation method and re-run this audit."
        effort: high
        source: "Fairlearn mitigation documentation"                                                               # [VERIFY: method names]
    informational:
      - id: FAIR-900
        text: "No action needed. Keep monitoring."
        source: internal_design_choice
anomaly:
  is_anomaly:
    informational:
      - id: ANOM-001
        text: "Check the source system for the flagged records."
        source: internal_design_choice
```

Entries without a verified external source are tagged `internal_design_choice`, matching the README's convention of disclosing unsourced parameters. `[VERIFY]` the EEOC citation text (Uniform Guidelines, four-fifths rule) before quoting it in a report.

### 8.8 Disclosure
Reports state that fixes are suggestions for the model owner to evaluate, not guarantees of compliance.

### 8.9 Anomaly grouping
One paragraph per dominant contributing feature (from the existing z-score signal), not one per record. List record IDs in an expandable table and explain one representative record.

---

## 9. Streamlit integration

- Tabs: Upload → Validation → Config approval → Results → Report → Ask VERITAS → Trace.
- Run the graph in a background thread and stream node events into `st.status`.
- `st.session_state` holds `run_id`, `AuditState`, approval status.
- Sidebar toggle: **Deterministic mode** (agents off).
- Keep the existing CSV example download and the existing HTML/PDF outputs.

---

## 10. Testing and evaluation

Extend the existing 84-test suite. Add `tests/agents/`.

| Test / experiment | What it proves | Pass criterion |
|---|---|---|
| **Golden equivalence** | Agentic mode with the same config reproduces deterministic mode | Identical SHA-256 of findings and mapped findings (reuse manifest hashing) |
| Tool wrappers | Wrapping changed no behaviour | Existing tests still pass unmodified |
| Allowlist enforcement | An agent cannot call another agent's tools | Call is rejected and logged |
| Verifier | Wrong numbers or control IDs are caught | 100% rejection on injected errors |
| Schema inference | Agent-1 handles unseen headers | Correct mapping on 3 to 5 log files with different column names; ambiguous ones trigger a user question |
| Label safety | Agent-1 never alters values | Output values byte-identical to input for mapped columns |
| Config proposals | Agent-3 proposals are sensible | Reviewed against `recalibration_required` guidance on 2 or more datasets |
| Reproducibility | Same input, 5 runs | Identical numbers and mappings |
| Explanation quality | New reports are clearer than old | Short rubric scored by teammates and guide |
| MEASURE 2.13 end-to-end (existing roadmap item) | Pipeline flags a known-bad classifier and not a known-fair one | Reuse for both modes |

---

## 11. Implementation roadmap

Ordered so that each stage delivers value alone and the cut line is explicit.

| Stage | Deliverable | Depends on | Done when |
|---|---|---|---|
| A | Explanation layer: templates, remediation catalog, verifier, optional schema fields, anomaly grouping, tests | Read `explainability_trace.py` | New report shows what / why / fix / control for every finding; verifier tests pass |
| B | `AuditState`, trace logger, tool wrappers, Master graph in deterministic mode | A not required | Golden-equivalence test passes |
| C | Streamlit integration of the graph, event streaming, deterministic toggle | B | Dashboard runs both modes |
| D | Agent-1 schema inference + Agent-3 proposals + approval gate | C | Schema and label-safety tests pass; approval recorded in trace |
| E | Agent-2 review notes, Agent-5 rewrite behind verifier, Agent-6 Q&A | D | Verifier and Q&A citation checks pass |
| F | Evaluation experiments, README status flip, `docs/module_contracts.md` update | E | Results table filled with real numbers |

**Cut line if time is short:** A + B + C + D gives a defensible agentic system (config proposals, schema inference, approval, trace). E is the polish. Do not start E before A to D are tested.

**README rule:** keep status rows as 🔲 Planned until the code and tests land, then flip them.

---

## 12. Risks and decisions needed

| Risk | Mitigation |
|---|---|
| Panel sees a renamed pipeline | Show config-proposal rationales, schema inference on unseen files, approval gate, trace, and the evaluation table |
| LLM non-determinism | Determinism boundary, golden-equivalence test, deterministic mode |
| Hallucinated advice or numbers | Catalog-only fixes, verifier, fallback draft |
| Sensitive logs sent to an external API | Summaries only or local SLM |
| `MappedFinding` schema change breaks contracts | Optional fields only; update `module_contracts.md` and tests in the same change |
| Scope creep before open items close | Stage order above; open README items (per-type recall, knee-vs-grid review, `significance_level` decision) stay on the roadmap |
| "Agentic" undefined by sponsor | Get the expectation in writing |

### Decisions to confirm
1. What the sponsor means by "agentic" and whether human-in-the-loop is acceptable. A no-human requirement conflicts with audit defensibility, so be ready to argue for the approval gate.
2. Which LLM is allowed (hosted API vs local SLM) and the sponsor's data policy.
3. Whether the sponsor's real dataset schema is available to test Agent-1 against.
4. Who owns which stage, given the team split (this affects the module-ownership story in the final presentation).

### Items to verify before stating as fact
- LangGraph checkpointer and interrupt behaviour in the installed version.
- Function names in `report_generator/run_report.py` and the dashboard service layer.
- `explainability_trace.py` current output fields.
- Fairlearn mitigation method names and the Mehrabi et al. citation details.
- EEOC four-fifths citation wording.
