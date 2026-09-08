#!/usr/bin/env python3
"""Create a small, deterministic CUMCM triad project skeleton.

The target is a new project directory, not the Skill repository. Existing
non-empty targets are refused unless --force is supplied. The initializer does
not copy benchmark material, prompts, credentials, or private paths.
Exit codes: 0 CREATED, 2 INVALID_OR_REFUSED.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


DIRECTORIES = (
    "raw",
    "planning/decision_cards",
    "planning/risk_cards",
    "logs",
    "code",
    "results",
    "reviews",
    "paper",
    "compliance",
)
LOG_FILES = (
    "human_decisions.jsonl",
    "autonomous_decisions.jsonl",
    "failures.jsonl",
    "ai_usage.jsonl",
    "route_changes.jsonl",
    "run_log.jsonl",
    "time_log.jsonl",
    "events.jsonl",
    "reviews.jsonl",
    "claims.jsonl",
)
GATES = ("START", "TOPIC", "DEFINITION", "ROUTE", "MODEL", "PAPER", "LAYOUT", "COMPLIANCE", "FREEZE")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path, help="new project directory")
    parser.add_argument("--force", action="store_true", help="allow an existing target only when every generated path is absent")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ is required")

    target = args.project.expanduser()
    if target.exists() and not target.is_dir():
        print(f"REFUSED: target is not a directory: {target}", file=sys.stderr)
        return 2
    if target.exists() and any(target.iterdir()) and not args.force:
        print("REFUSED: target is non-empty; choose a new directory or pass --force explicitly", file=sys.stderr)
        return 2

    paths = [target / directory for directory in DIRECTORIES]
    paths.extend(target / "logs" / filename for filename in LOG_FILES)
    paths.append(target / "project_state.json")
    existing = [path for path in paths if path.exists()]
    if existing:
        print("REFUSED: generated paths already exist; no files were changed", file=sys.stderr)
        for path in existing:
            print(f"  {path}", file=sys.stderr)
        return 2

    try:
        for directory in DIRECTORIES:
            (target / directory).mkdir(parents=True, exist_ok=False)
        for filename in LOG_FILES:
            (target / "logs" / filename).write_text("", encoding="utf-8", newline="\n")
        state = {
            "schema_version": "1.0",
            "project_state": "INITIALIZED",
            "current_gate": "START",
            "gate_status": "WAITING_HUMAN",
            "review_status": "NOT_RUN",
            "open_blockers": 0,
            "created_by": "cumcm-triad-workflow.init_project",
            "notes": "Replace placeholders through decision cards; no gate is pre-approved by initialization.",
        }
        (target / "project_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        profile = {
            "schema_version": "1.0", "mode": "REPLACE_WITH_TRAINING_OR_FORMAL",
            "year": None, "group": None, "problem": None, "rules_ref": None,
            "clock_start": None, "clock_deadline": None,
            "allowed_sources": [], "forbidden_sources": [],
            "roles": {"human_decider": None, "executor": None, "independent_reviewer": None},
            "status": "NEEDS_HUMAN_INPUT",
        }
        (target / "project_profile.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        (target / "planning" / "gate_registry.json").write_text(json.dumps({"schema_version": "1.0", "gates": list(GATES)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    except (OSError, ValueError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"status": "CREATED", "project": str(target), "directories": list(DIRECTORIES), "log_files": list(LOG_FILES)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
