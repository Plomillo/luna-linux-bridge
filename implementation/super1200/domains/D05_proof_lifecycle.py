"""D05 proof-lifecycle primitives for capabilities 133-136.
Fail-closed descriptors only. No theorem claims. No global certification.
"""
from __future__ import annotations
import hashlib, json, re
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

def canonical_json(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def digest(v: Any) -> str:
    return hashlib.sha256(canonical_json(v)).hexdigest()

def _name(v: Any, f: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f + "_required")
    return v.strip()

def _sha(v: Any, f: str) -> str:
    if not isinstance(v, str) or not _SHA256.fullmatch(v):
        raise ValueError(f + "_must_be_lowercase_sha256")
    return v

def invalidate_proof_closure(*, graph_sha256: str, changed_node_ids: list[str], invalidated_all: list[str]) -> dict[str, Any]:
    _sha(graph_sha256, "graph_sha256")
    if not isinstance(changed_node_ids, list) or not isinstance(invalidated_all, list):
        raise ValueError("invalidation_lists_required")
    changed = sorted({_name(x, "changed_node_id") for x in changed_node_ids})
    all_ids = sorted({_name(x, "invalidated_id") for x in invalidated_all})
    if not set(changed).issubset(set(all_ids)):
        raise ValueError("changed_must_be_subset_of_invalidated")
    out = {
        "schema": "SUPER1200_PROOF_INVALIDATION/1",
        "graph_sha256": graph_sha256,
        "changed": changed,
        "invalidated_all": all_ids,
        "decision": "INVALIDATION_CLOSURE_RECORDED",
        "theorem_claim": False,
        "certification_granted": False,
    }
    out["invalidation_sha256"] = digest(out)
    return out

def build_proof_carrying_artifact(*, artifact_id: str, proof_term_sha256: str, source_sha256: str, claim_scope: str) -> dict[str, Any]:
    artifact_id = _name(artifact_id, "artifact_id")
    claim_scope = _name(claim_scope, "claim_scope")
    _sha(proof_term_sha256, "proof_term_sha256")
    _sha(source_sha256, "source_sha256")
    if claim_scope == "GLOBAL":
        raise ValueError("proof_carrying_artifact_must_not_claim_global")
    out = {
        "schema": "SUPER1200_PROOF_CARRYING_ARTIFACT/1",
        "artifact_id": artifact_id,
        "proof_term_sha256": proof_term_sha256,
        "source_sha256": source_sha256,
        "claim_scope": claim_scope,
        "decision": "PROOF_BOUND_TO_ARTIFACT_DESCRIPTOR",
        "theorem_claim": False,
        "global_certification": False,
    }
    out["carrying_sha256"] = digest(out)
    return out

def bind_proof_carrying_configuration(*, config_id: str, config_sha256: str, proof_artifact_sha256: str) -> dict[str, Any]:
    config_id = _name(config_id, "config_id")
    _sha(config_sha256, "config_sha256")
    _sha(proof_artifact_sha256, "proof_artifact_sha256")
    out = {
        "schema": "SUPER1200_PROOF_CARRYING_CONFIGURATION/1",
        "config_id": config_id,
        "config_sha256": config_sha256,
        "proof_artifact_sha256": proof_artifact_sha256,
        "decision": "CONFIG_BOUND_TO_PROOF_DESCRIPTOR",
        "theorem_claim": False,
        "global_certification": False,
    }
    out["binding_sha256"] = digest(out)
    return out

def record_proof_carrying_migration(*, migration_id: str, from_sha256: str, to_sha256: str, proof_artifact_sha256: str) -> dict[str, Any]:
    migration_id = _name(migration_id, "migration_id")
    _sha(from_sha256, "from_sha256")
    _sha(to_sha256, "to_sha256")
    _sha(proof_artifact_sha256, "proof_artifact_sha256")
    if from_sha256 == to_sha256:
        raise ValueError("migration_requires_distinct_states")
    out = {
        "schema": "SUPER1200_PROOF_CARRYING_MIGRATION/1",
        "migration_id": migration_id,
        "from_sha256": from_sha256,
        "to_sha256": to_sha256,
        "proof_artifact_sha256": proof_artifact_sha256,
        "decision": "MIGRATION_BOUND_TO_PROOF_DESCRIPTOR",
        "theorem_claim": False,
        "global_certification": False,
    }
    out["migration_sha256"] = digest(out)
    return out
