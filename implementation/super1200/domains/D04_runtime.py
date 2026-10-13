"""D04 provenance primitives: deterministic, fail-closed building blocks.

This module implements only the behavior covered by its tests. It does not
close D04, mark capabilities EVIDENCED, or certify any capability.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
import re
from typing import Any
from urllib.parse import quote


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def content_id(value: Any) -> str:
    """Return a stable SHA-256 content address for JSON-compatible data."""
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def _sha256(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(field + "_must_be_lowercase_sha256_hex")
    return value


def universal_object_id(namespace: str, value: Any) -> str:
    """Create a deterministic, namespace-scoped ID without leaking object content."""
    if not isinstance(namespace, str) or not namespace.strip():
        raise ValueError("namespace_required")
    namespace = quote(namespace.strip(), safe=".-_")
    digest = hashlib.sha256(canonical_json(value)).hexdigest()
    return f"urn:louksna:object:{namespace}:sha256:{digest}"


@dataclass(frozen=True)
class ProvenanceNode:
    node_id: str
    kind: str
    subject: str
    input_hashes: tuple[str, ...]
    output_hash: str
    actor: str
    tool: str
    tool_version: str
    policy_version: str


class ProvenanceGraph:
    """Append-only, hash-addressed provenance DAG with cycle prevention."""

    def __init__(self) -> None:
        self._nodes: dict[str, ProvenanceNode] = {}
        self._edges: set[tuple[str, str]] = set()

    @property
    def nodes(self) -> tuple[ProvenanceNode, ...]:
        return tuple(self._nodes[k] for k in sorted(self._nodes))

    @property
    def edges(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(self._edges))

    def add(self, node: ProvenanceNode) -> None:
        if not node.node_id or not node.kind or not node.subject:
            raise ValueError("node_identity_required")
        if not node.actor or not node.tool or not node.tool_version or not node.policy_version:
            raise ValueError("provenance_fields_required")
        if not node.output_hash:
            raise ValueError("output_hash_required")
        if node.node_id in self._nodes:
            if self._nodes[node.node_id] != node:
                raise ValueError("immutable_node_conflict")
            return
        missing = [parent for parent in node.input_hashes if parent not in self._nodes]
        if missing:
            raise ValueError("unknown_provenance_parent:" + ",".join(missing))
        self._nodes[node.node_id] = node
        for parent in node.input_hashes:
            self._edges.add((parent, node.node_id))
        if self.has_cycle():
            del self._nodes[node.node_id]
            self._edges = {e for e in self._edges if e[1] != node.node_id}
            raise ValueError("provenance_cycle")

    def has_cycle(self) -> bool:
        adjacency: dict[str, list[str]] = {n: [] for n in self._nodes}
        for source, target in self._edges:
            adjacency[source].append(target)
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for child in adjacency.get(node, []):
                if visit(child):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        return any(visit(node) for node in sorted(adjacency) if node not in visited)

    def export(self) -> dict[str, Any]:
        nodes = [asdict(n) for n in self.nodes]
        edges = [list(e) for e in self.edges]
        return {
            "schema": "SUPER1200_D04_PROVENANCE_GRAPH/1",
            "nodes": nodes,
            "edges": edges,
            "graph_sha256": hashlib.sha256(canonical_json({
                "nodes": nodes, "edges": edges,
            })).hexdigest(),
        }


def to_w3c_prov(graph: ProvenanceGraph) -> dict[str, Any]:
    """Export a deterministic W3C PROV-JSON subset from a validated DAG."""
    if graph.has_cycle():
        raise ValueError("provenance_graph_must_be_acyclic")
    nodes = {node.node_id: node for node in graph.nodes}
    entity: dict[str, dict[str, Any]] = {}
    activity: dict[str, dict[str, Any]] = {}
    was_generated_by: dict[str, dict[str, str]] = {}
    used: dict[str, dict[str, str]] = {}
    for node in graph.nodes:
        entity_id = "urn:louksna:sha256:" + node.output_hash.removeprefix("sha256:")
        activity_id = "urn:louksna:activity:" + quote(node.node_id, safe=".-_")
        entity[entity_id] = {"prov:label": node.subject, "louksna:outputHash": node.output_hash}
        activity[activity_id] = {
            "prov:type": node.kind, "louksna:actor": node.actor,
            "louksna:tool": node.tool, "louksna:toolVersion": node.tool_version,
            "louksna:policyVersion": node.policy_version,
        }
        was_generated_by["_:generation_" + quote(node.node_id, safe=".-_")] = {
            "prov:entity": entity_id, "prov:activity": activity_id,
        }
        for parent_id in node.input_hashes:
            parent = nodes[parent_id]
            parent_entity = "urn:louksna:sha256:" + parent.output_hash.removeprefix("sha256:")
            used["_:usage_" + quote(parent_id, safe=".-_") + "_" + quote(node.node_id, safe=".-_")] = {
                "prov:activity": activity_id, "prov:entity": parent_entity,
            }
    return {
        "prefix": {"prov": "http://www.w3.org/ns/prov#", "louksna": "urn:louksna:"},
        "entity": entity, "activity": activity,
        "wasGeneratedBy": was_generated_by, "used": used,
    }


def to_intoto_statement(subject_name: str, subject_sha256: str,
                        predicate_type: str, predicate: dict[str, Any]) -> dict[str, Any]:
    """Create an in-toto Statement v1 envelope; signing is intentionally separate."""
    if not isinstance(subject_name, str) or not subject_name.strip():
        raise ValueError("subject_name_required")
    _sha256(subject_sha256, "subject_sha256")
    if not isinstance(predicate_type, str) or not predicate_type.startswith("https://"):
        raise ValueError("predicate_type_https_uri_required")
    if not isinstance(predicate, dict):
        raise ValueError("predicate_must_be_object")
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": subject_name, "digest": {"sha256": subject_sha256}}],
        "predicateType": predicate_type,
        "predicate": predicate,
    }


def to_slsa_provenance(*, builder_id: str, build_type: str, invocation_id: str,
                       source_uri: str, source_sha256: str,
                       started_on: str, finished_on: str,
                       external_parameters: dict[str, Any] | None = None,
                       byproducts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Create a minimal SLSA Provenance v1 predicate; this function does not sign it."""
    for value, field in ((builder_id, "builder_id"), (build_type, "build_type"),
                         (invocation_id, "invocation_id"), (source_uri, "source_uri"),
                         (started_on, "started_on"), (finished_on, "finished_on")):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(field + "_required")
    if not build_type.startswith("https://"):
        raise ValueError("build_type_https_uri_required")
    _sha256(source_sha256, "source_sha256")
    if external_parameters is not None and not isinstance(external_parameters, dict):
        raise ValueError("external_parameters_must_be_object")
    if byproducts is not None and not isinstance(byproducts, list):
        raise ValueError("byproducts_must_be_list")
    return {
        "buildDefinition": {
            "buildType": build_type,
            "externalParameters": external_parameters or {},
            "resolvedDependencies": [{
                "uri": source_uri, "digest": {"sha256": source_sha256},
            }],
        },
        "runDetails": {
            "builder": {"id": builder_id},
            "metadata": {
                "invocationId": invocation_id,
                "startedOn": started_on,
                "finishedOn": finished_on,
            },
            "byproducts": byproducts or [],
        },
    }


