from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EaProbeResult:
    returncode: int
    payload: dict[str, Any]
    stdout: str
    stderr: str


def run_ea_import_probe(
    repository: Path,
    xmi: Path,
    import_diagrams: bool,
    strip_guids: bool,
    timeout_seconds: int,
) -> EaProbeResult:
    ea_pids_before = _ea_process_ids()
    command = [
        sys.executable,
        str(_repo_root() / "scripts" / "ea_import_probe.py"),
        "--repository",
        str(repository),
        "--xmi",
        str(xmi),
        "--import-diagrams",
        "1" if import_diagrams else "0",
        "--strip-guids",
        "1" if strip_guids else "0",
    ]
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _terminate_new_ea_processes(ea_pids_before)
        raise
    return EaProbeResult(
        returncode=completed.returncode,
        payload=parse_probe_json(completed.stdout),
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def parse_probe_json(stdout: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except Exception:
        return {
            "ok": False,
            "stage": "probe_output",
            "message": "EA import probe did not return valid JSON.",
            "exception": stdout,
        }
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "stage": "probe_output",
            "message": "EA import probe returned JSON that was not an object.",
            "exception": stdout,
        }
    return payload


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _ea_process_ids() -> set[int]:
    if platform.system() != "Windows":
        return set()
    completed = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq EA.exe", "/FO", "CSV", "/NH"],
        text=True,
        capture_output=True,
        check=False,
    )
    pids: set[int] = set()
    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("INFO:"):
            continue
        parts = [part.strip('"') for part in stripped.split('","')]
        if len(parts) > 1 and parts[0].lower() == "ea.exe":
            try:
                pids.add(int(parts[1]))
            except ValueError:
                continue
    return pids


def _terminate_new_ea_processes(existing_pids: set[int]) -> None:
    deadline = time.monotonic() + 5
    killed_any = False
    while True:
        new_pids = _ea_process_ids() - existing_pids
        for pid in sorted(new_pids):
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                text=True,
                capture_output=True,
                check=False,
            )
            killed_any = True
        if time.monotonic() >= deadline:
            return
        if not new_pids:
            if killed_any:
                return
            time.sleep(0.5)
            continue
        time.sleep(0.2)
