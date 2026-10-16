# VERITAS: Streamlit → Full-Stack Website

Migration plan and design spec for the VERITAS AI Audit Dashboard.
Written against the uploaded `dashboard/` folder (16 Oct 2026).

**Confidence tags used below:** `[Certain]` = verified by reading the code, running it, or an official doc fetched in this session. `[Likely]` = strong inference, not verified. `[Guessing]` = filling a gap, treat as a hypothesis.

---

## 0. Read this first

1. **The UI is the cheap part. The hard part is state.** `app.py` hides a *pausable, human-approved LangGraph run* inside `st.session_state` (lines 17–22, 111–115, 189–214). A website has no `session_state`, so you must rebuild that lifecycle on the server. `[Certain]`
2. **I only saw the dashboard layer.** The zip contains no `src/` (graph, anomaly detection, fairness scan, mapping, report generators) and no `config/config.yaml`. Everything below about those modules is inferred from how `app.py` calls them. Field names I could not see are marked "check". `[Certain]`
3. **Your reusable code is better than expected.** Only `app.py` imports Streamlit. `services/` and `utils/` have zero Streamlit imports, so the analytics layer ports almost unchanged. `[Certain]`
4. **Two real bugs and one performance problem exist today** (section 4.6). They will bite harder on a public website than in a classroom demo. Both bugs were reproduced; the repro is in the appendix.
5. **"Approver name" is a free-text box** (line 171). For a product whose pitch is accountability, that is not an audit trail. Fix it in the website version (section 7). `[Certain]` about the code, `[Likely]` that it matters for your evaluators.

---

## 1. What exists today → what it becomes

| Streamlit piece (`app.py`) | Website equivalent |
|---|---|
| `st.file_uploader` + `pd.read_csv/read_excel` (l. 82–94) | Drag-and-drop zone → `POST /api/validate` (dry run) |
| `st.dataframe(df.head(10))` | Preview rows returned by the validate endpoint |
| `st.session_state["agentic_active_run"]` | A **run record on the server**, addressed by URL `/runs/{run_id}` |
| `graph.invoke(initial_state)` on button click | `POST /api/runs` → background job → pauses at the approval interrupt |
| `graph_result["__interrupt__"][0].value` | `review` object inside `GET /api/runs/{id}` |
| Multiselect / number inputs (l. 140–169) | Form whose bounds come **from the API** (no duplicated limits in the frontend) |
| Approve / Reject buttons → `Command(resume=…)` | `POST /api/runs/{id}/approve` and `/reject` → `202 Accepted`, background resume |
| `st.metric` ×4 | Summary stat strip |
| `st.tabs` | Route-based tabs (deep-linkable) |
| `st.html(report_html, unsafe_allow_javascript=True)` | **Sandboxed iframe** (section 7.1) |
| `st.download_button` PDF (l. 249) | `GET /api/runs/{id}/report.pdf` (generated on request, not on every rerun) |
| `.head(25)` on anomalies (l. 241) | Server-side pagination and sorting |
| `InMemorySaver` per browser session (l. 18) | **One durable checkpointer for the whole server** (section 4.2) |

---

## 2. Target architecture

```
 Browser ──► Next.js frontend (UI only)
               │  same-origin proxy: /api/* ──►
               ▼
            FastAPI backend  ── imports ──►  existing dashboard/services, dashboard/utils, src/*
               │
               ├─ Job worker (thread pool)   runs graph.invoke(...) off the request thread
               ├─ LangGraph graph (built ONCE at startup) + durable checkpointer
               └─ Run store (SQLite → Postgres later): run metadata, config, summary, result JSON
```

**Why Python stays Python:** your pipeline (`src/*`: scikit-learn, fairlearn, LangGraph, reportlab) is Python. Rewriting it in Node would be a second project. The website is a thin, typed API over the code you already have. `[Certain]`

---

## 3. Stack decisions

