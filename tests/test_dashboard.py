from __future__ import annotations

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from dashboard.app import st  # noqa: F401
from dashboard.services.veritas_runner import build_summary, run_veritas_on_records
from dashboard.utils.data_adapter import normalize_uploaded_dataframe, validate_uploaded_dataframe


def _sample_uploaded_df() -> pd.DataFrame:
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


def test_normalize_uploaded_dataframe_creates_valid_records():
    df = _sample_uploaded_df()

    records = normalize_uploaded_dataframe(df)

    assert isinstance(records, list)
    assert len(records) == 4
    assert all("record_id" in r for r in records)
    assert all("features" in r for r in records)
    assert all("protected_attributes" in r for r in records)
    assert all("predicted_label" in r for r in records)
    assert all("true_label" in r for r in records)


def test_run_veritas_on_records_returns_analysis_outputs():
    df = _sample_uploaded_df()
    records = normalize_uploaded_dataframe(df)

    result = run_veritas_on_records(records)

    assert "anomaly" in result
    assert "fairness" in result
    assert "mapped_findings" in result
    assert "report_html" in result
    assert len(result["anomaly"]["findings"]) == len(records)
    assert len(result["fairness"]["findings"]) >= 1
    assert len(result["mapped_findings"]) >= 1
    assert "<html" in result["report_html"].lower()


def test_upload_runner_uses_uploaded_protected_attribute_names():
    df = pd.DataFrame({
        "record_id": [f"r{index}" for index in range(8)],
        "gender": ["F", "M"] * 4,
        "prediction": [1, 0] * 4,
        "actual": [1, 0, 0, 1, 1, 0, 0, 1],
        "feature_a": list(range(8)),
    })
    records = normalize_uploaded_dataframe(df)

    result = run_veritas_on_records(records)

    assert result["effective_run_config"]["input_mode"] == "uploaded_predictions"
    assert result["effective_run_config"]["protected_attributes"] == ["gender"]
    assert result["fairness"]["config"]["protected_attributes_scanned"] == ["gender"]


def test_build_summary_reports_aggregate_counts():
    df = _sample_uploaded_df()
    records = normalize_uploaded_dataframe(df)
    result = run_veritas_on_records(records)

    summary = build_summary(result)

    assert summary["anomaly_total"] >= 0
    assert summary["fairness_violations"] >= 0
    assert summary["total_findings"] == len(result["mapped_findings"])
    assert summary["mapped_violation_count"] + summary["mapped_informational_count"] == summary["total_findings"]


def test_validate_uploaded_dataframe_accepts_whitespace_and_case_variants_in_columns():
    df = pd.DataFrame(
        {
            " Record ID ": ["r1", "r2"],
            " Timestamp ": ["2026-01-01T10:00:00", "2026-01-02T11:00:00"],
            " Sex ": ["Male", "Female"],
            " Prediction ": [1, 0],
            " ACTUAL ": [1, 0],
            "Feature A": [5.1, 4.3],
            "Feature B": [2.2, 9.1],
        }
    )

    validate_uploaded_dataframe(df)


def test_validate_uploaded_dataframe_rejects_non_binary_label_values():
    bad_df = pd.DataFrame(
        {
            "record_id": ["r1", "r2"],
            "timestamp": ["2026-01-01T10:00:00", "2026-01-02T11:00:00"],
            "sex": ["Male", "Female"],
            "prediction": ["approve", "deny"],
            "actual": ["approve", "deny"],
            "feature_a": [5.1, 4.3],
            "feature_b": [2.2, 9.1],
        }
    )

    with pytest.raises(ValueError, match="binary|0/1|true/false"):
        validate_uploaded_dataframe(bad_df)


def test_validate_uploaded_dataframe_rejects_missing_protected_attribute():
    bad_df = pd.DataFrame(
        {
            "id": [1, 2],
            "timestamp": ["2026-01-01T10:00:00", "2026-01-02T11:00:00"],
            "prediction": [1, 0],
            "actual": [1, 0],
            "feature_a": [5.1, 4.3],
            "feature_b": [2.2, 9.1],
        }
    )

    with pytest.raises(ValueError, match="Missing protected-attribute column"):
        validate_uploaded_dataframe(bad_df)


def test_validate_uploaded_dataframe_rejects_empty_or_non_numeric_dataset():
    empty_df = pd.DataFrame({})
    with pytest.raises(ValueError, match="empty|too few columns|No usable numeric feature"):
        validate_uploaded_dataframe(empty_df)

    non_numeric_df = pd.DataFrame(
        {
            "id": [1, 2],
            "timestamp": ["2026-01-01T10:00:00", "2026-01-02T11:00:00"],
            "sex": ["Male", "Female"],
            "prediction": [1, 0],
            "actual": [1, 0],
            "text_one": ["a", "b"],
            "text_two": ["c", "d"],
        }
    )

    with pytest.raises(ValueError, match="No usable numeric feature"):
        validate_uploaded_dataframe(non_numeric_df)


def test_dashboard_displays_html_and_offers_pdf_download_only():
    app = AppTest.from_file("../dashboard/app.py", default_timeout=30).run()
    csv_data = _sample_uploaded_df().to_csv(index=False).encode("utf-8")

    app.file_uploader[0].upload("audit.csv", csv_data, "text/csv").run()
    app.button[0].click().run()
    assert not app.exception
    assert any(button.label == "Approve config and run audit" for button in app.button)

    app.text_input[0].set_value("dashboard reviewer").run()
    approve_button = next(
        button for button in app.button if button.label == "Approve config and run audit"
    )
    approve_button.click().run(timeout=30)

    assert not app.exception
    assert any(element.value == "Approved audit completed." for element in app.success)
    download_labels = {element.proto.label for element in app.get("download_button")}
    assert download_labels == {"Download sample upload template", "Download PDF report"}


def test_segment_protected_attribute_normalizes_without_crash():
    df = pd.DataFrame({
        "record_id": [f"r{i}" for i in range(10)],
        "timestamp": ["2026-01-01T10:00:00"] * 10,
        "segment": ["TierA", "TierB"] * 5,
        "prediction": [1, 0] * 5,
        "actual": [1, 1, 0, 0] * 2 + [1, 0],
        "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        "feature_b": [10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0],
    })
    validate_uploaded_dataframe(df)
    records = normalize_uploaded_dataframe(df)
    assert len(records) == 10
    assert records[0]["protected_attributes"].get("segment") == "TierA"

