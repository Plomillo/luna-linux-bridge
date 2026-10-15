"""Name-specific D05 primitives for capabilities 137-176.

Fail-closed. No theorem claim. No global certification.
Each capability has its own decision and its own rejection.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from typing import Any, Callable

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _name(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + "_required")
    return value.strip()


def _sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(field + "_must_be_lowercase_sha256")
    return value


def _ident(value: Any, field: str) -> str:
    text = _name(value, field)
    if not _IDENT.fullmatch(text):
        raise ValueError(field + "_must_be_identifier")
    return text


def rec(schema: str, decision: str, **fields: Any) -> dict[str, Any]:
    if fields.get("certification_granted") or fields.get("global_certification"):
        raise ValueError("self_certification_forbidden")
    out: dict[str, Any] = {
        "schema": schema,
        "decision": decision,
        "theorem_claim": False,
        "certification_granted": False,
        "global_certification": False,
    }
    out.update(fields)
    out["record_sha256"] = digest({k: v for k, v in out.items() if k != "record_sha256"})
    return out


def _graph(spec: dict[str, Any], *, allow_empty: bool = False) -> tuple[list[str], list[tuple[str, str]]]:
    nodes = spec.get("nodes")
    if not isinstance(nodes, list) or (not nodes and not allow_empty):
        raise ValueError("nodes_required")
    ids: list[str] = []
    for node in nodes:
        if isinstance(node, str):
            ident = node
        elif isinstance(node, dict):
            ident = node.get("id")
        else:
            ident = None
        ident = _name(ident, "node_id")
        ids.append(ident)
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_node_id")
    edges = spec.get("edges", [])
    if not isinstance(edges, list):
        raise ValueError("edges_must_be_list")
    norm: list[tuple[str, str]] = []
    known = set(ids)
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise ValueError("edge_must_be_pair")
        src, dst = edge
        if src not in known or dst not in known:
            raise ValueError("edge_endpoint_unknown")
        norm.append((str(src), str(dst)))
    return ids, norm


def _adj(ids: list[str], edges: list[tuple[str, str]]) -> dict[str, list[str]]:
    adj = {i: [] for i in ids}
    for src, dst in edges:
        adj[src].append(dst)
    return adj


def _reachable(ids: list[str], edges: list[tuple[str, str]], roots: list[str]) -> list[str]:
    adj = _adj(ids, edges)
    seen: list[str] = []
    stack = list(roots)
    visited: set[str] = set()
    while stack:
        cur = stack.pop()
        if cur in visited:
            continue
        visited.add(cur)
        seen.append(cur)
        stack.extend(adj.get(cur, []))
    return seen


def _cycles(ids: list[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    adj = _adj(ids, edges)
    color = {i: 0 for i in ids}
    found: list[list[str]] = []

    def dfs(node: str, path: list[str]) -> None:
        color[node] = 1
        path.append(node)
        for nxt in adj[node]:
            if color[nxt] == 0:
                dfs(nxt, path)
            elif color[nxt] == 1:
                cycle = path[path.index(nxt) :] + [nxt]
                found.append(cycle)
        path.pop()
        color[node] = 2

    for ident in ids:
        if color[ident] == 0:
            dfs(ident, [])
    return found


def _cmp(left: int, op: str, right: int) -> bool:
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    raise ValueError("comparison_op_unknown")


def _hold(env: dict[str, int], clauses: list[dict[str, Any]]) -> bool:
    for clause in clauses:
        var = _name(clause.get("var"), "clause_var")
        if var not in env:
            raise ValueError("clause_var_unknown")
        op = _name(clause.get("op"), "clause_op")
        value = clause.get("value")
        if not isinstance(value, int):
            raise ValueError("clause_value_must_be_int")
        if not _cmp(env[var], op, value):
            return False
    return True


def proof_carrying_api_contract(
    *,
    contract_id: str,
    version: int,
    request_schema: dict[str, str],
    response_schema: dict[str, str],
    proof_term_sha256: str,
    consumer_scope: str,
) -> dict[str, Any]:
    contract_id = _name(contract_id, "contract_id")
    consumer_scope = _name(consumer_scope, "consumer_scope")
    if consumer_scope == "GLOBAL":
        raise ValueError("api_contract_rejects_global_consumer")
    if not isinstance(version, int) or version < 1:
        raise ValueError("api_contract_version_required")
    for label, schema in (("request", request_schema), ("response", response_schema)):
        if not isinstance(schema, dict) or not schema:
            raise ValueError(label + "_schema_required")
        for field, typ in schema.items():
            if not isinstance(field, str) or not field.strip():
                raise ValueError(label + "_field_name_required")
            if not isinstance(typ, str) or not typ.strip():
                raise ValueError(label + "_field_type_required")
    _sha(proof_term_sha256, "proof_term_sha256")
    return rec(
        "SUPER1200_PROOF_CARRYING_API_CONTRACT/1",
        "API_CONTRACT_BOUND",
        contract_id=contract_id,
        version=version,
        consumer_scope=consumer_scope,
        proof_term_sha256=proof_term_sha256,
        request_fields=sorted(request_schema),
        response_fields=sorted(response_schema),
    )


def _model_check(states: list[str], init: str, transitions: list[list[str]], forbidden: list[str]) -> tuple[list[str], list[str]]:
    if not isinstance(states, list) or not states:
        raise ValueError("states_required")
    clean = [_name(s, "state") for s in states]
    if len(clean) != len(set(clean)):
        raise ValueError("duplicate_state")
    init = _name(init, "init")
    if init not in clean:
        raise ValueError("init_unknown")
    if not isinstance(forbidden, list):
        raise ValueError("forbidden_required")
    bad = [_name(s, "forbidden_state") for s in forbidden]
    unknown = [s for s in bad if s not in clean]
    if unknown:
        raise ValueError("forbidden_state_unknown")
    if not isinstance(transitions, list):
        raise ValueError("transitions_required")
    pairs: list[tuple[str, str]] = []
    for item in transitions:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("transition_must_be_pair")
        src, dst = _name(item[0], "transition_src"), _name(item[1], "transition_dst")
        if src not in clean or dst not in clean:
            raise ValueError("transition_unknown_state")
        pairs.append((src, dst))
    reached = _reachable(clean, pairs, [init])
    hit = [s for s in bad if s in reached]
    return reached, hit


def model_checking_fabric(*, states: list[str], init: str, transitions: list[list[str]], forbidden: list[str]) -> dict[str, Any]:
    reached, hit = _model_check(states, init, transitions, forbidden)
    return rec(
        "SUPER1200_MODEL_CHECKING_FABRIC/1",
        "COUNTEREXAMPLE" if hit else "SAFETY_HOLDS",
        init=init,
        reachable=reached,
        violated=hit,
    )


def tla_plus_provider(*, spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("tla_spec_required")
    for key in ("Init", "Next", "Invariant"):
        if key not in spec:
            raise ValueError("tla_" + key.lower() + "_required")
    properties = spec.get("properties", [])
    if not isinstance(properties, list):
        raise ValueError("tla_properties_must_be_list")
    if "liveness" in properties and spec.get("fairness") is not True:
        raise ValueError("liveness_requires_fairness")
    reached, hit = _model_check(spec["states"] if "states" in spec else [spec["Init"]], spec["Init"], spec["Next"], spec["Invariant"])
    return rec(
        "SUPER1200_TLA_PLUS_PROVIDER/1",
        "TLA_COUNTEREXAMPLE" if hit else "TLA_INVARIANT_HOLDS",
        fairness=bool(spec.get("fairness")),
        reachable=reached,
        violated=hit,
    )


def apalache_provider(*, bound: int, variables: dict[str, int], updates: list[dict[str, int]]) -> dict[str, Any]:
    if not isinstance(bound, int) or bound < 1:
        raise ValueError("apalache_bound_required")
    if not isinstance(variables, dict) or not variables:
        raise ValueError("apalache_variables_required")
    current: dict[str, int] = {}
    for key, value in variables.items():
        _name(key, "variable")
        if not isinstance(value, int):
            raise ValueError("apalache_value_must_be_int")
        if value < 0 or value > bound:
            raise ValueError("apalache_value_out_of_bound")
        current[key] = value
    if not isinstance(updates, list):
        raise ValueError("apalache_updates_required")
    for update in updates:
        if not isinstance(update, dict):
            raise ValueError("apalache_update_must_be_object")
        for key, value in update.items():
            if key not in current:
                raise ValueError("apalache_update_unknown_variable")
            if not isinstance(value, int):
                raise ValueError("apalache_value_must_be_int")
            if value < 0 or value > bound:
                raise ValueError("apalache_value_out_of_bound")
            current[key] = value
    return rec("SUPER1200_APALACHE_PROVIDER/1", "BOUNDED_MODEL_ACCEPTED", bound=bound, variables=current)


def alloy_provider(*, atoms: list[str], tuples: list[list[str]], multiplicity: str) -> dict[str, Any]:
    if not isinstance(atoms, list) or not atoms:
        raise ValueError("alloy_atoms_required")
    atom_ids = [_name(a, "atom") for a in atoms]
    if len(atom_ids) != len(set(atom_ids)):
        raise ValueError("duplicate_atom")
    multiplicity = _name(multiplicity, "multiplicity")
    if multiplicity not in {"one", "lone", "some", "set"}:
        raise ValueError("alloy_multiplicity_unknown")
    if not isinstance(tuples, list):
        raise ValueError("alloy_tuples_required")
    clean: list[list[str]] = []
    known = set(atom_ids)
    for item in tuples:
        if not isinstance(item, list) or not item:
            raise ValueError("alloy_tuple_required")
        row = [_name(x, "atom_ref") for x in item]
        if any(x not in known for x in row):
            raise ValueError("alloy_unknown_atom")
        clean.append(row)
    if multiplicity == "one" and len(clean) != 1:
        raise ValueError("alloy_one_requires_exactly_one_tuple")
    if multiplicity == "some" and len(clean) < 1:
        raise ValueError("alloy_some_requires_a_tuple")
    if multiplicity == "lone" and len(clean) > 1:
        raise ValueError("alloy_lone_rejects_multiple_tuples")
    return rec("SUPER1200_ALLOY_PROVIDER/1", "RELATIONAL_SPEC_ACCEPTED", multiplicity=multiplicity, tuple_count=len(clean))


def dafny_provider(*, env: dict[str, int], pre: list[dict[str, Any]], assigns: dict[str, int], post: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(env, dict):
        raise ValueError("dafny_env_required")
    current = {}
    for key, value in env.items():
        _name(key, "env_var")
        if not isinstance(value, int):
            raise ValueError("dafny_env_must_be_int")
        current[key] = value
    if not _hold(current, pre):
        raise ValueError("dafny_precondition_failed")
    if not isinstance(assigns, dict):
        raise ValueError("dafny_assigns_required")
    for key, value in assigns.items():
        if key not in current:
            raise ValueError("dafny_assign_unknown")
        if not isinstance(value, int):
            raise ValueError("dafny_assign_must_be_int")
        current[key] = value
    if not _hold(current, post):
        raise ValueError("dafny_postcondition_failed")
    return rec("SUPER1200_DAFNY_PROVIDER/1", "HOARE_TRIPLE_HOLDS", env=current)


def _smt_eval(constraints: list[dict[str, Any]], model: dict[str, int]) -> bool:
    if not isinstance(constraints, list) or not constraints:
        raise ValueError("smt_constraints_required")
    if not isinstance(model, dict):
        raise ValueError("smt_model_required")

    def val(side: Any) -> int:
        if isinstance(side, int):
            return side
        if isinstance(side, str):
            if side not in model or not isinstance(model[side], int):
                raise ValueError("smt_unknown_var")
            return model[side]
        raise ValueError("smt_side_invalid")

    ok = True
    for constraint in constraints:
        if not isinstance(constraint, dict):
            raise ValueError("smt_constraint_invalid")
        op = _name(constraint.get("op"), "smt_op")
        if not _cmp(val(constraint.get("left")), op, val(constraint.get("right"))):
            ok = False
    return ok


def smt_provider(*, constraints: list[dict[str, Any]], model: dict[str, int]) -> dict[str, Any]:
    sat = _smt_eval(constraints, model)
    return rec("SUPER1200_SMT_PROVIDER/1", "SAT" if sat else "UNSAT")


def z3_provider(*, logic: str, constraints: list[dict[str, Any]], model: dict[str, int]) -> dict[str, Any]:
    logic = _name(logic, "logic")
    if logic not in {"QF_LIA", "QF_IDL"}:
        raise ValueError("z3_unsupported_logic")
    if logic == "QF_IDL":
        for constraint in constraints:
            if not isinstance(constraint, dict) or constraint.get("diff") is not True:
                raise ValueError("qf_idl_requires_difference_constraint")
            if not isinstance(constraint.get("left"), str) or not isinstance(constraint.get("right"), str):
                raise ValueError("qf_idl_requires_variables")
    sat = _smt_eval(constraints, model)
    return rec("SUPER1200_Z3_PROVIDER/1", "SAT" if sat else "UNSAT", logic=logic)


def _property_holds(kind: str, sample: list[Any]) -> bool:
    if kind == "all_non_negative":
        return all(isinstance(x, int) and x >= 0 for x in sample)
    if kind == "sorted":
        return all(isinstance(x, int) for x in sample) and list(sample) == sorted(sample)
    raise ValueError("property_kind_unknown")


def property_based_testing(*, properties: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(properties, list) or not properties:
        raise ValueError("properties_required")
    failures = []
    for prop in properties:
        kind = _name(prop.get("kind"), "property_kind")
        samples = prop.get("samples")
        if not isinstance(samples, list) or not samples:
            raise ValueError("property_samples_required")
        for sample in samples:
            if not isinstance(sample, list):
                raise ValueError("property_sample_must_be_list")
            if not _property_holds(kind, sample):
                failures.append({"kind": kind, "sample": sample})
    return rec(
        "SUPER1200_PROPERTY_BASED_TESTING/1",
        "PROPERTY_COUNTEREXAMPLE" if failures else "PROPERTIES_HOLD",
        failures=failures,
    )


def hypothesis_provider(*, seed: int, max_examples: int) -> dict[str, Any]:
    if not isinstance(seed, int):
        raise ValueError("hypothesis_seed_required")
    if not isinstance(max_examples, int) or max_examples < 1:
        raise ValueError("hypothesis_max_examples_required")
    rng = random.Random(seed)
    samples = [rng.randint(-2, 4) for _ in range(max_examples)]
    bad = [n for n in samples if n < 0]
    return rec(
        "SUPER1200_HYPOTHESIS_PROVIDER/1",
        "HYPOTHESIS_COUNTEREXAMPLE" if bad else "HYPOTHESIS_HOLDS",
        seed=seed,
        failures=bad,
    )


def quickcheck_style_provider(*, generator: str, trials: int, seed: int) -> dict[str, Any]:
    generator = _name(generator, "generator")
    if generator not in {"int", "bool", "list_int"}:
        raise ValueError("quickcheck_generator_unknown")
    if not isinstance(trials, int) or trials < 1:
        raise ValueError("quickcheck_trials_required")
    if not isinstance(seed, int):
        raise ValueError("quickcheck_seed_required")
    rng = random.Random(seed)
    failures = []
    for _ in range(trials):
        if generator == "int":
            value = rng.randint(-3, 3)
            if value < 0:
                failures.append(value)
        elif generator == "bool":
            value = rng.choice([True, False])
            if value is False:
                failures.append(False)
        else:
            value = [rng.randint(-1, 2) for _ in range(3)]
            if value != sorted(value):
                failures.append(value)
    return rec(
        "SUPER1200_QUICKCHECK_STYLE_PROVIDER/1",
        "QUICKCHECK_COUNTEREXAMPLE" if failures else "QUICKCHECK_HOLDS",
        generator=generator,
        failure_count=len(failures),
    )


def _hex_bytes(value: str) -> bytes:
    text = _name(value, "corpus_hex")
    try:
        return bytes.fromhex(text)
    except ValueError as exc:
        raise ValueError("corpus_hex_invalid") from exc


def fuzzing_fabric(*, corpus: list[str], oracle: str) -> dict[str, Any]:
    oracle = _name(oracle, "oracle")
    if oracle not in {"no_nul", "crash_token"}:
        raise ValueError("fuzz_oracle_unknown")
    if not isinstance(corpus, list) or not corpus:
        raise ValueError("fuzz_corpus_required")
    findings = []
    for item in corpus:
        blob = bytearray(_hex_bytes(item))
        if blob:
            blob[0] ^= 0x01
        mutated = bytes(blob)
        originals = (_hex_bytes(item), mutated)
        if oracle == "no_nul" and any(b"\x00" in x for x in originals):
            findings.append(item)
        if oracle == "crash_token" and any(b"CRASH" in x for x in originals):
            findings.append(item)
    return rec("SUPER1200_FUZZING_FABRIC/1", "FUZZ_FINDINGS" if findings else "FUZZ_CLEAN", oracle=oracle, findings=findings)


def libfuzzer_provider(*, entrypoint: str, max_len: int, corpus: list[str]) -> dict[str, Any]:
    entrypoint = _ident(entrypoint, "entrypoint")
    if not isinstance(max_len, int) or max_len < 1:
        raise ValueError("libfuzzer_max_len_required")
    if not isinstance(corpus, list) or not corpus:
        raise ValueError("libfuzzer_corpus_required")
    kept = []
    for item in corpus:
        blob = _hex_bytes(item)
        if len(blob) <= max_len:
            kept.append(item)
    return rec("SUPER1200_LIBFUZZER_PROVIDER/1", "LIBFUZZER_CORPUS_BOUNDED", entrypoint=entrypoint, kept=len(kept), dropped=len(corpus) - len(kept))


def cargo_fuzz_provider(*, crate: str, harness: str) -> dict[str, Any]:
    return rec(
        "SUPER1200_CARGO_FUZZ_PROVIDER/1",
        "CARGO_FUZZ_TARGET_ACCEPTED",
        crate=_ident(crate, "crate"),
        harness=_ident(harness, "harness"),
    )


def oss_fuzz_compatibility(*, language: str, fuzz_targets: list[str], dockerfile: str) -> dict[str, Any]:
    language = _name(language, "language")
    if language not in {"c", "c++", "rust", "go", "python"}:
        raise ValueError("oss_fuzz_language_unsupported")
    dockerfile = _name(dockerfile, "dockerfile")
    if not isinstance(fuzz_targets, list) or not fuzz_targets:
        raise ValueError("oss_fuzz_targets_required")
    targets = [_ident(t, "fuzz_target") for t in fuzz_targets]
    return rec("SUPER1200_OSS_FUZZ_COMPATIBILITY/1", "OSS_FUZZ_COMPATIBLE", language=language, targets=targets, dockerfile=dockerfile)


def state_machine_testing(*, start: str, transitions: dict[str, dict[str, str]], trace: list[str], accept: list[str]) -> dict[str, Any]:
    start = _name(start, "start")
    if not isinstance(transitions, dict) or start not in transitions:
        raise ValueError("state_machine_start_unknown")
    if not isinstance(trace, list):
        raise ValueError("state_machine_trace_required")
    if not isinstance(accept, list) or not accept:
        raise ValueError("state_machine_accept_required")
    current = start
    for event in trace:
        event = _name(event, "event")
        table = transitions.get(current)
        if not isinstance(table, dict) or event not in table:
            raise ValueError("state_machine_event_unknown")
        current = _name(table[event], "next_state")
    accepted = [_name(s, "accept_state") for s in accept]
    return rec(
        "SUPER1200_STATE_MACHINE_TESTING/1",
        "TRACE_ACCEPTED" if current in accepted else "TRACE_REJECTED",
        final=current,
    )


def concurrency_model_checking(*, threads: list[list[dict[str, str]]]) -> dict[str, Any]:
    if not isinstance(threads, list) or len(threads) < 2:
        raise ValueError("concurrency_threads_required")
    writes: dict[str, int] = {}
    for thread in threads:
        if not isinstance(thread, list) or not thread:
            raise ValueError("concurrency_thread_empty")
        for action in thread:
            if not isinstance(action, dict):
                raise ValueError("concurrency_action_invalid")
            op = _name(action.get("op"), "op")
            var = _name(action.get("var"), "var")
            if op not in {"read", "write"}:
                raise ValueError("concurrency_op_unknown")
            if op == "write":
                writes[var] = writes.get(var, 0) + 1
    raced = sorted([var for var, count in writes.items() if count >= 2])
    return rec("SUPER1200_CONCURRENCY_MODEL_CHECKING/1", "DATA_RACE" if raced else "NO_DATA_RACE", raced=raced)


def deadlock_detection(*, edges: list[list[str]]) -> dict[str, Any]:
    if not isinstance(edges, list):
        raise ValueError("deadlock_edges_required")
    pairs = []
    nodes: list[str] = []
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise ValueError("deadlock_edge_must_be_pair")
        src, dst = _name(edge[0], "waiter"), _name(edge[1], "holder")
        pairs.append((src, dst))
        if src not in nodes:
            nodes.append(src)
        if dst not in nodes:
            nodes.append(dst)
    cyc = _cycles(nodes, pairs) if nodes else []
    self_wait = [src for src, dst in pairs if src == dst]
    dead = bool(cyc or self_wait)
    return rec("SUPER1200_DEADLOCK_DETECTION/1", "DEADLOCK" if dead else "NO_DEADLOCK", cycles=cyc, self_wait=self_wait)


def liveness_properties(*, states: list[str], init: str, transitions: list[list[str]], goal: str) -> dict[str, Any]:
    goal = _name(goal, "goal")
    reached, _hit = _model_check(states, init, transitions, [])
    if goal not in states:
        raise ValueError("goal_unknown")
    return rec(
        "SUPER1200_LIVENESS_PROPERTIES/1",
        "LIVENESS_HOLDS" if goal in reached else "LIVENESS_VIOLATION",
        goal=goal,
        reachable=reached,
    )


def safety_properties(*, states: list[str], init: str, transitions: list[list[str]], forbidden: list[str]) -> dict[str, Any]:
    if not isinstance(forbidden, list) or not forbidden:
        raise ValueError("safety_property_required")
    _reached, hit = _model_check(states, init, transitions, forbidden)
    return rec("SUPER1200_SAFETY_PROPERTIES/1", "SAFETY_VIOLATION" if hit else "SAFETY_HOLDS", violated=hit)


def architecture_as_data(*, components: list[dict[str, str]], relations: list[list[str]]) -> dict[str, Any]:
    if not isinstance(components, list) or not components:
        raise ValueError("components_required")
    ids = []
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("component_must_be_object")
        ident = _name(component.get("id"), "component_id")
        _name(component.get("owner"), "component_owner")
        ids.append(ident)
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_component_id")
    _graph({"nodes": ids, "edges": relations})
    return rec("SUPER1200_ARCHITECTURE_AS_DATA/1", "ARCHITECTURE_RECORDED", components=ids, relation_count=len(relations))


def architecture_schema(*, version: int, components: list[str], relations: list[list[str]]) -> dict[str, Any]:
    if not isinstance(version, int) or version < 1:
        raise ValueError("architecture_schema_version_required")
    if not isinstance(components, list) or not components:
        raise ValueError("architecture_schema_components_required")
    _graph({"nodes": components, "edges": relations}, allow_empty=False)
    return rec("SUPER1200_ARCHITECTURE_SCHEMA/1", "ARCHITECTURE_SCHEMA_ACCEPTED", version=version, components=components)


def architecture_graph(*, nodes: list[str], edges: list[list[str]]) -> dict[str, Any]:
    ids, norm = _graph({"nodes": nodes, "edges": edges})
    return rec("SUPER1200_ARCHITECTURE_GRAPH/1", "GRAPH_ACCEPTED", nodes=ids, edge_count=len(norm))


def architecture_diff(*, left: dict[str, Any], right: dict[str, Any], claim_changed: bool) -> dict[str, Any]:
    l_ids, l_edges = _graph(left)
    r_ids, r_edges = _graph(right)
    same = digest({"nodes": l_ids, "edges": l_edges}) == digest({"nodes": r_ids, "edges": r_edges})
    if claim_changed is True and same:
        raise ValueError("false_change_claim")
    if not isinstance(claim_changed, bool):
        raise ValueError("claim_changed_required")
    return rec(
        "SUPER1200_ARCHITECTURE_DIFF/1",
        "DIFF_RECORDED",
        added_nodes=sorted(set(r_ids) - set(l_ids)),
        removed_nodes=sorted(set(l_ids) - set(r_ids)),
        identical=same,
    )


def architecture_linter(*, nodes: list[dict[str, str]], edges: list[list[str]], rules: list[str]) -> dict[str, Any]:
    if not isinstance(rules, list) or not rules:
        raise ValueError("lint_rules_required")
    allowed = {"owner_required", "no_orphan_edge"}
    unknown = [rule for rule in rules if rule not in allowed]
    if unknown:
        raise ValueError("lint_rule_unknown")
    ids = []
    owners = {}
    for node in nodes:
        ident = _name(node.get("id") if isinstance(node, dict) else None, "node_id")
        ids.append(ident)
        owners[ident] = node.get("owner") if isinstance(node, dict) else None
    _graph({"nodes": ids, "edges": edges})
    violations = []
    if "owner_required" in rules:
        violations.extend([i for i, owner in owners.items() if not isinstance(owner, str) or not owner.strip()])
    if "no_orphan_edge" in rules:
        for src, dst in edges:
            if src not in ids or dst not in ids:
                violations.append(str(src) + "->" + str(dst))
    return rec("SUPER1200_ARCHITECTURE_LINTER/1", "LINT_VIOLATIONS" if violations else "LINT_CLEAN", violations=violations)


def architecture_tester(*, nodes: list[str], edges: list[list[str]], assertions: list[dict[str, Any]]) -> dict[str, Any]:
    ids, norm = _graph({"nodes": nodes, "edges": edges})
    if not isinstance(assertions, list) or not assertions:
        raise ValueError("architecture_assertions_required")
    edge_set = set(norm)
    for assertion in assertions:
        kind = _name(assertion.get("kind"), "assertion_kind")
        if kind == "exists":
            if _name(assertion.get("id"), "assertion_id") not in ids:
                raise ValueError("architecture_assertion_failed")
        elif kind == "edge":
            pair = (_name(assertion.get("src"), "assertion_src"), _name(assertion.get("dst"), "assertion_dst"))
            if pair not in edge_set:
                raise ValueError("architecture_assertion_failed")
        else:
            raise ValueError("assertion_kind_unknown")
    return rec("SUPER1200_ARCHITECTURE_TESTER/1", "ARCHITECTURE_TESTS_PASSED", assertions=len(assertions))


def architecture_compiler(*, nodes: list[str], edges: list[list[str]]) -> dict[str, Any]:
    ids, norm = _graph({"nodes": nodes, "edges": edges})
    if _cycles(ids, norm):
        raise ValueError("architecture_cycle")
    indeg = {i: 0 for i in ids}
    adj = _adj(ids, norm)
    for _src, dst in norm:
        indeg[dst] += 1
    ready = sorted([i for i, deg in indeg.items() if deg == 0])
    order = []
    while ready:
        cur = ready.pop(0)
        order.append(cur)
        for nxt in adj[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                ready.append(nxt)
                ready.sort()
    if len(order) != len(ids):
        raise ValueError("architecture_cycle")
    return rec("SUPER1200_ARCHITECTURE_COMPILER/1", "TOPO_ORDER_EMITTED", order=order)


def architecture_simulator(*, nodes: list[str], edges: list[list[str]], tokens: dict[str, int], steps: int) -> dict[str, Any]:
    ids, norm = _graph({"nodes": nodes, "edges": edges})
    if not isinstance(steps, int) or steps < 0:
        raise ValueError("simulator_steps_required")
    if not isinstance(tokens, dict):
        raise ValueError("simulator_tokens_required")
    state = {}
    for ident in ids:
        value = tokens.get(ident, 0)
        if not isinstance(value, int) or value < 0:
            raise ValueError("simulator_token_invalid")
        state[ident] = value
    total = sum(state.values())
    for _ in range(steps):
        moves = []
        for src, dst in norm:
            if state[src] > 0:
                moves.append((src, dst))
        for src, dst in moves:
            state[src] -= 1
            state[dst] += 1
    if sum(state.values()) != total:
        raise ValueError("simulator_token_leak")
    return rec("SUPER1200_ARCHITECTURE_SIMULATOR/1", "SIMULATION_CONSERVED", tokens=state, total=total)


def architecture_dependency_analyzer(*, nodes: list[str], edges: list[list[str]], component: str, direction: str) -> dict[str, Any]:
    ids, norm = _graph({"nodes": nodes, "edges": edges})
    component = _name(component, "component")
    direction = _name(direction, "direction")
    if component not in ids:
        raise ValueError("component_unknown")
    if direction not in {"in", "out"}:
        raise ValueError("dependency_direction_unknown")
    if direction == "out":
        deps = sorted({dst for src, dst in norm if src == component})
    else:
        deps = sorted({src for src, dst in norm if dst == component})
    return rec("SUPER1200_ARCHITECTURE_DEPENDENCY_ANALYZER/1", "DEPENDENCIES_LISTED", component=component, direction=direction, dependencies=deps)


def architecture_cycle_detector(*, nodes: list[str], edges: list[list[str]]) -> dict[str, Any]:
    ids, norm = _graph({"nodes": nodes, "edges": edges}, allow_empty=False)
    found = _cycles(ids, norm)
    return rec("SUPER1200_ARCHITECTURE_CYCLE_DETECTOR/1", "CYCLES_FOUND" if found else "ACYCLIC", cycles=found)


def architecture_dead_component_detector(*, nodes: list[str], edges: list[list[str]], roots: list[str]) -> dict[str, Any]:
    ids, norm = _graph({"nodes": nodes, "edges": edges})
    if not isinstance(roots, list):
        raise ValueError("roots_required")
    root_ids = [_name(r, "root") for r in roots]
    if any(r not in ids for r in root_ids):
        raise ValueError("root_unknown")
    live = set(_reachable(ids, norm, root_ids))
    dead = [i for i in ids if i not in live]
    return rec("SUPER1200_ARCHITECTURE_DEAD_COMPONENT_DETECTOR/1", "DEAD_COMPONENTS_LISTED", dead=dead)


def architecture_duplication_detector(*, names: list[str]) -> dict[str, Any]:
    if not isinstance(names, list) or not names:
        raise ValueError("duplication_names_required")
    clean = [_name(n, "name") for n in names]
    dup = sorted({n for n in clean if clean.count(n) > 1})
    return rec("SUPER1200_ARCHITECTURE_DUPLICATION_DETECTOR/1", "DUPLICATES_FOUND" if dup else "NO_DUPLICATES", duplicates=dup)


def architecture_reachability_analyzer(*, nodes: list[str], edges: list[list[str]], roots: list[str]) -> dict[str, Any]:
    ids, norm = _graph({"nodes": nodes, "edges": edges})
    if not isinstance(roots, list) or not roots:
        raise ValueError("reachability_roots_required")
    root_ids = [_name(r, "root") for r in roots]
    if any(r not in ids for r in root_ids):
        raise ValueError("root_unknown")
    reached = _reachable(ids, norm, root_ids)
    return rec("SUPER1200_ARCHITECTURE_REACHABILITY_ANALYZER/1", "REACHABILITY_COMPUTED", reachable=sorted(reached))


def architectural_blast_radius(*, nodes: list[str], edges: list[list[str]], changed: str) -> dict[str, Any]:
    ids, norm = _graph({"nodes": nodes, "edges": edges})
    changed = _name(changed, "changed")
    if changed not in ids:
        raise ValueError("changed_node_unknown")
    impacted = [n for n in _reachable(ids, norm, [changed]) if n != changed]
    return rec("SUPER1200_ARCHITECTURAL_BLAST_RADIUS/1", "BLAST_RADIUS_COMPUTED", changed=changed, impacted=impacted, radius=len(impacted))


def architectural_complexity_metrics(*, nodes: list[str], edges: list[list[str]]) -> dict[str, Any]:
    ids, norm = _graph({"nodes": nodes, "edges": edges})
    possible = max(1, len(ids) * (len(ids) - 1))
    density = len(norm) / possible
    return rec(
        "SUPER1200_ARCHITECTURAL_COMPLEXITY_METRICS/1",
        "COMPLEXITY_RECORDED",
        node_count=len(ids),
        edge_count=len(norm),
        density=density,
        cyclic=bool(_cycles(ids, norm)),
    )


def architectural_cost_model(*, nodes: list[str], costs: dict[str, int]) -> dict[str, Any]:
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("nodes_required")
    ids = [_name(n, "node_id") for n in nodes]
    if not isinstance(costs, dict):
        raise ValueError("costs_required")
    total = 0
    for ident in ids:
        if ident not in costs:
            raise ValueError("cost_missing")
        value = costs[ident]
        if not isinstance(value, int) or value < 0:
            raise ValueError("negative_cost_forbidden")
        total += value
    return rec("SUPER1200_ARCHITECTURAL_COST_MODEL/1", "COST_SUMMED", total=total)


def architectural_debt_ledger(*, entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(entries, list) or not entries:
        raise ValueError("debt_entries_required")
    prev = "0" * 64
    checked = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("debt_entry_invalid")
        ident = _name(entry.get("id"), "debt_id")
        principal = entry.get("principal")
        if not isinstance(principal, int) or principal < 0:
            raise ValueError("debt_principal_invalid")
        claimed = _sha(entry.get("prev_sha256"), "prev_sha256")
        if claimed != prev:
            raise ValueError("debt_chain_broken")
        body = {"id": ident, "principal": principal, "prev_sha256": claimed}
        prev = digest(body)
        checked.append(body)
    return rec("SUPER1200_ARCHITECTURAL_DEBT_LEDGER/1", "DEBT_CHAIN_VALID", entries=checked, head_sha256=prev)


def architectural_debt_interest(*, principal: int, rate: float) -> dict[str, Any]:
    if not isinstance(principal, int) or principal < 0:
        raise ValueError("interest_principal_invalid")
    if not isinstance(rate, (int, float)) or isinstance(rate, bool) or rate < 0:
        raise ValueError("interest_rate_invalid")
    interest = principal * float(rate)
    return rec("SUPER1200_ARCHITECTURAL_DEBT_INTEREST/1", "INTEREST_COMPUTED", principal=principal, rate=float(rate), interest=interest)


def architectural_refactoring_planner(*, roots: list[str], dead: list[str], drop: list[str]) -> dict[str, Any]:
    if not isinstance(roots, list):
        raise ValueError("refactor_roots_required")
    root_ids = {_name(r, "root") for r in roots}
    dead_ids = [_name(d, "dead") for d in dead] if isinstance(dead, list) else None
    if dead_ids is None:
        raise ValueError("refactor_dead_required")
    drop_ids = [_name(d, "drop") for d in drop] if isinstance(drop, list) else None
    if drop_ids is None:
        raise ValueError("refactor_drop_required")
    if any(item in root_ids for item in drop_ids):
        raise ValueError("refactor_would_drop_root")
    if any(item not in dead_ids for item in drop_ids):
        raise ValueError("refactor_drop_not_dead")
    return rec("SUPER1200_ARCHITECTURAL_REFACTORING_PLANNER/1", "REFACTOR_PLAN_RECORDED", steps=[{"drop": i} for i in drop_ids])


def architectural_regression_detector(*, baseline: dict[str, float], current: dict[str, float], tolerance: float) -> dict[str, Any]:
    if not isinstance(baseline, dict) or "cost" not in baseline:
        raise ValueError("regression_baseline_required")
    if not isinstance(current, dict) or "cost" not in current:
        raise ValueError("regression_current_required")
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or tolerance < 0:
        raise ValueError("regression_tolerance_invalid")
    base = baseline["cost"]
    cur = current["cost"]
    if not isinstance(base, (int, float)) or not isinstance(cur, (int, float)):
        raise ValueError("regression_cost_invalid")
    regressed = float(cur) > float(base) + float(tolerance)
    return rec(
        "SUPER1200_ARCHITECTURAL_REGRESSION_DETECTOR/1",
        "REGRESSION" if regressed else "NO_REGRESSION",
        baseline_cost=float(base),
        current_cost=float(cur),
        tolerance=float(tolerance),
    )


FUNCS: dict[int, tuple[str, Callable[..., dict[str, Any]]]] = {
    137: ("PROOF_CARRYING_API_CONTRACT", proof_carrying_api_contract),
    138: ("MODEL_CHECKING_FABRIC", model_checking_fabric),
    139: ("TLA_PLUS_PROVIDER", tla_plus_provider),
    140: ("APALACHE_PROVIDER", apalache_provider),
    141: ("ALLOY_PROVIDER", alloy_provider),
    142: ("DAFNY_PROVIDER", dafny_provider),
    143: ("SMT_PROVIDER", smt_provider),
    144: ("Z3_PROVIDER", z3_provider),
    145: ("PROPERTY_BASED_TESTING", property_based_testing),
    146: ("HYPOTHESIS_PROVIDER", hypothesis_provider),
    147: ("QUICKCHECK_STYLE_PROVIDER", quickcheck_style_provider),
    148: ("FUZZING_FABRIC", fuzzing_fabric),
    149: ("LIBFUZZER_PROVIDER", libfuzzer_provider),
    150: ("CARGO_FUZZ_PROVIDER", cargo_fuzz_provider),
    151: ("OSS_FUZZ_COMPATIBILITY", oss_fuzz_compatibility),
    152: ("STATE_MACHINE_TESTING", state_machine_testing),
    153: ("CONCURRENCY_MODEL_CHECKING", concurrency_model_checking),
    154: ("DEADLOCK_DETECTION", deadlock_detection),
    155: ("LIVENESS_PROPERTIES", liveness_properties),
    156: ("SAFETY_PROPERTIES", safety_properties),
    157: ("ARCHITECTURE_AS_DATA", architecture_as_data),
    158: ("ARCHITECTURE_SCHEMA", architecture_schema),
    159: ("ARCHITECTURE_GRAPH", architecture_graph),
    160: ("ARCHITECTURE_DIFF", architecture_diff),
    161: ("ARCHITECTURE_LINTER", architecture_linter),
    162: ("ARCHITECTURE_TESTER", architecture_tester),
    163: ("ARCHITECTURE_COMPILER", architecture_compiler),
    164: ("ARCHITECTURE_SIMULATOR", architecture_simulator),
    165: ("ARCHITECTURE_DEPENDENCY_ANALYZER", architecture_dependency_analyzer),
    166: ("ARCHITECTURE_CYCLE_DETECTOR", architecture_cycle_detector),
    167: ("ARCHITECTURE_DEAD_COMPONENT_DETECTOR", architecture_dead_component_detector),
    168: ("ARCHITECTURE_DUPLICATION_DETECTOR", architecture_duplication_detector),
    169: ("ARCHITECTURE_REACHABILITY_ANALYZER", architecture_reachability_analyzer),
    170: ("ARCHITECTURAL_BLAST_RADIUS", architectural_blast_radius),
    171: ("ARCHITECTURAL_COMPLEXITY_METRICS", architectural_complexity_metrics),
    172: ("ARCHITECTURAL_COST_MODEL", architectural_cost_model),
    173: ("ARCHITECTURAL_DEBT_LEDGER", architectural_debt_ledger),
    174: ("ARCHITECTURAL_DEBT_INTEREST", architectural_debt_interest),
    175: ("ARCHITECTURAL_REFACTORING_PLANNER", architectural_refactoring_planner),
    176: ("ARCHITECTURAL_REGRESSION_DETECTOR", architectural_regression_detector),
}