| Layer | Pick | Alternative | Why |
|---|---|---|---|
| Backend | **FastAPI** + Pydantic v2 + Uvicorn | Flask | Auto-generated OpenAPI → typed frontend client; Pydantic already underlies your `RunConfig`/`AuditState` (`model_dump`, `model_validate` appear in `app.py`). |
| Frontend framework | **Next.js (App Router) + TypeScript** | Vite + React SPA | Pick the SPA if you do not need a public landing page; it is simpler to host. Next.js wins if you want a landing page and Vercel deploy. Neither choice affects the backend. |
| Styling | Tailwind CSS with **design tokens as CSS variables** (section 8) | CSS Modules | Tokens live in one file; dark mode can be added later without a rewrite. |
| UI primitives | Radix UI / shadcn-style components, restyled | MUI | Accessible primitives (dialog, tabs, select) without inheriting a look you then fight. |
| Data fetching | TanStack Query (polling for run status) | SWR | Polling, caching and retry built in. |
| Tables | TanStack Table | AG Grid | Findings tables need sorting/pagination; AG Grid is overkill. |
| Charts | **Hand-written SVG** for the signature disparity chart; Recharts for anything generic | Plotly | The signature chart is simple geometry and is the memorable element of the design. A chart library fights you on it. |
| Forms | react-hook-form + zod | Formik | Bounds validated client-side *and* server-side. |
| API types | `openapi-typescript` generated from FastAPI's schema | Hand-written types | Prevents frontend/backend drift. |
| Checkpointer | **SQLite locally, Postgres when deployed** (`langgraph-checkpoint-sqlite` / `-postgres`) | `InMemorySaver` | See 4.2. Verify package names against current LangGraph docs before installing. |
| Hosting `[Guessing]` | Frontend on Vercel; backend as a container on Render/Railway/Fly | One VPS | Your pipeline needs a long-lived Python process, which serverless functions handle badly. |

Drop `.xls` support. The uploader accepts it (l. 80) but `xlrd` is not in `requirements.txt`, so it fails on a clean install. `[Certain]`

---

## 4. Backend changes

### 4.1 Minimal-risk file layout

Do **not** move files in the first pass. `veritas_runner.py` computes `CONFIG_PATH` from its own location (`parents[1]` → `dashboard/`, then `.parent` → repo root). Moving it silently breaks config loading. `[Certain]` Add the API *beside* the existing package, then reorganise last.

```
repo/
├─ src/                     # unchanged
├─ config/config.yaml       # unchanged
├─ dashboard/               # keep for now; delete app.py at the end
│  ├─ services/             # reused as-is
│  └─ utils/data_adapter.py # reused after the fixes in 4.6
├─ api/                     # NEW
│  ├─ main.py               # FastAPI app + lifespan (builds graph once)
│  ├─ routes_runs.py
│  ├─ routes_meta.py        # /health, /sample.csv, /config-bounds
│  ├─ schemas.py            # Pydantic response/request models
│  ├─ jobs.py               # thread-pool execution, per-run locks
│  ├─ store.py              # run metadata + results (SQLite)
│  ├─ jsonable.py           # numpy/NaN-safe serialisation
│  ├─ security.py           # auth dependency, upload limits
│  └─ settings.py           # env-driven config (PROJECT_ROOT, DB path, limits)
├─ frontend/                # NEW (section 5)
└─ tests/api/
```

### 4.2 Graph and checkpointer: the part most likely to go wrong

Today each browser session builds its own graph and `InMemorySaver` (l. 17–22). On a server:

- Build the graph **once** in FastAPI's lifespan and share it. `[Certain]` (design requirement)
- Use a **durable** checkpointer. LangGraph's docs state that interrupts pause until resumed, rely on the persistence layer, and say to use a durable checkpointer in production. `[Certain]` See Evidence E1.
- `InMemorySaver` is per-process memory, so with more than one Uvicorn worker an approve request can land on a worker that has never seen the run, and every restart loses all pending approvals. `[Likely]` (inference from what "in-memory" means; not tested).
- Run with a single worker until a durable saver is in place.
- Resume with the same `thread_id` (your `run_id`). Your `app.py` already does this (l. 109, 188). Keep that contract.

**Privacy consequence you must decide on:** the initial graph state carries the uploaded records (`make_initial_audit_state(records, run_config)`), including protected attributes. A durable checkpointer therefore persists raw rows. `[Likely]` (I have not seen `AuditState`.) Add a retention job that deletes checkpoints and raw data after the run completes or after a TTL (suggest 24 h, configurable). `[Guessing]` on the number.

### 4.3 Run lifecycle

```
POST /api/runs ─► validating ─► awaiting_approval ─► running ─► completed
                      │                │                 │
                      └──► failed      └──► rejected     └──► failed
                                       (any) ──► expired (TTL purge)
```

