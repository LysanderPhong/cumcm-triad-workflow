#!/usr/bin/env python3
"""Validate claim -> evidence -> reproducible run links for a triad project.

The checker is deliberately conservative: a claim is release-eligible only when
its referenced run exists and succeeded, each evidence path is a project-relative
regular file, and the evidence is declared by that run (or is explicitly marked
as a decision/reference artifact). It does not infer scientific truth.

Usage: python scripts/claim_check.py PROJECT [--claims PATH] [--runs PATH]
Exit codes: 0 VALID, 2 INVALID or refused.
Python 3.10+, standard library only.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

LOG_DIR = "logs"
DEFAULT_CLAIMS = "logs/claims.jsonl"
DEFAULT_RUNS = "logs/run_log.jsonl"
APPROVED = {"APPROVED", "RELEASE_ELIGIBLE"}


def read_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    rows, errors = [], []
    if not path.exists():
        return rows, [f"missing file: {path.as_posix()}"]
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return rows, [f"cannot read {path}: {exc}"]
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.as_posix()}:{n}: malformed JSON ({exc.msg})")
            continue
        if not isinstance(row, dict):
            errors.append(f"{path.as_posix()}:{n}: expected JSON object")
            continue
        rows.append(row)
    return rows, errors


def safe_ref(project: Path, ref: object, label: str, errors: list[str]) -> Path | None:
    if not isinstance(ref, str) or not ref.strip():
        errors.append(f"{label}: evidence_ref must be a non-empty string")
        return None
    p = Path(ref)
    if p.is_absolute() or ".." in p.parts:
        errors.append(f"{label}: absolute or parent path is not allowed: {ref}")
        return None
    candidate = project / p
    if candidate.is_symlink() or not candidate.is_file():
        errors.append(f"{label}: evidence file is missing or symlink: {ref}")
        return None
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--claims", default=DEFAULT_CLAIMS, help="claims JSONL, relative to project")
    parser.add_argument("--runs", default=DEFAULT_RUNS, help="run JSONL, relative to project")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        print("ERROR: Python 3.10+ is required", file=sys.stderr); return 2
    project = args.project.expanduser().resolve()
    if not project.is_dir():
        print(f"ERROR: project is not a directory: {project}", file=sys.stderr); return 2
    claim_path = Path(args.claims)
    run_path = Path(args.runs)
    if claim_path.is_absolute() or ".." in claim_path.parts or run_path.is_absolute() or ".." in run_path.parts:
        print("ERROR: --claims/--runs must be project-relative", file=sys.stderr); return 2
    claims, errors = read_jsonl(project / claim_path)
    runs, run_errors = read_jsonl(project / run_path)
    errors.extend(run_errors)
    known_event_ids: set[str] = set()
    for log in ("events.jsonl", "human_decisions.jsonl", "reviews.jsonl"):
        rows, log_errors = read_jsonl(project / LOG_DIR / log)
        errors.extend(log_errors)
        for row in rows:
            identifier = row.get("event_id")
            if isinstance(identifier, str) and identifier.strip():
                known_event_ids.add(identifier)
    run_map: dict[str, dict] = {}
    for i, row in enumerate(runs, 1):
        run_id = row.get("run_id") or row.get("event_id")
        if not isinstance(run_id, str) or not run_id.strip():
            errors.append(f"{run_path.as_posix()}:{i}: missing run_id/event_id")
            continue
        if run_id in run_map:
            errors.append(f"duplicate run_id: {run_id}")
        else:
            run_map[run_id] = row
    claim_ids: set[str] = set()
    for i, claim in enumerate(claims, 1):
        where = f"{claim_path.as_posix()}:{i}"
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            errors.append(f"{where}: missing claim_id"); continue
        if claim_id in claim_ids:
            errors.append(f"duplicate claim_id: {claim_id}")
        claim_ids.add(claim_id)
        if not isinstance(claim.get("text"), str) or not claim["text"].strip():
            errors.append(f"{where}: claim text is empty")
        status = str(claim.get("status", "DRAFT")).upper()
        evidence = claim.get("evidence_refs", [])
        run_ids = claim.get("run_ids", [])
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{where}: evidence_refs must contain at least one path")
            evidence = []
        if not isinstance(run_ids, list) or not run_ids:
            errors.append(f"{where}: run_ids must contain at least one run")
            run_ids = []
        evidence_set = {str(x) for x in evidence if isinstance(x, str)}
        declared_by_successful_run: set[str] = set()
        for run_id in run_ids:
            if not isinstance(run_id, str) or not run_id.strip():
                errors.append(f"{where}: run_ids contains an invalid value"); continue
            run = run_map.get(run_id)
            if run is None:
                errors.append(f"{where}: referenced run_id not found: {run_id}"); continue
            if str(run.get("status", "")).upper() != "SUCCEEDED":
                errors.append(f"{where}: run {run_id} is not SUCCEEDED")
            output_refs = run.get("output_refs", [])
            if not isinstance(output_refs, list):
                errors.append(f"{where}: run {run_id} output_refs must be a list"); output_refs = []
            declared_by_successful_run.update(str(x) for x in output_refs if isinstance(x, str))
        for ref in evidence:
            safe_ref(project, ref, where, errors)
        # A run must explicitly declare at least one of the claim's evidence files.
        # Decision/reference artifacts can opt out with evidence_role=DECISION.
        evidence_role = claim.get("evidence_role", "RUN_OUTPUT")
        if str(evidence_role).upper() != "DECISION" and evidence_set.isdisjoint(declared_by_successful_run):
            errors.append(f"{where}: no evidence_ref is declared in referenced run output_refs")
        if status in APPROVED:
            for key in ("decision_ref", "review_ref"):
                value = claim.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{where}: approved claim requires {key}")
                elif value not in known_event_ids:
                    errors.append(f"{where}: {key} does not resolve to a recorded event: {value}")
    result = {"status": "VALID" if not errors else "INVALID", "claims": len(claims), "runs": len(run_map), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
