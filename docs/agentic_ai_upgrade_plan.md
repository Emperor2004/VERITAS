# VERITAS Agentic AI Upgrade Plan

**Status:** In progress. This plan refines `VERITAS_Agentic_Upgrade.md` against the current repository and the agreed implementation scope.

## Decisions

- Schema inference targets dashboard-uploaded prediction logs first. The UCI Adult Income ingestion and stand-in model remain unchanged.
- The architecture is one Master Agent plus six specialists. Agent-6 is read-only dashboard Q&A.
- A human must approve the effective run configuration before compliance mapping.
- Build and validate a deterministic-only graph before introducing LLM calls.
- No provider or model is selected yet. Do not send raw uploaded rows to an external model until the sponsor's data policy and approved provider are confirmed.
- Metrics, anomaly scores, fairness verdicts, severity decisions, and NIST control IDs remain deterministic outputs of existing tools.

## Current Baseline

The repository already has deterministic ingestion, anomaly, fairness, mapping, and report modules. The subprocess orchestrator runs anomaly and fairness in parallel; the in-memory pipeline and dashboard runner execute them sequentially. Mapping already attaches trigger explanations and NIST action citations. HTML and DOCX report templates and PDF generation are implemented.

Completed foundation work:

- `RunConfig` is an immutable, versioned Pydantic model for analysis settings, input mode, and protected-attribute selection.
- CLI, dashboard, and in-memory paths consume the effective analysis settings. The subprocess manifest and saved in-memory artifacts record the effective config.
- `MappedFinding` now includes a stable opaque `finding_id`, derived from finding type, source ID, and metric; `source_record_id` remains provenance.
- `VeritasPipeline` reads nested IsolationForest settings, and the subprocess CLI receives the project config explicitly.

The current test suite has 95 tests. `RunConfig` does **not** yet capture all Adult-ingestion settings, schema mappings, canonical input identity, or code/dependency identity. The agent graph, approval UI, checkpointing, per-tool trace, schema inference, and Q&A are not implemented.

## Determinism Boundary

Agents may propose schema mappings, configuration, investigation steps, and narrative wording. Deterministic code remains authoritative for validation, metric values, anomaly scores, threshold decisions, severity, and control assignments. Agent proposals must be distinguishable from user-approved effective settings. Unknown controls or finding types must never be guessed into existence.

## Implementation Stages

### 1. Complete the effective run contract

Extend `src/run_config.py` only for settings that can change results. Add Adult model/ingestion options while keeping the Adult path separate from uploaded-prediction semantics. Add a validated schema-mapping representation for uploads when Agent-1 is introduced. Define canonical serialization and hashes for the approved config and input identity; keep volatile timestamps out of result-equivalence checks.

**Acceptance checks:** non-default config values produce the same results through CLI, in-memory, and dashboard entrypoints; invalid policy values fail validation; the approved config snapshot is serialized and can reproduce the run.

### 2. Add typed run state and deterministic adapters

Create versioned Pydantic `AuditState` and `TraceEvent` models with safe default factories. Include run ID, input/artifact references, proposed and approved configuration, lifecycle status, approval record, failures, and trace events. Wrap the current stage functions rather than duplicating algorithms. Define idempotency and bounded retry behavior before enabling retries.

Trace at least the tool/stage name, input and output hashes, effective-config hash, timestamp, status, and rationale when one exists. Avoid storing raw uploaded rows in the trace or sending them to an LLM.

**Acceptance checks:** state round-trips through serialization; invalid transitions are rejected; traces can verify artifact identity; retrying a completed deterministic stage does not silently overwrite a different run.

### 3. Build the deterministic Master graph and approval gate

Use fixed graph edges, not free-form agent-to-agent conversation:

1. Validate input and effective configuration.
2. Run anomaly detection and fairness scanning in parallel.
3. Join both results and pause for explicit human approval.
4. Run compliance mapping only after approval.
5. Generate HTML and PDF reports and finalize the trace/manifest.

Preserve the current CLI, `VeritasPipeline`, and dashboard entrypoints during migration. Define how graph checkpoint/resume works with the existing subprocess manifest and artifact paths.

**Acceptance checks:** mapping cannot run before approval; approve, edit, reject, interrupted, and resumed runs are tested; parallel outputs join once; failures are visible and never silently skip a stage; deterministic numeric findings and control mappings match the current baseline.

### 4. Add Agent-1 for uploaded schemas

Extend `dashboard/utils/data_adapter.py` with a schema profile and proposed column mapping for unfamiliar uploads. Show mappings and confidence to the user before normalization. Keep the current deterministic validator as the final acceptance boundary. Report accepted/rejected rows and reasons; never silently coerce labels or repair values without an explicit, recorded user decision. Do not change `src/ingestion/log_loader.py` as part of this stage.