- `awaiting_approval`, `rejected`, `completed` are the three `graph_result["status"]` values `app.py` already branches on. `[Certain]` The rest are API-level states you add.
- Approve returns **202 immediately** and runs `Command(resume=…)` in a worker thread. The UI polls. Reason: `permutations` is allowed up to 100,000 (l. 164), and a blocking HTTP request that long will hit proxy timeouts. `[Likely]`
- Guard against double-submit: approve/reject return **409** unless status is `awaiting_approval`; hold a per-run lock.
- Progress: if the graph exposes node names, stream them (`graph.stream(..., stream_mode="updates")`) and store the current stage so the UI can show "Fairness scan" instead of a spinner. Check `src/agentic/graph.py` for node names and verify the stream mode in the current docs. `[Likely]`

### 4.4 Endpoints

| Method + path | Purpose | Notes |
|---|---|---|
| `GET /api/health` | Liveness | |
| `GET /api/config-bounds` | Min/max/default for significance, min group size, permutations | Source of truth is `RunConfig`; today the bounds are hard-coded in `app.py` (0.001–0.999, 1–1,000,000, 1–100,000). |
| `GET /api/sample.csv` | Sample template | Generate ~500 rows with a fixed seed. The current template has **4 rows** (l. 28–43), too few for any group-size warning to be meaningful. |
| `POST /api/validate` | Dry run: parse, validate, return the **column mapping** | Multipart upload. Returns detected prediction/actual/protected/feature/ignored columns, row count, first 10 rows, errors. Nothing is stored. |
| `POST /api/runs` | Create run, normalise, run graph to the approval interrupt | Returns `run_id`. |
| `GET /api/runs` | Run history (paginated) | Needs the store; optional in v1. |
| `GET /api/runs/{id}` | Status, stage, `review` payload when awaiting approval, `summary` when completed | The polling endpoint. |
| `POST /api/runs/{id}/approve` | Body: protected attributes, significance, min group size, permutations | Validate with `RunConfig.model_validate` as `app.py` does (l. 184). Approver identity comes from auth, **not** the body. |
| `POST /api/runs/{id}/reject` | Body: reason | |
| `GET /api/runs/{id}/anomalies?page&size&sort` | Paginated anomaly findings | Sort key: check the finding dict for the score field (not visible to me). |
| `GET /api/runs/{id}/fairness` | Fairness findings | |
| `GET /api/runs/{id}/findings` | Mapped (NIST) findings, filter by `severity_tier` | `violation` / `informational` are the two tiers in `build_summary`. `[Certain]` |
| `GET /api/runs/{id}/report.html` | Report HTML, with strict headers (7.1) | |
| `GET /api/runs/{id}/report.pdf` | `render_pdf_report(mapped_findings)` on demand | Today it re-renders on every Streamlit rerun (l. 249–250). |
| `DELETE /api/runs/{id}` | Purge run + data | |

### 4.5 Serialisation (will fail on first real run if skipped)

Findings come out of pandas / scikit-learn / fairlearn. Expect `numpy.bool_`, `numpy.float64`, `NaN`, `inf`, timestamps. FastAPI's JSON encoder will raise on some of these and browsers reject `NaN` in JSON. `[Likely]` Write one `to_jsonable()` (numpy → Python scalars, NaN/inf → `null`, datetimes → ISO strings) and pass every result through it before it reaches a response model or the store.

### 4.6 Fixes to make **before** wiring the API

All line numbers refer to `dashboard/utils/data_adapter.py` unless noted. Lines are counted after normalising Windows line endings.

