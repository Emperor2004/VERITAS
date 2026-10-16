from __future__ import annotations

import pandas as pd
import streamlit as st
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from dashboard.services.agentic_runner import create_uploaded_audit_state
from dashboard.services.veritas_runner import build_summary, run_veritas_on_records
from dashboard.utils.data_adapter import normalize_uploaded_dataframe, validate_uploaded_dataframe
from src.agentic.graph import build_audit_graph
from src.agentic.agents.qa_agent import AuditQAAgent
from src.report_generator.pdf_report import render_pdf_report
from src.run_config import RunConfig

st.set_page_config(page_title="VERITAS Audit Intelligence", page_icon="🛡️", layout="wide")

if "agentic_checkpointer" not in st.session_state:
    st.session_state["agentic_checkpointer"] = InMemorySaver()
if "agentic_graph" not in st.session_state:
    st.session_state["agentic_graph"] = build_audit_graph(
        st.session_state["agentic_checkpointer"]
    )
if "qa_chat_history" not in st.session_state:
    st.session_state["qa_chat_history"] = []

# Rich modern aesthetics (Glassmorphism, refined fonts, sleek dark mode)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    .stApp {
        background: radial-gradient(circle at top left, #0f172a 0%, #090d16 100%);
        color: #f1f5f9;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1300px;
    }
    div[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.85);
        backdrop-filter: blur(12px);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    div[data-testid="metric-container"] {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.4);
    }
    .glass-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .badge-violation {
        background: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.4);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-info {
        background: rgba(56, 189, 248, 0.2);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.4);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
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


st.title("🛡️ VERITAS AI Audit Dashboard")
st.caption("Verifiable Evidence & Risk Identification Toolkit for AI Systems (NIST AI RMF)")

