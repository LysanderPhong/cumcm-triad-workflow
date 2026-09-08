#!/usr/bin/env python3
"""Small standard-library orchestrator for a CUMCM triad project.

This command automates file intake, project status, human-decision recording,
and review-packet assembly. It never approves a core modeling gate or freezes
a submission on the user's behalf.

Examples:
  python scripts/triad.py start my-project --input problem.pdf data/
  python scripts/triad.py status my-project
  python scripts/triad.py record-human my-project --gate-id START --gate-class CORE_MODELING \
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
import tempfile
import zipfile


GATES = ("START", "TOPIC", "DEFINITION", "ROUTE", "MODEL", "PAPER", "LAYOUT", "COMPLIANCE", "FREEZE")
GATE_SET = set(GATES)
LOG_FILES = (
    "human_decisions.jsonl", "autonomous_decisions.jsonl", "failures.jsonl",
    "ai_usage.jsonl", "route_changes.jsonl", "run_log.jsonl", "time_log.jsonl",
    "reviews.jsonl",
)
CORE_CLASSES = {"CORE_MODELING"}
EVENT_LOG = "events.jsonl"
TERMINAL_REVIEW_VERDICTS = {"PASS", "REJECT", "BLOCK", "ESCALATE"}


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


def event_ids(project: Path) -> set[str]:
    ids: set[str] = set()
    path = project / "logs" / EVENT_LOG
    if not path.exists():
        return ids
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed event at logs/{EVENT_LOG}:{number}: {exc}") from exc
        identifier = row.get("event_id")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError(f"event at logs/{EVENT_LOG}:{number} has no event_id")
        if identifier in ids:
            raise ValueError(f"duplicate event_id: {identifier}")
        ids.add(identifier)
    return ids


def append_event(project: Path, row: dict) -> None:
    identifier = row.get("event_id")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("event_id is required")
    if identifier in event_ids(project):
        raise ValueError(f"duplicate event_id: {identifier}")
    append_jsonl(project / "logs" / EVENT_LOG, row)


def validate_gate(gate: str) -> str:
    gate = gate.strip().upper()
    if gate not in GATE_SET:
        raise ValueError(f"unknown gate_id {gate!r}; use one of: {', '.join(GATES)}")
    return gate


def validate_relative_refs(project: Path, refs: list[str]) -> None:
    for ref in refs:
        path = Path(ref)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"evidence_ref must be a project-relative path: {ref}")
        if not (project / path).is_file():
            raise ValueError(f"evidence_ref does not exist inside project: {ref}")


def input_files(inputs: list[str], project: Path) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for raw in inputs:
        raw_path = Path(raw).expanduser()
        if raw_path.is_symlink():
            raise ValueError(f"input symlink is not accepted: {raw_path}")
        source = raw_path.resolve()
        if not source.exists():
            raise ValueError(f"input does not exist: {source}")
        if source == project or project in source.parents:
            raise ValueError("input must not be the project itself or inside it")
        if source.is_symlink():
            raise ValueError(f"input symlink is not accepted: {source}")
        if source.is_file():
            found.append((source, source.name))
        else:
            for item in sorted(source.rglob("*")):
                if item.is_symlink():
                    raise ValueError(f"input directory contains symlink: {item}")
                if item.is_file():
                    found.append((item, f"{source.name}/{item.relative_to(source).as_posix()}"))
    unique: dict[Path, str] = {}
    for item, relative in found:
        unique.setdefault(item, relative)
    return [(item, relative) for item, relative in unique.items()]


def ingest(project: Path, inputs: list[str]) -> dict:
    files = input_files(inputs, project)
    if not files:
        raise ValueError("no files found in input")
    raw_dir = project / "raw"
    destinations = [raw_dir / relative for _, relative in files]
    folded = [path.as_posix().casefold() for path in destinations]
    if len(set(folded)) != len(folded):
        raise ValueError("input contains duplicate paths (case-insensitive); rename them before ingest")
    existing = [path.name for path in destinations if path.exists()]
    if existing:
        raise ValueError(f"refusing to overwrite raw input: {', '.join(existing)}")
    manifest_rows = []
    staging = Path(tempfile.mkdtemp(prefix=".ingest-staging-", dir=project))
    try:
        for source, relative in files:
            staged = staging / relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, staged)
        for (_, relative), destination in zip(files, destinations):
            staged = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            staged.replace(destination)
            manifest_rows.append({
                "relative_path": destination.relative_to(project).as_posix(),
                "source_name": Path(relative).name,
                "source_relative": relative,
                "kind": destination.suffix.lower().lstrip(".") or "no_extension",
                "bytes": destination.stat().st_size,
                "readable": True,
                "ingested_at": now(),
            })
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    manifest_path = project / "planning" / "input_manifest.json"
    previous = []
    if manifest_path.exists():
        try:
            previous = json.loads(manifest_path.read_text(encoding="utf-8")).get("files", [])
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"existing input manifest is malformed; refusing ingest: {exc}") from exc
    manifest = {
        "schema_version": "1.0",
        "generated_at": now(),
        "source_policy": "copied by explicit user command; no hashes generated",
        "files": previous + manifest_rows,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    state = read_state(project)
    state.update({"project_state": "INPUTS_INGESTED", "current_gate": "START", "gate_status": "WAITING_HUMAN", "input_count": len(manifest_rows)})
    write_state(project, state)
    append_event(project, {"schema_version": "1.0", "event_id": f"INGEST-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}", "event_type": "inputs_ingested", "timestamp": now(), "count": len(manifest_rows)})
    return {"status": "INGESTED", "count": len(manifest_rows), "total_count": len(manifest["files"]), "manifest": "planning/input_manifest.json"}


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
    closed = state.get("closed_gates", [])
    next_gate = next((gate for gate in GATES if gate not in closed), None)
    open_failures = [
        {"failure_id": row.get("failure_id"), "gate_id": row.get("gate_id"), "severity": row.get("severity")}
        for row in log_rows(project, "failures.jsonl") if row.get("status") == "OPEN"
    ]
    if gate_status == "FROZEN":
        next_action = "none_project_frozen"
    elif open_failures:
        next_action = f"close_failures_first:{','.join(str(f['failure_id']) for f in open_failures)}"
    elif gate_status in {"WAITING_HUMAN", "BLOCKED"}:
        next_action = f"human_decision_required@{current}"
    elif next_gate:
        next_action = f"prepare_gate:{next_gate}"
    else:
        next_action = "inspect_project_state"
    return {
        "project": str(project), "current_gate": current, "gate_status": gate_status,
        "closed_gates": closed, "next_gate": next_gate, "open_failures": open_failures,
        "input_count": len(json.loads(manifest.read_text(encoding="utf-8")).get("files", [])) if manifest.exists() else 0,
        "log_counts": counts, "next_action": next_action,
    }


def record_human(args: argparse.Namespace) -> dict:
    project = require_project(args.project)
    gate_id = validate_gate(args.gate_id)
    gate_class = args.gate_class.upper()
    contribution = args.contribution.strip()
    selected = args.selected.strip()
    if gate_class in CORE_CLASSES and (len(contribution) < 12 or contribution.casefold() in {"a", "b", "c", "同意", "agree"}):
        raise ValueError("CORE_MODELING requires a concise substantive human contribution, not only A/B/C or agreement")
    if not selected or not args.rationale.strip():
        raise ValueError("selected and rationale are required")
    evidence = args.evidence or []
    validate_relative_refs(project, evidence)
    event_id = args.event_id or f"HD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    row = {
        "schema_version": "1.0", "event_id": event_id, "timestamp": now(),
        "gate_id": gate_id, "gate_class": gate_class, "decision_owner": "human",
        "proposal_source": args.proposal_source, "options_considered": args.option or [],
        "selected_option": selected, "human_contribution": contribution,
        "rationale": args.rationale.strip(), "status": args.status.upper(),
        "supersedes": args.supersedes, "evidence_refs": evidence,
    }
    append_event(project, {**row, "event_type": "human_decision"})
    append_jsonl(project / "logs" / "human_decisions.jsonl", row)
    state = read_state(project)
    state.update({"project_state": "HUMAN_DECISION_RECORDED", "current_gate": gate_id, "gate_status": "HUMAN_APPROVED_PENDING_REVIEW" if row["status"] == "APPROVED" else "WAITING_HUMAN", "human_decision_status": row["status"], "last_human_decision_id": event_id})
    write_state(project, state)
    return {"status": "RECORDED", "event_id": event_id, "gate_status": state["gate_status"]}


def review_packet(args: argparse.Namespace) -> dict:
    project = require_project(args.project)
    output = (project / "reviews" / (args.output or f"{args.mode}.zip")).resolve()
    reviews_dir = (project / "reviews").resolve()
    if reviews_dir not in output.parents:
        raise ValueError("review packet output must remain inside project/reviews")
    if output.exists():
        raise ValueError(f"refusing to overwrite review packet: {output}")
    include_roots = ("project_state.json", "project_profile.json", "planning", "raw", "code", "results", "paper", "compliance")
    if args.mode == "provenance-audit":
        include_roots = include_roots + ("logs",)
    added = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for root in include_roots:
            source = project / root
            if source.is_symlink():
                raise ValueError(f"refusing symlink in review packet: {source.relative_to(project)}")
            if source.is_file():
                archive.write(source, arcname=root)
                added += 1
                continue
            if not source.is_dir():
                continue
            for item in sorted(source.rglob("*")):
                if item.is_symlink():
                    raise ValueError(f"refusing symlink in review packet: {item.relative_to(project)}")
                if not item.is_file() or item.name.startswith(".") or item == output:
                    continue
                archive.write(item, arcname=item.relative_to(project).as_posix())
                added += 1
        archive.writestr("REVIEW_PACKET_README.txt", f"Generated by triad.py mode={args.mode}. Run anonym_scan.py and human review before sharing.\n")
    return {"status": "CREATED", "mode": args.mode, "packet": str(output), "files": added, "warning": "packet may contain sensitive inputs; anonymize before external sharing"}


def log_rows(project: Path, filename: str) -> list[dict]:
    path = project / "logs" / filename
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed {filename}:{number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{filename}:{number} must be a JSON object")
        rows.append(row)
    return rows


def record_review(args: argparse.Namespace) -> dict:
    project = require_project(args.project)
    gate_id = validate_gate(args.gate_id)
    verdict = args.verdict.upper()
    if verdict not in TERMINAL_REVIEW_VERDICTS:
        raise ValueError("verdict must be PASS, REJECT, BLOCK, or ESCALATE")
    if not args.context_id.strip():
        raise ValueError("independent reviewer context_id is required")
    evidence = args.evidence or []
    validate_relative_refs(project, evidence)
    if verdict == "PASS" and not evidence:
        raise ValueError("review PASS requires at least one project-relative evidence_ref")
    event_id = args.event_id or f"RV-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    self_review = bool(args.self_review_only)
    row = {"schema_version": "1.0", "event_id": event_id, "event_type": "review_verdict", "timestamp": now(), "gate_id": gate_id, "verdict": verdict, "reviewer_context_id": args.context_id.strip(), "same_context_as_executor": self_review, "review_scope": "SELF_REVIEW_ONLY" if self_review else "INDEPENDENT", "evidence_refs": evidence, "notes": args.notes.strip()}
    if self_review and verdict == "PASS":
        row["notes"] = (row["notes"] + " [self-review PASS cannot close a gate]").strip()
    append_event(project, row)
    append_jsonl(project / "logs" / "reviews.jsonl", row)
    state = read_state(project)
    if verdict == "PASS":
        state["gate_status"] = "SELF_REVIEWED" if self_review else "REVIEWED"
    else:
        state["gate_status"] = "BLOCKED"
    state.update({"review_status": verdict, "review_gate": gate_id, "last_review_id": event_id})
    write_state(project, state)
    return {"status": "RECORDED", "verdict": verdict, "event_id": event_id, "review_scope": row["review_scope"], "gate_status": state["gate_status"]}


def record_failure(args: argparse.Namespace) -> dict:
    project = require_project(args.project)
    gate_id = validate_gate(args.gate_id)
    severity = args.severity.upper()
    if severity not in {"CRITICAL", "MAJOR", "MINOR"}:
        raise ValueError("severity must be CRITICAL, MAJOR, or MINOR")
    failure_id = args.failure_id or f"F-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    existing = {row.get("failure_id") for row in log_rows(project, "failures.jsonl")}
    if failure_id in existing:
        raise ValueError(f"duplicate failure_id: {failure_id}")
    refs = args.evidence or []
    validate_relative_refs(project, refs)
    row = {"schema_version": "1.0", "event_id": f"FE-{failure_id}", "event_type": "failure_opened", "failure_id": failure_id, "timestamp": now(), "gate_id": gate_id, "severity": severity, "failure_type": args.failure_type.upper(), "description": args.description.strip(), "status": "OPEN", "evidence_refs": refs}
    append_event(project, row)
    append_jsonl(project / "logs" / "failures.jsonl", row)
    state = read_state(project)
    state.update({"project_state": "BLOCKED_BY_FAILURE", "gate_status": "BLOCKED", "open_blockers": int(state.get("open_blockers", 0)) + 1, "last_failure_id": failure_id})
    write_state(project, state)
    return {"status": "OPEN", "failure_id": failure_id, "gate_status": "BLOCKED"}


def close_failure(args: argparse.Namespace) -> dict:
    project = require_project(args.project)
    rows = log_rows(project, "failures.jsonl")
    matches = [row for row in rows if row.get("failure_id") == args.failure_id]
    if not matches:
        raise ValueError(f"failure_id not found: {args.failure_id}")
    if matches[-1].get("status") != "OPEN":
        raise ValueError("failure is not OPEN; history is append-only")
    refs = args.evidence or []
    validate_relative_refs(project, refs)
    event_id = args.event_id or f"FC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    row = {"schema_version": "1.0", "event_id": event_id, "event_type": "failure_closed", "failure_id": args.failure_id, "timestamp": now(), "status": args.status.upper(), "repair_ref": args.repair_ref, "verification_refs": refs, "notes": args.notes.strip()}
    append_event(project, row)
    append_jsonl(project / "logs" / "failures.jsonl", {**row, "failure_type": "CLOSURE"})
    state = read_state(project)
    state["open_blockers"] = max(0, int(state.get("open_blockers", 0)) - 1)
    state["gate_status"] = "WAITING_REVIEW" if state["open_blockers"] == 0 else "BLOCKED"
    write_state(project, state)
    return {"status": row["status"], "failure_id": args.failure_id, "open_blockers": state["open_blockers"]}


def record_run(args: argparse.Namespace) -> dict:
    project = require_project(args.project)
    run_id = args.run_id.strip()
    if not run_id:
        raise ValueError("run_id is required")
    existing = {str(row.get("run_id") or row.get("event_id")) for row in log_rows(project, "run_log.jsonl")}
    if run_id in existing:
        raise ValueError(f"duplicate run_id: {run_id}")
    run_status = args.status.upper()
    if run_status not in {"SUCCEEDED", "FAILED", "CANCELLED"}:
        raise ValueError("status must be SUCCEEDED, FAILED, or CANCELLED")
    outputs = args.output or []
    validate_relative_refs(project, outputs)
    if run_status == "SUCCEEDED" and not outputs:
        raise ValueError("SUCCEEDED run must declare at least one output_ref")
    event_id = args.event_id or f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    row = {"schema_version": "1.0", "event_id": event_id, "event_type": "run", "timestamp": now(), "run_id": run_id, "gate_id": validate_gate(args.gate_id) if args.gate_id else None, "command": args.command.strip(), "status": run_status, "output_refs": outputs, "notes": args.notes.strip()}
    append_event(project, {k: v for k, v in row.items() if v is not None})
    append_jsonl(project / "logs" / "run_log.jsonl", {k: v for k, v in row.items() if v is not None})
    return {"status": "RECORDED", "run_id": run_id, "run_status": run_status, "outputs": len(outputs)}


def record_claim(args: argparse.Namespace) -> dict:
    project = require_project(args.project)
    claim_id = args.claim_id.strip()
    text = args.text.strip()
    if not claim_id or not text:
        raise ValueError("claim_id and text are required")
    existing = {str(row.get("claim_id")) for row in log_rows(project, "claims.jsonl")}
    if claim_id in existing:
        raise ValueError(f"duplicate claim_id: {claim_id}")
    evidence = args.evidence or []
    run_ids = [r.strip() for r in (args.run_id or []) if r.strip()]
    if not evidence:
        raise ValueError("at least one --evidence is required")
    if not run_ids:
        raise ValueError("at least one --run-id is required")
    validate_relative_refs(project, evidence)
    runs = {str(row.get("run_id") or row.get("event_id")): row for row in log_rows(project, "run_log.jsonl")}
    declared: set[str] = set()
    for run_id in run_ids:
        run = runs.get(run_id)
        if run is None:
            raise ValueError(f"referenced run_id not found in run_log.jsonl: {run_id}")
        if str(run.get("status", "")).upper() != "SUCCEEDED":
            raise ValueError(f"run {run_id} is not SUCCEEDED")
        declared.update(str(x) for x in run.get("output_refs", []) if isinstance(x, str))
    evidence_role = args.evidence_role.upper()
    if evidence_role not in {"RUN_OUTPUT", "DECISION"}:
        raise ValueError("evidence_role must be RUN_OUTPUT or DECISION")
    if evidence_role != "DECISION" and set(evidence).isdisjoint(declared):
        raise ValueError("no evidence_ref is declared in the referenced runs' output_refs")
    claim_status = args.status.upper()
    if claim_status not in {"DRAFT", "APPROVED"}:
        raise ValueError("status must be DRAFT or APPROVED")
    known = event_ids(project) | {str(row.get("event_id")) for row in log_rows(project, "human_decisions.jsonl")} | {str(row.get("event_id")) for row in log_rows(project, "reviews.jsonl")}
    row = {"schema_version": "1.0", "claim_id": claim_id, "recorded_at": now(), "text": text, "status": claim_status, "evidence_refs": evidence, "run_ids": run_ids, "evidence_role": evidence_role}
    if claim_status == "APPROVED":
        for key, value in (("decision_ref", args.decision_ref), ("review_ref", args.review_ref)):
            if not value or not value.strip():
                raise ValueError(f"APPROVED claim requires --{key.replace('_', '-')}")
            if value.strip() not in known:
                raise ValueError(f"{key} does not resolve to a recorded event: {value}")
            row[key] = value.strip()
    append_jsonl(project / "logs" / "claims.jsonl", row)
    return {"status": "RECORDED", "claim_id": claim_id, "claim_status": claim_status}


def close_gate(args: argparse.Namespace) -> dict:
    project = require_project(args.project)
    gate_id = validate_gate(args.gate_id)
    state = read_state(project)
    if state.get("current_gate") != gate_id:
        raise ValueError(f"current gate is {state.get('current_gate')!r}; cannot close {gate_id}")
    closed = state.get("closed_gates", [])
    predecessors = GATES[: GATES.index(gate_id)]
    missing = [gate for gate in predecessors if gate not in closed]
    if missing:
        raise ValueError(f"preceding gates not closed: {', '.join(missing)}")
    decisions = [row for row in log_rows(project, "human_decisions.jsonl") if row.get("gate_id") == gate_id and row.get("status") == "APPROVED"]
    independent = [row for row in log_rows(project, "reviews.jsonl") if row.get("gate_id") == gate_id and row.get("verdict") == "PASS" and not row.get("same_context_as_executor")]
    if not decisions:
        raise ValueError("gate has no APPROVED human decision")
    if not independent:
        raise ValueError("gate has no independent reviewer PASS (self-review PASS cannot close a gate)")
    # Order matters: the review must come after the latest approved decision.
    # events.jsonl append order is the source of truth; timestamps (1s resolution) are the fallback.
    reviews_after: list[dict] = []
    events_path = project / "logs" / EVENT_LOG
    if events_path.exists():
        decision_pos = -1
        review_positions: list[tuple[int, dict]] = []
        for index, row in enumerate(log_rows(project, EVENT_LOG)):
            if row.get("gate_id") != gate_id:
                continue
            if row.get("event_type") == "human_decision" and row.get("status") == "APPROVED":
                decision_pos = index
            elif row.get("event_type") == "review_verdict" and row.get("verdict") == "PASS" and not row.get("same_context_as_executor"):
                review_positions.append((index, row))
        reviews_after = [row for index, row in review_positions if index > decision_pos]
    else:
        latest_decision = max(str(row.get("timestamp", "")) for row in decisions)
        reviews_after = [row for row in independent if str(row.get("timestamp", "")) > latest_decision]
    if not reviews_after:
        raise ValueError("no independent PASS after the latest APPROVED human decision; re-review required")
    if int(state.get("open_blockers", 0)):
        raise ValueError("open blockers remain")
    event_id = args.event_id or f"GC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    row = {"schema_version": "1.0", "event_id": event_id, "event_type": "gate_closed", "timestamp": now(), "gate_id": gate_id, "human_decision_ref": decisions[-1].get("event_id"), "review_ref": reviews_after[-1].get("event_id")}
    append_event(project, row)
    state["gate_status"] = "CLOSED"
    state.setdefault("closed_gates", []).append(gate_id)
    upcoming = GATES[GATES.index(gate_id) + 1] if GATES.index(gate_id) + 1 < len(GATES) else None
    if upcoming:
        state["current_gate"] = upcoming
        state["gate_status"] = "CLOSED_ADVANCE_TO_" + upcoming
    write_state(project, state)
    return {"status": "CLOSED", "gate_id": gate_id, "event_id": event_id, "next_gate": upcoming}


def freeze(args: argparse.Namespace) -> dict:
    project = require_project(args.project)
    state = read_state(project)
    missing = [gate for gate in GATES[:-1] if gate not in state.get("closed_gates", [])]
    if missing:
        raise ValueError(f"cannot freeze; gates not closed: {', '.join(missing)}")
    if int(state.get("open_blockers", 0)):
        raise ValueError("cannot freeze with open blockers")
    confirmation = args.confirmation.strip()
    if len(confirmation) < 12:
        raise ValueError("freeze requires a substantive human confirmation")
    event_id = args.event_id or f"FR-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    row = {"schema_version": "1.0", "event_id": event_id, "event_type": "freeze", "timestamp": now(), "version": args.version, "human_confirmation": confirmation, "status": "FROZEN"}
    append_event(project, row)
    state.update({"project_state": "FROZEN", "current_gate": "FREEZE", "gate_status": "FROZEN", "frozen_version": args.version, "freeze_event_id": event_id})
    write_state(project, state)
    return {"status": "FROZEN", "version": args.version, "event_id": event_id}


def validate_project(project: Path) -> dict:
    errors: list[str] = []
    try:
        state = read_state(project)
    except ValueError as exc:
        return {"status": "INVALID", "errors": [str(exc)]}
    try:
        ids = event_ids(project)
    except ValueError as exc:
        errors.append(str(exc)); ids = set()
    if state.get("current_gate") not in GATE_SET:
        errors.append(f"unknown current_gate: {state.get('current_gate')}")
    for filename in ("human_decisions.jsonl", "reviews.jsonl", "failures.jsonl"):
        try:
            for row in log_rows(project, filename):
                if "gate_id" in row and row["gate_id"] not in GATE_SET:
                    errors.append(f"unknown gate_id in {filename}: {row['gate_id']}")
        except ValueError as exc:
            errors.append(str(exc))
    if not (project / "logs" / EVENT_LOG).exists():
        errors.append("missing logs/events.jsonl; project cannot be replay-validated")
    return {"status": "VALID" if not errors else "INVALID", "errors": errors, "event_count": len(ids), "current_gate": state.get("current_gate"), "gate_status": state.get("gate_status"), "open_blockers": state.get("open_blockers", 0)}


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
    p = sub.add_parser("record-review", help="append an independent reviewer verdict")
    p.add_argument("project")
    p.add_argument("--gate-id", required=True)
    p.add_argument("--verdict", required=True, choices=tuple(sorted(TERMINAL_REVIEW_VERDICTS)))
    p.add_argument("--context-id", required=True)
    p.add_argument("--self-review-only", action="store_true", help="honestly mark a same-context self-check; such PASS cannot close a gate")
    p.add_argument("--evidence", action="append")
    p.add_argument("--notes", default="")
    p.add_argument("--event-id")
    p.set_defaults(handler=record_review)
    p = sub.add_parser("record-failure", help="append an open failure blocker")
    p.add_argument("project")
    p.add_argument("--gate-id", required=True)
    p.add_argument("--severity", required=True)
    p.add_argument("--failure-type", default="MECHANICAL")
    p.add_argument("--description", required=True)
    p.add_argument("--evidence", action="append")
    p.add_argument("--failure-id")
    p.set_defaults(handler=record_failure)
    p = sub.add_parser("close-failure", help="append a verified failure closure")
    p.add_argument("project")
    p.add_argument("failure_id")
    p.add_argument("--repair-ref", required=True)
    p.add_argument("--evidence", action="append", required=True)
    p.add_argument("--status", default="FIXED", choices=("FIXED", "ACCEPTED_RISK"))
    p.add_argument("--notes", default="")
    p.add_argument("--event-id")
    p.set_defaults(handler=close_failure)
    p = sub.add_parser("record-run", help="append one run record to run_log.jsonl")
    p.add_argument("project")
    p.add_argument("--run-id", required=True)
    p.add_argument("--status", required=True, choices=("SUCCEEDED", "FAILED", "CANCELLED"))
    p.add_argument("--command", default="")
    p.add_argument("--gate-id")
    p.add_argument("--output", action="append", help="project-relative output file; repeatable")
    p.add_argument("--notes", default="")
    p.add_argument("--event-id")
    p.set_defaults(handler=record_run)
    p = sub.add_parser("record-claim", help="append one paper claim bound to evidence and runs")
    p.add_argument("project")
    p.add_argument("--claim-id", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--evidence", action="append", required=True)
    p.add_argument("--run-id", action="append", required=True)
    p.add_argument("--status", default="DRAFT", choices=("DRAFT", "APPROVED"))
    p.add_argument("--evidence-role", default="RUN_OUTPUT", choices=("RUN_OUTPUT", "DECISION"))
    p.add_argument("--decision-ref")
    p.add_argument("--review-ref")
    p.set_defaults(handler=record_claim)
    p = sub.add_parser("close-gate", help="close a gate only after human approval, reviewer PASS, and no blockers")
    p.add_argument("project")
    p.add_argument("--gate-id", required=True)
    p.add_argument("--event-id")
    p.set_defaults(handler=close_gate)
    p = sub.add_parser("freeze", help="freeze only after all gates and explicit human confirmation")
    p.add_argument("project")
    p.add_argument("--version", required=True)
    p.add_argument("--confirmation", required=True)
    p.add_argument("--event-id")
    p.set_defaults(handler=freeze)
    p = sub.add_parser("validate", help="validate event/log schemas and fail-closed state")
    p.add_argument("project")
    p.set_defaults(handler=lambda a: validate_project(require_project(a.project)))
    p = sub.add_parser("review-packet", help="assemble a zip for an independent reviewer")
    p.add_argument("project")
    p.add_argument("--output", help="relative filename under reviews/ (default review_packet.zip)")
    p.add_argument("--mode", choices=("blind-review", "provenance-audit"), default="blind-review")
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