@dataclass(frozen=True)
class EvidenceKey:
    capability_id: int
    input_hash: str
    source_hash: str
    tool_version: str
    policy_version: str


@dataclass(frozen=True)
class EvidenceRecord:
    key: EvidenceKey
    output_hash: str
    evidence_hash: str
    validated: bool
    invalidated: bool = False


class EvidenceReuseIndex:
    """Exact-key evidence reuse; invalidated or unvalidated records never match."""

    def __init__(self) -> None:
        self._records: dict[EvidenceKey, EvidenceRecord] = {}

    def put(self, record: EvidenceRecord) -> None:
        if record.key.capability_id <= 0:
            raise ValueError("capability_id_must_be_positive")
        if not all((record.key.input_hash, record.key.source_hash,
                    record.key.tool_version, record.key.policy_version,
                    record.output_hash, record.evidence_hash)):
            raise ValueError("evidence_identity_incomplete")
        old = self._records.get(record.key)
        if old is not None and old != record:
            raise ValueError("evidence_key_conflict")
        self._records[record.key] = record

    def get_reusable(self, key: EvidenceKey) -> EvidenceRecord | None:
        record = self._records.get(key)
        if record is None or not record.validated or record.invalidated:
            return None
        return record

    def invalidate(self, key: EvidenceKey) -> None:
        record = self._records.get(key)
        if record is not None:
            self._records[key] = EvidenceRecord(
                key=record.key, output_hash=record.output_hash,
                evidence_hash=record.evidence_hash, validated=record.validated,
                invalidated=True,
            )


def validate_policy_document(document: Any) -> tuple[str, ...]:
    """Validate a small, explicit policy envelope; not a full JSON Schema engine."""
    errors: list[str] = []
    if not isinstance(document, dict):
        return ("policy_must_be_object",)
    if document.get("schema") != "SUPER1200_POLICY/1":
        errors.append("policy_schema_invalid")
    if not isinstance(document.get("policy_id"), str) or not document["policy_id"].strip():
        errors.append("policy_id_required")
    if not isinstance(document.get("version"), str) or not document["version"].strip():
        errors.append("policy_version_required")
    rules = document.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("policy_rules_required")
    elif any(not isinstance(rule, dict) or not isinstance(rule.get("id"), str)
             or not rule["id"].strip() for rule in rules):
        errors.append("policy_rule_identity_invalid")
    return tuple(errors)


def github_artifact_attestation(subject_name: str, subject_sha256: str,
                                predicate: dict[str, Any], *, issuer: str) -> dict[str, Any]:
    """Build a deterministic, unsigned attestation envelope; signing is external."""
    if not isinstance(issuer, str) or not issuer.strip():
        raise ValueError("issuer_required")
    statement = to_intoto_statement(
        subject_name, subject_sha256,
        "https://louksna.md/attestations/super1200/v1", predicate,
    )
    payload = canonical_json(statement)
    return {
        "schema": "SUPER1200_GITHUB_ATTESTATION_ENVELOPE/1",
        "issuer": issuer.strip(),
        "statement": statement,
        "statement_sha256": hashlib.sha256(payload).hexdigest(),
        "signature_status": "UNSIGNED_REQUIRES_GITHUB_ATTESTATION",
    }


def validate_sigstore_bundle(bundle: Any, *, expected_subject_sha256: str,
                             verifier: Any) -> dict[str, Any]:
    """Validate bundle shape and delegate cryptographic verification to a trusted verifier."""
    _sha256(expected_subject_sha256, "expected_subject_sha256")
    if not isinstance(bundle, dict):
        raise ValueError("sigstore_bundle_must_be_object")
    if bundle.get("mediaType") not in {
        "application/vnd.dev.sigstore.bundle+json;version=0.1",
        "application/vnd.dev.sigstore.bundle+json;version=0.2",
        "application/vnd.dev.sigstore.bundle+json;version=0.3",
    }:
        raise ValueError("sigstore_bundle_media_type_unsupported")
    if not callable(verifier):
        raise ValueError("trusted_signature_verifier_required")
    digest = bundle.get("subject", {}).get("sha256") if isinstance(bundle.get("subject"), dict) else None
    _sha256(digest, "bundle_subject_sha256")
    if digest != expected_subject_sha256:
        raise ValueError("sigstore_subject_digest_mismatch")
    if verifier(bundle) is not True:
        raise ValueError("sigstore_cryptographic_verification_failed")
    return {"status": "VERIFIED", "subject_sha256": digest,
            "bundle_sha256": hashlib.sha256(canonical_json(bundle)).hexdigest()}


def validate_rekor_entry(entry: Any, *, expected_subject_sha256: str,
                         inclusion_verifier: Any) -> dict[str, Any]:
    """Check Rekor entry identity and require an external inclusion-proof verifier."""
    _sha256(expected_subject_sha256, "expected_subject_sha256")
    if not isinstance(entry, dict):
        raise ValueError("rekor_entry_must_be_object")
    body = entry.get("body")
    log_index = entry.get("logIndex")
    integrated_time = entry.get("integratedTime")
    proof = entry.get("verification")
    if not isinstance(body, dict) or not isinstance(log_index, int) or log_index < 0:
        raise ValueError("rekor_entry_identity_invalid")
    if not isinstance(integrated_time, int) or integrated_time <= 0:
        raise ValueError("rekor_integrated_time_invalid")
    if not isinstance(proof, dict) or not proof:
        raise ValueError("rekor_inclusion_proof_required")
    if not callable(inclusion_verifier):
        raise ValueError("trusted_rekor_verifier_required")
    digest = body.get("subject_sha256")
    _sha256(digest, "rekor_subject_sha256")
    if digest != expected_subject_sha256:
        raise ValueError("rekor_subject_digest_mismatch")
    if inclusion_verifier(entry) is not True:
        raise ValueError("rekor_inclusion_verification_failed")
    return {"status": "VERIFIED", "log_index": log_index,
            "integrated_time": integrated_time,
            "entry_sha256": hashlib.sha256(canonical_json(entry)).hexdigest()}


