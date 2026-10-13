"""D04 policy governance primitives for capabilities 105-108.

This extension is deliberately separate from D04_runtime.py so the already
certified 93-104 source hashes remain stable. It performs no certification.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from domains.D04_runtime import (
    EvidenceInvalidationGraph,
    canonical_json,
    validate_policy_document,
)


_REQUIRED_CATEGORIES = {"positive", "negative", "bypass", "conflict", "unknown"}
_VALID_DECISIONS = {"ALLOW", "DENY", "UNKNOWN"}


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + "_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(field + "_invalid_iso8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(field + "_timezone_required")
    return parsed.astimezone(timezone.utc)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def run_policy_test_suite(policy: Any, cases: Any, evaluator: Any) -> dict[str, Any]:
    """Run mandatory positive/negative/bypass/conflict/UNKNOWN cases fail-closed.

    The evaluator is injected so test harnesses can exercise real policy engines
    without this suite pretending to implement OPA/CUE or a signature verifier.
    """
    policy_errors = validate_policy_document(policy)
    if policy_errors:
        raise ValueError("policy_document_invalid:" + ",".join(policy_errors))
    if not isinstance(cases, list) or not cases:
        raise ValueError("policy_test_cases_required")
    if not callable(evaluator):
        raise ValueError("policy_evaluator_required")
    seen: set[str] = set()
    categories: set[str] = set()
    results: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("policy_test_case_must_be_object")
        case_id = case.get("case_id")
        category = case.get("category")
        expected = case.get("expected_decision")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("policy_test_case_id_required")
        if case_id in seen:
            raise ValueError("policy_test_case_id_duplicate")
        seen.add(case_id)
        if category not in _REQUIRED_CATEGORIES:
            raise ValueError("policy_test_case_category_invalid:" + case_id)
        categories.add(category)
        if expected not in _VALID_DECISIONS:
            raise ValueError("policy_test_expected_decision_invalid:" + case_id)
        if category == "positive" and expected != "ALLOW":
            raise ValueError("positive_case_must_expect_allow:" + case_id)
        if category in {"negative", "bypass", "conflict"} and expected != "DENY":
            raise ValueError("deny_case_expected_decision_invalid:" + case_id)
        if category == "unknown" and expected not in {"UNKNOWN", "DENY"}:
            raise ValueError("unknown_case_must_fail_closed:" + case_id)
        case_input = case.get("input")
        input_hash = _digest(case_input)
        exception_type = None
        try:
            outcome = evaluator(policy, case_input)
            observed = outcome.get("decision") if isinstance(outcome, dict) else None
            if observed not in _VALID_DECISIONS:
                observed = "UNKNOWN"
        except Exception as exc:  # fail closed and preserve only the exception type
            observed = "UNKNOWN"
            exception_type = type(exc).__name__
        result = {
            "case_id": case_id,
            "category": category,
            "expected_decision": expected,
            "observed_decision": observed,
            "result": "PASS" if observed == expected else "FAIL",
            "input_sha256": input_hash,
            "evaluator_exception_type": exception_type,
        }
        results.append(result)
    missing = sorted(_REQUIRED_CATEGORIES - categories)
    if missing:
        raise ValueError("policy_test_category_coverage_missing:" + ",".join(missing))
    results.sort(key=lambda item: item["case_id"])
    summary = {
        "schema": "SUPER1200_POLICY_TEST_SUITE_RESULT/1",
        "policy_id": policy["policy_id"],
        "policy_version": policy["version"],
        "case_count": len(results),
        "passed": sum(item["result"] == "PASS" for item in results),
        "failed": sum(item["result"] == "FAIL" for item in results),
        "coverage": sorted(categories),
        "cases": results,
    }
    summary["suite_sha256"] = _digest(summary)
    summary["status"] = "PASS" if summary["failed"] == 0 else "FAIL"
    return summary


class PolicyVersionRegistry:
    """Append-only policy version ledger with immutable identities and effective intervals."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], dict[str, Any]] = {}

    def entries(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {**self._entries[key]}
            for key in sorted(self._entries)
        )

    def register(
        self,
        policy: Any,
        *,
        effective_from_utc: str,
        effective_until_utc: str | None = None,
        supersedes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        errors = validate_policy_document(policy)
        if errors:
            raise ValueError("policy_document_invalid:" + ",".join(errors))
        start = _utc(effective_from_utc, "effective_from_utc")
        end = _utc(effective_until_utc, "effective_until_utc") if effective_until_utc is not None else None
        if end is not None and end <= start:
            raise ValueError("policy_effective_interval_invalid")
        policy_id, version = policy["policy_id"], policy["version"]
        key = (policy_id, version)
        frozen_policy = {
            "schema": policy["schema"],
            "policy_id": policy_id,
            "version": version,
            "rules": policy["rules"],
            **{k: v for k, v in policy.items() if k not in {"schema", "policy_id", "version", "rules"}},
        }
        if key in self._entries:
            candidate = {
                "policy": frozen_policy,
                "effective_from_utc": start.isoformat().replace("+00:00", "Z"),
                "effective_until_utc": end.isoformat().replace("+00:00", "Z") if end else None,
                "supersedes": supersedes,
            }
            if self._entries[key] != candidate:
                raise ValueError("policy_version_identity_immutable")
            return {**self._entries[key]}

        supersedes_key = None
        if supersedes is not None:
            if (not isinstance(supersedes, dict)
                or not isinstance(supersedes.get("policy_id"), str)
                or not isinstance(supersedes.get("version"), str)):
                raise ValueError("policy_supersession_identity_invalid")
            supersedes_key = (supersedes["policy_id"], supersedes["version"])
            previous = self._entries.get(supersedes_key)
            if previous is None:
                raise ValueError("policy_superseded_version_unknown")
            if supersedes_key[0] != policy_id:
                raise ValueError("policy_supersession_id_mismatch")
            if previous["effective_until_utc"] is None:
                raise ValueError("policy_superseded_interval_must_be_closed")
            previous_end = _utc(previous["effective_until_utc"], "previous_effective_until_utc")
            if previous_end > start:
                raise ValueError("policy_supersession_interval_overlap")
            if any(entry.get("supersedes") == {"policy_id": supersedes_key[0], "version": supersedes_key[1]}
                   for entry in self._entries.values()):
                raise ValueError("policy_version_already_superseded")
        for existing_key, existing in self._entries.items():
            if existing_key[0] != policy_id:
                continue
            existing_start = _utc(existing["effective_from_utc"], "existing_effective_from_utc")
            existing_end = _utc(existing["effective_until_utc"], "existing_effective_until_utc") if existing["effective_until_utc"] else None
            new_end = end
            if (existing_end is None or existing_end > start) and (new_end is None or new_end > existing_start):
                raise ValueError("policy_effective_interval_overlap")
        record = {
            "policy": frozen_policy,
            "effective_from_utc": start.isoformat().replace("+00:00", "Z"),
            "effective_until_utc": end.isoformat().replace("+00:00", "Z") if end else None,
            "supersedes": {"policy_id": supersedes_key[0], "version": supersedes_key[1]} if supersedes_key else None,
        }
        record["policy_sha256"] = _digest(frozen_policy)
        record["record_sha256"] = _digest(record)
        self._entries[key] = record
        return {**record}

    def get(self, policy_id: str, version: str) -> dict[str, Any] | None:
        record = self._entries.get((policy_id, version))
        return {**record} if record is not None else None

    def select(self, policy_id: str, *, now_utc: str) -> dict[str, Any] | None:
        now = _utc(now_utc, "now_utc")
        active = []
        for (entry_policy_id, _), entry in self._entries.items():
            if entry_policy_id != policy_id:
                continue
            start = _utc(entry["effective_from_utc"], "effective_from_utc")
            end = _utc(entry["effective_until_utc"], "effective_until_utc") if entry["effective_until_utc"] else None
            if start <= now and (end is None or now < end):
                active.append(entry)
        if len(active) > 1:
            raise ValueError("policy_active_version_ambiguity")
        return {**active[0]} if active else None


def semantic_policy_diff(before: Any, after: Any) -> dict[str, Any]:
    """Compare policy semantics by rule identity, not serialized list order."""
    for value, field in ((before, "before"), (after, "after")):
        errors = validate_policy_document(value)
        if errors:
            raise ValueError("policy_" + field + "_invalid:" + ",".join(errors))
    if before["policy_id"] != after["policy_id"]:
        raise ValueError("policy_diff_identity_mismatch")
    def rules_by_id(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
        rules = {}
        for rule in policy["rules"]:
            if not isinstance(rule, dict) or not isinstance(rule.get("id"), str) or not rule["id"].strip():
                raise ValueError("policy_rule_identity_invalid")
            if rule["id"] in rules:
                raise ValueError("policy_rule_id_duplicate")
            rules[rule["id"]] = rule
        return rules
    old_rules, new_rules = rules_by_id(before), rules_by_id(after)
    added = sorted(set(new_rules) - set(old_rules))
    removed = sorted(set(old_rules) - set(new_rules))
    changed = []
    for rule_id in sorted(set(old_rules) & set(new_rules)):
        if canonical_json(old_rules[rule_id]) != canonical_json(new_rules[rule_id]):
            fields = sorted(set(old_rules[rule_id]) | set(new_rules[rule_id]))
            changed_fields = [field for field in fields if canonical_json(old_rules[rule_id].get(field)) != canonical_json(new_rules[rule_id].get(field))]
            changed.append({
                "rule_id": rule_id,
                "changed_fields": changed_fields,
                "before_sha256": _digest(old_rules[rule_id]),
                "after_sha256": _digest(new_rules[rule_id]),
            })
    metadata = {"schema", "policy_id", "version", "effective_from_utc", "effective_until_utc", "supersedes", "description"}
    old_fields = {k: v for k, v in before.items() if k not in metadata | {"rules"}}
    new_fields = {k: v for k, v in after.items() if k not in metadata | {"rules"}}
    policy_fields_changed = sorted(
        key for key in set(old_fields) | set(new_fields)
        if canonical_json(old_fields.get(key)) != canonical_json(new_fields.get(key))
    )
    affected = sorted(set(added) | set(removed) | {entry["rule_id"] for entry in changed})
    changed_semantically = bool(added or removed or changed or policy_fields_changed)
    result = {
        "schema": "SUPER1200_SEMANTIC_POLICY_DIFF/1",
        "policy_id": before["policy_id"],
        "before_version": before["version"],
        "after_version": after["version"],
        "before_sha256": _digest(before),
        "after_sha256": _digest(after),
        "added_rule_ids": added,
        "removed_rule_ids": removed,
        "changed_rules": changed,
        "policy_semantic_fields_changed": policy_fields_changed,
        "affected_decision_rules": affected,
        "semantic_change": changed_semantically,
    }
    result["diff_sha256"] = _digest(result)
    return result


def analyze_policy_impact(
    graph: EvidenceInvalidationGraph,
    *,
    policy_node_id: str,
    semantic_diff: Any,
) -> dict[str, Any]:
    """Propagate a semantic policy change through policy→claim/test/auth/evidence edges."""
    if not isinstance(graph, EvidenceInvalidationGraph):
        raise ValueError("policy_dependency_graph_required")
    if not isinstance(policy_node_id, str) or policy_node_id not in set(graph.evidence_ids):
        raise ValueError("policy_node_unknown")
    if not isinstance(semantic_diff, dict) or semantic_diff.get("schema") != "SUPER1200_SEMANTIC_POLICY_DIFF/1":
        raise ValueError("semantic_policy_diff_required")
    if not isinstance(semantic_diff.get("semantic_change"), bool):
        raise ValueError("semantic_policy_diff_flag_invalid")
    if semantic_diff.get("semantic_change"):
        closure = set(graph.invalidation_closure(policy_node_id))
        recompute = sorted(closure)
        impacted = sorted(closure - {policy_node_id})
    else:
        recompute = []
        impacted = []
    all_nodes = set(graph.evidence_ids)
    preserved = sorted(all_nodes - set(recompute))
    buckets = {
        "claims": sorted(x for x in impacted if x.startswith("claim:")),
        "tests": sorted(x for x in impacted if x.startswith("test:")),
        "authorizations": sorted(x for x in impacted if x.startswith("auth:")),
        "evidence": sorted(x for x in impacted if x.startswith("evidence:")),
        "other": sorted(x for x in impacted if not x.startswith(("claim:", "test:", "auth:", "evidence:"))),
    }
    result = {
        "schema": "SUPER1200_POLICY_IMPACT_ANALYSIS/1",
        "policy_node_id": policy_node_id,
        "policy_id": semantic_diff.get("policy_id"),
        "diff_sha256": semantic_diff.get("diff_sha256"),
        "status": "IMPACT_ANALYZED",
        "semantic_change": semantic_diff["semantic_change"],
        "recompute_ids": recompute,
        "affected_dependents": impacted,
        "affected_by_kind": buckets,
        "preserved_ids": preserved,
        "certification_granted": False,
    }
    result["impact_sha256"] = _digest(result)
    return result
