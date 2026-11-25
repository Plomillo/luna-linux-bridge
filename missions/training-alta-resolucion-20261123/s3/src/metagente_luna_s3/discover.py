"""Fixture discovery against a path index. A keyword is not a finding."""
from __future__ import annotations


def discover(case_id: str, operation: str, paths: list[str]) -> dict:
    keyword = "laboratorio" in operation.lower()
    case_paths = [path for path in paths if case_id in path]
    elf_paths = [path for path in paths if path.endswith(".elf")]
    if case_paths:
        result = "FIXTURE_FOUND"
    elif keyword:
        result = "FIXTURE_NOT_IN_TREE"
    else:
        result = "NOT_A_LAB_REFERENCE"
    return {
        "case_id": case_id,
        "paths_checked": len(paths),
        "keyword_hit": keyword,
        "keyword_is_evidence": False,
        "case_paths": case_paths,
        "elf_paths": elf_paths,
        "result": result,
    }