**Acceptance checks:** test 3–5 distinct schemas, ambiguous and missing columns, invalid labels, missing numeric values, user edits, and rejection. Verify the normalized output passes the existing schema contract and no raw row is sent to a model.

### 5. Add Agents 2 and 3 as config proposers

Agent-2 may propose an allowlisted feature/config choice; Agent-3 may propose protected attributes, proxy-feature cautions, and group-size settings. Keep all calculations in `src/anomaly_detection/` and `src/fairness_scanner/`. Every proposal requires approval before it becomes effective. Treat significance level, protected attributes, and minimum group size as policy choices. Do not expose supervised grid search as a general production threshold selector because it uses ground truth for validation.

**Acceptance checks:** proposals outside schema/range are rejected; approval changes are recorded; unapproved proposals never affect outputs; repeated runs with the same approved config preserve numeric findings and control mappings.

### 6. Add deterministic explanations, remediation catalog, and verifier

Add curated explanation templates and a remediation catalog keyed by finding type, metric, and severity. Build deterministic drafts from fields actually present in source findings. Verify every number against source data, every control against `nist_control_lookup.yaml`, and every remedy against a catalog ID. Keep the current GOVERN-scope and non-certification disclosures. Render the same verified explanation data through `report_template.html` and `report_template.docx`.

**Acceptance checks:** verifier rejects altered numbers, unknown IDs, uncatalogued remedies, and compliance/certification claims; rejection falls back to the deterministic draft and is traced; HTML/PDF content agrees for normal, informational, empty, and small-group cases.

### 7. Add optional Agent-5 report rewriting

Only after the deterministic draft and verifier are stable, allow Agent-5 to improve readability or group related findings. It may not create metrics, verdicts, control IDs, thresholds, or uncatalogued advice. Group anomaly rows by existing contributing-feature evidence; do not invent measurements absent from the findings.

**Acceptance checks:** every generated statement references stable finding IDs; verifier rejection returns the deterministic draft; numeric and control fields are unchanged by rewriting.

### 8. Add Agent-6 read-only Q&A

Expose Q&A in the Streamlit dashboard over persisted, validated run artifacts. Queries may retrieve findings, explanations, controls, and trace events but cannot modify data, configuration, or findings. Answers cite `finding_id`; unknown IDs return an explicit not-found response.

**Acceptance checks:** Q&A is read-only, source-grounded, citation-checked, and tested for unknown IDs and unsupported questions. Confirm session isolation and retention policy before persistence is enabled.

### 9. Evaluate, document, and release

Extend the existing pytest suite for configuration, state transitions, approval, parallel joins, retries, trace integrity, schema proposals, verifier rejection, and Q&A. Compare numeric results and control mappings independently from time-bearing report bytes. Confirm NIST IDs and action text against `Norms/nist_ai_rmf_playbook.json`; repository consistency is not external regulatory validation. Update the root and dashboard READMEs only after implemented behavior is stable.

**Release gate:** full test suite passes; manual upload-to-approval-to-report workflow succeeds; manifest and trace reconstruct the effective run; privacy and provider decisions are approved; remaining limitations are documented.

## Risks and Open Decisions

- Confirm sponsor policy for model/provider, local versus hosted inference, and whether schema summaries may leave the environment.
- Define approver identity, authentication, and audit retention; the current dashboard has no user identity model.
- Define checkpoint and artifact retention and whether uploaded rows are persisted.
- Choose behavior for unknown finding types: preserve current fail-fast behavior or introduce an explicit `needs_review` state. Never silently skip or guess a mapping.
- Verify LangGraph interrupt/checkpointer APIs and the resolved Streamlit version before selecting integration APIs. LangGraph and LLM provider dependencies are not currently declared.
- Define reproducibility as identical numeric findings/mappings with volatile timestamps excluded, or as byte-identical artifacts with timestamps controlled.
- The upload adapter currently fills some absent values with generated defaults; review and explicitly disclose or change those behaviors before schema-inference agents rely on them.

## Key Files

- `src/run_config.py`, `src/pipeline.py`, `src/orchestrator.py`
- `dashboard/app.py`, `dashboard/services/veritas_runner.py`, `dashboard/utils/data_adapter.py`
- `src/anomaly_detection/`, `src/fairness_scanner/`
- `src/compliance_mapping/`, `src/compliance_mapping/nist_control_lookup.yaml`
- `src/report_generator/`, `src/report_generator/templates/report_template.html`, `src/report_generator/templates/report_template.docx`
- `tests/`, `docs/module_contracts.md`, `docs/architecture.md`, `Norms/nist_ai_rmf_playbook.json`
