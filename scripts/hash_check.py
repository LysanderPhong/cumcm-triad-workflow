#!/usr/bin/env python3
"""Verify a trusted SHA-256 manifest; never create or update the manifest.

Manifest JSON format:
  {"algorithm":"sha256","files":[{"path":"paper/main.pdf","sha256":"64 hex digits"}]}
Paths are relative to --root (default: the manifest's directory). Absolute
paths, traversal, duplicate entries and symlink components are rejected before
any content is hashed. Only use for authorized integrity/version verification.
Matching hashes establish byte identity, not mathematical or semantic validity.
Exit codes: 0 MATCH, 1 MISMATCH, 2 INVALID_OR_INCOMPLETE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import sys


def unique_keys(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_manifest(manifest: Path, root: Path) -> list[tuple[str, Path, str]]:
    data = json.loads(manifest.read_text(encoding="utf-8"), object_pairs_hook=unique_keys)
    if not isinstance(data, dict) or set(data) != {"algorithm", "files"} or data["algorithm"] != "sha256":
        raise ValueError("manifest must contain exactly algorithm='sha256' and files")
    if not isinstance(data["files"], list) or not data["files"]:
        raise ValueError("files must be a non-empty list")
    if not root.is_dir():
        raise ValueError("root must be an existing directory")
    seen = set()
    items = []
    for index, entry in enumerate(data["files"], 1):
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise ValueError(f"entry {index}: expected exactly path and sha256")
        name, digest = entry["path"], entry["sha256"]
        if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
            raise ValueError(f"entry {index}: invalid relative POSIX path")
        path = PurePosixPath(name)
        if path.is_absolute() or PureWindowsPath(name).drive or ".." in path.parts or path == PurePosixPath("."):
            raise ValueError(f"entry {index}: absolute/traversal/empty path is forbidden")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError(f"entry {index}: sha256 must contain 64 hexadecimal characters")
        target = root.joinpath(*path.parts)
        cursor = root
        for part in path.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ValueError(f"entry {index}: symlink components are forbidden")
        resolved = target.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise ValueError(f"entry {index}: resolved path escapes root")
        if not resolved.is_file():
            raise ValueError(f"entry {index}: target is not a regular file")
        if resolved in seen:
            raise ValueError(f"entry {index}: duplicate target")
        seen.add(resolved)
        items.append((name, resolved, digest.lower()))
    return items


def check_file(target: Path) -> str:
    # One SHA-256 computation per listed file; no secondary fingerprint.
    with target.open("rb") as stream:
        # fstat checks the opened file, avoiding a second content read.
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("opened target is not a regular file")
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        after = os.fstat(stream.fileno())
        current = target.stat()
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, key) != getattr(after, key) or getattr(after, key) != getattr(current, key) for key in fields):
            raise ValueError("target changed while being checked")
        return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", required=True, type=Path, help="trusted manifest JSON; this file is read only")
    parser.add_argument("--root", type=Path, help="allowed file root; defaults to manifest directory")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ is required")
    report = {"status": "INVALID_OR_INCOMPLETE", "files": [], "errors": [], "scope": "byte identity only"}
    try:
        manifest = args.manifest.expanduser().resolve(strict=True)
        root = (args.root.expanduser() if args.root else manifest.parent).resolve(strict=True)
        items = load_manifest(manifest, root)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        report["errors"].append(str(exc))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2
    for name, target, expected in items:
        try:
            actual = check_file(target)
            report["files"].append({"path": name, "expected": expected, "actual": actual,
                                    "match": actual == expected})
        except (OSError, ValueError) as exc:
            report["errors"].append({"path": name, "error": str(exc)})
    if report["errors"]:
        code = 2
    elif all(item["match"] for item in report["files"]):
        report["status"], code = "MATCH", 0
    else:
        report["status"], code = "MISMATCH", 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
