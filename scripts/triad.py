#!/usr/bin/env python3
"""Small standard-library orchestrator for a CUMCM triad project.

This command automates file intake, project status, human-decision recording,
and review-packet assembly. It never approves a core modeling gate or freezes
a submission on the user's behalf.

Examples:
  python scripts/triad.py start my-project --input problem.pdf data/
  python scripts/triad.py status my-project
  python scripts/triad.py record-human my-project --gate-id G1 --gate-class CORE_MODELING \
      --selected "主方法" --contribution "我选择..." --rationale "..."
  python scripts/triad.py review-packet my-project

Exit codes: 0 success, 1 validation failure, 2 refused or missing project.
Python 3.10+, standard library only.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


GATES = ("START", "TOPIC", "DEFINITION", "ROUTE", "MODEL", "PAPER", "LAYOUT", "COMPLIANCE", "FREEZE")
LOG_FILES = (
    "human_decisions.jsonl", "autonomous_decisions.jsonl", "failures.jsonl",
    "ai_usage.jsonl", "route_changes.jsonl", "run_log.jsonl", "time_log.jsonl",
)
CORE_CLASSES = {"CORE_MODELING"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def project_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def require_project(value: str) -> Path:
    project = project_path(value)
    if not project.is_dir() or not (project / "project_state.json").is_file():
        raise ValueError(f"not an initialized triad project: {project}")
    return project


def read_state(project: Path) -> dict:
    try:
        state = json.loads((project / "project_state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read project_state.json: {exc}") from exc
    if not isinstance(state, dict):
        raise ValueError("project_state.json must contain an object")
    return state


def write_state(project: Path, state: dict) -> None:
    temporary = project / "project_state.json.tmp"
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(project / "project_state.json")


def append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def input_files(inputs: list[str], project: Path) -> list[Path]:
    found: list[Path] = []
    for raw in inputs:
        source = Path(raw).expanduser().resolve()
        if not source.exists():
            raise ValueError(f"input does not exist: {source}")
        if source == project or project in source.parents:
            raise ValueError("input must not be the project itself or inside it")
        if source.is_file():
            found.append(source)
        else:
            found.extend(item for item in sorted(source.rglob("*")) if item.is_file())
    unique = {item: None for item in found}
    return list(unique)


def ingest(project: Path, inputs: list[str]) -> dict:
    files = input_files(inputs, project)
    if not files:
        raise ValueError("no files found in input")
    raw_dir = project / "raw"
    destinations = [raw_dir / source.name for source in files]
    if len({path.name for path in destinations}) != len(destinations):
        raise ValueError("input contains duplicate filenames; rename them before ingest to preserve traceability")
    existing = [path.name for path in destinations if path.exists()]
    if existing:
        raise ValueError(f"refusing to overwrite raw input: {', '.join(existing)}")
    manifest_rows = []
    for source, destination in zip(files, destinations):
        shutil.copy2(source, destination)
        manifest_rows.append({
            "relative_path": destination.relative_to(project).as_posix(),
            "source_name": source.name,
            "kind": source.suffix.lower().lstrip(".") or "no_extension",
            "bytes": destination.stat().st_size,
            "readable": True,
            "ingested_at": now(),
        })
    manifest = {
        "schema_version": "1.0",
        "generated_at": now(),
        "source_policy": "copied by explicit user command; no hashes generated",
        "files": manifest_rows,
    }
    (project / "planning" / "input_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    state = read_state(project)
    state.update({"project_state": "INPUTS_INGESTED", "current_gate": "START", "gate_status": "WAITING_HUMAN", "input_count": len(manifest_rows)})
    write_state(project, state)
    return {"status": "INGESTED", "count": len(manifest_rows), "manifest": "planning/input_manifest.json"}


def start(args: argparse.Namespace) -> dict:
    project = project_path(args.project)
    if project.exists() and any(project.iterdir()):
        raise ValueError("start refuses a non-empty directory; use init_project.py rules explicitly")
    initializer = Path(__file__).with_name("init_project.py")
    command = [sys.executable, str(initializer), str(project)]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        raise ValueError(f"initializer refused project (exit {result.returncode}): {result.stdout.strip()}")
    output = {"status": "STARTED", "project": str(project), "init": json.loads(result.stdout)}
    if args.input:
        output["ingest"] = ingest(project, args.input)
    return output


def status(project: Path) -> dict:
    state = read_state(project)
    manifest = project / "planning" / "input_manifest.json"
    counts = {}
    for name in LOG_FILES:
        path = project / "logs" / name
        counts[name] = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()) if path.exists() else 0
    current = state.get("current_gate", "UNKNOWN")
    gate_status = state.get("gate_status", "UNKNOWN")
    if gate_status in {"WAITING_HUMAN", "BLOCKED"}:
        next_action = "human_decision_required"
    elif current in GATES:
        next_action = "prepare_or_run_current_gate"
    else:
        next_action = "inspect_project_state"
    return {
        "project": str(project), "current_gate": current, "gate_status": gate_status,
        "input_count": len(json.loads(manifest.read_text(encoding="utf-8")).get("files", [])) if manifest.exists() else 0,
        "log_counts": counts, "next_action": next_action,
    }


def record_human(args: argparse.Namespace) -> dict:
    project = require_project(args.project)
    gate_class = args.gate_class.upper()
    contribution = args.contribution.strip()
    selected = args.selected.strip()
    if gate_class in CORE_CLASSES and (len(contribution) < 12 or contribution.casefold() in {"a", "b", "c", "同意", "agree"}):
        raise ValueError("CORE_MODELING requires a concise substantive human contribution, not only A/B/C or agreement")
    if not selected or not args.rationale.strip():
        raise ValueError("selected and rationale are required")
    event_id = args.event_id or f"HD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    row = {
        "schema_version": "1.0", "event_id": event_id, "timestamp": now(),
        "gate_id": args.gate_id, "gate_class": gate_class, "decision_owner": "human",
        "proposal_source": args.proposal_source, "options_considered": args.option or [],
        "selected_option": selected, "human_contribution": contribution,
        "rationale": args.rationale.strip(), "status": args.status.upper(),
        "supersedes": args.supersedes, "evidence_refs": args.evidence or [],
    }
    append_jsonl(project / "logs" / "human_decisions.jsonl", row)
    state = read_state(project)
    state.update({"project_state": "HUMAN_DECISION_RECORDED", "current_gate": args.gate_id, "gate_status": "APPROVED" if row["status"] == "APPROVED" else "WAITING_HUMAN", "last_human_decision_id": event_id})
    write_state(project, state)
    return {"status": "RECORDED", "event_id": event_id, "gate_status": state["gate_status"]}


def review_packet(args: argparse.Namespace) -> dict:
    project = require_project(args.project)
    output = project / "reviews" / (args.output or "review_packet.zip")
    if output.exists():
        raise ValueError(f"refusing to overwrite review packet: {output}")
    include_roots = ("project_state.json", "planning", "logs", "code", "results", "paper", "compliance")
    added = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for root in include_roots:
            source = project / root
            if source.is_file():
                archive.write(source, arcname=root)
                added += 1
                continue
            if not source.is_dir():
                continue
            for item in sorted(source.rglob("*")):
                if not item.is_file() or item.name.startswith(".") or item == output:
                    continue
                archive.write(item, arcname=item.relative_to(project).as_posix())
                added += 1
        archive.writestr("REVIEW_PACKET_README.txt", "Generated by triad.py. Run anonym_scan.py and human review before sharing.\n")
    return {"status": "CREATED", "packet": str(output), "files": added, "warning": "packet may contain sensitive inputs; anonymize before external sharing"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("start", help="initialize and optionally ingest input files")
    p.add_argument("project")
    p.add_argument("--input", nargs="*", default=[])
    p.set_defaults(handler=start)
    for name in ("status", "next"):
        p = sub.add_parser(name, help="show current state and the next action")
        p.add_argument("project")
        p.set_defaults(handler=lambda a: status(require_project(a.project)))
    p = sub.add_parser("ingest", help="copy explicitly supplied files into raw/ and write a manifest")
    p.add_argument("project")
    p.add_argument("inputs", nargs="+")
    p.set_defaults(handler=lambda a: ingest(require_project(a.project), a.inputs))
    p = sub.add_parser("record-human", help="append one human decision and update project state")
    p.add_argument("project")
    p.add_argument("--gate-id", required=True)
    p.add_argument("--gate-class", required=True, choices=("CORE_MODELING", "IMPLEMENTATION", "PRESENTATION", "ADMINISTRATIVE"))
    p.add_argument("--selected", required=True)
    p.add_argument("--contribution", required=True)
    p.add_argument("--rationale", required=True)
    p.add_argument("--proposal-source", default="human", choices=("human", "executor", "planner", "reviewer"))
    p.add_argument("--option", action="append")
    p.add_argument("--evidence", action="append")
    p.add_argument("--status", default="APPROVED", choices=("APPROVED", "REJECTED", "DEFERRED"))
    p.add_argument("--supersedes")
    p.add_argument("--event-id")
    p.set_defaults(handler=record_human)
    p = sub.add_parser("review-packet", help="assemble a zip for an independent reviewer")
    p.add_argument("project")
    p.add_argument("--output", help="relative filename under reviews/ (default review_packet.zip)")
    p.set_defaults(handler=review_packet)
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        print("Python 3.10+ is required", file=sys.stderr)
        return 1
    try:
        result = args.handler(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
