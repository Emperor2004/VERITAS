from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st

from dashboard.services.veritas_runner import build_summary, run_veritas_on_records
from dashboard.utils.data_adapter import normalize_uploaded_dataframe, validate_uploaded_dataframe

st.set_page_config(page_title="VERITAS Dashboard", page_icon="🛡️", layout="wide")

st.title("VERITAS AI Audit Dashboard")
st.caption("Upload CSV or XLSX prediction logs and run the audit pipeline in minutes.")

with st.sidebar:
    st.header("Input")
    uploaded = st.file_uploader("Choose a CSV or XLSX file", type=["csv", "xlsx", "xls"])
    run_analysis = st.button("Run VERITAS analysis", type="primary")
    st.markdown("---")
    st.caption("Expected columns include prediction, true labels, protected attributes, or a similar AI log schema.")

if uploaded is not None:
    if uploaded.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)

    st.subheader("Uploaded data preview")
    st.dataframe(df.head(10), use_container_width=True)

    if run_analysis:
        try:
            validate_uploaded_dataframe(df)
            records = normalize_uploaded_dataframe(df)
            if not records:
                raise ValueError("No valid records were produced after normalization.")

            with st.spinner("Running anomaly detection, fairness scan, and compliance mapping..."):
                result = run_veritas_on_records(records)
                summary = build_summary(result)

            st.success("Analysis complete.")

            st.subheader("Executive summary")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total anomalies", summary["anomaly_total"])
            col2.metric("Fairness violations", summary["fairness_violations"])
            col3.metric("Violation findings", summary["mapped_violation_count"])
            col4.metric("Informational findings", summary["mapped_informational_count"])

            st.subheader("Anomaly findings")
            anomaly_df = pd.DataFrame(result["anomaly"]["findings"])
            st.dataframe(anomaly_df.head(25), use_container_width=True)

            st.subheader("Fairness findings")
            fairness_df = pd.DataFrame(result["fairness"]["findings"])
            st.dataframe(fairness_df, use_container_width=True)

            st.subheader("Mapped findings")
            mapped_df = pd.DataFrame(result["mapped_findings"])
            st.dataframe(mapped_df, use_container_width=True)

            st.subheader("Audit report")
            report_html = result["report_html"]
            st.components.v1.html(report_html, height=900, scrolling=True)

            st.download_button(
                label="Download report (.html)",
                data=report_html.encode("utf-8"),
                file_name="veritas_audit_report.html",
                mime="text/html",
            )

            mapped_json = __import__("json").dumps({"mapped_findings": result["mapped_findings"]}, indent=2, default=str)
            st.download_button(
                label="Download mapped findings (.json)",
                data=mapped_json,
                file_name="mapped_findings.json",
                mime="application/json",
            )

        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
            st.exception(exc)
else:
    st.info("Upload a CSV or XLSX file to begin the VERITAS audit workflow.")