def make_spdx_sbom(*, document_id: str, name: str,
                   packages: list[dict[str, Any]]) -> dict[str, Any]:
    """Create an SPDX 2.3 JSON SBOM from explicit, hash-bound package records."""
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("spdx_document_id_required")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("spdx_name_required")
    if not isinstance(packages, list):
        raise ValueError("spdx_packages_must_be_list")
    normalized = []
    seen = set()
    for item in packages:
        if not isinstance(item, dict):
            raise ValueError("spdx_package_must_be_object")
        pid, pname = item.get("SPDXID"), item.get("name")
        version, license_id, digest = item.get("versionInfo"), item.get("licenseConcluded"), item.get("sha256")
        if not all(isinstance(v, str) and v.strip() for v in (pid, pname, version, license_id)):
            raise ValueError("spdx_package_identity_or_license_required")
        if pid in seen:
            raise ValueError("spdx_package_id_duplicate")
        seen.add(pid)
        _sha256(digest, "spdx_package_sha256")
        normalized.append({
            "SPDXID": pid, "name": pname, "versionInfo": version,
            "downloadLocation": item.get("downloadLocation", "NOASSERTION"),
            "filesAnalyzed": False, "licenseConcluded": license_id,
            "licenseDeclared": item.get("licenseDeclared", license_id),
            "checksums": [{"algorithm": "SHA256", "checksumValue": digest}],
        })
    normalized.sort(key=lambda p: p["SPDXID"])
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": name,
        "documentNamespace": "https://louksna.md/spdx/" + quote(document_id.strip(), safe=".-_"),
        "creationInfo": {"creators": ["Tool: super1200-d04-runtime"], "created": "1970-01-01T00:00:00Z"},
        "packages": normalized,
    }


def make_cyclonedx_sbom(*, serial_number: str, components: list[dict[str, Any]]) -> dict[str, Any]:
    """Create deterministic CycloneDX 1.5 JSON inventory with SHA-256 component hashes."""
    if not isinstance(serial_number, str) or not serial_number.strip():
        raise ValueError("cyclonedx_serial_number_required")
    if not isinstance(components, list):
        raise ValueError("cyclonedx_components_must_be_list")
    normalized = []
    seen = set()
    for item in components:
        if not isinstance(item, dict):
            raise ValueError("cyclonedx_component_must_be_object")
        name, version, digest = item.get("name"), item.get("version"), item.get("sha256")
        if not all(isinstance(v, str) and v.strip() for v in (name, version)):
            raise ValueError("cyclonedx_component_identity_required")
        _sha256(digest, "cyclonedx_component_sha256")
        bom_ref = item.get("bom-ref") or f"{name}@{version}"
        if bom_ref in seen:
            raise ValueError("cyclonedx_bom_ref_duplicate")
        seen.add(bom_ref)
        component = {"type": item.get("type", "library"), "name": name, "version": version,
                     "bom-ref": bom_ref,
                     "hashes": [{"alg": "SHA-256", "content": digest}]}
        if item.get("licenses") is not None:
            if not isinstance(item["licenses"], list):
                raise ValueError("cyclonedx_licenses_must_be_list")
            component["licenses"] = item["licenses"]
        normalized.append(component)
    normalized.sort(key=lambda c: c["bom-ref"])
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "serialNumber": serial_number, "components": normalized}



def certification_non_transitive(*, certificate: dict[str, Any],
                                 subject_sha256: str,
                                 requested_scope: dict[str, Any]) -> bool:
    """Allow certification only for the exact attested subject and exact scope."""
    return certification_applies(certificate=certificate, subject_sha256=subject_sha256,
                                 requested_scope=requested_scope)


def evidence_is_current(*, validated_at_utc: str, expires_at_utc: str,
                        now_utc: str) -> bool:
    """Fail closed unless timestamps are timezone-aware and now is in [validation, expiry)."""
    from datetime import datetime, timezone
    def parse(value: str, field: str) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(field + "_required")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(field + "_invalid_iso8601") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(field + "_timezone_required")
        return parsed.astimezone(timezone.utc)
    validated = parse(validated_at_utc, "validated_at_utc")
    expires = parse(expires_at_utc, "expires_at_utc")
    now = parse(now_utc, "now_utc")
    if expires <= validated:
        raise ValueError("expiry_must_follow_validation")
    return validated <= now < expires


class EvidenceInvalidationGraph:
    """Append-only evidence dependency graph; invalidation propagates to descendants."""
    def __init__(self) -> None:
        self._dependencies: dict[str, set[str]] = {}

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._dependencies))

    def add_evidence(self, evidence_id: str) -> None:
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise ValueError("evidence_id_required")
        self._dependencies.setdefault(evidence_id, set())

    def add_dependency(self, source_id: str, dependent_id: str) -> None:
        if source_id not in self._dependencies or dependent_id not in self._dependencies:
            raise ValueError("unknown_evidence_dependency")
        if source_id == dependent_id or self._reachable(dependent_id, source_id):
            raise ValueError("evidence_dependency_cycle")
        self._dependencies[source_id].add(dependent_id)

    def _reachable(self, start: str, target: str) -> bool:
        pending, seen = [start], set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current in seen:
                continue
            seen.add(current)
            pending.extend(sorted(self._dependencies.get(current, ()), reverse=True))
        return False

    def invalidation_closure(self, evidence_id: str) -> tuple[str, ...]:
        if evidence_id not in self._dependencies:
            raise ValueError("unknown_evidence_id")
        pending, seen = [evidence_id], set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            pending.extend(sorted(self._dependencies[current], reverse=True))
        return tuple(sorted(seen))


def certification_scope_id(subject_sha256: str, scope: dict[str, Any]) -> str:
    """Bind certification identity to one exact subject digest and declared scope."""
    _sha256(subject_sha256, "subject_sha256")
    if not isinstance(scope, dict) or not scope:
        raise ValueError("certification_scope_required")
    return "urn:louksna:certification-scope:" + hashlib.sha256(
        canonical_json({"subject_sha256": subject_sha256, "scope": scope})
    ).hexdigest()


def certification_applies(*, certificate: dict[str, Any], subject_sha256: str,
                           requested_scope: dict[str, Any]) -> bool:
    """No transitive certification: only exact subject and exact scope can match."""
    _sha256(subject_sha256, "subject_sha256")
    if not isinstance(certificate, dict):
        return False
    if certificate.get("subject_sha256") != subject_sha256:
        return False
    scope = certificate.get("scope")
    if not isinstance(scope, dict):
        return False
    return canonical_json(scope) == canonical_json(requested_scope)



def minimal_recomputation_plan(graph: EvidenceInvalidationGraph, *,
                               invalidated_evidence_ids: list[str] | tuple[str, ...],
                               preservation_basis: dict[str, str]) -> dict[str, Any]:
    """Recompute invalidated nodes and descendants; require explicit reasons for preserved nodes."""
    if not isinstance(graph, EvidenceInvalidationGraph):
        raise ValueError("evidence_invalidation_graph_required")
    if not isinstance(invalidated_evidence_ids, (list, tuple)) or not invalidated_evidence_ids:
        raise ValueError("invalidated_evidence_ids_required")
    roots = list(invalidated_evidence_ids)
    if len(set(roots)) != len(roots):
        raise ValueError("duplicate_invalidated_evidence_id")
    known = set(graph.evidence_ids)
    if any(not isinstance(x, str) or x not in known for x in roots):
        raise ValueError("unknown_invalidated_evidence_id")
    recompute = set().union(*(set(graph.invalidation_closure(x)) for x in roots))
    preserved = known - recompute
    if not isinstance(preservation_basis, dict) or set(preservation_basis) != preserved:
        raise ValueError("preservation_basis_scope_mismatch")
    basis = {}
    for item in sorted(preserved):
        reason = preservation_basis[item]
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("preservation_basis_required:" + item)
        basis[item] = reason.strip()
    plan = {"schema":"SUPER1200_MINIMAL_RECOMPUTATION_PLAN/1",
            "invalidated_roots":sorted(roots),"recompute_ids":sorted(recompute),
            "preserved_ids":sorted(preserved),"preservation_basis":basis}
    plan["plan_sha256"] = hashlib.sha256(canonical_json(plan)).hexdigest()
    return plan