| # | Problem | Evidence | Fix |
|---|---|---|---|
| 1 | **Crash on a valid upload.** Validation accepts `segment` as a protected column (l. 122), but the extractor's candidate list (l. 182–185) omits it. Fallback code then calls `row[col].dtype` on a plain string (l. 196). | Reproduced: `AttributeError: 'str' object has no attribute 'dtype'`. `[Certain]` | Define **one** `COLUMN_ALIASES` constant used by validate, extract and normalise. The lists are copy-pasted in at least three places and have already drifted. Replace the fallback with a DataFrame-level check. |
| 2 | **Slow normalisation.** `_extract_protected_attributes` builds a DataFrame per candidate per row (`row.to_frame().T`, l. 188), and `feature_columns` is recomputed inside the row loop (l. 227–228). | Measured ~3.5 ms/row: 4,000 rows ≈ 14 s, in my sandbox (pandas 3.0.2, numpy 2.4.4). Linear, not quadratic. `[Certain]` for the measurement; ~6 min for 100k rows is an extrapolation `[Likely]`. | Resolve columns **once**, outside the loop; build records with `itertuples()` / `to_dict("records")`. Cap rows at upload time (7.3). |
| 3 | `validate_uploaded_dataframe` runs twice per upload: `app.py` l. 103, and again inside `normalize_uploaded_dataframe` (l. 205). | `[Certain]` | Call `normalize_*` once; add a separate `describe_upload(df)` for the dry-run column map. |
| 4 | `run_veritas_on_records` is imported (`app.py` l. 9) but never called. It runs the pipeline **without** the approval gate. | `[Certain]` | Delete it. Never expose it through the API; it is a way to bypass human sign-off. `import json` in `veritas_runner.py` l. 3 is also unused. |
| 5 | `datetime.utcnow()` (l. 159, 164, 274) is deprecated since Python 3.12; your bytecode shows CPython 3.14. Rows with no timestamp each get a *different* "now". | `[Certain]` deprecation; `[Certain]` per-row difference (call is inside the loop) | `datetime.now(timezone.utc)`, computed once per upload. |
| 6 | Possible dependency mismatch on 3.14: your pycache shows `cpython-314`. | `[Guessing]` that some wheels (scikit-learn, fairlearn, reportlab) lag a new Python | Pin the backend Docker image to the Python version your tests pass on, and run the golden test (section 9) inside it. |

---

## 5. Frontend structure

```
frontend/
├─ app/
│  ├─ layout.tsx                 # fonts, tokens, header
│  ├─ page.tsx                   # Upload + column check
│  ├─ runs/page.tsx              # history (phase 4)
│  ├─ runs/[id]/page.tsx         # redirects to the right step by status
│  ├─ runs/[id]/review/page.tsx  # sign-off
│  ├─ runs/[id]/(results)/
│  │   ├─ layout.tsx             # case-file header + stat strip + tabs
│  │   ├─ summary/page.tsx
│  │   ├─ fairness/page.tsx
│  │   ├─ anomalies/page.tsx
│  │   ├─ controls/page.tsx      # NIST-mapped findings
│  │   └─ report/page.tsx
│  └─ method/page.tsx            # what each check does, in plain language
├─ components/
│  ├─ Dropzone.tsx   ColumnCheck.tsx   RunStepper.tsx   SignOff.tsx
│  ├─ DisparityChart.tsx   FindingsTable.tsx   SeverityMark.tsx
│  └─ ReportFrame.tsx        # the sandboxed iframe
├─ lib/api.ts                # generated client + TanStack Query hooks
└─ styles/tokens.css         # section 8 tokens
```

**Routing rule:** the run's **status decides the page**. `/runs/{id}` redirects: `awaiting_approval` → `/review`, `running` → progress view, `completed` → `/summary`, `rejected`/`failed` → explanatory state. This replaces the long `if/elif` ladder in `app.py` (l. 125–233) and makes refresh/back/share links work, which Streamlit cannot do.

**Polling:** `useQuery` on `GET /api/runs/{id}` with `refetchInterval` of ~1.5 s while status is `validating` or `running`, stopping on terminal states. Move to SSE only if polling proves insufficient. `[Guessing]` that polling is enough at your scale.

---

## 6. Screens (wireframes)

Alignment: left-aligned content, one primary column, a narrow secondary column for context. No centred hero.

### 6.1 Upload + column check

```
┌────────────────────────────────────────────────────────────────────────┐
│ VERITAS                              Runs   Method   Sample file   [Om] │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│ Check a model's predictions for bias and drift.      ┌───────────────┐ │
│ See which NIST AI RMF controls the findings touch.   │ Drop a CSV or │ │
│                                                      │ XLSX here     │ │
│ Your file needs predictions, actual outcomes,        │ up to 10 MB   │ │
│ a protected attribute and one numeric feature.       └───────────────┘ │
│                                                                        │
│ ── after a file is chosen ──────────────────────────────────────────── │
│ loans_q3.csv   12,480 rows   11 columns                                │
│                                                                        │
│  Prediction   prediction                                        found  │
│  Actual       actual                                            found  │
│  Protected    sex, race                                         2 found│
│  Features     feature_a, feature_b, feature_c                   3 found│
│  Not used     record_id, timestamp, confidence                         │
│                                                                        │
│  [ Create audit run ]      Nothing is analysed until you approve.      │
└────────────────────────────────────────────────────────────────────────┘
```

