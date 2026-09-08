#!/usr/bin/env python3
"""Behavior tests for the hardened triad.py gate engine.

Covers: self-review PASS cannot close a gate, gate-order enforcement,
review-after-decision timing, record-run/record-claim fail-closed checks,
and status guidance. Prints HARDENED_GATES_PASS on success, exit 2 otherwise.
Python 3.10+, standard library only.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

TRIAD = Path(__file__).resolve().parent.parent / "scripts" / "triad.py"
FAILURES: list[str] = []


def run(*args: str) -> tuple[int, dict | None, str]:
    result = subprocess.run(
        [sys.executable, str(TRIAD), *args], text=True, capture_output=True
    )
    payload = None
    if result.stdout.strip():
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
    return result.returncode, payload, result.stderr.strip()


def check(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        FAILURES.append(f"{name}: {detail}")


def human(project: str, gate: str) -> int:
    code, _, err = run(
        "record-human", project, "--gate-id", gate, "--gate-class", "CORE_MODELING",
        "--selected", f"方向{gate}", "--contribution", "我先验证可解释基线再决定是否增加复杂度",
        "--rationale", "保持同口径基准便于比较", "--evidence", "raw/problem.pdf",
    )
    return code


def review(project: str, gate: str, *extra: str) -> int:
    code, _, err = run(
        "record-review", project, "--gate-id", gate, "--verdict", "PASS",
        "--context-id", "ctx-1", "--evidence", "raw/problem.pdf", *extra,
    )
    return code


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        project = str(Path(tmp) / "proj")
        problem = Path(tmp) / "problem.pdf"
        problem.write_bytes(b"fake problem")
        code, _, err = run("start", project, "--input", str(problem))
        check("start", code == 0, err)

        # 1. self-review PASS must not close the START gate
        check("human START", human(project, "START") == 0)
        check("self-review recorded", review(project, "START", "--self-review-only") == 0)
        code, _, err = run("close-gate", project, "--gate-id", "START")
        check("self-review PASS rejected at close-gate", code == 2 and "self-review" in err, err)

        # 2. independent PASS closes START; close-gate advances current gate
        check("independent review START", review(project, "START") == 0)
        code, payload, err = run("close-gate", project, "--gate-id", "START")
        check("close START", code == 0 and payload and payload.get("next_gate") == "TOPIC", err or str(payload))

        # 3. gate order enforced: ROUTE cannot close before TOPIC/DEFINITION
        check("human ROUTE", human(project, "ROUTE") == 0)
        check("review ROUTE", review(project, "ROUTE") == 0)
        code, _, err = run("close-gate", project, "--gate-id", "ROUTE")
        check("gate order enforced", code == 2 and "preceding gates not closed" in err, err)

        # 4. review-before-decision must not close TOPIC
        check("early review TOPIC", review(project, "TOPIC") == 0)
        check("human TOPIC", human(project, "TOPIC") == 0)
        code, _, err = run("close-gate", project, "--gate-id", "TOPIC")
        check("stale review rejected", code == 2 and "re-review required" in err, err)
        check("re-review TOPIC", review(project, "TOPIC") == 0)
        code, _, err = run("close-gate", project, "--gate-id", "TOPIC")
        check("close TOPIC after re-review", code == 0, err)

        # 5. record-run fail-closed checks
        code, _, err = run("record-run", project, "--run-id", "R1", "--status", "SUCCEEDED")
        check("SUCCEEDED without output refused", code == 2, err)
        out = Path(project) / "results"
        out.mkdir(exist_ok=True)
        (out / "q1.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        code, _, err = run("record-run", project, "--run-id", "R1", "--status", "SUCCEEDED",
                           "--command", "python code/q1.py", "--output", "results/q1.csv")
        check("record-run ok", code == 0, err)
        code, _, err = run("record-run", project, "--run-id", "R1", "--status", "FAILED")
        check("duplicate run refused", code == 2 and "duplicate" in err, err)

        # 6. record-claim fail-closed checks
        code, _, err = run("record-claim", project, "--claim-id", "C1", "--text", "指标A提升12%",
                           "--evidence", "results/q1.csv", "--run-id", "R1")
        check("record-claim ok", code == 0, err)
        code, _, err = run("record-claim", project, "--claim-id", "C2", "--text", "不存在的运行",
                           "--evidence", "results/q1.csv", "--run-id", "R404")
        check("claim with unknown run refused", code == 2 and "not found" in err, err)
        code, _, err = run("record-claim", project, "--claim-id", "C3", "--text", "证据不在输出",
                           "--evidence", "raw/problem.pdf", "--run-id", "R1")
        check("claim with undeclared evidence refused", code == 2 and "output_refs" in err, err)
        code, _, err = run("record-claim", project, "--claim-id", "C4", "--text", "批准缺引用",
                           "--evidence", "results/q1.csv", "--run-id", "R1", "--status", "APPROVED")
        check("APPROVED claim without refs refused", code == 2 and "decision-ref" in err, err)

        # 7. claim_check passes on the CLI-written chain
        checker = TRIAD.with_name("claim_check.py")
        result = subprocess.run([sys.executable, str(checker), project], text=True, capture_output=True)
        check("claim_check VALID on CLI-written chain", result.returncode == 0, result.stdout + result.stderr)

        # 8. status guidance
        code, payload, err = run("status", project)
        check("status shows next_gate", code == 0 and payload and payload.get("next_gate") == "DEFINITION", str(payload))
        check("status next_action names gate", payload and "DEFINITION" in str(payload.get("next_action")), str(payload))

        # 9. open failure blocks close-gate and appears in status
        code, _, err = run("record-failure", project, "--gate-id", "DEFINITION",
                           "--severity", "MAJOR", "--description", "测试失败阻断")
        check("record-failure ok", code == 0, err)
        check("human DEFINITION", human(project, "DEFINITION") == 0)
        check("review DEFINITION", review(project, "DEFINITION") == 0)
        code, _, err = run("close-gate", project, "--gate-id", "DEFINITION")
        check("open blocker refuses close", code == 2 and "open blockers" in err, err)
        code, payload, _ = run("status", project)
        check("status lists open failure", payload and len(payload.get("open_failures", [])) == 1, str(payload))

    if FAILURES:
        for failure in FAILURES:
            print(f"FAIL {failure}")
        return 2
    print("HARDENED_GATES_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
