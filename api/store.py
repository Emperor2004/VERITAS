"""
SQLite-backed persistent store for VERITAS run metadata and outputs.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from api.jsonable import to_jsonable
from api.settings import DB_PATH


def _get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """Initialize SQLite database schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                upload_name TEXT NOT NULL,
                status TEXT NOT NULL,
                current_stage TEXT,
                row_count INTEGER NOT NULL,
                config_fingerprint TEXT,
                approved_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                validation_summary_json TEXT,
                config_proposal_json TEXT,
                proposed_config_json TEXT,
                approved_config_json TEXT,
                results_json TEXT,
                error_message TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC)
        """)
        conn.commit()


def create_run_record(
    run_id: str,
    upload_name: str,
    status: str,
    row_count: int,
    validation_summary: Dict[str, Any],
    proposed_config: Dict[str, Any],
    config_proposal: Optional[Dict[str, Any]] = None,
    current_stage: str = "validating",
    db_path: Path = DB_PATH,
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    with _get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO runs (
                run_id, upload_name, status, current_stage, row_count,
                created_at, updated_at, validation_summary_json,
                config_proposal_json, proposed_config_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            upload_name,
            status,
            current_stage,
            row_count,
            now_iso,
            now_iso,
            json.dumps(to_jsonable(validation_summary)),
            json.dumps(to_jsonable(config_proposal)) if config_proposal else None,
            json.dumps(to_jsonable(proposed_config)),
        ))
        conn.commit()


def get_run_record(run_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    with _get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        for k in ["validation_summary_json", "config_proposal_json", "proposed_config_json", "approved_config_json", "results_json"]:
            if d.get(k):
                d[k.replace("_json", "")] = json.loads(d[k])
            else:
                d[k.replace("_json", "")] = None
        return d


def update_run_status(
    run_id: str,
    status: str,
    current_stage: Optional[str] = None,
    approved_by: Optional[str] = None,
    config_fingerprint: Optional[str] = None,
    approved_config: Optional[Dict[str, Any]] = None,
    results: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    updates = ["status = ?", "updated_at = ?"]
    params: List[Any] = [status, now_iso]

    if current_stage is not None:
        updates.append("current_stage = ?")
        params.append(current_stage)
    if approved_by is not None:
        updates.append("approved_by = ?")
        params.append(approved_by)
    if config_fingerprint is not None:
        updates.append("config_fingerprint = ?")
        params.append(config_fingerprint)
    if approved_config is not None:
        updates.append("approved_config_json = ?")
        params.append(json.dumps(to_jsonable(approved_config)))
    if results is not None:
        updates.append("results_json = ?")
        params.append(json.dumps(to_jsonable(results)))
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)

    params.append(run_id)
    with _get_connection(db_path) as conn:
        conn.execute(f"UPDATE runs SET {', '.join(updates)} WHERE run_id = ?", params)
        conn.commit()


def list_runs(limit: int = 50, offset: int = 0, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    with _get_connection(db_path) as conn:
        cursor = conn.execute("""
            SELECT run_id, upload_name, status, current_stage, row_count,
                   config_fingerprint, approved_by, created_at, updated_at
            FROM runs
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        return [dict(r) for r in cursor.fetchall()]


def delete_run_record(run_id: str, db_path: Path = DB_PATH) -> bool:
    with _get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
        conn.commit()
        return cursor.rowcount > 0