This is the interactive moment: the user sees *how their columns were interpreted* before anything runs. It is possible because the adapter already auto-detects columns via alias lists.

### 6.2 Sign-off (the approval gate, promoted to the centrepiece)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Run 7f3a…c91   loans_q3.csv   12,480 rows validated   ① Upload ② Review ③ Results │
├───────────────────────────────────────────────┬────────────────────────┤
│ Proposed configuration                        │ What will run          │
│  Protected attributes   [x] sex  [x] race     │  Anomaly detection     │
│  Significance level     [ 0.05 ]              │  Fairness scan         │
│  Minimum group size     [ 30   ]              │  NIST control mapping  │
│  Permutation count      [ 1000 ]              │  Report + PDF          │
│  (bounds shown under each field)              │                        │
├───────────────────────────────────────────────┴────────────────────────┤
│ Sign-off                                                               │
│  Reviewer   om@…  (from your login)      Config fingerprint  9c1e4a07  │
│  Date       16 Oct 2026, 14:52 UTC                                     │
│                                                                        │
│  [ Approve and run ]     [ Reject… ]                                   │
└────────────────────────────────────────────────────────────────────────┘
```

The stepper (① ② ③) is a real sequence, so numbering is justified here. The **config fingerprint** (short SHA-256 of the canonical approved-config JSON) is stored with the run and printed in the report, so a result can be tied to the exact settings that produced it. Values shown (0.05, 30, 1000) are placeholders; use whatever the API returns. `[Guessing]` on defaults.

### 6.3 Results

```
┌────────────────────────────────────────────────────────────────────────┐
│ loans_q3.csv · approved by Om · fingerprint 9c1e4a07 · 16 Oct 2026     │
│ 23 anomalies    4 fairness violations    9 violations    14 informational │
│ Summary | Fairness | Anomalies | Controls | Report                      │
├────────────────────────────────────────────────────────────────────────┤
│ Fairness                                                               │
│                                  threshold                             │
│ sex   Female  ████████████████████░░░░░░░░ 0.71 ┆  below threshold     │
│       Male    ████████████████████████████ 1.00 reference              │
│ race  Asian   ████████████████████████░░░░ 0.93 ┆                      │
│       Black   ███████████████████░░░░░░░░░ 0.68 ┆  below threshold     │
│                                                                        │
│ Each bar is a group's selection rate relative to the reference group.  │
│ [ Findings table below, sortable ]                                     │
└────────────────────────────────────────────────────────────────────────┘
```

Numbers in the wireframe are illustrative. The real metric names and values come from `fairness_output["findings"]`. I only know three boolean fields exist: `disparate_impact_violation`, `demographic_parity_violation`, `equalized_odds_violation`. Check the finding schema before designing the exact chart.

---

## 7. Security and privacy (not optional for an audit tool that ingests protected attributes)

### 7.1 Report HTML: treat it as untrusted

`app.py` renders `report_html` with `unsafe_allow_javascript=True` (l. 247). Report content includes strings that come from the uploaded file (group names, column names, IDs), so a crafted CSV could carry markup. `[Likely]` (depends on whether `html_report.py` escapes; I cannot see it).

- **Test it first:** upload a file whose `race` value is `<img src=x onerror=alert(1)>`. If an alert fires in the current report, escaping is missing. Also confirm Jinja2 autoescape is on in `src/report_generator/html_report.py`.
- Render in `<iframe sandbox srcdoc=…>` or point the iframe at `/api/runs/{id}/report.html`.
- If the report needs **no** JavaScript: use `sandbox=""` and serve with `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; img-src data:`.
- If it **does** need JavaScript: `sandbox="allow-scripts"` and **never add `allow-same-origin`**. Combined with same-origin content, those two tokens let the framed page remove its own sandbox.
- Evidence: E2 (MDN: `srcdoc` markup runs same-origin unless sandboxed) and E3 (HTML spec text on `allow-scripts` + `allow-same-origin`).

### 7.2 Identity

- Replace the free-text approver with a login (Auth.js with GitHub/Google is enough for a college project; a shared demo password is the floor). The server stamps `approved_by` from the session.
- If you keep free text for a demo, label it "Reviewer name (not verified)" and store it that way. Do not present it as an audit trail.
- A UUID run ID is hard to guess but it is **not authorisation**. Check run ownership on every route. `[Certain]`

### 7.3 Uploads and data handling

- Limits (proposals, `[Guessing]` on numbers): 10 MB, 100,000 rows, 100 columns; reject early with a clear message.
- XLSX is a zip container: enforce size limits before parsing and parse in the worker, not the request thread. `[Likely]` risk.
- If you ever export findings as CSV, prefix cells that start with `=`, `+`, `-`, `@` to prevent spreadsheet formula injection.
- Do not log row contents. Log run IDs and counts only.
- Retention: purge raw records and checkpoints on a TTL; keep only findings and summary. Provide `DELETE /api/runs/{id}`.
- CORS: prefer the Next.js `/api` rewrite so browser and API share an origin; otherwise allow exactly one origin.
- Add rate limiting on upload/run creation (e.g. `slowapi`).

---

## 8. Design system: "Workpaper"

### 8.1 Concept

An audit workpaper: a sober, document-like surface where evidence is laid out, signed and filed. The product's differentiator is the **human sign-off**, so the sign-off block and the disparity chart get the visual weight; everything else stays quiet.

**Why not keep the current dark slate + gradient look?** It is the default "AI dashboard" look, and your report and PDF are *documents* people print and file. A paper-toned light interface keeps the web UI and the exported report visually continuous. This is a judgement call, not a fact; if your audience prefers dark, flip the tokens (8.2) and keep everything else. `[Guessing]` about audience preference.

**Where the boldness goes:** one signature element, the disparity chart (6.3). Everything else is flat, ruled, and restrained.

### 8.2 Tokens

| Token | Hex | Role | Contrast* |
|---|---|---|---|
| `--paper` | `#EEF1F0` | Page background (cool grey-green, deliberately not cream) | |
| `--sheet` | `#FBFCFB` | Document panels, tables, report frame | |
| `--ink` | `#13202A` | Primary text | 14.6 : 1 on paper |
| `--ink-soft` | `#4A5A66` | Secondary text, input borders | 6.3 : 1 |
| `--rule` | `#C7D0D2` | Hairlines and dividers **only** | 1.4 : 1, decorative |
| `--verdigris` | `#1E6F68` | Primary action, focus ring, approved seal | 5.2 : 1; white on it 6.0 : 1 |
| `--oxide` | `#B3261E` | Violation | 5.8 : 1; white on it 6.5 : 1 |
| `--cobalt` | `#3452A4` | Informational | 6.4 : 1 |
| `--amber` | `#8A5200` | Caution / small-group warning | 5.6 : 1 |
| `--moss` | `#2F7A4B` | Within threshold | 4.6 : 1 |

