# NIST AI RMF 1.0 Compliance Mapping Reference

This document details the compliance translation methodology used by the VERITAS Compliance Mapping Engine (Phase 4), establishing a verifiable bridge between technical machine learning findings and standard **NIST AI Risk Management Framework (AI RMF 1.0)** controls.

---

## 1. Compliance Philosophy: Rules-Based vs Generative

VERITAS rejects using large language models or heuristic black boxes to dynamically generate compliance citations. In an audit context:
* **Hallucination Risk**: An LLM could cite nonexistent subcategories or conflate control requirements.
* **Non-Determinism**: An identical audit log run on two different days could generate different control mappings.
* **Auditor Verification**: A third-party regulator or human auditor must be able to trace every finding back to a fixed, peer-reviewed rules table.

VERITAS relies on a deterministic lookup database (`src/compliance_mapping/nist_control_lookup.yaml`) drawn directly from the official **NIST AI RMF Playbook** companion dataset.

---

## 2. Core Mapped Controls

| Control ID | Function / Category | Official Title | Matched Audit Finding |
|---|---|---|---|
| **MEASURE 2.4** | MEASURE: System Performance | Functionality and behavior of the AI system are monitored when in production. | **Anomaly Finding**: Operational anomalies (off-hours executions, rare auth tokens) and feature outliers detected by IsolationForest. |
| **MEASURE 2.11** | MEASURE: Fairness & Bias | Fairness and bias are evaluated and results are documented. | **Fairness Finding**: Algorithmic disparities in disparate impact ratio, demographic parity difference, or equalized odds difference. |
| **MAP 5.1** | MAP: Impact Assessment | Likelihood and magnitude of each identified impact are identified and documented. | **Fairness Finding**: Contextual documentation of potential negative disparate impact on protected demographic groups. |
| **MANAGE 1.3** | MANAGE: Risk Treatment | Responses to the AI risks deemed high priority are developed, planned, and documented. | **Violation Escalation**: Automatically appended to any finding categorized under the `violation` severity tier. |
| **MANAGE 1.4** | MANAGE: Residual Risk | Negative residual risks to downstream users are documented and communicated. | **Violation Escalation**: Mandates documentation of residual unmitigated risk when a statistical or regulatory threshold is crossed. |

---

## 3. Severity Tier & Escalation Policy

Findings are classified into two deterministic severity tiers based on quantitative thresholds:

1. **Informational Tier**:
   * *Criteria*: Statistical metrics that do not cross an enforced legal/statistical threshold (e.g., disparate impact ratio $\ge 0.8$, or raw anomaly scores under the knee-point cutoff).
   * *Escalation*: Mapped directly to monitoring and measurement controls (`MEASURE 2.4`, `MEASURE 2.11`).

2. **Violation Tier**:
   * *Criteria*: Metrics that breach defined thresholds (e.g., EEOC Four-Fifths rule breach where disparate impact $< 0.8$, or confirmed statistically significant disparity with $p < 0.05$).
   * *Escalation Policy*: Escalates automatically by appending risk-treatment controls:
     $$\text{Controls} = \text{Base Controls} \cup \{\text{MANAGE 1.3}, \text{MANAGE 1.4}\}$$
   * Requires organizational intervention, mitigation planning, and documentation of residual harm.

---

## 4. Evidence Trace Structure

Every mapped finding generates an audit trail containing:
* **Trigger Explanation**: Exact numeric comparison (e.g., `0.357 < 0.8 -> violation`).
* **Source Record / Attribute**: Identifies individual transaction ID or protected demographic cohort.
* **Exact NIST Action Text**: Full verbatim text from the NIST Playbook to support formal audit defense.
