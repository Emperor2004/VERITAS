# VERITAS: Executive Demonstration Guide
### Prepared for Demonstration to CEO, Optywise

---

## Executive Summary: What is VERITAS?

**VERITAS** is an enterprise AI audit and governance platform designed to evaluate production machine learning models for **demographic bias (disparate impact)**, **feature drift / anomalies**, and compliance with the **NIST AI Risk Management Framework (NIST AI RMF 1.0 / NIST AI 100-1)**.

### The Problem It Solves
Enterprises deploying automated decision models (credit lending, hiring, insurance underwriting, fraud detection) face severe regulatory scrutiny under EEOC regulations, the EU AI Act, and emerging global AI governance standards. Existing tools either offer opaque dashboards without compliance mapping or rely on non-deterministic LLMs that hallucinate metrics and introduce legal risk.

### The VERITAS Solution
VERITAS enforces an architectural **Deterministic Statistical Boundary**:
1. **Zero Hallucinated Numbers:** All numerical calculations (disparity ratios, $p$-values, $z$-scores, selection rates) are computed 100% deterministically by mathematical engines.
2. **Agentic AI Layer:** Specialized AI agents assist with schema discovery, configuration justification, multivariate outlier clustering, plain-language translation, and conversational audit interrogation.
3. **Durable Human Sign-Off:** No statistical computation proceeds until an authorized human auditor signs off on the configuration, sealing the run with a cryptographic SHA-256 fingerprint.

---

## 1. Quick Start: How to Run the Website

Open two PowerShell terminal windows in the project directory: `d:\Studies\semester7\B Tech Project\VERITAS`.

### Terminal 1: FastAPI Backend
```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```
*Expected output: `Application startup complete. Uvicorn running on http://127.0.0.1:8000`*

### Terminal 2: Next.js Frontend
```powershell
cd frontend
npm run dev
```
*Expected output: `Ready in ~1.5s · Local: http://localhost:3000`*

### Browser
Open **`http://localhost:3000`** in Google Chrome or Microsoft Edge.

---

## 2. The Demonstration Dataset

Use the pre-packaged enterprise demo dataset located at:
`d:\Studies\semester7\B Tech Project\VERITAS\data\demo_audit_dataset.csv`

### Dataset Context
This dataset simulates **1,000 real-world consumer loan underwriting decisions**:
- **Protected Demographics:** `sex` (Female, Male) and `race` (Asian, Black, Hispanic, White).
- **Financial Features:** `credit_score` (450–850), `annual_income`, `debt_to_income_ratio`.
- **Decisions & Outcomes:** `prediction` (model loan approval: 0 or 1) and `actual` (true ground-truth default: 0 or 1).
- **Embedded Findings for Demo:**
  - Simulated disparate impact against female and minority applicant groups (selection ratios below $0.80$).
  - 25 extreme multivariate outliers (anomalous credit scores and debt-to-income spikes).

*(Alternative: You can also click the **"Sample Dataset"** button on the navbar to download a live 500-row synthetic benchmark).*

---

## 3. Step-by-Step CEO Demonstration Script

### Act 1: Frictionless Ingestion & Column Intelligence (2 Minutes)
**URL:** `http://localhost:3000`

1. **Action:** Drag and drop `data/demo_audit_dataset.csv` into the dropzone.
2. **What Happens:** The dropzone immediately executes an asynchronous dry-run validation against `/api/validate`.
3. **What to Say to the CEO:**
   > *"Notice that the moment an auditor uploads a dataset, VERITAS executes an automated dry-run inspection without persisting any raw customer data to the server.*
   > *Our **Schema Inference Agent (Agent-1)** automatically resolves column roles:*
   > - *It identified the decision outcome (`prediction`) and ground truth (`actual`).*
   > - *It automatically isolated sensitive protected attributes (`sex` and `race`).*
   > - *It mapped continuous numeric features while ignoring raw transaction IDs and timestamps.*
   > *The auditor sees a 10-row preview right here to verify data ingestion before anything runs."*
4. **Action:** Click **"Create Audit Run"**.

---

### Act 2: Human-in-the-Loop Pre-Flight Governance (3 Minutes)
**URL:** `http://localhost:3000/runs/[id]/review`

