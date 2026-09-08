#!/usr/bin/env python3
"""Smoke-test the claim -> evidence -> run checker without external dependencies."""
from __future__ import annotations
import json, pathlib, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parents[1]
PYTHON = sys.executable

def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        project = pathlib.Path(td)
        (project / "logs").mkdir(); (project / "results").mkdir()
        (project / "results" / "q1.csv").write_text("metric,value\nrmse,1\n", encoding="utf-8")
        write_jsonl(project / "logs" / "run_log.jsonl", [{"run_id":"RUN-1", "status":"SUCCEEDED", "output_refs":["results/q1.csv"]}])
        write_jsonl(project / "logs" / "events.jsonl", [{"event_id":"HD-1"},{"event_id":"RV-1"}])
        write_jsonl(project / "logs" / "human_decisions.jsonl", [])
        write_jsonl(project / "logs" / "reviews.jsonl", [])
        write_jsonl(project / "logs" / "claims.jsonl", [{"claim_id":"C-1","text":"测试主张","status":"APPROVED","evidence_refs":["results/q1.csv"],"run_ids":["RUN-1"],"decision_ref":"HD-1","review_ref":"RV-1"}])
        checker = HERE / "scripts" / "claim_check.py"
        valid = subprocess.run([PYTHON, str(checker), str(project)], capture_output=True, text=True)
        if valid.returncode != 0:
            print(valid.stdout, valid.stderr, file=sys.stderr); return 1
        write_jsonl(project / "logs" / "claims.jsonl", [{"claim_id":"C-2","text":"伪造主张","status":"APPROVED","evidence_refs":["results/missing.csv"],"run_ids":["RUN-NOPE"],"decision_ref":"HD-X","review_ref":"RV-X"}])
        invalid = subprocess.run([PYTHON, str(checker), str(project)], capture_output=True, text=True)
        if invalid.returncode != 2:
            print(invalid.stdout, invalid.stderr, file=sys.stderr); return 1
    print("CLAIM_CHAIN_SMOKE_PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
