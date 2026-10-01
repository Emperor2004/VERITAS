# VERITAS Module Data Contracts & Schemas

VERITAS enforces strict contracts across all module boundaries. This document specifies the exact JSON schemas and data shapes consumed and produced at each stage of the audit pipeline.

---

## Phase 1: Ingestion Output (`normalized_log.json`)

**Location:** `data/processed/normalized_log.json`  
**Validator:** `src.ingestion.schema.NormalizedLogRecord`

### Top-Level Shape:
An array of objects: `List[NormalizedLogRecord]`

### Record Schema:
```json
{
  "record_id": "SESS-0000001",
  "timestamp": "2026-03-01T10:14:02",
  "session_id": "b3e04a11-54c3-42bc-86aa-83a38d7211bf",
  "auth_method": "password",
  "features": {
    "age": 0.35,
    "education-num": 1.12,
    "hours-per-week": 0.05,
    "capital-gain": -0.21,
    "capital-loss": -0.19,
    "predicted_probability": 0.87,
    "prediction_entropy": 0.38,
    "is_off_hours": 0,
    "is_rare_auth_method": 0
  },
  "protected_attributes": {
    "sex": "Female",
    "race": "White"
  },
  "predicted_label": 1,
  "prediction_confidence": 0.87,
  "true_label": 1,
  "ground_truth_operational_anomaly": false,
  "ground_truth_anomaly_type": null
}
```

---

## Phase 2: Anomaly Detection Output (`anomaly_findings.json`)

**Location:** `outputs/logs/anomaly_findings.json`  
**Validator:** `src.anomaly_detection.output_schema.validate_output`

### Payload Structure:
```json
{
  "findings": [
    {
      "record_id": "SESS-0000001",
      "anomaly_score": 0.4521,
      "is_anomaly": true,
      "top_contributing_features": [
        {
          "feature": "is_off_hours",
          "z_score": 3.42
        },
        {
          "feature": "is_rare_auth_method",
          "z_score": 2.81
        }
      ]
    }
  ],
  "evaluation": {
    "precision": 0.9412,
    "recall": 0.8933,
    "f1": 0.9166,
    "n_ground_truth_anomalies": 1350,
    "n_flagged": 1281,
    "note": "Ground truth covers injected operational anomalies only."
  },
  "threshold_selection": {
    "unsupervised": {
      "method": "knee_point",
      "contamination": 0.03,
      "cutoff_score": 0.3821
    },
    "supervised": {
      "method": "grid_search",
      "contamination": 0.032,
      "f1": 0.92
    }
  },
  "config": {
    "n_estimators": 100,
    "random_state": 42,
    "manual_contamination_override": null
  }
}
```

---

## Phase 3: Fairness Scanner Output (`fairness_findings.json`)

**Location:** `outputs/logs/fairness_findings.json`  
**Validator:** `src.fairness_scanner.output_schema.validate_output`

### Payload Structure:
```json
{
  "findings": [
    {
      "attribute": "sex",
      "selection_rates": {
        "Female": 0.109,
        "Male": 0.305
      },
      "disparate_impact_ratio": 0.357,
      "disparate_impact_violation": true,
      "demographic_parity_difference": 0.196,
      "demographic_parity_p_value": 0.001,
      "demographic_parity_violation": true,
      "equalized_odds_difference": 0.182,
      "equalized_odds_p_value": 0.001,
      "equalized_odds_violation": true,
      "small_group_warning": []
    }
  ],
  "config": {
    "eeoc_four_fifths_threshold": 0.8,
    "min_group_size_warning": 30,
    "protected_attributes_scanned": ["sex", "race"]
  }
}
```

---

## Phase 4: Compliance Mapping Output (`mapped_findings.json`)

**Location:** `outputs/logs/mapped_findings.json`  
**Validator:** `src.compliance_mapping.output_schema.validate_output`

### Payload Structure:
```json
{
  "mapped_findings": [
    {
      "finding_type": "fairness_finding",
      "metric_name": "disparate_impact_ratio",
      "observed_value": 0.357,
      "severity_tier": "violation",
      "source_record_id": "sex",
      "trigger_explanation": "Disparate impact ratio 0.357 is below EEOC four-fifths threshold 0.8.",
      "controls_applied": [
        {
          "control_id": "MEASURE 2.11",
          "title": "Fairness and Bias Measurement",
          "citation": "NIST AI RMF 1.0, MEASURE 2.11",
          "matched_action_text": "AI system fairness and bias are measured, documented, and monitored."
        }
      ],
      "supporting_evidence": [
        {
          "attribute": "sex",
          "selection_rates": {"Female": 0.109, "Male": 0.305}
        }
      ]
    }
  ]
}
```

---

## Phase 5: Audit Reports (`audit_report.html`, `audit_report.pdf`)

**Location:** `outputs/reports/audit_report.html` and `audit_report.pdf`

* **HTML Report**: Self-contained, static single-file HTML document. Includes CSS styles inline (glassmorphism accents, table formatting, severity badges) and operates offline without third-party CDN scripts or tracking.
* **PDF Report**: Rendered directly from semantic HTML styling using WeasyPrint (with fallback diagnostics if GTK3 libraries are not present in the runtime environment).