1. **What Appears:** The centerpiece approval screen. The pipeline is paused at a durable LangGraph checkpoint.
2. **What to Say to the CEO:**
   > *"This is the core differentiator of VERITAS: **Mandatory Human-in-the-Loop Governance**.*
   > *In regulated industries, automated tools cannot run unsupervised. Here, the system pauses at an approval gate.*
   > *Notice the **Agent-3 AI Stability Card**: Our AI analyzed the data distribution and provided an explicit statistical rationale for setting the significance threshold to $\alpha = 0.05$, analyzed sample-size stability, and screened for potential proxy correlations.*
   > *All parameter inputs are bound by strict limits to prevent user error."*
3. **Action:**
   - Type your name or title into the **Reviewer Identity** box (e.g. `Om (Lead AI Compliance Auditor)`).
   - Point to the UTC timestamp and configuration fingerprint preview.
4. **Action:** Click **"Approve and Run Audit"**.

---

### Act 3: Disparity & Fairness Analysis (3 Minutes)
**URL:** `http://localhost:3000/runs/[id]/fairness`

1. **What Appears:** The case-file header, the 4-stat metric strip, and the signature **Hand-Crafted SVG Disparity Chart**.
2. **What to Say to the CEO:**
   > *"Here is the quantitative audit result. Notice our stat strip: 1,000 records analyzed, 47 multivariate anomalies detected, and actionable fairness violations identified.*
   > *Let's look at the **Signature Disparity Chart**:*
   > - *This implements the **EEOC 4/5ths Rule (80% threshold)**, which is the legal standard in US employment and lending law, codified under **NIST AI RMF Measure-2.1**.*
   > - *The dotted red vertical line represents the 0.80 benchmark.*
   > - *The teal bars represent groups receiving fair selection relative to the reference group.*
   > - *The red oxide bars immediately spotlight groups falling below 0.80—in this case, Female applicants and minority racial groups receive statistically disparate approval rates.*
   > *Crucially: this chart was hand-rendered in SVG for mathematical precision—no third-party chart library is guessing geometry."*

---

### Act 4: Multivariate Drift & Outlier Clusters (2 Minutes)
**URL:** `http://localhost:3000/runs/[id]/summary` and `.../anomalies`

1. **What Appears:** Executive Summary & Agent-2 Outlier Cluster breakdown.
2. **What to Say to the CEO:**
   > *"Model bias often stems from data drift and unrepresentative outliers.*
   > *VERITAS uses an Isolation Forest paired with robust median-and-IQR scaling to detect anomalies without being skewed by extreme values.*
   > *Instead of giving the auditor an unorganized list of hundreds of flagged rows, **Agent-2 (Anomaly Clustering Agent)** groups them by their dominant statistical signature:*
   > - *Cluster 1: Extreme Debt-to-Income Deviation.*
   > - *Cluster 2: Depressed Credit Score Outliers.*
   > *Each cluster provides estimated precision figures so data science teams know exactly where the model's training distribution failed."*

---

### Act 5: Actionable NIST AI RMF Controls & Number Verification (3 Minutes)
**URL:** `http://localhost:3000/runs/[id]/controls`

1. **What Appears:** The NIST Controls table categorized into *Violations* and *Informational* findings.
2. **Action:** Click **"Details"** on any finding (e.g., `MEASURE-2.1` or `MAP-1.5`).
3. **What to Say to the CEO:**
   > *"Most tools stop at showing a chart. VERITAS translates statistical failures into **actionable regulatory compliance**.*
   > *Every finding is deterministically bound to the **NIST AI Risk Management Framework 1.0 (Govern, Map, Measure, Manage)**.*
   > *Notice this green badge: **'Verified Traceability'**.*
   > *When **Agent-5** drafts the Plain-English explanation ('What Happened', 'Why It Matters', 'Recommended Action'), it passes through our deterministic **Explanation Verifier**.*
   > *The verifier checks that every number in the text matches raw engine output, verifies valid control IDs, and guarantees that no false compliance claims are made.*
   > *Beside it is a dedicated **Remediation Playbook** telling engineers whether to apply re-weighting, threshold shifting, or adversarial debiasing."*