\*Computed with the WCAG 2.x relative-luminance formula against `--paper` (E5). Body-size text needs ≥ 4.5 : 1; UI component boundaries need ≥ 3 : 1. **`--rule` fails the 3 : 1 test, so never use it as an input or button border**; use `--ink-soft`. Severity is never colour-only: pair each colour with a distinct shape/label (filled square = violation, ring = informational, dash = within threshold).

Radius: 2 px on controls, 0 on tables and the report frame (documents have square corners). No drop shadows; separation comes from rules and the paper/sheet tone shift. Optional dark mode later: swap `--paper`→`#0F1A22`, `--sheet`→`#16242E`, `--ink`→`#E6ECEA`, and re-check every contrast pair.

### 8.3 Type

- **IBM Plex Sans** for UI and headings (600 weight, tight tracking at large sizes).
- **IBM Plex Serif** for the on-screen report and long explanatory copy on `/method` (slightly more line-height than sans: ~1.6 vs ~1.5; line length ≤ 70 characters).
- **IBM Plex Mono** only for run IDs, hashes and the config fingerprint, where character-level legibility matters.
- Numbers in tables: tabular figures (`font-variant-numeric: tabular-nums`). Verify Plex Sans exposes them in your build; fall back to the mono face for numeric columns if not. `[Guessing]`
- Scale: 14 / 16 / 20 / 28 / 40 px. Headings in sentence case. No all-caps eyebrow labels above headings.
- Load via `next/font` so there is no layout shift and no third-party font request at runtime.

### 8.4 Components and states

