#!/usr/bin/env python3
"""Executable fail-closed checks for the triad command surface.

This is a contract test for the local adapter, not proof of full competition
readiness. It uses only synthetic data and a temporary project.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
TRIAD = ROOT / "scripts" / "triad.py"


def run(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TRIAD), *args, str(project)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="triad-contract-") as directory:
        project = Path(directory) / "project"
        result = run(project, "start")
        assert result.returncode == 0, result.stdout
        (project / "results" / "evidence.txt").write_text("synthetic evidence\n", encoding="utf-8")
        result = run(project, "record-human", "--gate-id", "G999", "--gate-class", "CORE_MODELING", "--selected", "x", "--contribution", "这是一条足够长的实质性说明。", "--rationale", "x")
        assert result.returncode == 2 and "unknown gate_id" in result.stdout, result.stdout
        result = run(project, "record-human", "--gate-id", "START", "--gate-class", "CORE_MODELING", "--selected", "基线", "--contribution", "我先使用可解释基线检查数据关系，再决定是否增加复杂模型。", "--rationale", "保留可比较起点", "--evidence", "results/missing.txt")
        assert result.returncode == 2 and not (project / "logs" / "events.jsonl").read_text(encoding="utf-8").strip(), result.stdout
        result = run(project, "record-human", "--gate-id", "START", "--gate-class", "CORE_MODELING", "--selected", "基线", "--contribution", "我先使用可解释基线检查数据关系，再决定是否增加复杂模型。", "--rationale", "保留可比较起点")
        assert result.returncode == 0, result.stdout
        result = run(project, "record-review", "--gate-id", "START", "--verdict", "PASS", "--context-id", "isolated-review-1", "--evidence", "results/evidence.txt")
        assert result.returncode == 0, result.stdout
        result = run(project, "close-gate", "--gate-id", "START")
        assert result.returncode == 0, result.stdout
        result = run(project, "record-failure", "--gate-id", "TOPIC", "--severity", "MAJOR", "--description", "synthetic blocker", "--evidence", "results/evidence.txt")
        assert result.returncode == 0, result.stdout
        result = run(project, "freeze", "--version", "candidate", "--confirmation", "我确认这是经过人工检查的候选版本。")
        assert result.returncode == 2 and "not closed" in result.stdout, result.stdout
        result = run(project, "review-packet", "--output", "../../escape.zip")
        assert result.returncode == 2 and not (Path(directory) / "escape.zip").exists(), result.stdout
        result = run(project, "validate")
        assert result.returncode == 0, result.stdout
        report = json.loads(result.stdout)
        assert report["status"] == "VALID" and report["open_blockers"] == 1, report
    print("GATE_ENGINE_CONTRACT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
