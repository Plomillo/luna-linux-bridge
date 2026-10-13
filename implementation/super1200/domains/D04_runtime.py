"""D04 provenance primitives: concrete, deterministic building blocks.

This module intentionally implements only the primitives covered by its tests.
It does not mark the D04 domain complete or certify any capability.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from typing import Any, Iterable


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def content_id(value: Any) -> str:
    """Return a stable SHA-256 content address for JSON-compatible data."""
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


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
        return {
            "schema": "SUPER1200_D04_PROVENANCE_GRAPH/1",
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [list(e) for e in self.edges],
            "graph_sha256": hashlib.sha256(canonical_json({
                "nodes": [asdict(n) for n in self.nodes],
                "edges": [list(e) for e in self.edges],
            })).hexdigest(),
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
    """Validate a small, explicit policy envelope; this is not a full JSON Schema engine."""
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