- **Dropzone:** square-cornered, 1 px `--ink-soft` dashed border; on drag-over the border turns solid `--verdigris`. Error states state the cause and the fix, reusing your existing validation messages (they are already specific).
- **Column check rows:** left label, right detected column(s), a status mark. A missing required row turns oxide and says what to add.
- **Sign-off block:** the only element with a filled `--verdigris` button. After approval it becomes a read-only "stamp": reviewer, timestamp, fingerprint. This stamp is repeated in the results header and the PDF.
- **Severity mark:** small shape + text, never colour alone.
- **Tables:** ruled rows, sticky header, 44 px minimum row height on touch, sortable columns with `aria-sort`. Below 640 px collapse each row into a stacked definition list.
- **Empty and failed states** say what happened and what to do next ("The file has no protected-attribute column. Add one such as sex, gender or race, then upload again.").

### 8.5 Motion

One orchestrated moment: when results first load, the disparity bars grow from zero over ~600 ms, once. Everything else responds only to user action (dialogs opening, tabs switching, button confirming). While a run is `running`, show the real stage name from the backend. Respect `prefers-reduced-motion` by disabling the bar animation.

### 8.6 Accessibility floor

Visible keyboard focus (2 px `--verdigris` ring with offset), full keyboard path through upload → review → approve, labelled form fields with associated error text, `aria-live="polite"` for status changes, charts have a text/table alternative, layout works down to 360 px wide.

### 8.7 Copy rules

Sentence case, plain verbs, one name per action throughout ("Approve and run" → toast "Audit approved"). No apologetic errors. Say "protected attribute", not "demographic proxy variable"; explain terms once on `/method`.

---

## 9. Migration plan

Effort figures are `[Guessing]` for one developer working part-time; scale to your calendar.

| Phase | Work | Done when | Est. |
|---|---|---|---|
| **0. Lock behaviour** | Script that runs the **current** pipeline on a fixed sample and saves `summary` + counts as a golden JSON. Apply fixes 4.6 #1, #3, #4, #5. | Golden test passes; the `segment`-only file no longer crashes. | 0.5–1 day |
| **1. API** | `api/` package, single graph + durable checkpointer, run lifecycle, all endpoints in 4.4, `to_jsonable`. | `curl`/pytest can: validate → create run → see `awaiting_approval` → approve → poll to `completed` → fetch PDF, and the summary **matches the golden JSON**. Restarting the server mid-approval does not lose the run. | 2–3 days |
| **2. Frontend skeleton** | Next.js app, generated API client, Upload → Column check → Sign-off → Results with plain tables. No styling beyond tokens. | A new user can finish the whole flow in a browser; refresh on any step lands on the correct page. | 3–4 days |
| **3. Design pass** | Tokens, type, `DisparityChart`, stage progress, sandboxed `ReportFrame`, PDF download, responsive tables. | Lighthouse accessibility ≥ 90 `[Guessing]` as a target; keyboard-only walkthrough passes; the XSS test in 7.1 is neutralised. | 3–4 days |
| **4. Hardening + deploy** | Auth, ownership checks, limits, rate limiting, retention job, `DELETE`, Docker, env config, Playwright end-to-end test, remove `app.py` and Streamlit from requirements. | Fresh clone → `docker compose up` → full flow works; a second user cannot open the first user's run. | 2–3 days |

Total ≈ 2–3 weeks part-time `[Guessing]`. Phases 0–2 give you a *working* site; 3–4 make it good and safe.

### Testing checklist

- **Golden test** (phase 0) as the regression anchor: same input → same summary through Streamlit-era code and through the API.
- **API tests** (pytest + `httpx`): bad file types, empty file, missing columns, non-binary labels (existing messages should surface verbatim), double-approve (409), reject path, restart-resume.
- **Security tests:** the XSS payload (7.1), oversize upload, another user's run ID.
- **Frontend:** Playwright flow upload → approve → results → PDF download; axe-core accessibility scan on each route.

---

## 10. Open questions (answer these and the plan tightens)

1. What does `src/agentic/graph.py` expose: node names (for stage progress) and `AuditState` fields (what is persisted in checkpoints)?
2. Does `report_html` need JavaScript, and is Jinja2 autoescape enabled?
3. What are the keys in anomaly, fairness and mapped finding dicts (score field, metric values, control IDs, NIST function)? The charts and sort keys depend on this.
4. Is this a classroom demo (shared password is fine) or something others will use with real data (real auth + retention policy required)?
5. Where will it be hosted, and is there a deadline? That decides whether phase 4 is full or minimal.

---

## Appendix A: How to reproduce the two code findings

Run from the folder that contains `dashboard/`. Needs only `pandas` and `numpy`.

