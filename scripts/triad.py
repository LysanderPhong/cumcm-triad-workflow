#!/usr/bin/env python3
"""Lean modeling workflow. One authoritative event journal; derived status.

Human checkpoints: SCOPE, ROUTE, explicit final freeze.
Independent review: RESULTS and DELIVERY. Python 3.10+, standard library.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from hash_check import check_file as digest

if sys.platform == 'win32':
    import msvcrt
else:
    import fcntl

GATES = ('SCOPE', 'ROUTE', 'RESULTS', 'DELIVERY')
HUMAN_GATES = {'SCOPE', 'ROUTE'}
REVIEW_GATES = {'RESULTS', 'DELIVERY'}
DIRECTORIES = ('raw', 'code', 'results', 'paper', 'reviews', 'compliance', 'logs', 'releases')
JOURNAL = 'logs/events.jsonl'
EVENT_REQUIRED = {
    'initialized': (), 'inputs_ingested': ('fingerprints',),
    'human_decision': ('gate_id', 'selected', 'contribution', 'status', 'fingerprints'),
    'review': ('gate_id', 'verdict', 'same_context_as_executor', 'fingerprints', 'context'),
    'failure': ('failure_id', 'status', 'description', 'fingerprints'),
    'run': ('run_id', 'status', 'verified_execution', 'fingerprints'),
    'claim': ('claim_id', 'text', 'status', 'run_ids', 'fingerprints'),
    'gate_closed': ('gate_id',),
    'freeze': ('version', 'confirmation', 'fingerprints'), 'reopened': ('source',),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def project_path(value):
    return Path(value).expanduser().resolve()


def require_project(value):
    p = project_path(value)
    if (p / 'project_state.json').exists():
        raise ValueError('legacy project: keep its records; create a new lean project (format 2.0)')
    if not (p / JOURNAL).is_file():
        raise ValueError('not a lean project; use start with a new directory')
    events = rows(p)
    if not events or events[0]['type'] != 'initialized':
        raise ValueError('journal missing initialization event')
    return p


def rows(p):
    events = []
    ids = set()
    for number, line in enumerate((p / JOURNAL).read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or row.get('schema_version') != '2.0' or not row.get('event_id') or not row.get('type'):
            raise ValueError(f'invalid event at line {number}')
        kind = row['type']
        if kind not in EVENT_REQUIRED or any(key not in row for key in EVENT_REQUIRED[kind]):
            raise ValueError(f'invalid {kind} event at line {number}')
        if not isinstance(row['event_id'], str) or ('gate_id' in row and row['gate_id'] not in GATES):
            raise ValueError(f'invalid event id or gate at line {number}')
        if 'fingerprints' in row and (not isinstance(row['fingerprints'], dict) or any(not isinstance(k, str) or not isinstance(v, str) or not re.fullmatch('[0-9a-f]{64}', v) for k, v in row['fingerprints'].items())):
            raise ValueError(f'invalid fingerprints at line {number}')
        allowed_status = {'human_decision': {'APPROVED','REJECTED','DEFERRED'}, 'failure': {'OPEN','FIXED','ACCEPTED_RISK'}, 'run': {'SUCCEEDED','FAILED','CANCELLED'}, 'claim': {'DRAFT','APPROVED','REJECTED'}}
        if kind in allowed_status and row.get('status') not in allowed_status[kind]:
            raise ValueError(f'invalid status at line {number}')
        if kind == 'review' and (row['verdict'] not in {'PASS','REJECT','BLOCK','ESCALATE'} or not isinstance(row['same_context_as_executor'], bool) or not isinstance(row['context'], dict)):
            raise ValueError(f'invalid review at line {number}')
        if kind == 'claim' and (not isinstance(row['run_ids'], list) or not row['run_ids'] or any(not isinstance(r, str) for r in row['run_ids'])):
            raise ValueError(f'invalid claim run IDs at line {number}')
        for key in ('run_id', 'claim_id', 'failure_id'):
            if key in row and (not isinstance(row[key], str) or not row[key].strip()):
                raise ValueError(f'invalid {key} at line {number}')
        if row['event_id'] in ids:
            raise ValueError('duplicate event_id')
        ids.add(row['event_id'])
        events.append(row)
    return events


@contextmanager
def locked(p):
    # Keep one inode: unlinking an advisory lock can admit two writers.
    with (p / 'logs/write.lock').open('a+b') as handle:
        if sys.platform == 'win32' and handle.tell() == 0:
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            if sys.platform == 'win32':
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError('another write is active; retry after it finishes') from exc
        try:
            yield
        finally:
            if sys.platform == 'win32':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def append(p, kind, **fields):
    events = rows(p)
    row = dict(schema_version='2.0', event_id=fields.pop('event_id', None) or uuid.uuid4().hex,
               timestamp=now(), type=kind, **fields)
    if any(e['event_id'] == row['event_id'] for e in events):
        raise ValueError('duplicate event_id')
    temporary = p / 'logs/events.tmp'
    temporary.write_text(''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in events + [row]), encoding='utf-8')
    temporary.replace(p / JOURNAL)
    return row


def gate(value):
    value = value.upper()
    if value not in GATES:
        raise ValueError('gate must be ' + ', '.join(GATES))
    return value


def evidence(p, refs):
    result = {}
    for ref in refs or []:
        rel = Path(ref)
        if not ref or rel.is_absolute() or '..' in rel.parts:
            raise ValueError(f'project-relative file required: {ref}')
        candidate = p / rel
        cursor = p
        for part in rel.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ValueError(f'symlink evidence forbidden: {ref}')
        if not candidate.is_file() or not candidate.resolve().is_relative_to(p):
            raise ValueError(f'evidence missing or outside project: {ref}')
        result[rel.as_posix()] = digest(candidate)
    return result


def unchanged(p, fingerprints):
    try:
        return evidence(p, list(fingerprints)) == fingerprints
    except (ValueError, OSError):
        return False


def run_inputs(p, script_refs=()):
    return {**bundle(p, ('raw', 'code')), **evidence(p, script_refs)}


def current_run(p, run):
    saved = run.get('input_fingerprints', {})
    scripts = [ref for ref in saved if not ref.startswith('raw/')]
    try:
        return run.get('tracks_code', False) and unchanged(p, run['fingerprints']) and saved == run_inputs(p, scripts)
    except (ValueError, OSError):
        return False


def latest(events, kind, key):
    result = {}
    for e in events:
        if e['type'] == kind:
            result[e[key]] = e
    return result


def bundle(p, roots=('raw', 'code', 'results', 'paper', 'compliance')):
    # Review binds the actual scientific/production files, including journaled inputs.
    files = []
    for root in roots:
        for file in sorted((p / root).rglob('*')):
            if root == 'code' and ('__pycache__' in file.relative_to(p).parts or file.suffix in {'.pyc', '.pyo'}):
                continue
            if file.is_symlink():
                raise ValueError('production tree contains symlink')
            if file.is_file():
                files.append(file.relative_to(p).as_posix())
    return evidence(p, files)


def state(p):
    events = rows(p)
    closed = []
    frozen = False
    version = None
    claim_versions = {}
    for e in events:
        if e['type'] == 'gate_closed':
            if e['gate_id'] not in closed:
                closed.append(e['gate_id'])
        elif e['type'] == 'claim':
            signature = claim_signature(e)
            if claim_versions.get(e['claim_id']) != signature:
                closed = [g for g in closed if GATES.index(g) < GATES.index('RESULTS')]
            claim_versions[e['claim_id']] = signature
        elif e['type'] in {'human_decision', 'review', 'run', 'inputs_ingested', 'failure'}:
            affected = e['gate_id'] if e['type'] in {'human_decision', 'review'} else 'RESULTS'
            closed = [g for g in closed if GATES.index(g) < GATES.index(affected)]
        elif e['type'] == 'freeze':
            frozen, version = True, e['version']
        elif e['type'] == 'reopened':
            frozen = False
            closed = [g for g in closed if g in HUMAN_GATES]
    failures = latest(events, 'failure', 'failure_id')
    open_failures = [e for e in failures.values() if e['status'] == 'OPEN']
    current = next((g for g in GATES if g not in closed), 'FREEZE')
    return dict(current_gate=current, closed_gates=closed, frozen=frozen, frozen_version=version,
                open_failures=open_failures, open_blockers=len(open_failures))


def valid_decision(events, g):
    decisions = [e for e in events if e['type'] == 'human_decision' and e['gate_id'] == g]
    if not decisions or decisions[-1]['status'] != 'APPROVED':
        return None
    decision = decisions[-1]
    if g == 'ROUTE':
        scope = valid_decision(events, 'SCOPE')
        if not scope or events.index(decision) < events.index(scope):
            return None
    return decision


def valid_review(p, events, g):
    reviews = [e for e in events if e['type'] == 'review' and e['gate_id'] == g]
    if not reviews:
        return None
    r = reviews[-1]
    if r['verdict'] != 'PASS' or r['same_context_as_executor']:
        return None
    context = review_context(p, events)
    if r.get('context') != context or not unchanged(p, r['fingerprints']):
        return None
    return r


def review_context(p, events):
    kinds = {'human_decision', 'run', 'failure'}
    claims = latest(events, 'claim', 'claim_id')
    return dict(files=bundle(p), record_ids=[e['event_id'] for e in events if e['type'] in kinds],
                claims={key: claim_signature(claim) for key, claim in claims.items()})


def claim_signature(claim):
    return {key: claim[key] for key in ('text', 'run_ids', 'fingerprints')}


def check_claims(p, events):
    errors = []
    runs = latest(events, 'run', 'run_id')
    claims = latest(events, 'claim', 'claim_id')
    by_id = {e['event_id']: e for e in events}
    for c in claims.values():
        if c['status'] == 'REJECTED':
            continue
        label = c['claim_id']
        if not unchanged(p, c['fingerprints']):
            errors.append(label + ': evidence changed or missing')
        declared = {}
        for rid in c['run_ids']:
            run = runs.get(rid)
            if not run or run['status'] != 'SUCCEEDED' or not run.get('verified_execution'):
                errors.append(label + ': run not successfully executed by run command: ' + rid)
            elif not current_run(p, run):
                errors.append(label + ': run outputs changed: ' + rid)
            else:
                declared.update(run['fingerprints'])
        if not set(c['fingerprints']).issubset(declared):
            errors.append(label + ': every evidence file must be a recorded run output')
        if c['status'] == 'APPROVED':
            d, r = by_id.get(c.get('decision_ref')), by_id.get(c.get('review_ref'))
            if not d or d['type'] != 'human_decision' or d['status'] != 'APPROVED' or valid_decision(events, d['gate_id']) != d:
                errors.append(label + ': invalid or superseded human decision')
            if not r or r['type'] != 'review' or r['verdict'] != 'PASS' or r['same_context_as_executor']:
                errors.append(label + ': invalid independent review')
            elif latest(events, 'review', 'gate_id').get(r['gate_id']) != r or not unchanged(p, r['fingerprints']) or not set(c['fingerprints']).issubset(r['fingerprints']):
                errors.append(label + ': review superseded, evidence changed, or evidence not reviewed')
        elif c['status'] != 'DRAFT':
            errors.append(label + ': unknown status')
    return errors


def checks(p, g):
    events = rows(p)
    errors = []
    s = state(p)
    if s['open_blockers']:
        errors.append('open failures remain')
    for h in HUMAN_GATES:
        if GATES.index(h) <= GATES.index(g) and not valid_decision(events, h):
            errors.append('human decision needed: ' + h)
    if g in REVIEW_GATES and not valid_review(p, events, g):
        errors.append('current independent PASS needed: ' + g)
    if g in REVIEW_GATES:
        errors.extend(check_claims(p, events))
        successful = [e for e in events if e['type'] == 'run' and e['status'] == 'SUCCEEDED' and e.get('verified_execution') and current_run(p, e)]
        if not successful:
            errors.append('no current successful execution; use run')
    if g == 'DELIVERY':
        finals = [f for f in (p / 'paper').glob('*.pdf') if f.is_file() and not f.is_symlink()]
        def pdf_header(file):
            with file.open('rb') as source:
                return file.stat().st_size > 100 and source.read(5) == b'%PDF-'
        if not any(pdf_header(f) for f in finals):
            errors.append('final PDF needed under paper/')
        delivery_reviews = [e for e in events if e['type'] == 'review' and e['gate_id'] == 'DELIVERY']
        required = {'rendered_pdf', 'figures_tables', 'references', 'anonymity', 'ai_disclosure', 'supporting_files'}
        if not delivery_reviews or not required.issubset(set(delivery_reviews[-1].get('checks', []))):
            errors.append('delivery review must record: ' + ', '.join(sorted(required)))
    return errors


def start(args):
    p = project_path(args.project)
    if p.exists() and (not p.is_dir() or any(p.iterdir())):
        raise ValueError('start requires a new or empty directory')
    # Validate input before creating any project files.
    incoming = inputs(args.input or [])
    p.mkdir(parents=True, exist_ok=True)
    for d in DIRECTORIES:
        (p / d).mkdir()
    (p / JOURNAL).write_text('', encoding='utf-8')
    append(p, 'initialized')
    if incoming:
        ingest_files(p, incoming)
    return dict(status='STARTED', project=str(p), **state(p))


def inputs(values):
    found = {}
    for value in values:
        path = Path(value).expanduser()
        if path.is_symlink() or not path.exists():
            raise ValueError('missing input or symlink: ' + value)
        candidates = [path] if path.is_file() else sorted(path.rglob('*'))
        for f in candidates:
            if f.is_symlink():
                raise ValueError('input contains symlink')
            if f.is_file():
                relative = f.name if path.is_file() else (Path(path.name) / f.relative_to(path)).as_posix()
                key = relative.casefold()
                if key in found:
                    raise ValueError('duplicate input name')
                found[key] = (f.resolve(), relative)
    return list(found.values())


def ingest_files(p, files):
    if not files:
        raise ValueError('no input files')
    rows(p)  # validate journal before copying
    for source, rel in files:
        if source.is_relative_to(p):
            raise ValueError('inputs must be outside project')
        if (p / 'raw' / rel).exists():
            raise ValueError('refusing to overwrite raw input: ' + rel)
    staged = Path(tempfile.mkdtemp(prefix='.ingest-', dir=p))
    committed = []
    try:
        for source, rel in files:
            dest = staged / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        for source, rel in files:
            dest = p / 'raw' / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            (staged / rel).replace(dest)
            committed.append(dest)
        append(p, 'inputs_ingested', fingerprints=evidence(p, [f.relative_to(p).as_posix() for f in committed]))
    except Exception:
        for dest in committed:
            dest.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(staged, ignore_errors=True)
    return dict(status='INGESTED', count=len(files))


def status(p):
    s = state(p)
    g = s['current_gate']
    if s['frozen']:
        action = 'frozen; use reopen with a new project directory to continue'
    elif s['open_failures']:
        action = 'resolve open failures: ' + ', '.join(e['failure_id'] for e in s['open_failures'])
    elif g == 'FREEZE':
        errors = checks(p, 'DELIVERY')
        action = '; '.join(errors) if errors else 'freeze with version and explicit human confirmation'
    else:
        errors = checks(p, g)
        action = '; '.join(errors) if errors else 'close-gate ' + g
    return dict(**s, next_action=action)


def handle(args, p):
    command = args.command
    if command == 'ingest':
        return ingest_files(p, inputs(args.inputs))
    if command == 'record-human':
        g = gate(args.gate_id)
        if g not in HUMAN_GATES:
            raise ValueError('human decisions are only needed at SCOPE and ROUTE')
        if not args.selected.strip() or not args.contribution.strip():
            raise ValueError('selected and contribution required; no minimum essay length')
        return append(p, 'human_decision', gate_id=g, selected=args.selected, contribution=args.contribution,
                     rationale=args.rationale, status=args.status, fingerprints=evidence(p, args.evidence))
    if command == 'record-review':
        g = gate(args.gate_id)
        if g not in REVIEW_GATES:
            raise ValueError('independent review only needed at RESULTS and DELIVERY')
        if not args.context_id.strip():
            raise ValueError('context-id required')
        fingerprints = evidence(p, args.evidence)
        if args.verdict == 'PASS' and not fingerprints:
            raise ValueError('PASS requires evidence')
        return append(p, 'review', gate_id=g, verdict=args.verdict, reviewer_context_id=args.context_id,
                     same_context_as_executor=args.self_review_only, fingerprints=fingerprints,
                     context=review_context(p, rows(p)), checks=args.check or [], notes=args.notes)
    if command == 'record-failure':
        fid = args.failure_id or uuid.uuid4().hex
        if fid in latest(rows(p), 'failure', 'failure_id'):
            raise ValueError('failure_id already exists')
        return append(p, 'failure', failure_id=fid, status='OPEN', description=args.description,
                     fingerprints=evidence(p, args.evidence))
    if command == 'close-failure':
        old = latest(rows(p), 'failure', 'failure_id').get(args.failure_id)
        if not old or old['status'] != 'OPEN':
            raise ValueError('failure not OPEN')
        return append(p, 'failure', failure_id=args.failure_id, status=args.status,
                      description=old['description'], fingerprints=evidence(p, args.evidence + [args.repair_ref]), notes=args.notes)
    if command == 'run':
        rid = args.run_id
        if rid in latest(rows(p), 'run', 'run_id'):
            raise ValueError('run_id already exists; use a new id for a rerun')
        argv = args.argv
        if argv and argv[0] == '--':
            argv = argv[1:]
        if not argv:
            raise ValueError('run requires argv after --')
        if args.timeout <= 0:
            raise ValueError('timeout must be positive')
        # New output paths prevent an old artifact being credited to a no-op run.
        for ref in args.output:
            rel = Path(ref)
            if rel.is_absolute() or '..' in rel.parts or not rel.parts or rel.parts[0] not in {'results', 'paper'}:
                raise ValueError('run outputs must be new files under results/ or paper/')
            if (p / rel).exists():
                raise ValueError('use a new output version: ' + ref)
        script_refs = list(args.input_ref)
        for token in argv:
            candidate = p / token
            if not Path(token).is_absolute() and candidate.is_file() and candidate.resolve().is_relative_to(p):
                script_refs.append(candidate.relative_to(p).as_posix())
        input_fingerprints = run_inputs(p, script_refs)
        try:
            proc = subprocess.run(argv, cwd=p, capture_output=True, text=True, errors='replace', timeout=args.timeout)
            console, code = proc.stdout + '\n' + proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            output = [part.decode('utf-8', errors='replace') if isinstance(part, bytes) else part or ''
                      for part in (exc.stdout, exc.stderr)]
            console, code = '\n'.join(output + [str(exc)]), None
        except OSError as exc:
            console, code = str(exc), None
        log = p / 'logs' / ('execution-' + uuid.uuid4().hex + '.txt')
        log.write_text(console, encoding='utf-8')
        success = code == 0
        try:
            fingerprints = evidence(p, args.output) if success else {}
            if run_inputs(p, script_refs) != input_fingerprints:
                raise ValueError('run inputs changed during execution; rerun with current inputs')
        except ValueError as exc:
            success, fingerprints = False, {}
            log.write_text(console + '\n' + str(exc), encoding='utf-8')
        return append(p, 'run', run_id=rid, status='SUCCEEDED' if success else 'FAILED',
                     argv=argv, exit_code=code, verified_execution=True, fingerprints=fingerprints,
                     input_fingerprints=input_fingerprints, tracks_code=True,
                     execution_log=log.relative_to(p).as_posix())
    if command in {'record-claim', 'approve-claim'}:
        events = rows(p)
        old = latest(events, 'claim', 'claim_id').get(args.claim_id)
        if command == 'approve-claim':
            if not old:
                raise ValueError('claim not found')
            data = {k: old[k] for k in ('claim_id', 'text', 'run_ids', 'fingerprints')}
            data.update(status='APPROVED', decision_ref=args.decision_ref, review_ref=args.review_ref)
        else:
            data = dict(claim_id=args.claim_id, text=args.text, run_ids=args.run_id,
                        fingerprints=evidence(p, args.evidence), status='DRAFT')
            if not data['fingerprints']:
                raise ValueError('claim needs evidence')
        trial = dict(schema_version='2.0', event_id='trial-' + uuid.uuid4().hex, type='claim', **data)
        # Validate this edit; stale sibling claims still block global acceptance.
        errors = check_claims(p, [e for e in events if e['type'] != 'claim'] + [trial])
        if errors:
            raise ValueError('; '.join(errors))
        return append(p, 'claim', **data)
    if command == 'close-gate':
        g = gate(args.gate_id)
        if state(p)['current_gate'] != g:
            raise ValueError('close only current gate: ' + state(p)['current_gate'])
        errors = checks(p, g)
        if errors:
            raise ValueError('; '.join(errors))
        return append(p, 'gate_closed', gate_id=g)
    if command == 'freeze':
        if state(p)['current_gate'] != 'FREEZE':
            raise ValueError('close all gates before freeze')
        errors = checks(p, 'DELIVERY')
        if errors:
            raise ValueError('; '.join(errors))
        if not args.confirmation.strip():
            raise ValueError('explicit human confirmation required')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', args.version):
            raise ValueError('version must be a simple directory name')
        release = p / 'releases' / args.version
        if release.exists():
            raise ValueError('release version already exists')
        staging = Path(tempfile.mkdtemp(prefix='.release-', dir=p / 'releases'))
        try:
            fingerprints = bundle(p)
            for ref in fingerprints:
                dest = staging / ref
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p / ref, dest)
            shutil.copy2(p / JOURNAL, staging / 'events.jsonl')
            if not unchanged(p, fingerprints) or not unchanged(staging, fingerprints):
                raise ValueError('files changed during freeze; retry review')
            files = {**fingerprints, 'events.jsonl': digest(staging / 'events.jsonl')}
            manifest = dict(algorithm='sha256', files=[dict(path=ref, sha256=sha) for ref, sha in files.items()])
            (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
            staging.replace(release)
            return append(p, 'freeze', version=args.version, confirmation=args.confirmation, fingerprints=files)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            shutil.rmtree(release, ignore_errors=True)
            raise
    if command == 'review-packet':
        output = p / 'reviews' / ('review-' + now().replace(':', '-') + '-' + uuid.uuid4().hex[:6] + '.zip')
        with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
            for ref in bundle(p):
                archive.write(p / ref, ref)
            archive.write(p / JOURNAL, 'events.jsonl')
        return dict(status='CREATED', packet=str(output))
    if command == 'reopen':
        target = project_path(args.new_project)
        if target == p or target.is_relative_to(p) or target.exists():
            raise ValueError('new-project must be a new directory outside the old project')
        shutil.copytree(p, target, ignore=shutil.ignore_patterns('releases', 'reviews', 'write.lock'))
        for d in ('releases', 'reviews'):
            (target / d).mkdir()
        append(target, 'reopened', source=str(p))
        return dict(status='REOPENED', project=str(target), **state(target))
    raise ValueError('unknown command')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    def sub(name):
        p = subs.add_parser(name)
        p.add_argument('project')
        return p
    p = sub('start')
    p.add_argument('--input', nargs='*', default=[])
    for name in ('status', 'validate', 'review-packet'):
        sub(name)
    p = sub('ingest')
    p.add_argument('inputs', nargs='+')
    p = sub('record-human')
    p.add_argument('--gate-id', required=True)
    p.add_argument('--selected', required=True)
    p.add_argument('--contribution', required=True)
    p.add_argument('--rationale', default='')
    p.add_argument('--evidence', action='append', default=[])
    p.add_argument('--status', choices=('APPROVED','REJECTED','DEFERRED'), default='APPROVED')
    p = sub('record-review')
    p.add_argument('--gate-id', required=True)
    p.add_argument('--verdict', choices=('PASS','REJECT','BLOCK','ESCALATE'), required=True)
    p.add_argument('--context-id', required=True)
    p.add_argument('--self-review-only', action='store_true')
    p.add_argument('--evidence', action='append', default=[])
    p.add_argument('--check', action='append')
    p.add_argument('--notes', default='')
    p = sub('record-failure')
    p.add_argument('--failure-id')
    p.add_argument('--description', required=True)
    p.add_argument('--evidence', action='append', default=[])
    p = sub('close-failure')
    p.add_argument('failure_id')
    p.add_argument('--repair-ref', required=True)
    p.add_argument('--evidence', action='append', default=[])
    p.add_argument('--status', choices=('FIXED','ACCEPTED_RISK'), default='FIXED')
    p.add_argument('--notes', default='')
    p = sub('run')
    p.add_argument('--run-id', required=True)
    p.add_argument('--output', action='append', required=True)
    p.add_argument('--input-ref', action='append', default=[])
    p.add_argument('--timeout', type=float, default=600)
    p = sub('record-claim')
    p.add_argument('--claim-id', required=True)
    p.add_argument('--text', required=True)
    p.add_argument('--evidence', action='append', required=True)
    p.add_argument('--run-id', action='append', required=True)
    p = sub('approve-claim')
    p.add_argument('--claim-id', required=True)
    p.add_argument('--decision-ref', required=True)
    p.add_argument('--review-ref', required=True)
    p = sub('close-gate')
    p.add_argument('--gate-id', required=True)
    p = sub('freeze')
    p.add_argument('--version', required=True)
    p.add_argument('--confirmation', required=True)
    p = sub('reopen')
    p.add_argument('new_project')
    raw = sys.argv[1:]
    argv = []
    if raw and raw[0] == 'run' and '--' in raw:
        split = raw.index('--')
        raw, argv = raw[:split], raw[split + 1:]
    args = parser.parse_args(raw)
    args.argv = argv
    try:
        if args.command == 'start':
            result = start(args)
        else:
            p = require_project(args.project)
            if args.command == 'status':
                result = status(p)
            elif args.command == 'validate':
                errors = check_claims(p, rows(p))
                if state(p)['frozen']:
                    errors.extend(checks(p, 'DELIVERY'))
                    frozen = [e for e in rows(p) if e['type'] == 'freeze'][-1]
                    release = p / 'releases' / frozen['version']
                    if not unchanged(release, frozen['fingerprints']):
                        errors.append('frozen snapshot changed or missing')
                result = dict(status='INVALID' if errors else 'VALID_RECORDS', errors=errors, **state(p))
            else:
                with locked(p):
                    if state(p)['frozen'] and args.command not in ('reopen', 'review-packet'):
                        raise ValueError('project frozen; use reopen with a new project directory')
                    result = handle(args, p)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2 if result.get('errors') or (args.command == 'run' and result.get('status') == 'FAILED') else 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
