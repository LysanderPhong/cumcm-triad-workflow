#!/usr/bin/env python3
"""Find possible identifying text in files; never redact or rewrite input.

Built-in heuristics flag institution/name/region labels and absolute paths.
Supply --term or --terms-file for real school, person, region and username
strings: arbitrary names cannot be reliably inferred by regex. PDF reading uses
optional pypdf. Missing pypdf, encrypted PDFs, extraction errors or blank pages
produce INCOMPLETE rather than a pass. No OCR or image/embedded-file inspection
is performed; visually inspect logos, scanned text and PDF attachments yourself.
Exit codes: 0 NO_FINDINGS, 1 FINDINGS, 2 INCOMPLETE_OR_INVALID.
NO_FINDINGS means no configured text pattern matched, not certified anonymity.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import re
import sys


TEXT_SUFFIXES = {
    ".txt", ".md", ".tex", ".json", ".jsonl", ".csv", ".tsv", ".yaml", ".yml",
    ".log", ".html", ".htm", ".bib", ".rst", ".py", ".m", ".js", ".mjs",
    ".c", ".cpp", ".h", ".r", ".ipynb",
}
PATTERNS = [
    ("chinese_institution", re.compile(r"[\u4e00-\u9fff]{2,24}(?:大学|学院|中学|学校)")),
    ("english_institution", re.compile(r"\b[A-Z][A-Za-z.&'-]*(?:[ \t]+[A-Za-z.&'-]+){0,5}[ \t]+(?:University|College|School)\b", re.I)),
    ("identity_label", re.compile(r"(?:姓名|队员|参赛者|指导教师|指导老师|学校|院校|赛区|用户名|学号)[ \t]*[:：][ \t]*[^\n\r,，;；]{1,60}")),
    ("contest_region", re.compile(r"[\u4e00-\u9fff]{2,10}赛区")),
    ("english_identity_label", re.compile(r"\b(?:student[ _-]?name|full[ _-]?name|username|student[ _-]?id|institution|region)[ \t]*:[ \t]*[^\r\n,;]{1,60}", re.I)),
    ("windows_absolute_path", re.compile(r"(?<!\w)[A-Za-z]:[\\/][^\s<>\"'，。；）)]+|\\\\[^\s\\]+\\[^\s<>\"']+")),
    ("unix_absolute_path", re.compile(r"(?<![\w:/])/(?:[A-Za-z0-9_.~@-]+/)*[A-Za-z0-9_.~@-]+")),
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
]


def scan_text(text: str, source: str, location: str, patterns: list[tuple]) -> list[dict]:
    findings = []
    for rule, pattern in patterns:
        for match in pattern.finditer(text):
            findings.append({"file": source, "location": location, "line": text.count("\n", 0, match.start()) + 1,
                             "rule": rule, "match": match.group(0)})
    return findings


def pdf_text(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    try:
        pypdf = importlib.import_module("pypdf")
    except ImportError:
        return [], ["PDF extraction unavailable: install optional pypdf in this interpreter, or extract text separately and scan it; PDF remains unverified"]
    chunks = []
    errors = []
    try:
        reader = pypdf.PdfReader(str(path))
        if reader.is_encrypted:
            return [], ["Encrypted PDF was not inspected"]
        metadata = reader.metadata
        if metadata:
            chunks.append(("metadata", "\n".join(f"{key.lstrip('/')}: {value}" for key, value in metadata.items())))
            if metadata.get("/Author"):
                chunks.append(("metadata author", f"Full name: {metadata['/Author']}"))
        if not reader.pages:
            errors.append("PDF has no pages")
        for number, page in enumerate(reader.pages, 1):
            try:
                text = page.extract_text() or ""
                if not text.strip():
                    errors.append(f"page {number}: no extractable text; OCR/visual review is required")
                else:
                    chunks.append((f"page {number}", text))
            except Exception as exc:
                errors.append(f"page {number}: extraction error: {exc}")
        # Attached files are outside page-text scanning and may reveal identity.
        names = reader.trailer["/Root"].get("/Names", {})
        if hasattr(names, "get_object"):
            names = names.get_object()
        if names and "/EmbeddedFiles" in names:
            errors.append("PDF has embedded files; attached content was not inspected")
    except Exception as exc:
        errors.append(f"PDF read error: {exc}")
    return chunks, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", type=Path, help="files or directories to scan (directories recurse over supported text/PDF extensions)")
    parser.add_argument("--term", action="append", default=[], help="additional literal identity string; repeat for each person/school/region/username")
    parser.add_argument("--terms-file", type=Path, help="UTF-8 identity strings, one per line; blank lines and # comments ignored")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ is required")
    report: dict = {"status": "INCOMPLETE_OR_INVALID", "scanned_files": [], "findings": [], "errors": [],
                   "limitations": ["Regex findings require human judgment; arbitrary names need --term/--terms-file", "No OCR, logo, image or embedded-file identity inspection", "NO_FINDINGS is not an anonymity certification"]}
    terms = list(args.term)
    try:
        if args.terms_file:
            terms.extend(line.strip() for line in args.terms_file.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#"))
    except (OSError, UnicodeError) as exc:
        report["errors"].append({"file": str(args.terms_file), "error": str(exc)})
    patterns = PATTERNS + [("provided_identity_term", re.compile(re.escape(term), re.I)) for term in sorted(set(terms)) if term]
    files: list[Path] = []
    seen = set()
    for requested in args.paths:
        try:
            path = requested.expanduser()
            if path.is_symlink():
                raise ValueError("symlinks are not followed; pass the intended real file explicitly")
            if not path.exists():
                raise ValueError("path does not exist")
            if path.is_dir():
                candidates = sorted(item for item in path.rglob("*") if item.suffix.lower() in TEXT_SUFFIXES | {".pdf"})
            else:
                candidates = [path]
            if not candidates:
                raise ValueError("no supported files found")
            for item in candidates:
                if item.is_symlink():
                    report["errors"].append({"file": str(item), "error": "symlink not inspected"})
                    continue
                resolved = item.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    files.append(item)
        except (OSError, ValueError, RuntimeError) as exc:
            report["errors"].append({"file": str(requested), "error": str(exc)})
    for path in files:
        source = str(path)
        chunks = []
        errors = []
        try:
            if path.suffix.lower() == ".pdf":
                chunks, errors = pdf_text(path)
            elif path.suffix.lower() in TEXT_SUFFIXES:
                chunks = [("text", path.read_text(encoding="utf-8-sig"))]
            else:
                errors = ["unsupported extension; no content inspected"]
        except (OSError, UnicodeError) as exc:
            errors = [str(exc)]
        for location, content in chunks:
            report["findings"].extend(scan_text(content, source, location, patterns))
        report["scanned_files"].append({"file": source, "extracted_sections": len(chunks), "complete_text_extraction": not errors})
        report["errors"].extend({"file": source, "error": error} for error in errors)
    if not files:
        report["errors"].append({"error": "no files were inspected"})
    if report["errors"]:
        code = 2
    elif report["findings"]:
        report["status"], code = "FINDINGS", 1
    else:
        report["status"], code = "NO_FINDINGS", 0
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