with st.sidebar:
    st.header("Input")
    uploaded = st.file_uploader("Choose a CSV or XLSX file", type=["csv", "xlsx", "xls"])
    run_analysis = st.button("Run VERITAS analysis", type="primary")
    st.markdown("---")
    agentic_mode = st.toggle("Agentic Mode (Inference + Proposals + Q&A)", value=True)
    st.caption("Required signals: prediction, actual labels, protected attribute, and numeric features.")
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
    try:
        if uploaded.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)
    except Exception as exc:
        df = None
        st.error(f"Could not read uploaded file: {exc}")

    if df is not None:
        st.subheader("Uploaded data preview")
        st.dataframe(df.head(10), width="stretch")

        if run_analysis:
            try:
                validate_uploaded_dataframe(df)
                records = normalize_uploaded_dataframe(df)
                if not records:
                    raise ValueError("No valid records were produced after normalization.")

                audit_state = create_uploaded_audit_state(records)
                graph_config = {"configurable": {"thread_id": audit_state.run_id}}
                with st.spinner("Validating upload and preparing the approval request..."):
                    graph_result = st.session_state["agentic_graph"].invoke(
                        audit_state.model_dump(mode="python"),
                        config=graph_config,
                    )
                st.session_state["agentic_active_run"] = {
                    "thread_id": audit_state.run_id,
                    "upload_name": uploaded.name,
                    "state": graph_result,
                }
            except Exception as exc:
                st.error(f"Analysis failed: {exc}")
                st.exception(exc)

        active_run = st.session_state.get("agentic_active_run")
        if active_run and active_run["upload_name"] == uploaded.name:
            graph_config = {"configurable": {"thread_id": active_run["thread_id"]}}
            graph_result = active_run["state"]

            if graph_result["status"] == "awaiting_approval":
                interrupt_value = graph_result["__interrupt__"][0].value
                proposal = interrupt_value["proposed_run_config"]
                validation = interrupt_value["validation_summary"]
                config_proposal = interrupt_value.get("config_proposal")

                st.subheader("Review run configuration")
                st.caption(
                    f"{validation['rows']} validated rows; no analysis or control mapping runs until approval."
                )

                if config_proposal and agentic_mode:
                    with st.expander("🤖 Agent-3 Configuration Proposal & Rationales", expanded=True):
                        st.markdown(f"**Sample Size Guidance:** {config_proposal.get('group_size_rationale', '')}")
                        if config_proposal.get("proxy_feature_warnings"):
                            for warn in config_proposal["proxy_feature_warnings"]:
                                st.warning(f"⚠️ {warn}")
                        st.info(f"💡 {config_proposal.get('significance_level_recommendation', '')}")

                st.write("Available protected attributes:", ", ".join(validation["protected_attributes"]))

                widget_suffix = active_run["thread_id"]
                selected_attributes = st.multiselect(
                    "Protected attributes to scan",
                    options=validation["protected_attributes"],
                    default=list(proposal["protected_attributes"]),
                    key=f"protected_attributes_{widget_suffix}",
                )
                config_col1, config_col2, config_col3 = st.columns(3)
                significance_level = config_col1.number_input(
                    "Significance level",
                    min_value=0.001,
                    max_value=0.999,
                    value=float(proposal["significance_level"]),
                    step=0.01,
                    key=f"significance_level_{widget_suffix}",
                )
                min_group_size = config_col2.number_input(
                    "Minimum group size",
                    min_value=1,
                    max_value=1_000_000,
                    value=int(proposal["min_group_size_warning"]),
                    step=1,
                    key=f"min_group_size_{widget_suffix}",
                )
                permutations = config_col3.number_input(
                    "Permutation count",
                    min_value=1,
                    max_value=100_000,
                    value=int(proposal["permutations"]),
                    step=100,
                    key=f"permutations_{widget_suffix}",
                )
                approver = st.text_input("Approver name", key=f"approver_{widget_suffix}")
                approve_col, reject_col = st.columns(2)
                if approve_col.button(
                    "Approve config and run audit",
                    type="primary",
                    disabled=not approver.strip() or not selected_attributes,
                    key=f"approve_{widget_suffix}",
                ):
                    try:
                        approved_config = dict(proposal)
                        approved_config.update({
                            "protected_attributes": selected_attributes,
                            "significance_level": significance_level,
                            "min_group_size_warning": min_group_size,
                            "permutations": permutations,
                        })
                        approved_config = RunConfig.model_validate(approved_config)
                        with st.spinner("Running approved anomaly and fairness analysis..."):
                            active_run["state"] = st.session_state["agentic_graph"].invoke(
                                Command(resume={
                                    "approved": True,
                                    "approved_by": approver,
                                    "approved_run_config": approved_config.model_dump(mode="json"),
                                }),
                                config=graph_config,
                            )
                        st.session_state["agentic_active_run"] = active_run
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not approve this run: {exc}")
                if reject_col.button(
                    "Reject run",
                    disabled=not approver.strip(),
                    key=f"reject_{widget_suffix}",
                ):
                    active_run["state"] = st.session_state["agentic_graph"].invoke(
                        Command(resume={
                            "approved": False,
                            "approved_by": approver,
                            "note": "Rejected by reviewer",
                        }),
                        config=graph_config,
                    )
                    st.session_state["agentic_active_run"] = active_run
                    st.rerun()

            elif graph_result["status"] == "rejected":
                st.warning("This audit run was rejected before analysis and compliance mapping.")

            elif graph_result["status"] == "completed":
                result = {
                    "anomaly": graph_result["anomaly_output"],
                    "fairness": graph_result["fairness_output"],
                    "mapped_findings": graph_result["mapped_findings"],
                    "report_html": graph_result["report_html"],
                    "anomaly_groups": graph_result.get("anomaly_groups", []),
                }
                summary = build_summary(result)
                st.success("Approved audit completed.")

                st.subheader("Executive summary")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total anomalies", summary["anomaly_total"])
                col2.metric("Fairness violations", summary["fairness_violations"])
                col3.metric("Violation findings", summary["mapped_violation_count"])
                col4.metric("Informational findings", summary["mapped_informational_count"])

                tab_anomaly, tab_fairness, tab_mapped, tab_groups, tab_qa, tab_report = st.tabs(
                    [
                        "Anomaly findings",
                        "Fairness findings",
                        "Mapped findings",
                        "Anomaly clusters",
                        "Ask VERITAS",
                        "Audit report",
                    ]
                )
                with tab_anomaly:
                    st.dataframe(pd.DataFrame(result["anomaly"]["findings"]).head(25), width="stretch")
                with tab_fairness:
                    st.dataframe(pd.DataFrame(result["fairness"]["findings"]), width="stretch")
                with tab_mapped:
                    st.dataframe(pd.DataFrame(result["mapped_findings"]), width="stretch")
                with tab_groups:
                    st.subheader("Agent-2: Dominant Feature Outlier Clusters")
                    if result["anomaly_groups"]:
                        for grp in result["anomaly_groups"]:
                            with st.expander(f"Cluster: {grp['dominant_feature']} ({grp['record_count']} records)"):
                                st.write(grp["deterministic_summary"])
                                st.caption(f"Representative Record: {grp['representative_record_id']} (score: {grp['representative_score']})")
                    else:
                        st.info("No anomaly clusters detected.")
                with tab_qa:
                    st.subheader("Agent-6: Conversational Audit Q&A")
                    st.caption("Ask questions about findings, NIST controls, or anomaly clusters.")
                    user_q = st.chat_input("Ask a question about the audit findings...")
                    if user_q:
                        agent = AuditQAAgent(llm_client=None)
                        answer = agent.answer(user_q, {
                            "run_id": active_run["thread_id"],
                            "status": "completed",
                            "mapped_findings": result["mapped_findings"],
                            "anomaly_groups": result["anomaly_groups"],
                        })
                        st.session_state["qa_chat_history"].append((user_q, answer))

                    for q, a in st.session_state["qa_chat_history"]:
                        with st.chat_message("user"):
                            st.write(q)
                        with st.chat_message("assistant"):
                            st.write(a)
                with tab_report:
                    st.html(result["report_html"], width="stretch", unsafe_allow_javascript=True)
                    st.download_button(
                        label="Download PDF report",
                        data=render_pdf_report(result["mapped_findings"]),
                        file_name="veritas_audit_report.pdf",
                        mime="application/pdf",
                        on_click="ignore",
                    )
else:
    st.info("Upload a CSV or XLSX file to begin the VERITAS audit workflow.")