def evaluate_attestation_policy(policy: Any, attestation: Any, *,
                                expected_subject_sha256: str,
                                now_utc: str) -> dict[str, Any]:
    """Evaluate issuer, exact subject, predicate type, freshness and trusted verifier; deny on any gap."""
    _sha256(expected_subject_sha256, "expected_subject_sha256")
    if not isinstance(policy, dict) or policy.get("schema") != "SUPER1200_ATTESTATION_POLICY/1":
        raise ValueError("attestation_policy_schema_invalid")
    for key in ("policy_id","version","gate_id","predicate_type"):
        if not isinstance(policy.get(key), str) or not policy[key].strip():
            raise ValueError("attestation_policy_identity_invalid")
    issuers, verifiers, max_age = policy.get("acceptable_issuers"), policy.get("acceptable_verifiers"), policy.get("max_age_seconds")
    if not isinstance(issuers,list) or not issuers or not isinstance(verifiers,list) or not verifiers:
        raise ValueError("attestation_policy_trust_lists_invalid")
    if not isinstance(max_age,int) or isinstance(max_age,bool) or max_age <= 0:
        raise ValueError("attestation_policy_max_age_invalid")
    required_fields = policy.get("required_predicate_fields", [])
    if not isinstance(required_fields,list) or any(not isinstance(x,str) or not x for x in required_fields):
        raise ValueError("attestation_policy_predicate_fields_invalid")
    from datetime import datetime, timezone
    def stamp(value, field):
        if not isinstance(value,str) or not value.strip():
            raise ValueError(field+"_required")
        try: result=datetime.fromisoformat(value.replace("Z","+00:00"))
        except ValueError as exc: raise ValueError(field+"_invalid_iso8601") from exc
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError(field+"_timezone_required")
        return result.astimezone(timezone.utc)
    now=stamp(now_utc,"now_utc")
    reasons=[]
    if not isinstance(attestation,dict):
        return {"schema":"SUPER1200_ATTESTATION_POLICY_DECISION/1","decision":"DENY",
                "reasons":["attestation_must_be_object"],"policy_id":policy["policy_id"]}
    if attestation.get("issuer") not in issuers: reasons.append("issuer_not_accepted")
    statement=attestation.get("statement")
    if not isinstance(statement,dict): statement={}
    if statement.get("predicateType") != policy["predicate_type"]: reasons.append("predicate_type_not_accepted")
    predicate=statement.get("predicate")
    if not isinstance(predicate,dict): predicate={}
    for field in required_fields:
        if field not in predicate: reasons.append("required_predicate_field_missing:"+field)
    subjects=statement.get("subject")
    observed=None
    if not isinstance(subjects,list) or len(subjects)!=1 or not isinstance(subjects[0],dict):
        reasons.append("subject_identity_invalid")
    else:
        digest=subjects[0].get("digest")
        observed=digest.get("sha256") if isinstance(digest,dict) else None
        if observed != expected_subject_sha256: reasons.append("subject_digest_mismatch")
    try:
        age=(now-stamp(attestation.get("issued_at_utc"),"issued_at_utc")).total_seconds()
        if age < 0: reasons.append("attestation_issued_in_future")
        elif age > max_age: reasons.append("attestation_stale")
    except ValueError as exc: reasons.append(str(exc))
    verification=attestation.get("verification")
    if not isinstance(verification,dict) or verification.get("status")!="VERIFIED":
        reasons.append("cryptographic_verification_missing")
    elif verification.get("verifier_id") not in verifiers:
        reasons.append("verifier_not_trusted")
    return {"schema":"SUPER1200_ATTESTATION_POLICY_DECISION/1",
            "decision":"ALLOW" if not reasons else "DENY","reasons":reasons,
            "policy_id":policy["policy_id"],"policy_version":policy["version"],
            "gate_id":policy["gate_id"],"expected_subject_sha256":expected_subject_sha256,
            "observed_subject_sha256":observed,"predicate_type":statement.get("predicateType"),
            "issuer":attestation.get("issuer"),
            "cryptographic_verification_performed_by":verification.get("verifier_id")
                if isinstance(verification,dict) and verification.get("status")=="VERIFIED" else None}


