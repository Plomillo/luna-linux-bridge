#!/usr/bin/env python3
"""Create a deterministic, redacted, repository-wide tracked-file census for CP-01."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

SECRET_RULES = (
    ("github_token", re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{30,})\b")),
    ("aws_access_key", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key_header", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("openai_style_key", re.compile(rb"\bsk-[A-Za-z0-9_-]{32,}\b")),
    ("credential_assignment", re.compile(rb"(?i)\b(?:api[_-]?key|access[_-]?token|password|client[_-]?secret)\b\s*[:=]\s*['\"][^'\"]{16,}['\"]")),
)
TEXT_EXTENSIONS = {
    ".py", ".pyi", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".rs", ".go",
    ".java", ".kt", ".c", ".h", ".cc", ".cpp", ".hpp", ".sh", ".bash", ".ps1",
    ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".conf", ".md", ".txt",
    ".html", ".css", ".scss", ".xml", ".sql", ".lock", ".gitignore", ".dockerfile",
}


def git(root: pathlib.Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).stdout


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_file(root: pathlib.Path, relative: str) -> tuple[dict, list[dict]]:
    path = root / relative
    try:
        info = path.lstat()
    except OSError as exc:
        return ({
            "path": relative, "state": "MISSING_OR_UNREADABLE",
            "error_type": type(exc).__name__, "sha256": None,
            "size_bytes": None, "line_count": None, "kind": "unknown",
        }, [])

    if path.is_symlink():
        target = os.readlink(path)
        raw = os.fsencode(target)
        return ({
            "path": relative, "state": "PRESENT", "kind": "symlink",
            "symlink_target": target, "size_bytes": len(raw),
            "sha256": sha256_bytes(raw), "line_count": None,
        }, [])

    if not path.is_file():
        return ({
            "path": relative, "state": "PRESENT", "kind": "non_regular",
            "size_bytes": info.st_size, "sha256": None, "line_count": None,
        }, [])

    digest = hashlib.sha256()
    size = 0
    nul_found = False
    first = b""
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            if not first:
                first = chunk[:8192]
            if b"\x00" in chunk:
                nul_found = True
            digest.update(chunk)
            size += len(chunk)

    text_candidate = not nul_found and (
        path.suffix.lower() in TEXT_EXTENSIONS or path.name.lower() in {".gitignore", "dockerfile", "makefile"}
        or (first and first[:4] != b"\x7fELF" and b"\x00" not in first)
    )
    line_count = None
    findings = []
    if text_candidate:
        line_count = 0
        try:
            with path.open("rb") as stream:
                for line_number, raw_line in enumerate(stream, 1):
                    line_count = line_number
                    for rule, pattern in SECRET_RULES:
                        if pattern.search(raw_line):
                            findings.append({
                                "path": relative, "line": line_number, "rule": rule,
                                "evidence": "MATCH_REDACTED",
                            })
        except OSError as exc:
            findings.append({
                "path": relative, "line": None, "rule": "read_error",
                "evidence": type(exc).__name__,
            })

    return ({
        "path": relative,
        "state": "PRESENT",
        "kind": "text" if text_candidate else "binary_or_nontext",
        "size_bytes": size,
        "sha256": digest.hexdigest(),
        "line_count": line_count,
        "executable": bool(info.st_mode & 0o111),
    }, findings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path("evidence/zona-directiva-v03"))
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    output.mkdir(parents=True, exist_ok=True)

    paths = sorted(os.fsdecode(item) for item in git(root, "ls-files", "-z").split(b"\x00") if item)
    manifest_path = output / "CP-01-repository-census.jsonl"
    findings = []
    totals = {"tracked_files": len(paths), "present_files": 0, "missing_files": 0,
              "text_files": 0, "binary_or_nontext_files": 0, "symlinks": 0,
              "total_bytes": 0, "total_lines": 0}
    manifest_hash = hashlib.sha256()
    with manifest_path.open("wb") as manifest:
        for relative in paths:
            row, row_findings = inspect_file(root, relative)
            encoded = (json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            manifest.write(encoded)
            manifest_hash.update(encoded)
            findings.extend(row_findings)
            if row["state"] == "PRESENT":
                totals["present_files"] += 1
                totals["total_bytes"] += row.get("size_bytes") or 0
                if row["kind"] == "text":
                    totals["text_files"] += 1
                    totals["total_lines"] += row.get("line_count") or 0
                elif row["kind"] == "binary_or_nontext":
                    totals["binary_or_nontext_files"] += 1
                elif row["kind"] == "symlink":
                    totals["symlinks"] += 1
            else:
                totals["missing_files"] += 1

    report = {
        "schema": "louksna.repository-forensic-census.v1",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repository": os.environ.get("GITHUB_REPOSITORY"),
        "ref": os.environ.get("GITHUB_REF"),
        "commit_sha": os.environ.get("GITHUB_SHA"),
        "scope": "all Git-tracked files at the exact checkout commit",
        "method": "per-file SHA-256, byte count, text line census, executable/symlink classification, redacted high-confidence credential-pattern scan",
        "totals": totals,
        "manifest_path": manifest_path.name,
        "manifest_sha256": manifest_hash.hexdigest(),
        "credential_pattern_findings": findings,
        "credential_values_emitted": False,
        "untracked_files_included": False,
        "independent_validation": "NOT_PERFORMED",
        "certified": False,
        "status": "HOLD" if totals["missing_files"] or any(x["rule"] in {"github_token", "aws_access_key", "private_key_header", "openai_style_key"} for x in findings) else "PASS_WITH_SCOPE_LIMITS",
        "limits": [
            "The census hashes all tracked files but does not claim semantic correctness for every line.",
            "Credential-pattern matches are redacted indicators and require human triage; absence of matches is not proof that no secret exists.",
            "Repository settings and hosted runtime state are outside the checked-out source tree.",
            "This census is not independent validation or certification."
        ],
    }
    summary_path = output / "CP-01-repository-census-summary.json"
    summary_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["status"] == "HOLD" else 0


if __name__ == "__main__":
    raise SystemExit(main())
