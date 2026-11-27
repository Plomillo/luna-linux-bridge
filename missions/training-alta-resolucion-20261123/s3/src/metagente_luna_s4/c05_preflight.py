"""Source-bound preflight blocker for cases without a complete executable plan.

This module records a genuine BLOCKED outcome before invoking the case operation.
It must never be used to label an unattempted operation as PASS.
"""
from __future__ import annotations


def blocked_preflight_probe(
    case_id: str, blocker_code: str, phase: str, details: str,
) -> dict:
    if not case_id.startswith("MGL5-INF-"):
        raise ValueError("preflight blocker only accepts canonical INF case IDs")
    if phase not in {"NORMAL_PLAN", "NEGATIVE_CONTROL", "BOUNDARY_CONTROL"}:
        raise ValueError("invalid preflight phase")
    if not blocker_code or not details:
        raise ValueError("a specific blocker code and explanation are required")
    return {
        "blocked": True,
        "case_id": case_id,
        "blocker_code": blocker_code,
        "phase": phase,
        "operation_invoked": False,
        "details": details,
    }
