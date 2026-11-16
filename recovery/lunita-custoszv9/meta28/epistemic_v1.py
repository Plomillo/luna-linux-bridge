"""Epistemic state machine for LUNITA-META-28. Fail closed.

DECLARED != EVIDENCE != VALIDATION != INDEPENDENT_VALIDATION != CERTIFICATION.
"""

from __future__ import annotations

ALLOWED = (
    "DECLARED",
    "IMPLEMENTED",
    "EVIDENCED",
    "VALIDATED",
    "INDEPENDENTLY_VALIDATED",
    "CERTIFIED",
    "ACTIVE",
)

# Adjacent promotions only. No jump to CERTIFIED or ACTIVE.
_NEXT = {
    "DECLARED": "IMPLEMENTED",
    "IMPLEMENTED": "EVIDENCED",
    "EVIDENCED": "VALIDATED",
    "VALIDATED": "INDEPENDENTLY_VALIDATED",
    "INDEPENDENTLY_VALIDATED": "CERTIFIED",
    "CERTIFIED": "ACTIVE",
    "ACTIVE": None,
}


class EpistemicError(Exception):
    pass


def promote(current: str, target: str, *, independent_validation: bool) -> str:
    if current not in ALLOWED or target not in ALLOWED:
        raise EpistemicError("UNKNOWN_STATE")
    if target == current:
        return current
    if _NEXT[current] != target:
        raise EpistemicError("FORBIDDEN_TRANSITION")
    if target == "CERTIFIED" and not independent_validation:
        raise EpistemicError("VALIDATED_TO_CERTIFIED_WITHOUT_INDEPENDENT_VALIDATION")
    if target == "ACTIVE" and current != "CERTIFIED":
        raise EpistemicError("ACTIVE_WITHOUT_REQUIRED_EVIDENCE")
    return target
