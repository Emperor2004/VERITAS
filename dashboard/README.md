# VERITAS Dashboard

The Streamlit dashboard accepts prediction logs, validates and normalizes the upload, runs anomaly and fairness analysis, maps findings to NIST AI RMF controls, displays the HTML report in the website, and provides a PDF document download.

## Install

Run these commands from the repository root. The dashboard has a separate requirements file for its additional dependencies.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r dashboard/requirements.txt
```

On macOS or Linux, activate the virtual environment with `source .venv/bin/activate` instead.

## Start

From the repository root:

```bash
python -m streamlit run dashboard/app.py
```

Streamlit prints the local URL after startup. Keep the working directory at the repository root so the dashboard can load the shared configuration and NIST control lookup.

## Upload Format

Upload CSV or Excel (`.xlsx`) data. Legacy `.xls` files may require the optional `xlrd` package. Column names are case-insensitive and spaces or hyphens are normalized to underscores.

Required data:

| Signal | Accepted examples |
|---|---|
| Prediction | `predicted_label`, `prediction`, `predicted`, `decision`, `output_label`, `model_prediction` |
| Actual outcome | `true_label`, `actual_label`, `ground_truth`, `label`, `target`, `actual`, `outcome` |
| Protected attribute | `sex`, `gender`, `race`, `demographic_group`, `group`, `region`, `protected_group`, `segment` |
| Numeric feature | At least one measurable numeric column not used as a label, protected attribute, ID, or timestamp |

The file must be non-empty and contain at least four columns. Prediction and actual-outcome values must be present and binary: `0`/`1`, true/false, yes/no, or equivalent supported values. Invalid labels are rejected rather than silently converted. The app sidebar includes a sample CSV download with the expected shape.

## Results

After a successful run, the dashboard shows summary counts and tabs for anomaly findings, fairness findings, mapped findings, and the HTML audit report. The HTML report stays on the page; use **Download PDF report** in the report tab for a document copy. The dashboard does not offer HTML or JSON downloads and does not write run artifacts to the repository's `outputs/` directory. The sample CSV download is an input template, not analysis output.
