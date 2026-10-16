"""Configuration settings for VERITAS FastAPI backend."""
from __future__ import annotations

import os
from pathlib import Path

# Paths
API_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = API_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
LOOKUP_PATH = PROJECT_ROOT / "src" / "compliance_mapping" / "nist_control_lookup.yaml"

DATA_DIR = PROJECT_ROOT / "outputs" / "api_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.environ.get("VERITAS_DB_PATH", DATA_DIR / "veritas_runs.sqlite"))
CHECKPOINT_DB_PATH = Path(os.environ.get("VERITAS_CHECKPOINT_DB_PATH", DATA_DIR / "checkpoints.sqlite"))

# Upload & resource limits
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_ROWS = 100_000
MAX_COLUMNS = 100
DEFAULT_PAGE_SIZE = 50