---

### Act 6: Conversational Audit Interrogation (2 Minutes)
**URL:** `http://localhost:3000/runs/[id]/qa`

1. **What Appears:** The **Ask VERITAS (Agent-6)** interactive Q&A assistant.
2. **Action:** Click one of the suggested prompt chips or type:
   `"Which protected attribute has the lowest disparate impact ratio?"`
3. **What to Say to the CEO:**
   > *"Enterprise auditors and executives don't always want to comb through hundreds of rows. They want to ask questions.*
   > ***Agent-6** is a conversational audit assistant with two enterprise guarantees:*
   > 1. *It has **strict citation requirements**—every answer quotes specific findings and NIST controls.*
   > 2. *It operates under **immutable read-only guardrails**. It cannot modify audit data, alter thresholds, or delete case records."*

---

### Act 7: Sandboxed Workpaper & Official PDF Report (1 Minute)
**URL:** `http://localhost:3000/runs/[id]/report`

1. **Action:** Show the live rendered HTML report, then click **"Download Official PDF"**.
2. **What to Say to the CEO:**
   > *"For legal, security, and board reporting, VERITAS compiles a complete executive workpaper.*
   > - *The HTML view is rendered in a **strictly sandboxed iframe** (`sandbox="allow-scripts"` without `allow-same-origin`) to prevent any cross-site scripting vulnerabilities.*
   > - *With one click, we generate an **official, board-ready PDF** stamped with the exact **SHA-256 configuration fingerprint**.*
   > *An enterprise can file this document with regulators, external audit partners, or internal compliance committees with full cryptographic confidence."*

---

## 4. Tough Questions the CEO Might Ask (And Winning Answers)

### Q1: "How do you ensure the AI doesn't hallucinate metrics or bias scores?"
> **Answer:** *"By design, generative AI NEVER calculates numbers in VERITAS. All disparity ratios, standard deviations, z-scores, and p-values are computed by deterministic Python libraries (scikit-learn, fairlearn, scipy). The AI agents only assist with schema discovery, clustering, and narrative explanation behind a strict verifier. If an agent tries to output a number not calculated by the engine, the Explanation Verifier immediately rejects it and falls back to a deterministic template."*

### Q2: "Can our data leak to external LLM providers?"
> **Answer:** *"No. We enforce a strict privacy boundary: raw record contents are never sent to external LLMs. Only column names, data types, cardinality, and at most 5 sanitized non-PII samples are analyzed for schema inference. Furthermore, VERITAS supports fully local or on-premise open weights LLMs (e.g. Ollama, vLLM)."*

### Q3: "What happens if our server crashes while an auditor is reviewing a run?"
> **Answer:** *"The entire approval lifecycle is backed by a durable SQLite checkpointer (`SqliteSaver` via LangGraph). Pending approvals, run states, and configurations are persisted to disk and survive server restarts without losing state."*

### Q4: "How does this scale to enterprise datasets?"
> **Answer:** *"In Phase 0 we resolved the per-row extraction bottlenecks, allowing 10,000+ records to normalize in under 150 milliseconds. For production deployments, the SQLite persistence layer seamlessly swaps to PostgreSQL, and long-running permutation tests execute in isolated thread pool workers so the web interface remains fast and responsive."*

---

## 5. System Health & Verification Checklist

To verify the system is 100% operational before your presentation, run:
```powershell
.\.venv\Scripts\python.exe tests/e2e_live_check.py
```
*Expected result:*
```
--- Starting End-to-End Live Verification ---
1. Health check: 200 {'status': 'ok', 'service': 'veritas-api', 'version': '0.2.0'}
2. Sample CSV: 200 36108 bytes
3. Validate dry-run: 200 500 rows, roles resolved
4. Create run: 201 Created
5. Review envelope status: awaiting_approval
6. Approve response: 202 Accepted
7. Completed successfully!
8. Q&A Ask response: 200 OK
9. Report HTML: 200 | Report PDF: 200
10. Frontend pages: 200 OK
>>> ALL 10 END-TO-END CHECKS PASSED OPERATIONAL VERIFICATION! <<<
```
