"""
Metadata and utility routes: health, config bounds, and sample file download.
"""
from __future__ import annotations

import io
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import numpy as np
import pandas as pd

from api.schemas import ConfigBoundsResponse
from src.agentic.agents.config_proposer import KNOWN_DEMOGRAPHIC_CANDIDATES

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "veritas-api", "version": "0.2.0"}


@router.get("/config-bounds", response_model=ConfigBoundsResponse)
def get_config_bounds():
    return ConfigBoundsResponse(
        significance_level={"min": 0.001, "max": 0.999, "default": 0.05, "step": 0.01},
        min_group_size={"min": 1, "max": 1_000_000, "default": 30, "step": 1},
        permutations={"min": 1, "max": 100_000, "default": 1000, "step": 100},
        default_protected_candidates=sorted(KNOWN_DEMOGRAPHIC_CANDIDATES),
    )


@router.get("/sample.csv")
def get_sample_csv():
    """
    Generate realistic synthetic audit sample (500 records) with fixed seed
    so testers can test fairness scanning and anomaly detection.
    """
    rng = np.random.default_rng(42)
    n = 500
    df = pd.DataFrame({
        "record_id": [f"REC-{i:04d}" for i in range(1, n + 1)],
        "timestamp": pd.date_range("2026-01-01", periods=n, freq="30min").strftime("%Y-%m-%dT%H:%M:%S"),
        "sex": rng.choice(["Male", "Female"], n, p=[0.55, 0.45]),
        "race": rng.choice(["White", "Black", "Asian", "Hispanic"], n, p=[0.60, 0.18, 0.12, 0.10]),
        "prediction": rng.integers(0, 2, n),
        "actual": rng.integers(0, 2, n),
        "confidence": np.round(rng.uniform(0.55, 0.98, n), 3),
        "credit_score": np.round(rng.normal(680, 50, n), 1),
        "income": np.round(rng.normal(65000, 15000, n), 0),
        "debt_to_income": np.round(rng.uniform(0.1, 0.6, n), 3),
    })

    stream = io.StringIO()
    df.to_csv(stream, index=False)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=veritas_sample_audit.csv"},
    )