class TransparencyLog:
    """Append-only hash chain with ordered sequence, causal parents, corrections and anchor metadata."""
    GENESIS_HASH = "0" * 64
    def __init__(self):
        self._entries = []
    @property
    def entries(self):
        return tuple(json.loads(canonical_json(x)) for x in self._entries)
    def append(self, *, event_id, event_type, actor, payload, timestamp_utc,
               causal_parents=(), correction_of=None):
        from datetime import datetime
        if any(not isinstance(x,str) or not x.strip() for x in (event_id,event_type,actor)):
            raise ValueError("transparency_event_identity_required")
        if any(x["event_id"]==event_id for x in self._entries):
            raise ValueError("transparency_event_id_immutable")
        if not isinstance(causal_parents,(list,tuple)) or len(set(causal_parents))!=len(causal_parents):
            raise ValueError("causal_parents_invalid")
        known={x["event_id"] for x in self._entries}
        if any(x not in known for x in causal_parents):
            raise ValueError("causal_parent_must_precede_event")
        try: stamp=datetime.fromisoformat(timestamp_utc.replace("Z","+00:00"))
        except (AttributeError,ValueError) as exc: raise ValueError("transparency_timestamp_invalid") from exc
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError("transparency_timestamp_timezone_required")
        if correction_of is not None and (correction_of not in known or correction_of not in causal_parents):
            raise ValueError("correction_target_must_be_causal_parent")
        unsigned={"schema":"SUPER1200_TRANSPARENCY_ENTRY/1","sequence":len(self._entries)+1,
                  "event_id":event_id,"event_type":event_type,"actor":actor.strip(),
                  "timestamp_utc":stamp.astimezone(__import__("datetime").timezone.utc).isoformat().replace("+00:00","Z"),
                  "causal_parents":list(causal_parents),"correction_of":correction_of,
                  "payload_sha256":hashlib.sha256(canonical_json(payload)).hexdigest(),
                  "previous_hash":self._entries[-1]["entry_hash"] if self._entries else self.GENESIS_HASH}
        entry=dict(unsigned); entry["entry_hash"]=hashlib.sha256(canonical_json(unsigned)).hexdigest()
        self._entries.append(entry)
        return json.loads(canonical_json(entry))
    @classmethod
    def verify_entries(cls, entries):
        if not isinstance(entries,(list,tuple)): return False
        seen=set(); previous=cls.GENESIS_HASH
        for i,entry in enumerate(entries,1):
            if not isinstance(entry,dict) or entry.get("schema")!="SUPER1200_TRANSPARENCY_ENTRY/1": return False
            if entry.get("sequence")!=i or entry.get("previous_hash")!=previous: return False
            event_id=entry.get("event_id")
            if not isinstance(event_id,str) or not event_id.strip() or event_id in seen: return False
            parents=entry.get("causal_parents")
            if not isinstance(parents,list) or any(x not in seen for x in parents): return False
            correction=entry.get("correction_of")
            if correction is not None and (correction not in seen or correction not in parents): return False
            try:
                _sha256(entry.get("payload_sha256"),"payload_sha256")
                _sha256(entry.get("entry_hash"),"entry_hash")
            except ValueError: return False
            unsigned=dict(entry); recorded=unsigned.pop("entry_hash")
            if hashlib.sha256(canonical_json(unsigned)).hexdigest()!=recorded: return False
            seen.add(event_id); previous=recorded
        return True
    def verify(self): return self.verify_entries(self._entries)
    def anchor(self):
        if not self.verify(): raise ValueError("transparency_log_integrity_failed")
        entries=self._entries
        anchor={"schema":"SUPER1200_TRANSPARENCY_ANCHOR/1","entry_count":len(entries),
                "first_sequence":entries[0]["sequence"] if entries else None,
                "last_sequence":entries[-1]["sequence"] if entries else None,
                "head_hash":entries[-1]["entry_hash"] if entries else self.GENESIS_HASH}
        anchor["anchor_sha256"]=hashlib.sha256(canonical_json(anchor)).hexdigest()
        return anchor


def reconcile_dual_ledgers(operational_records: Any, transparency_entries: Any) -> dict[str, Any]:
    """Cross-reference distinct operational and cryptographic ledgers without conflating them."""
    if not isinstance(operational_records,list) or not isinstance(transparency_entries,list):
        raise ValueError("dual_ledger_inputs_must_be_lists")
    if not TransparencyLog.verify_entries(transparency_entries):
        raise ValueError("transparency_ledger_integrity_failed")
    operational={}
    for item in operational_records:
        if not isinstance(item,dict) or item.get("schema")!="SUPER1200_OPERATIONAL_EVIDENCE/1":
            raise ValueError("operational_record_schema_invalid")
        eid,event_id,digest=item.get("evidence_id"),item.get("transparency_event_id"),item.get("payload_sha256")
        if not isinstance(eid,str) or not eid.strip(): raise ValueError("operational_evidence_id_required")
        if eid in operational: raise ValueError("operational_evidence_id_duplicate")
        if not isinstance(event_id,str) or not event_id.strip(): raise ValueError("transparency_event_reference_required")
        _sha256(digest,"operational_payload_sha256")
        operational[eid]=item
    transparency={x["event_id"]:x for x in transparency_entries}
    if len(transparency)!=len(transparency_entries): raise ValueError("transparency_event_id_duplicate")
    used=set(); refs=[]
    for eid in sorted(operational):
        item=operational[eid]; event_id=item["transparency_event_id"]
        if event_id not in transparency: raise ValueError("transparency_event_reference_missing")
        if event_id in used: raise ValueError("transparency_event_reference_reused")
        used.add(event_id)
        if item["payload_sha256"]!=transparency[event_id]["payload_sha256"]:
            raise ValueError("dual_ledger_payload_mismatch")
        refs.append({"evidence_id":eid,"transparency_event_id":event_id,"payload_sha256":item["payload_sha256"]})
    ops=[operational[k] for k in sorted(operational)]
    return {"schema":"SUPER1200_DUAL_LEDGER_RECONCILIATION/1","status":"RECONCILED",
            "operational_ledger_sha256":hashlib.sha256(canonical_json(ops)).hexdigest(),
            "transparency_ledger_sha256":hashlib.sha256(canonical_json(transparency_entries)).hexdigest(),
            "operational_record_count":len(ops),"transparency_entry_count":len(transparency_entries),
            "cross_references":refs,"ledgers_conflated":False}



def evaluate_policy_as_code(policy: Any, input_document: Any, provider_result: Any, *,
                            evaluated_at_utc: str) -> dict[str, Any]:
    """Produce a version-bound deterministic policy decision and audit receipt; provider has no authority."""
    from datetime import datetime, timezone
    if not isinstance(policy, dict) or policy.get("schema") != "SUPER1200_POLICY_AS_CODE/1":
        raise ValueError("policy_as_code_schema_invalid")
    for key in ("policy_id","version","engine","provider_version_pin","effective_from_utc","effective_until_utc"):
        if not isinstance(policy.get(key), str) or not policy[key].strip():
            raise ValueError("policy_as_code_identity_invalid:"+key)
    if policy["engine"] not in {"OPA_REGO","CUE","JSON_SCHEMA"}:
        raise ValueError("policy_as_code_engine_unsupported")
    def parse(value, field):
        try: dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        except (AttributeError,ValueError) as exc: raise ValueError(field+"_invalid_iso8601") from exc
        if dt.tzinfo is None or dt.utcoffset() is None: raise ValueError(field+"_timezone_required")
        return dt.astimezone(timezone.utc)
    now=parse(evaluated_at_utc,"evaluated_at_utc")
    start=parse(policy["effective_from_utc"],"effective_from_utc")
    end=parse(policy["effective_until_utc"],"effective_until_utc")
    if end<=start: raise ValueError("policy_effective_interval_invalid")
    policy_hash=hashlib.sha256(canonical_json(policy)).hexdigest()
    input_hash=hashlib.sha256(canonical_json(input_document)).hexdigest()
    reasons=[]
    if not start<=now<end: reasons.append("policy_not_effective")
    if not isinstance(provider_result,dict): reasons.append("provider_result_missing")
    else:
        if provider_result.get("input_sha256")!=input_hash: reasons.append("provider_input_binding_mismatch")
        if provider_result.get("policy_sha256")!=policy_hash: reasons.append("provider_policy_binding_mismatch")
        if provider_result.get("provider_version")!=policy["provider_version_pin"]: reasons.append("provider_version_pin_mismatch")
        if provider_result.get("provider_authority")!="NONE": reasons.append("provider_authority_must_be_none")
        if provider_result.get("sandboxed") is not True: reasons.append("provider_evaluation_not_sandboxed")
        if provider_result.get("deterministic") is not True: reasons.append("provider_determinism_not_attested")
        if provider_result.get("decision") not in {"ALLOW","DENY","UNKNOWN"}: reasons.append("provider_decision_invalid")
        if provider_result.get("decision")=="UNKNOWN": reasons.append("provider_decision_unknown_fail_closed")
    provider_hash=hashlib.sha256(canonical_json(provider_result)).hexdigest() if isinstance(provider_result,dict) else None
    decision="DENY" if reasons else provider_result["decision"]
    receipt={"schema":"SUPER1200_POLICY_AUDIT_RECEIPT/1","policy_id":policy["policy_id"],
        "policy_version":policy["version"],"engine":policy["engine"],"policy_sha256":policy_hash,
        "input_sha256":input_hash,"provider_result_sha256":provider_hash,"decision":decision,
        "reasons":reasons,"evaluated_at_utc":now.isoformat().replace("+00:00","Z"),
        "provider_authority":"NONE"}
    receipt["receipt_sha256"]=hashlib.sha256(canonical_json(receipt)).hexdigest()
    return receipt


