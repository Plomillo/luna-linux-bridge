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
