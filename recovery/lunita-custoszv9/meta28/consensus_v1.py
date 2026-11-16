"""E15 consensus. Same model twice is not independence."""

from __future__ import annotations


def evaluate(validators: list[dict], evidence_digest: str) -> dict:
    if not validators or not evidence_digest:
        return {"status": "CONSENSUS_UNAVAILABLE", "reason": "MISSING_VALIDATORS_OR_DIGEST"}
    logics = set()
    for validator in validators:
        if validator.get("evidence_digest") != evidence_digest:
            return {"status": "CONSENSUS_UNAVAILABLE", "reason": "DIGEST_MISMATCH"}
        if validator.get("vote") != "ACCEPT":
            return {"status": "CONSENSUS_UNAVAILABLE", "reason": "NOT_UNANIMOUS"}
        logic = validator.get("decision_logic_id")
        runtime = validator.get("runtime_id")
        if not logic or not runtime:
            return {"status": "CONSENSUS_UNAVAILABLE", "reason": "IDENTITY_INCOMPLETE"}
        logics.add((logic, runtime))
    if len(logics) < 2:
        return {
            "status": "CONSENSUS_UNAVAILABLE",
            "reason": "VALIDATORS_NOT_INDEPENDENT",
        }
    return {
        "status": "CONSENSUS_UNANIMOUS",
        "validator_count": len(validators),
        "evidence_digest": evidence_digest,
    }