```python
import importlib.util, time
import numpy as np, pandas as pd

spec = importlib.util.spec_from_file_location("da", "dashboard/utils/data_adapter.py")
da = importlib.util.module_from_spec(spec); spec.loader.exec_module(da)

def make(n, prot="sex"):
    r = np.random.default_rng(0)
    return pd.DataFrame({
        "record_id": [f"r{i}" for i in range(n)],
        "timestamp": ["2026-01-01T10:00:00"] * n,
        prot: r.choice(["A", "B"], n),
        "prediction": r.integers(0, 2, n), "actual": r.integers(0, 2, n),
        "confidence": r.random(n),
        "feature_a": r.random(n), "feature_b": r.random(n), "feature_c": r.random(n),
    })

# Finding 1: validation passes, normalisation crashes
df = make(10, prot="segment")
da.validate_uploaded_dataframe(df)          # passes
da.normalize_uploaded_dataframe(df)         # AttributeError: 'str' object has no attribute 'dtype'

# Finding 2: cost per row
for n in (500, 1000, 2000, 4000):
    t = time.time(); da.normalize_uploaded_dataframe(make(n)); print(n, round(time.time() - t, 2), "s")
```

My run (pandas 3.0.2, numpy 2.4.4): 1.71 s, 3.24 s, 7.10 s, 14.24 s for 500 / 1000 / 2000 / 4000 rows. Your machine will differ; the shape (linear, several ms per row) is what matters. **What would show I'm wrong:** a flat or sub-millisecond per-row time on your machine, or `segment` being handled somewhere upstream that I did not see.

## Appendix B: Evidence and source quality

| ID | Claim | Source | Status | Is the source appropriate? | What would show it wrong |
|---|---|---|---|---|---|
| E1 | LangGraph interrupts pause using the persistence layer, resume via `Command(resume=…)`, and production use needs a durable checkpointer. | LangGraph docs, "Human-in-the-loop": https://docs.langchain.com/oss/python/langgraph/human-in-the-loop | Seen in search results this session | Yes: official vendor docs for the library you use. Docs state a recommendation; "`InMemorySaver` breaks across workers" is **my inference** from its being in-process memory, not a quoted claim. | Test two Uvicorn workers with `InMemorySaver`: approve on a worker that did not create the run. |
| E2 | `srcdoc` lets arbitrary markup run, same-origin with the parent unless sandboxed; mitigate with a sandbox that omits `allow-same-origin`. | MDN, `HTMLIFrameElement.srcdoc`: https://developer.mozilla.org/docs/Web/API/HTMLIFrameElement/srcdoc | Seen in search results this session | Yes: MDN is a maintained reference and carries this exact warning. | The XSS payload test in 7.1 failing to execute in your current report. |
| E3 | `allow-scripts` together with `allow-same-origin` (same-origin content) lets framed content remove its own sandbox. | W3C HTML5 author draft (2011): https://www.w3.org/TR/2011/WD-html5-author-20110809/the-iframe-element.html | Seen in search results this session | **Weak on currency**: a 2011 working draft. The behaviour is long-standing, but confirm against the current WHATWG HTML Standard or MDN's `<iframe>` page before citing in a report. | Current spec text contradicting it (I do not expect this). |
| E4 | Data-adapter bugs and per-row cost. | Your code, executed locally (Appendix A) | Reproduced | Primary evidence; independently re-runnable. | Appendix A giving different results on your machine. |
| E5 | Contrast ratios; 4.5 : 1 text and 3 : 1 UI-component thresholds. | Computed with the WCAG 2.x relative-luminance formula. Thresholds: WCAG 2.1 SC 1.4.3 and 1.4.11 (W3C). | Ratios computed this session; WCAG pages **not fetched** | The formula and thresholds are standard; read the W3C pages to confirm before quoting in a report. | Any independent contrast checker disagreeing with the table. |
| E6 | NIST AI RMF has four core functions (Govern, Map, Measure, Manage), used to group controls. | NIST AI RMF 1.0 (NIST AI 100-1), https://www.nist.gov/itl/ai-risk-management-framework | **Not fetched** this session; stated from general knowledge | Authoritative source, but unverified here: check it, and check whether your `nist_control_lookup.yaml` carries the function. | Your lookup file using a different grouping. |
| E7 | Stack choices (FastAPI, Next.js, TanStack, Tailwind, hosting) | None | Engineering judgement; not sourced | Not evidence, a recommendation. Check each library's current docs and Python 3.14 compatibility before locking versions. | A library lacking support for your Python version. |
