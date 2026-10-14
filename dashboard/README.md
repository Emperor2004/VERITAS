# VERITAS Dashboard

This folder contains the web dashboard for the VERITAS project.

## Run locally

From the project root:

```bash
python -m streamlit run dashboard/app.py
```

## Supported input

- CSV
- XLSX

The app accepts common prediction-log schemas and adapts them into the internal normalized record format used by the project pipeline.