def validate_opa_rego_result(result: Any, *, expected_input_sha256: str,
                             expected_policy_bundle_sha256: str,
                             pinned_version: str) -> dict[str, Any]:
    """Validate a sandboxed, version-pinned OPA/Rego result; the provider is never an authority."""
    _sha256(expected_input_sha256,"expected_input_sha256")
    _sha256(expected_policy_bundle_sha256,"expected_policy_bundle_sha256")
    if not isinstance(pinned_version,str) or not pinned_version.strip():
        raise ValueError("opa_pinned_version_required")
    if not isinstance(result,dict): raise ValueError("opa_result_must_be_object")
    checks={
        "provider_id":result.get("provider_id")=="opa-rego",
        "provider_version":result.get("provider_version")==pinned_version,
        "input_sha256":result.get("input_sha256")==expected_input_sha256,
        "policy_bundle_sha256":result.get("policy_bundle_sha256")==expected_policy_bundle_sha256,
        "sandboxed":result.get("sandboxed") is True,
        "provider_authority":result.get("provider_authority")=="NONE",
        "deterministic":result.get("deterministic") is True,
        "decision":result.get("decision") in {"ALLOW","DENY","UNKNOWN"},
    }
    failed=[key for key,value in checks.items() if not value]
    return {"schema":"SUPER1200_OPA_REGO_RESULT/1","status":"VALID" if not failed else "INVALID",
        "decision":result.get("decision") if not failed else "UNKNOWN","reasons":["invalid_"+x for x in failed],
        "provider_id":result.get("provider_id"),"provider_version":result.get("provider_version"),
        "input_sha256":result.get("input_sha256"),"policy_bundle_sha256":result.get("policy_bundle_sha256"),
        "provider_authority":"NONE","result_sha256":hashlib.sha256(canonical_json(result)).hexdigest()}


def validate_cue_provider_result(result: Any, *, expected_input_sha256: str,
                                 expected_schema_sha256: str,
                                 pinned_version: str) -> dict[str, Any]:
    """Validate CUE constraint results and require deterministic export with exact schema/input bindings."""
    _sha256(expected_input_sha256,"expected_input_sha256")
    _sha256(expected_schema_sha256,"expected_schema_sha256")
    if not isinstance(pinned_version,str) or not pinned_version.strip():
        raise ValueError("cue_pinned_version_required")
    if not isinstance(result,dict): raise ValueError("cue_result_must_be_object")
    errors=[]
    if result.get("provider_id")!="cue": errors.append("provider_id_mismatch")
    if result.get("provider_version")!=pinned_version: errors.append("provider_version_mismatch")
    if result.get("input_sha256")!=expected_input_sha256: errors.append("input_sha256_mismatch")
    if result.get("schema_sha256")!=expected_schema_sha256: errors.append("schema_sha256_mismatch")
    if result.get("provider_authority")!="NONE": errors.append("provider_authority_must_be_none")
    exported=result.get("exported_config")
    if not isinstance(exported,dict): errors.append("exported_config_must_be_object")
    export_hash=hashlib.sha256(canonical_json(exported)).hexdigest() if isinstance(exported,dict) else None
    if result.get("deterministic_export") is not True: errors.append("deterministic_export_not_attested")
    if result.get("export_sha256")!=export_hash: errors.append("export_hash_mismatch")
    if not isinstance(result.get("valid"),bool): errors.append("validity_result_required")
    provider_errors=result.get("errors",[])
    if not isinstance(provider_errors,list): errors.append("provider_errors_must_be_list")
    valid=(not errors and result.get("valid") is True and provider_errors==[])
    return {"schema":"SUPER1200_CUE_VALIDATION/1","status":"VALID" if valid else "INVALID",
        "valid":valid,"reasons":errors+([f"cue_constraint_error_count:{len(provider_errors)}"] if isinstance(provider_errors,list) and provider_errors else []),
        "input_sha256":result.get("input_sha256"),"schema_sha256":result.get("schema_sha256"),
        "export_sha256":export_hash,"provider_version":result.get("provider_version"),
        "provider_authority":"NONE","result_sha256":hashlib.sha256(canonical_json(result)).hexdigest()}


def validate_json_schema_provider_result(result: Any, *, expected_instance_sha256: str,
                                         expected_schema_sha256: str, dialect: str,
                                         pinned_version: str) -> dict[str, Any]:
    """Require pinned JSON Schema dialect/provider, strict unknown-field handling and a passing regression corpus."""
    _sha256(expected_instance_sha256,"expected_instance_sha256")
    _sha256(expected_schema_sha256,"expected_schema_sha256")
    if not isinstance(dialect,str) or not dialect.strip(): raise ValueError("json_schema_dialect_required")
    if not isinstance(pinned_version,str) or not pinned_version.strip(): raise ValueError("json_schema_pinned_version_required")
    if not isinstance(result,dict): raise ValueError("json_schema_result_must_be_object")
    reasons=[]
    if result.get("provider_id")!="json-schema": reasons.append("provider_id_mismatch")
    if result.get("provider_version")!=pinned_version: reasons.append("provider_version_mismatch")
    if result.get("dialect")!=dialect: reasons.append("schema_dialect_mismatch")
    if result.get("instance_sha256")!=expected_instance_sha256: reasons.append("instance_sha256_mismatch")
    if result.get("schema_sha256")!=expected_schema_sha256: reasons.append("schema_sha256_mismatch")
    if result.get("provider_authority")!="NONE": reasons.append("provider_authority_must_be_none")
    if result.get("strict_unknown_fields") is not True: reasons.append("strict_unknown_field_policy_required")
    unknown=result.get("unknown_fields",[])
    errors=result.get("errors",[])
    if not isinstance(unknown,list): reasons.append("unknown_fields_must_be_list"); unknown=[]
    if not isinstance(errors,list): reasons.append("validation_errors_must_be_list"); errors=[]
    corpus=result.get("regression_corpus")
    if not isinstance(corpus,dict) or corpus.get("passed") is not True or not isinstance(corpus.get("tests_total"),int) or corpus.get("tests_total")<=0 or corpus.get("tests_passed")!=corpus.get("tests_total"):
        reasons.append("regression_corpus_not_passed")
    if unknown: reasons.append("unknown_fields_rejected")
    if errors: reasons.append("schema_validation_errors_present")
    if result.get("valid") is not True: reasons.append("instance_not_valid")
    valid=not reasons
    return {"schema":"SUPER1200_JSON_SCHEMA_VALIDATION/1","status":"VALID" if valid else "INVALID",
        "valid":valid,"reasons":reasons,"dialect":result.get("dialect"),
        "instance_sha256":result.get("instance_sha256"),"schema_sha256":result.get("schema_sha256"),
        "provider_version":result.get("provider_version"),"regression_corpus":corpus,
        "provider_authority":"NONE","result_sha256":hashlib.sha256(canonical_json(result)).hexdigest()}



