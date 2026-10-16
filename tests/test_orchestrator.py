from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from src.orchestrator import REPO_ROOT


def test_report_stage_manifest_records_effective_config_and_both_reports(tmp_path):
    shutil.copytree(REPO_ROOT / "src", tmp_path / "src")
    shutil.copytree(REPO_ROOT / "config", tmp_path / "config")
    mapped_path = tmp_path / "outputs" / "logs" / "mapped_findings.json"
    mapped_path.parent.mkdir(parents=True)
    mapped_path.write_text(json.dumps({"mapped_findings": []}), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "src" / "orchestrator.py"),
            "--root", str(tmp_path),
            "--only", "5",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    manifest_path = tmp_path / "outputs" / "logs" / "run" / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stage = manifest["stages"][0]

    assert manifest["effective_run_config"]["schema_version"] == 1
    assert manifest["effective_run_config"]["input_mode"] == "adult_income"
    assert set(stage["outputs"]) == {
        "outputs/reports/audit_report.html",
        "outputs/reports/audit_report.pdf",
    }