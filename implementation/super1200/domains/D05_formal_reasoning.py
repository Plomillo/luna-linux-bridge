"""D05 formal reasoning primitives for capabilities 121-124.

This is a deliberately small, explicitly scoped type-theory kernel and proof
obligation fabric. A type-check result is not a theorem-proving claim; a proof
is marked replay-verified only when a trusted external checker callback confirms
the exact proof, source, obligation, tool identity, version and replay state.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def require_sha256(value: Any, field: str) -> str:
    if not valid_sha256(value):
        raise ValueError(field + "_must_be_lowercase_sha256")
    return value


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(field + "_must_be_object")
    return value


def _name(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + "_required")
    return value.strip()


def explicit_assumption(*, assumption_id: str, statement: str,
                        source_sha256: str, justification: str) -> dict[str, Any]:
    """Record an axiom/assumption without treating it as a derived theorem."""
    assumption_id = _name(assumption_id, "assumption_id")
    statement = _name(statement, "assumption_statement")
    justification = _name(justification, "assumption_justification")
    require_sha256(source_sha256, "assumption_source_sha256")
    record = {
        "schema": "SUPER1200_FORMAL_ASSUMPTION/1",
        "assumption_id": assumption_id,
        "statement": statement,
        "justification": justification,
        "source_sha256": source_sha256,
        "epistemic_status": "DECLARED_EXPLICIT_ASSUMPTION_NOT_PROVED",
        "theorem_claim": False,
    }
    record["assumption_sha256"] = digest(record)
    return record


def build_proof_obligation(*, theorem_id: str, goal: str,
                           assumptions: list[dict[str, Any]],
                           source_sha256: str, prover_id: str,
                           prover_version: str, environment_sha256: str,
                           proof_term_sha256: str | None = None) -> dict[str, Any]:
    """Create a deterministic obligation pinned to assumptions and an environment."""
    theorem_id = _name(theorem_id, "theorem_id")
    goal = _name(goal, "goal")
    prover_id = _name(prover_id, "prover_id")
    prover_version = _name(prover_version, "prover_version")
    require_sha256(source_sha256, "source_sha256")
    require_sha256(environment_sha256, "environment_sha256")
    if proof_term_sha256 is not None:
        require_sha256(proof_term_sha256, "proof_term_sha256")
    if not isinstance(assumptions, list):
        raise ValueError("assumptions_must_be_list")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for assumption in assumptions:
        _object(assumption, "assumption")
        aid = _name(assumption.get("assumption_id"), "assumption_id")
        recorded = assumption.get("assumption_sha256")
        unsigned = dict(assumption)
        unsigned.pop("assumption_sha256", None)
        if recorded != digest(unsigned):
            raise ValueError("assumption_hash_mismatch:" + aid)
        if assumption.get("epistemic_status") != "DECLARED_EXPLICIT_ASSUMPTION_NOT_PROVED":
            raise ValueError("assumption_epistemic_status_invalid:" + aid)
        if assumption.get("theorem_claim") is not False:
            raise ValueError("assumption_must_not_claim_theorem:" + aid)
        if aid in seen:
            raise ValueError("assumption_id_duplicate:" + aid)
        seen.add(aid)
        normalized.append(dict(assumption))
    normalized.sort(key=lambda x: x["assumption_id"])
    unsigned_obligation = {
        "schema": "SUPER1200_PROOF_OBLIGATION/1",
        "theorem_id": theorem_id,
        "goal": goal,
        "assumptions": normalized,
        "source_sha256": source_sha256,
        "prover_id": prover_id,
        "prover_version": prover_version,
        "environment_sha256": environment_sha256,
        "proof_term_sha256": proof_term_sha256,
        "status": "OPEN_NOT_PROVED",
        "proof_claim": False,
    }
    obligation = dict(unsigned_obligation)
    obligation["obligation_sha256"] = digest(unsigned_obligation)
    return obligation


def validate_replay_receipt(obligation: Any, receipt: Any, *,
                            trusted_checker: Any) -> dict[str, Any]:
    """Verify exact replay binding; deny if checker identity or proof binding is absent."""
    if not isinstance(obligation, dict) or obligation.get("schema") != "SUPER1200_PROOF_OBLIGATION/1":
        raise ValueError("proof_obligation_schema_invalid")
    if obligation.get("proof_claim") is not False or obligation.get("status") != "OPEN_NOT_PROVED":
        raise ValueError("proof_obligation_epistemic_state_invalid")
    if not isinstance(receipt, dict):
        return {"decision": "DENY", "reason": "checker_receipt_missing",
                "theorem_claim": False}
    required_strings = ("checker_id", "checker_version", "proof_sha256",
                        "obligation_sha256", "source_sha256", "environment_sha256")
    for field in required_strings:
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            return {"decision": "DENY", "reason": "checker_receipt_field_missing:" + field,
                    "theorem_claim": False}
    for field in ("proof_sha256", "obligation_sha256", "source_sha256", "environment_sha256"):
        if not valid_sha256(receipt[field]):
            return {"decision": "DENY", "reason": "checker_receipt_digest_invalid:" + field,
                    "theorem_claim": False}
    if receipt.get("obligation_sha256") != obligation.get("obligation_sha256"):
        return {"decision": "DENY", "reason": "obligation_digest_mismatch",
                "theorem_claim": False}
    if receipt.get("source_sha256") != obligation.get("source_sha256"):
        return {"decision": "DENY", "reason": "source_digest_mismatch",
                "theorem_claim": False}
    if receipt.get("environment_sha256") != obligation.get("environment_sha256"):
        return {"decision": "DENY", "reason": "environment_digest_mismatch",
                "theorem_claim": False}
    if receipt.get("replayed") is not True or receipt.get("result") != "PASS":
        return {"decision": "DENY", "reason": "exact_proof_replay_not_passed",
                "theorem_claim": False}
    if receipt.get("checker_signature_verified") is not True:
        return {"decision": "DENY", "reason": "checker_signature_not_verified",
                "theorem_claim": False}
    if not callable(trusted_checker):
        return {"decision": "DENY", "reason": "trusted_checker_callback_required",
                "theorem_claim": False}
    try:
        trusted = trusted_checker(obligation, receipt) is True
    except Exception:
        trusted = False
    if not trusted:
        return {"decision": "DENY", "reason": "trusted_checker_rejected_receipt",
                "theorem_claim": False}
    return {
        "schema": "SUPER1200_PROOF_REPLAY_DECISION/1",
        "decision": "ALLOW_REPLAY_VERIFIED",
        "obligation_sha256": obligation["obligation_sha256"],
        "proof_sha256": receipt["proof_sha256"],
        "source_sha256": obligation["source_sha256"],
        "checker_id": receipt["checker_id"],
        "checker_version": receipt["checker_version"],
        "epistemic_status": "PROOF_REPLAY_VERIFIED_FOR_EXACT_OBLIGATION",
        "theorem_claim": True,
        "scope_only": True,
    }


def _kind(term: Any) -> str:
    if not isinstance(term, dict) or not isinstance(term.get("kind"), str):
        raise ValueError("term_kind_required")
    return term["kind"]


def _var(name: Any) -> str:
    return _name(name, "variable_name")


def _check_sort(term: Any, context: dict[str, Any], signature: dict[str, Any]) -> int:
    inferred = infer_type(term, context=context, signature=signature)
    if _kind(inferred) != "Sort":
        raise ValueError("type_expression_does_not_have_sort")
    return inferred["level"]


def substitute(term: Any, variable: str, replacement: Any) -> Any:
    """Capture-aware substitution for the named-binder AST used by this kernel."""
    if not isinstance(term, dict):
        return term
    kind = term.get("kind")
    if kind == "Var" and term.get("name") == variable:
        return replacement
    result = {}
    for key, value in term.items():
        if key in ("body", "codomain") and term.get("binder") == variable:
            result[key] = value
        else:
            result[key] = _substitute_nested(value, variable, replacement)
    return result


def _substitute_nested(value: Any, variable: str, replacement: Any) -> Any:
    if isinstance(value, dict):
        return substitute(value, variable, replacement)
    if isinstance(value, list):
        return [_substitute_nested(x, variable, replacement) for x in value]
    if isinstance(value, tuple):
        return tuple(_substitute_nested(x, variable, replacement) for x in value)
    return value


def normalize(term: Any, *, fuel: int = 256) -> Any:
    """Normalize beta-redexes; bounded reduction fails closed on exhaustion."""
    if fuel < 0:
        raise ValueError("normalization_fuel_exhausted")
    if not isinstance(term, dict):
        return term
    kind = term.get("kind")
    if kind == "App":
        function = normalize(term.get("function"), fuel=fuel-1)
        argument = normalize(term.get("argument"), fuel=fuel-1)
        if isinstance(function, dict) and function.get("kind") == "Lam":
            reduced = substitute(function["body"], function["binder"], argument)
            return normalize(reduced, fuel=fuel-1)
        return {"kind": "App", "function": function, "argument": argument}
    out = {}
    for key, value in term.items():
        if isinstance(value, dict):
            out[key] = normalize(value, fuel=fuel-1)
        elif isinstance(value, list):
            out[key] = [normalize(x, fuel=fuel-1) if isinstance(x, dict) else x for x in value]
        else:
            out[key] = value
    return out


def definitionally_equal(left: Any, right: Any) -> bool:
    try:
        return canonical_json(normalize(left)) == canonical_json(normalize(right))
    except (ValueError, RecursionError):
        return False


def infer_type(term: Any, *, context: dict[str, Any] | None = None,
               signature: dict[str, Any] | None = None) -> dict[str, Any]:
    """Infer types for Sort, Var, Const, Pi, Lam, App, Identity and Refl terms."""
    context = dict(context or {})
    signature = dict(signature or {})
    kind = _kind(term)
    if kind == "Sort":
        level = term.get("level")
        if not isinstance(level, int) or isinstance(level, bool) or level < 0:
            raise ValueError("sort_level_invalid")
        return {"kind": "Sort", "level": level + 1}
    if kind == "Var":
        name = _var(term.get("name"))
        if name not in context:
            raise ValueError("variable_unbound:" + name)
        return context[name]
    if kind == "Const":
        name = _name(term.get("name"), "constant_name")
        if name not in signature:
            raise ValueError("constant_unbound:" + name)
        return signature[name]
    if kind == "Pi":
        binder = _var(term.get("binder"))
        domain = term.get("domain")
        codomain = term.get("codomain")
        domain_level = _check_sort(domain, context, signature)
        nested = dict(context)
        nested[binder] = domain
        codomain_level = _check_sort(codomain, nested, signature)
        return {"kind": "Sort", "level": max(domain_level, codomain_level)}
    if kind == "Lam":
        binder = _var(term.get("binder"))
        domain = term.get("domain")
        _check_sort(domain, context, signature)
        nested = dict(context)
        nested[binder] = domain
        body_type = infer_type(term.get("body"), context=nested, signature=signature)
        return {"kind": "Pi", "binder": binder, "domain": domain, "codomain": body_type}
    if kind == "App":
        function_type = infer_type(term.get("function"), context=context, signature=signature)
        if _kind(function_type) != "Pi":
            raise ValueError("application_function_not_pi")
        argument_type = infer_type(term.get("argument"), context=context, signature=signature)
        if not definitionally_equal(argument_type, function_type["domain"]):
            raise ValueError("application_argument_type_mismatch")
        return substitute(function_type["codomain"], function_type["binder"], term["argument"])
    if kind == "Identity":
        type_expr = term.get("type")
        level = _check_sort(type_expr, context, signature)
        left_type = infer_type(term.get("left"), context=context, signature=signature)
        right_type = infer_type(term.get("right"), context=context, signature=signature)
        if not definitionally_equal(left_type, type_expr):
            raise ValueError("identity_left_type_mismatch")
        if not definitionally_equal(right_type, type_expr):
            raise ValueError("identity_right_type_mismatch")
        return {"kind": "Sort", "level": level}
    if kind == "Refl":
        type_expr = term.get("type")
        value = term.get("value")
        level = _check_sort(type_expr, context, signature)
        value_type = infer_type(value, context=context, signature=signature)
        if not definitionally_equal(value_type, type_expr):
            raise ValueError("refl_value_type_mismatch")
        return {"kind": "Identity", "type": type_expr, "left": value, "right": value}
    raise ValueError("term_constructor_unsupported:" + kind)


def check_type(term: Any, expected_type: Any, *,
               context: dict[str, Any] | None = None,
               signature: dict[str, Any] | None = None) -> bool:
    inferred = infer_type(term, context=context, signature=signature)
    if not definitionally_equal(inferred, expected_type):
        raise ValueError("inferred_type_does_not_match_expected_type")
    return True


def validate_higher_order_type(type_expression: Any, *,
                               context: dict[str, Any] | None = None,
                               signature: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate well-formed higher-order Pi types; no semantic theorem is inferred."""
    level = _check_sort(type_expression, dict(context or {}), dict(signature or {}))
    binders: list[str] = []
    cursor = type_expression
    while isinstance(cursor, dict) and cursor.get("kind") == "Pi":
        binders.append(cursor.get("binder", ""))
        cursor = cursor.get("codomain")
    has_function_domain = _has_function_domain(type_expression)
    if not has_function_domain:
        raise ValueError("higher_order_function_domain_required")
    return {
        "schema": "SUPER1200_HIGHER_ORDER_TYPE_VALIDATION/1",
        "decision": "WELL_FORMED_TYPE",
        "sort_level": level,
        "binders": binders,
        "higher_order_domain_present": True,
        "theorem_claim": False,
    }


