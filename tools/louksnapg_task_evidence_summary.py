"""Fail-closed counting for task-adapter execution versus semantic quality.

A successful process exit is not a quality pass. The release report deliberately
records both counts so a caller cannot infer task correctness from execution alone.
"""
from __future__ import annotations

from typing import Any, Iterable


def summarize_task_results(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Return independent execution and semantic-quality counts for task rows."""
    execution_success_count = 0
    quality_pass_count = 0

    for row in rows:
        if not isinstance(row, dict):
            continue

        execution_ok = (
            row.get("status") == "PASS_FUNCTIONAL_EXECUTION"
            and isinstance(row.get("exit_code"), int)
            and not isinstance(row.get("exit_code"), bool)
            and row.get("exit_code") == 0
        )
        if execution_ok:
            execution_success_count += 1

        quality = row.get("quality_acceptance")
        if not isinstance(quality, dict):
            quality = row.get("quality_check")
        semantic_ok = (
            execution_ok
            and isinstance(quality, dict)
            and quality.get("status") == "PASS"
        )
        if semantic_ok:
            quality_pass_count += 1

    return {
        "execution_success_count": execution_success_count,
        "quality_pass_count": quality_pass_count,
        # Compatibility alias: "pass_count" means quality passed, never just executed.
        "pass_count": quality_pass_count,
    }
