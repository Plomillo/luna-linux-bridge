"""Case record helper. Status is never implied by the helper."""
from __future__ import annotations


def pack(domain: str, level: int, objective: str, inp: dict, facts: dict, good: bool, unlock: str = "", limits: str = "") -> dict:
    if unlock:
        status = "BLOCKED"
    elif good:
        status = "PASS_FUNCTIONAL"
    else:
        status = "FAIL"
    return {
        "domain": domain,
        "level": level,
        "objective": objective,
        "input": inp,
        "facts": facts,
        "status": status,
        "unlock": unlock,
        "limits": limits,
    }