def _has_function_domain(term: Any) -> bool:
    if not isinstance(term, dict):
        return False
    if term.get("kind") == "Pi" and isinstance(term.get("domain"), dict) and term["domain"].get("kind") == "Pi":
        return True
    return any(_has_function_domain(v) for v in term.values() if isinstance(v, dict))


def validate_hott_identity(identity_type: Any, proof_term: Any, *,
                            context: dict[str, Any] | None = None,
                            signature: dict[str, Any] | None = None,
                            universe_assumptions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Type-check an identity-type proof term and preserve universe assumptions explicitly."""
    assumptions = list(universe_assumptions or [])
    seen = set()
    for item in assumptions:
        _object(item, "universe_assumption")
        aid = _name(item.get("assumption_id"), "universe_assumption_id")
        if aid in seen:
            raise ValueError("universe_assumption_duplicate")
        seen.add(aid)
        if item.get("epistemic_status") != "DECLARED_EXPLICIT_ASSUMPTION_NOT_PROVED":
            raise ValueError("universe_assumption_not_explicit")
        unsigned = dict(item)
        recorded = unsigned.pop("assumption_sha256", None)
        if recorded != digest(unsigned):
            raise ValueError("universe_assumption_hash_mismatch")
    inferred = infer_type(proof_term, context=context, signature=signature)
    if not definitionally_equal(inferred, identity_type):
        raise ValueError("hott_proof_type_mismatch")
    if _kind(identity_type) != "Identity":
        raise ValueError("hott_identity_type_required")
    return {
        "schema": "SUPER1200_HOTT_IDENTITY_CHECK/1",
        "decision": "TYPE_CHECKED_ONLY",
        "identity_type_sha256": digest(identity_type),
        "proof_term_sha256": digest(proof_term),
        "universe_assumptions": sorted(assumptions, key=lambda x: x["assumption_id"]),
        "proof_replay_verified": False,
        "theorem_claim": False,
        "note": "Type checking alone is not independent proof replay or global certification.",
    }