def run_policy_test_suite(policy: Any, cases: Any, *, evaluator: Any) -> dict[str, Any]:
    """Require positive, negative, bypass, conflict and UNKNOWN cases; repeated decisions must be deterministic."""
    if not isinstance(policy,dict) or not isinstance(policy.get("policy_id"),str) or not isinstance(policy.get("version"),str):
        raise ValueError("policy_test_suite_identity_required")
    if not isinstance(cases,list) or not callable(evaluator):
        raise ValueError("policy_test_suite_cases_and_evaluator_required")
    expected={"positive":"ALLOW","negative":"DENY","bypass":"DENY","conflict":"DENY","unknown":"DENY"}
    seen=set(); categories=set(); results=[]; errors=[]
    for case in cases:
        if not isinstance(case,dict): raise ValueError("policy_test_case_must_be_object")
        cid,category=case.get("case_id"),case.get("category")
        if not isinstance(cid,str) or not cid.strip() or cid in seen: raise ValueError("policy_test_case_id_invalid")
        if category not in expected: raise ValueError("policy_test_case_category_invalid")
        seen.add(cid); categories.add(category)
        try:
            first=evaluator(policy,case.get("input"))
            second=evaluator(policy,case.get("input"))
            if not isinstance(first,dict) or first.get("decision") not in {"ALLOW","DENY","UNKNOWN"}:
                raise ValueError("policy_test_decision_invalid")
            if canonical_json(first)!=canonical_json(second):
                raise ValueError("policy_test_decision_nondeterministic")
            raw=first["decision"]
            normalized="DENY" if raw=="UNKNOWN" else raw
            passed=normalized==expected[category] and (category!="unknown" or raw=="UNKNOWN")
            result={"case_id":cid,"category":category,"raw_decision":raw,
                    "effective_decision":normalized,"expected_decision":expected[category],
                    "deterministic":True,"result":"PASS" if passed else "FAIL"}
            if not passed: errors.append("policy_case_expectation_failed:"+cid)
        except Exception as exc:
            result={"case_id":cid,"category":category,"result":"FAIL","error":type(exc).__name__+":"+str(exc)}
            errors.append("policy_case_evaluation_failed:"+cid)
        results.append(result)
    missing=sorted(set(expected)-categories)
    if missing: errors.append("policy_test_categories_missing:"+",".join(missing))
    receipt={"schema":"SUPER1200_POLICY_TEST_RECEIPT/1","policy_id":policy["policy_id"],
        "policy_version":policy["version"],"policy_sha256":hashlib.sha256(canonical_json(policy)).hexdigest(),
        "case_count":len(cases),"categories_seen":sorted(categories),"missing_categories":missing,
        "results":results,"errors":errors,"status":"PASS" if not errors and len(results)>0 else "FAIL"}
    receipt["receipt_sha256"]=hashlib.sha256(canonical_json(receipt)).hexdigest()
    return receipt


def make_policy_version_record(*, policy_id: str, version: str, policy_document: dict[str, Any],
                               effective_from_utc: str, effective_until_utc: str,
                               supersedes: str | None = None) -> dict[str, Any]:
    """Create a deterministic, hash-bound policy version record with explicit effective interval and supersession."""
    from datetime import datetime, timezone
    if not isinstance(policy_id,str) or not policy_id.strip() or not isinstance(version,str) or not version.strip():
        raise ValueError("policy_version_identity_required")
    if not isinstance(policy_document,dict) or policy_document.get("policy_id")!=policy_id or str(policy_document.get("version"))!=version:
        raise ValueError("policy_document_identity_mismatch")
    def parse(value,field):
        try: dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        except (AttributeError,ValueError) as exc: raise ValueError(field+"_invalid_iso8601") from exc
        if dt.tzinfo is None or dt.utcoffset() is None: raise ValueError(field+"_timezone_required")
        return dt.astimezone(timezone.utc)
    start=parse(effective_from_utc,"effective_from_utc"); end=parse(effective_until_utc,"effective_until_utc")
    if end<=start: raise ValueError("policy_effective_interval_invalid")
    record={"schema":"SUPER1200_POLICY_VERSION/1","policy_id":policy_id,"version":version,
        "policy_sha256":hashlib.sha256(canonical_json(policy_document)).hexdigest(),
        "policy_document":policy_document,"effective_from_utc":start.isoformat().replace("+00:00","Z"),
        "effective_until_utc":end.isoformat().replace("+00:00","Z"),"supersedes":supersedes}
    record["record_sha256"]=hashlib.sha256(canonical_json(record)).hexdigest()
    return record


