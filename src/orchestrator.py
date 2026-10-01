#!/usr/bin/env python3
"""VERITAS orchestrator: runs Phases 1-5 end to end.

Phase 1  Log ingestion            -> normalized_log.json
Phase 2  Anomaly detection   \\    (parallel, both read normalized_log.json)
Phase 3  Fairness scanner    /
Phase 4  Compliance mapping       -> mapped_findings.json
Phase 5  Report generation        -> audit_report.html

Each phase runs as its own subprocess so a crash in one cannot corrupt another's
state, and each phase keeps its existing CLI contract. After every stage the
orchestrator checks that declared outputs exist and are non-empty, then records
a SHA-256 of each in run_manifest.json (reproducibility evidence for the audit).

Place at src/orchestrator.py. Usage (from the repo root):
    python src/orchestrator.py                    # full run
    python src/orchestrator.py --dry-run          # print plan, execute nothing
    python src/orchestrator.py --from-phase 4     # resume; needs earlier outputs on disk
    python src/orchestrator.py --only 5           # rerun one phase (e.g. after report edits)
    python src/orchestrator.py --from-phase 2 --to-phase 3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

PY = sys.executable


@dataclass(frozen=True)
class Stage:
    name: str
    phase: int
    cmd: list[str]
    inputs: list[str] = field(default_factory=list)   # paths relative to --root
    outputs: list[str] = field(default_factory=list)  # paths relative to --root


# ---------------------------------------------------------------------------
# PIPELINE DEFINITION - commands and paths taken from README section 8.
# Groups run in order; stages inside a group run in parallel.
# All paths are relative to the repo root; every command runs with cwd=root so
# `python -m src.<module>` resolves.
# ---------------------------------------------------------------------------
NORMALIZED = "data/processed/normalized_log.json"
ANOMALY = "outputs/logs/anomaly_findings.json"
FAIRNESS = "outputs/logs/fairness_findings.json"
MAPPED = "outputs/logs/mapped_findings.json"
REPORT = "outputs/reports/audit_report.html"
LOOKUP = "src/compliance_mapping/nist_control_lookup.yaml"

# Files whose exact contents determine audit results; hashed into the manifest.
CONFIG_FILES = ["config/config.yaml", LOOKUP]

PIPELINE: list[list[Stage]] = [
    [Stage(
        name="ingestion", phase=1,
        cmd=[PY, "-m", "src.ingestion.log_loader", "--output", NORMALIZED],
        outputs=[NORMALIZED],
    )],
    [
        Stage(
            name="anomaly_detection", phase=2,
            cmd=[PY, "-m", "src.anomaly_detection.isolation_forest",
                 "--input", NORMALIZED, "--output", ANOMALY],
            inputs=[NORMALIZED],
            outputs=[ANOMALY],
        ),
        Stage(
            name="fairness_scanner", phase=3,
            cmd=[PY, "-m", "src.fairness_scanner.run_scan",
                 "--input", NORMALIZED, "--output", FAIRNESS],
            inputs=[NORMALIZED],
            outputs=[FAIRNESS],
        ),
    ],
    [Stage(
        name="compliance_mapping", phase=4,
        cmd=[PY, "-m", "src.compliance_mapping.run_mapping",
             "--anomaly-input", ANOMALY, "--fairness-input", FAIRNESS,
             "--lookup", LOOKUP, "--output", MAPPED],
        inputs=[ANOMALY, FAIRNESS, LOOKUP],
        outputs=[MAPPED],
    )],
    [Stage(
        name="report_generator", phase=5,
        cmd=[PY, "-m", "src.report_generator.run_report",
             "--input", MAPPED, "--output", REPORT],
        inputs=[MAPPED],
        outputs=[REPORT],
    )],
]


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_state(root: Path) -> dict:
    def run(*args: str) -> str | None:
        try:
            r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None

    status = run("status", "--porcelain")
    return {
        "commit": run("rev-parse", "HEAD"),
        "tag": run("describe", "--tags", "--always"),
        "dirty": bool(status) if status is not None else None,
    }


def run_stage(stage: Stage, root: Path, log_dir: Path) -> dict:
    result = {
        "name": stage.name, "phase": stage.phase, "cmd": stage.cmd,
        "status": "failed", "returncode": None, "seconds": 0.0,
        "outputs": {}, "error": None,
    }

    missing = [p for p in stage.inputs if not (root / p).is_file()]
    if missing:
        result["error"] = f"missing input(s): {', '.join(missing)}"
        return result

    log_path = log_dir / f"phase{stage.phase}_{stage.name}.log"
    start = time.monotonic()
    try:
        with log_path.open("w") as log:
            proc = subprocess.run(stage.cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT)
        result["returncode"] = proc.returncode
    except OSError as exc:
        result["error"] = f"could not launch: {exc}"
        return result
    finally:
        result["seconds"] = round(time.monotonic() - start, 2)

    result["log"] = str(log_path.relative_to(root)) if log_path.is_relative_to(root) else str(log_path)

    if result["returncode"] != 0:
        result["error"] = f"exit code {result['returncode']} (see {result['log']})"
        return result

    for rel in stage.outputs:
        p = root / rel
        if not p.is_file() or p.stat().st_size == 0:
            result["error"] = f"expected output missing or empty: {rel}"
            return result
        result["outputs"][rel] = {"bytes": p.stat().st_size, "sha256": sha256(p)}

    result["status"] = "ok"
    return result


def select(groups: list[list[Stage]], lo: int, hi: int, only: int | None) -> list[list[Stage]]:
    if only is not None:
        lo = hi = only
    picked = [[s for s in g if lo <= s.phase <= hi] for g in groups]
    return [g for g in picked if g]


def print_plan(groups: list[list[Stage]]) -> None:
    for i, group in enumerate(groups, 1):
        mode = "parallel" if len(group) > 1 else "single"
        print(f"step {i} ({mode})")
        for s in group:
            print(f"  phase {s.phase}  {s.name}: {' '.join(s.cmd)}")
            print(f"    in : {', '.join(s.inputs) or '-'}")
            print(f"    out: {', '.join(s.outputs)}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the VERITAS pipeline end to end.")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                    help="repo root; commands run from here (default: parent of src/)")
    ap.add_argument("--from-phase", type=int, default=1, choices=range(1, 6))
    ap.add_argument("--to-phase", type=int, default=5, choices=range(1, 6))
    ap.add_argument("--only", type=int, choices=range(1, 6), help="run a single phase")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and exit")
    args = ap.parse_args()

    if args.from_phase > args.to_phase:
        ap.error("--from-phase cannot exceed --to-phase")

    root = args.root.resolve()
    groups = select(PIPELINE, args.from_phase, args.to_phase, args.only)
    if not groups:
        ap.error("no stages selected")

    if args.dry_run:
        print_plan(groups)
        return 0

    log_dir = root / "outputs" / "logs" / "run"
    for d in (log_dir, root / "outputs" / "reports", root / "data" / "processed"):
        d.mkdir(parents=True, exist_ok=True)

    manifest = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git": git_state(root),
        "config_sha256": {c: sha256(root / c) if (root / c).is_file() else None for c in CONFIG_FILES},
        "selection": {"from": args.from_phase, "to": args.to_phase, "only": args.only},
        "stages": [],
        "success": False,
    }

    t0 = time.monotonic()
    failed = False
    for group in groups:
        names = ", ".join(f"phase {s.phase} {s.name}" for s in group)
        print(f"-> {names}", flush=True)
        with ThreadPoolExecutor(max_workers=len(group)) as pool:
            results = list(pool.map(lambda s: run_stage(s, root, log_dir), group))
        for r in results:
            manifest["stages"].append(r)
            mark = "ok    " if r["status"] == "ok" else "FAILED"
            print(f"   {mark} phase {r['phase']} {r['name']} ({r['seconds']}s)"
                  + (f" - {r['error']}" if r["error"] else ""), flush=True)
        if any(r["status"] != "ok" for r in results):
            failed = True
            break  # siblings in the group were allowed to finish so their logs exist

    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["total_seconds"] = round(time.monotonic() - t0, 2)
    manifest["success"] = not failed

    manifest_path = log_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"{'pipeline complete' if not failed else 'pipeline stopped'}; manifest: {manifest_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())