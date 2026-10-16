import io
import time
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.settings import DB_PATH, CHECKPOINT_DB_PATH


@pytest.fixture(scope="module")
def client():
    # Use FastAPI TestClient which runs lifespan
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_csv_bytes():
    df = pd.DataFrame({
        "record_id": [f"r{i}" for i in range(20)],
        "timestamp": ["2026-01-01T10:00:00"] * 20,
        "sex": ["Male", "Female"] * 10,
        "race": ["White", "Black"] * 10,
        "prediction": [1, 0] * 10,
        "actual": [1, 0, 0, 1] * 5,
        "confidence": [0.85] * 20,
        "feature_a": [float(i) for i in range(20)],
        "feature_b": [float(100 - i) for i in range(20)],
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf.getvalue()


def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_config_bounds(client):
    res = client.get("/api/config-bounds")
    assert res.status_code == 200
    data = res.json()
    assert "significance_level" in data
    assert "min_group_size" in data
    assert "permutations" in data


def test_sample_csv_download(client):
    res = client.get("/api/sample.csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    lines = res.text.strip().split("\n")
    assert len(lines) >= 500


def test_validate_dry_run(client, sample_csv_bytes):
    files = {"file": ("test.csv", sample_csv_bytes, "text/csv")}
    res = client.post("/api/validate", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["total_rows"] == 20
    assert "prediction" in data["detected_roles"]
    assert "actual" in data["detected_roles"]


def test_full_run_lifecycle_and_approval(client, sample_csv_bytes):
    # 1. Create run -> awaiting_approval
    files = {"file": ("loans.csv", sample_csv_bytes, "text/csv")}
    res_create = client.post("/api/runs", files=files)
    assert res_create.status_code == 201
    run_info = res_create.json()
    run_id = run_info["run_id"]
    assert run_info["status"] == "awaiting_approval"
    assert "validation_summary" in run_info
    assert "config_proposal" in run_info

    # 2. Poll /api/runs/{id}
    res_poll = client.get(f"/api/runs/{run_id}")
    assert res_poll.status_code == 200
    assert res_poll.json()["status"] == "awaiting_approval"

    # 3. Approve run
    approve_body = {
        "protected_attributes": ["sex"],
        "significance_level": 0.05,
        "min_group_size_warning": 5,
        "permutations": 20,
    }
    res_approve = client.post(
        f"/api/runs/{run_id}/approve",
        json=approve_body,
        headers={"X-User-Email": "lead_auditor@veritas.gov"},
    )
    assert res_approve.status_code == 202
    assert "config_fingerprint" in res_approve.json()

    # 4. Wait for background worker to complete
    completed = False
    for _ in range(30):
        time.sleep(0.5)
        poll = client.get(f"/api/runs/{run_id}").json()
        if poll["status"] == "completed":
            completed = True
            break
    assert completed, f"Run did not complete in time, status: {poll.get('status')}"
    assert poll["approved_by"] == "lead_auditor@veritas.gov"
    assert poll["summary"] is not None

    # 5. Double-approval should return 409 Conflict
    res_double = client.post(
        f"/api/runs/{run_id}/approve",
        json=approve_body,
    )
    assert res_double.status_code == 409

    # 6. Check finding endpoints
    res_findings = client.get(f"/api/runs/{run_id}/findings")
    assert res_findings.status_code == 200
    assert isinstance(res_findings.json(), list)

    res_anomalies = client.get(f"/api/runs/{run_id}/anomalies")
    assert res_anomalies.status_code == 200
    assert "items" in res_anomalies.json()

    res_clusters = client.get(f"/api/runs/{run_id}/anomaly-clusters")
    assert res_clusters.status_code == 200

    # 7. Ask question (Agent-6 Q&A)
    res_ask = client.post(
        f"/api/runs/{run_id}/ask",
        json={"question": "Can you provide a summary of the audit findings?"},
    )
    assert res_ask.status_code == 200
    assert "MEASURE" in res_ask.json()["answer"] or "findings" in res_ask.json()["answer"]

    # 8. Check reports
    res_html = client.get(f"/api/runs/{run_id}/report.html")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
    assert "Content-Security-Policy" in res_html.headers

    res_pdf = client.get(f"/api/runs/{run_id}/report.pdf")
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers["content-type"]

    # 9. Delete run
    res_del = client.delete(f"/api/runs/{run_id}")
    assert res_del.status_code == 204

    # 10. Check deleted
    assert client.get(f"/api/runs/{run_id}").status_code == 404