def validate_policy_version_history(records: Any) -> dict[str, Any]:
    """Validate version identity, content hashes, non-overlapping intervals and acyclic supersession chains."""
    from datetime import datetime
    if not isinstance(records,list) or not records: raise ValueError("policy_version_history_required")
    by_key={}; parsed={}
    def stamp(value,field):
        try: dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        except (AttributeError,ValueError) as exc: raise ValueError(field+"_invalid_iso8601") from exc
        if dt.tzinfo is None or dt.utcoffset() is None: raise ValueError(field+"_timezone_required")
        return dt
    for record in records:
        if not isinstance(record,dict) or record.get("schema")!="SUPER1200_POLICY_VERSION/1":
            raise ValueError("policy_version_record_schema_invalid")
        pid,version=record.get("policy_id"),record.get("version")
        if not isinstance(pid,str) or not pid.strip() or not isinstance(version,str) or not version.strip():
            raise ValueError("policy_version_identity_invalid")
        key=pid+"@"+version
        if key in by_key: raise ValueError("policy_version_duplicate")
        doc=record.get("policy_document")
        if not isinstance(doc,dict) or doc.get("policy_id")!=pid or str(doc.get("version"))!=version:
            raise ValueError("policy_version_document_identity_mismatch")
        if record.get("policy_sha256")!=hashlib.sha256(canonical_json(doc)).hexdigest():
            raise ValueError("policy_version_content_hash_mismatch")
        unsigned=dict(record); recorded=unsigned.pop("record_sha256",None)
        if recorded!=hashlib.sha256(canonical_json(unsigned)).hexdigest():
            raise ValueError("policy_version_record_hash_mismatch")
        start,end=stamp(record.get("effective_from_utc"),"effective_from_utc"),stamp(record.get("effective_until_utc"),"effective_until_utc")
        if end<=start: raise ValueError("policy_effective_interval_invalid")
        by_key[key]=record; parsed[key]=(start,end)
    for key,record in by_key.items():
        predecessor=record.get("supersedes")
        same=[k for k in by_key if k.startswith(record["policy_id"]+"@") and k!=key]
        if predecessor is not None:
            if predecessor not in by_key or by_key[predecessor]["policy_id"]!=record["policy_id"] or predecessor==key:
                raise ValueError("policy_supersession_target_invalid")
            if parsed[predecessor][1]>parsed[key][0]:
                raise ValueError("policy_supersession_interval_overlap")
        elif same and any(parsed[k][0]<parsed[key][0] for k in same):
            raise ValueError("policy_supersession_link_required")
    for pid in sorted({r["policy_id"] for r in records}):
        keys=sorted((k for k in by_key if by_key[k]["policy_id"]==pid),key=lambda k:parsed[k][0])
        for left,right in zip(keys,keys[1:]):
            if parsed[left][1]>parsed[right][0]: raise ValueError("policy_version_intervals_overlap")
    return {"schema":"SUPER1200_POLICY_VERSION_HISTORY_VALIDATION/1","status":"PASS",
        "record_count":len(records),"policy_versions":sorted(by_key),
        "history_sha256":hashlib.sha256(canonical_json([by_key[k] for k in sorted(by_key)])).hexdigest()}


def semantic_policy_diff(old_policy: Any, new_policy: Any) -> dict[str, Any]:
    """Compare policy rules by canonical meaning and enumerate affected claims, tests and authorizations."""
    if not isinstance(old_policy,dict) or not isinstance(new_policy,dict):
        raise ValueError("policy_diff_documents_required")
    if old_policy.get("schema")!="SUPER1200_POLICY_AS_CODE/1" or new_policy.get("schema")!="SUPER1200_POLICY_AS_CODE/1":
        raise ValueError("policy_diff_schema_invalid")
    if old_policy.get("policy_id")!=new_policy.get("policy_id"):
        raise ValueError("policy_diff_identity_mismatch")
    def index(policy):
        rules=policy.get("rules")
        if not isinstance(rules,list): raise ValueError("policy_rules_must_be_list")
        result={}
        for rule in rules:
            if not isinstance(rule,dict) or not isinstance(rule.get("id"),str) or not rule["id"].strip():
                raise ValueError("policy_rule_identity_invalid")
            if rule["id"] in result: raise ValueError("policy_rule_id_duplicate")
            result[rule["id"]]=rule
        return result
    old,new=index(old_policy),index(new_policy)
    old_ids,new_ids=set(old),set(new)
    added=sorted(new_ids-old_ids); removed=sorted(old_ids-new_ids)
    changed=sorted(k for k in old_ids&new_ids if canonical_json(old[k])!=canonical_json(new[k]))
    unchanged=sorted((old_ids&new_ids)-set(changed))
    affected=sorted(set(added+removed+changed))
    def values(key):
        collected=set()
        for rid in affected:
            for rule in (old.get(rid),new.get(rid)):
                if not isinstance(rule,dict): continue
                vals=rule.get(key,[])
                if not isinstance(vals,list) or any(not isinstance(x,str) or not x.strip() for x in vals):
                    raise ValueError("policy_rule_dependency_list_invalid:"+key)
                collected.update(vals)
        return sorted(collected)
    metadata={"schema","policy_id","version","rules","effective_from_utc","effective_until_utc"}
    old_settings={k:v for k,v in old_policy.items() if k not in metadata}
    new_settings={k:v for k,v in new_policy.items() if k not in metadata}
    report={"schema":"SUPER1200_SEMANTIC_POLICY_DIFF/1","policy_id":old_policy["policy_id"],
        "old_version":old_policy.get("version"),"new_version":new_policy.get("version"),
        "added_rule_ids":added,"removed_rule_ids":removed,"changed_rule_ids":changed,
        "unchanged_rule_ids":unchanged,"affected_decision_rules":affected,
        "affected_claims":values("claims"),"affected_tests":values("tests"),
        "affected_authorizations":values("authorizations"),
        "policy_settings_changed":canonical_json(old_settings)!=canonical_json(new_settings)}
    report["diff_sha256"]=hashlib.sha256(canonical_json(report)).hexdigest()
    return report


def analyze_policy_impact(policy_diff: Any, rule_dependencies: Any,
                          evidence_graph: EvidenceInvalidationGraph) -> dict[str, Any]:
    """Resolve reverse dependencies from changed rules to claims/tests/authorizations and causal evidence invalidation."""
    if not isinstance(policy_diff,dict) or policy_diff.get("schema")!="SUPER1200_SEMANTIC_POLICY_DIFF/1":
        raise ValueError("semantic_policy_diff_required")
    if not isinstance(rule_dependencies,dict) or not isinstance(evidence_graph,EvidenceInvalidationGraph):
        raise ValueError("policy_dependency_map_and_evidence_graph_required")
    rules=policy_diff.get("affected_decision_rules")
    if not isinstance(rules,list) or any(not isinstance(x,str) or not x for x in rules):
        raise ValueError("affected_decision_rules_invalid")
    claims=set(); tests=set(); auths=set(); roots=set()
    for rule_id in rules:
        dep=rule_dependencies.get(rule_id)
        if not isinstance(dep,dict): raise ValueError("policy_dependency_mapping_required:"+rule_id)
        for key,target in (("claims",claims),("tests",tests),("authorizations",auths),("evidence_ids",roots)):
            values=dep.get(key,[])
            if not isinstance(values,list) or any(not isinstance(x,str) or not x.strip() for x in values):
                raise ValueError("policy_dependency_list_invalid:"+rule_id+":"+key)
            target.update(values)
    known=set(evidence_graph.evidence_ids)
    if roots-known: raise ValueError("policy_impact_unknown_evidence_dependency")
    invalidated=set()
    for root in roots: invalidated.update(evidence_graph.invalidation_closure(root))
    impact={"schema":"SUPER1200_POLICY_IMPACT_ANALYSIS/1","status":"PASS",
        "policy_id":policy_diff.get("policy_id"),"policy_diff_sha256":policy_diff.get("diff_sha256"),
        "affected_decision_rules":sorted(rules),"affected_claims":sorted(claims),
        "affected_tests":sorted(tests),"affected_authorizations":sorted(auths),
        "invalidated_evidence_ids":sorted(invalidated),
        "preserved_evidence_ids":sorted(known-invalidated),
        "invalidation_basis":{x:"Causal descendant of evidence dependency of an affected policy rule." for x in sorted(invalidated)}}
    impact["impact_sha256"]=hashlib.sha256(canonical_json(impact)).hexdigest()
    return impact
