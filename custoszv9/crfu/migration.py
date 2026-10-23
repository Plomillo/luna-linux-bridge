"""Evidence-bound runtime checks for a declared migration invariant.

The checker validates artifact identities and supplied invariant/proof evidence.
It does not claim to prove arbitrary Python migration functions universally.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import re
from typing import Any


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class MigrationWitness:
    source_version: str
    target_version: str
    source_artifact_sha256: str
    target_artifact_sha256: str
    invariant_id: str
    invariant_proof_sha256: str
    proof_status: str
    producer_identity: str
    verifier_identity: str
    rollback_artifact_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest_is_valid(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def validate_migration_witness(
    witness: MigrationWitness,
    source_artifact: bytes,
    target_artifact: bytes,
    *,
    source_invariant_holds: bool,
    target_invariant_holds: bool,
) -> dict[str, Any]:
    """Validate endpoint binding, independent review, rollback and one invariant.

    PASS means that the stated witness matches these exact bytes and declared
    invariant checks. It is not a transferable certificate or a proof of every
    possible input to the migration algorithm.
    """
    if not isinstance(witness, MigrationWitness):
        return {
            "status": "HOLD",
            "reason": "MIGRATION_WITNESS_INVALID",
            "certification_propagation": False,
            "authority_transfer": False,
        }
    fields = (
        witness.source_artifact_sha256,
        witness.target_artifact_sha256,
        witness.invariant_proof_sha256,
        witness.rollback_artifact_sha256,
    )
    if not all(_digest_is_valid(item) for item in fields):
        return {
            "status": "HOLD",
            "reason": "MIGRATION_DIGEST_INVALID",
            "certification_propagation": False,
            "authority_transfer": False,
        }
    if not isinstance(witness.source_version, str) or not witness.source_version.strip():
        return {"status":"HOLD","reason":"MIGRATION_SOURCE_VERSION_MISSING",
                "certification_propagation":False,"authority_transfer":False}
    if not isinstance(witness.target_version, str) or not witness.target_version.strip():
        return {"status":"HOLD","reason":"MIGRATION_TARGET_VERSION_MISSING",
                "certification_propagation":False,"authority_transfer":False}
    if witness.source_version == witness.target_version:
        return {"status":"FAIL","reason":"MIGRATION_VERSIONS_NOT_DISTINCT",
                "certification_propagation":False,"authority_transfer":False}
    if not isinstance(witness.invariant_id, str) or not witness.invariant_id.strip():
        return {"status":"HOLD","reason":"MIGRATION_INVARIANT_UNBOUND",
                "certification_propagation":False,"authority_transfer":False}
    if witness.proof_status != "VERIFIED":
        return {"status":"HOLD","reason":"MIGRATION_PROOF_NOT_VERIFIED",
                "certification_propagation":False,"authority_transfer":False}
    if (
        not isinstance(witness.producer_identity, str)
        or not witness.producer_identity.strip()
        or not isinstance(witness.verifier_identity, str)
        or not witness.verifier_identity.strip()
        or witness.producer_identity == witness.verifier_identity
    ):
        return {"status":"HOLD","reason":"MIGRATION_REQUIRES_INDEPENDENT_VERIFIER",
                "certification_propagation":False,"authority_transfer":False}
    if hashlib.sha256(source_artifact).hexdigest() != witness.source_artifact_sha256:
        return {"status":"FAIL","reason":"MIGRATION_SOURCE_ARTIFACT_MISMATCH",
                "certification_propagation":False,"authority_transfer":False}
    if hashlib.sha256(target_artifact).hexdigest() != witness.target_artifact_sha256:
        return {"status":"FAIL","reason":"MIGRATION_TARGET_ARTIFACT_MISMATCH",
                "certification_propagation":False,"authority_transfer":False}
    if source_invariant_holds is not True:
        return {"status":"HOLD","reason":"MIGRATION_SOURCE_INVARIANT_NOT_ESTABLISHED",
                "certification_propagation":False,"authority_transfer":False}
    if target_invariant_holds is not True:
        return {"status":"FAIL","reason":"MIGRATION_TARGET_INVARIANT_FAILED",
                "certification_propagation":False,"authority_transfer":False}

    return {
        "status": "PASS_FOR_DECLARED_INVARIANT",
        "reason": None,
        "source_version": witness.source_version,
        "target_version": witness.target_version,
        "source_artifact_sha256": witness.source_artifact_sha256,
        "target_artifact_sha256": witness.target_artifact_sha256,
        "invariant_id": witness.invariant_id,
        "invariant_proof_sha256": witness.invariant_proof_sha256,
        "rollback_artifact_sha256": witness.rollback_artifact_sha256,
        "invariant_witness_validated": True,
        "universal_migration_refinement_proven": False,
        "certification_propagation": False,
        "authority_transfer": False,
    }
