from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st

from dashboard.services.veritas_runner import build_summary, run_veritas_on_records
from dashboard.utils.data_adapter import normalize_uploaded_dataframe, validate_uploaded_dataframe

st.set_page_config(page_title="VERITAS Dashboard", page_icon="🛡️", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.9);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _sample_upload_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "record_id": ["r1", "r2", "r3", "r4"],
            "timestamp": [
                "2026-01-01T10:00:00",
                "2026-01-02T11:00:00",
                "2026-01-03T09:00:00",
                "2026-01-04T17:00:00",
            ],
            "sex": ["Male", "Female", "Male", "Female"],
            "race": ["White", "Black", "White", "Asian"],
            "prediction": [1, 0, 1, 0],
            "actual": [1, 0, 0, 0],
            "confidence": [0.9, 0.73, 0.77, 0.6],
            "feature_a": [5, 7, 2, 9],
            "feature_b": [1, 1, 4, 8],
            "feature_c": [10, 8, 6, 9],
        }
    )


st.title("VERITAS AI Audit Dashboard")
st.caption("Upload CSV or XLSX prediction logs and run the audit pipeline in minutes.")

with st.sidebar:
    st.header("Input")
    uploaded = st.file_uploader("Choose a CSV or XLSX file", type=["csv", "xlsx", "xls"])
    run_analysis = st.button("Run VERITAS analysis", type="primary")
    st.markdown("---")
    st.caption("Required signals: prediction, actual/ground-truth labels, protected attribute, and at least one numeric feature column.")
    st.download_button(
        label="Download sample upload template",
        data=_sample_upload_dataframe().to_csv(index=False),
        file_name="veritas_sample_upload.csv",
        mime="text/csv",
    )

    with st.expander("Expected schema"):
        st.code(
            "record_id,timestamp,sex,race,prediction,actual,confidence,feature_a,feature_b,feature_c",
            language="text",
        )

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

            tab_anomaly, tab_fairness, tab_mapped, tab_report = st.tabs(["Anomaly findings", "Fairness findings", "Mapped findings", "Audit report"])

            with tab_anomaly:
                anomaly_df = pd.DataFrame(result["anomaly"]["findings"])
                st.dataframe(anomaly_df.head(25), use_container_width=True)

            with tab_fairness:
                fairness_df = pd.DataFrame(result["fairness"]["findings"])
                st.dataframe(fairness_df, use_container_width=True)

            with tab_mapped:
                mapped_df = pd.DataFrame(result["mapped_findings"])
                st.dataframe(mapped_df, use_container_width=True)

            with tab_report:
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
