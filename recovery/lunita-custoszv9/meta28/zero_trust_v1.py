"""Zero trust execution rule. Any failed mandatory control denies execution."""

from __future__ import annotations

CONTROLS = (
    "IDENTITY_CHECK",
    "AUTHORIZATION_CHECK",
    "INPUT_VALIDATION",
    "INTEGRITY_CHECK",
    "POLICY_EVALUATION",
    "OUTPUT_VALIDATION",
    "PROVENANCE_RECORD",
)


def authorize(checks: dict) -> dict:
    failed = [name for name in CONTROLS if checks.get(name) is not True]
    if failed:
        return {"decision": "DENY_EXECUTION", "failed_controls": failed}
    return {"decision": "ALLOW_EXECUTION", "failed_controls": []}
