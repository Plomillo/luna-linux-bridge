#!/usr/bin/env python3
"""Read-only discovery of CP references; never infers the canonical inventory."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

CP_PATTERN = re.compile(r"\bCP[-_ ]?(\d{1,3})\b", re.IGNORECASE)
SKIP_PARTS = {".git", ".venv", "node_modules", "__pycache__", "vendor"}
TEXT_SUFFIXES = {".md", ".txt", ".rst", ".yml", ".yaml", ".json", ".toml", ".py", ".sh"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json-output", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    hits: dict[str, list[dict[str, object]]] = {}
    source_candidates: list[str] = []
    read_errors: list[dict[str, str]] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            read_errors.append({"path": rel.as_posix(), "error": str(exc)})
            continue
        if re.search(r"canonical|acceptance|criterio|specification|especificaci[oó]n|registro|inventory|inventario", rel.as_posix(), re.I):
            source_candidates.append(rel.as_posix())
        for line_no, line in enumerate(text.splitlines(), 1):
            for match in CP_PATTERN.finditer(line):
                cp_id = f"CP-{int(match.group(1)):02d}"
                hits.setdefault(cp_id, []).append({
                    "path": rel.as_posix(),
                    "line": line_no,
                    "text": line.strip()[:400],
                })

    ids = sorted(hits, key=lambda value: int(value.split("-")[1]))
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip() or "unavailable"
    report = [
        "# CP reference discovery — NOT a canonical certification register",
        "",
        f"- Repository revision: {revision}",
        f"- Distinct CP identifiers observed in scanned text files: {len(ids)}",
        f"- Read errors: {len(read_errors)}",
        "",
        "## Fail-closed interpretation",
        "",
        "This report records textual references only. Mentions in workflow files, logs, examples, or cross-references do not prove that an identifier is a canonical CP or establish its order, requirements, completion, G23, or G24 status.",
        "The canonical inventory is unresolved until a repository source explicitly defining the complete ordered CP set and original acceptance criteria is located and validated. No missing IDs are inferred.",
        "",
        "## Observed identifiers",
        "",
    ]
    if ids:
        report.extend([f"- **{cp_id}** — {len(hits[cp_id])} reference(s)" for cp_id in ids])
    else:
        report.append("- No CP identifiers found in scanned text files.")
    report.extend(["", "## Candidate source files to inspect", ""])
    report.extend([f"- {item}" for item in source_candidates] or ["- None detected by filename/path heuristic."])
    report.extend(["", "## Evidence references", ""])
    for cp_id in ids:
        report.extend([f"### {cp_id}", ""])
        for item in hits[cp_id][:30]:
            report.append(f"- {item['path']}:{item['line']} — {item['text']}")
        if len(hits[cp_id]) > 30:
            report.append(f"- Additional references omitted from this summary: {len(hits[cp_id]) - 30}")
        report.append("")
    if read_errors:
        report.extend(["## Read errors", ""])
        report.extend([f"- {item['path']}: {item['error']}" for item in read_errors])

    payload = {
        "classification": "REFERENCE_DISCOVERY_NOT_CANONICAL_INVENTORY",
        "canonical_inventory_confirmed": False,
        "certification_granted": False,
        "g23": "NOT_GRANTED",
        "g24": "NOT_GRANTED",
        "observed_cp_ids": ids,
        "reference_counts": {key: len(value) for key, value in hits.items()},
        "source_candidates": source_candidates,
        "read_errors": read_errors,
        "references": hits,
    }
    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    json_out = root / args.json_output
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Observed {len(ids)} distinct CP identifiers; canonical inventory remains unconfirmed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
