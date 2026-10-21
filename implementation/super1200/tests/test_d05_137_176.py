"""Behavioral tests for D05 capabilities 137-176. One positive and one negative each."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "domains" / "d05_137_176.py"
spec = importlib.util.spec_from_file_location("d05_137_176", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)

SHA_A = "a" * 64
SHA_B = "b" * 64
GENESIS = "0" * 64


def _ok_payloads():
    m = mod
    return {
        137: lambda: m.proof_carrying_api_contract(contract_id="c", version=1, request_schema={"q": "string"}, response_schema={"ok": "bool"}, proof_term_sha256=SHA_A, consumer_scope="SCOPED"),
        138: lambda: m.model_checking_fabric(states=["s", "bad"], init="s", transitions=[["s", "s"]], forbidden=["bad"]),
        139: lambda: m.tla_plus_provider(spec={"Init": "s", "Next": [["s", "s"]], "Invariant": ["bad"], "states": ["s", "bad"], "properties": ["liveness"], "fairness": True}),
        140: lambda: m.apalache_provider(bound=3, variables={"x": 1}, updates=[{"x": 2}]),
        141: lambda: m.alloy_provider(atoms=["A"], tuples=[["A"]], multiplicity="one"),
        142: lambda: m.dafny_provider(env={"x": 1}, pre=[{"var": "x", "op": ">=", "value": 0}], assigns={"x": 2}, post=[{"var": "x", "op": "==", "value": 2}]),
        143: lambda: m.smt_provider(constraints=[{"left": "x", "op": ">", "right": 0}], model={"x": 2}),
        144: lambda: m.z3_provider(logic="QF_IDL", constraints=[{"left": "x", "op": ">", "right": "y", "diff": True}], model={"x": 2, "y": 1}),
        145: lambda: m.property_based_testing(properties=[{"kind": "sorted", "samples": [[1, 2, 3]]}]),
        146: lambda: m.hypothesis_provider(seed=1, max_examples=4),
        147: lambda: m.quickcheck_style_provider(generator="bool", trials=2, seed=1),
        148: lambda: m.fuzzing_fabric(corpus=["61"], oracle="no_nul"),
        149: lambda: m.libfuzzer_provider(entrypoint="LLVMFuzzerTestOneInput", max_len=8, corpus=["61"]),
        150: lambda: m.cargo_fuzz_provider(crate="core", harness="fuzz_target_1"),
        151: lambda: m.oss_fuzz_compatibility(language="rust", fuzz_targets=["fuzz_parse"], dockerfile="Dockerfile"),
        152: lambda: m.state_machine_testing(start="a", transitions={"a": {"go": "b"}, "b": {}}, trace=["go"], accept=["b"]),
        153: lambda: m.concurrency_model_checking(threads=[[{"op": "write", "var": "x"}], [{"op": "read", "var": "y"}]]),
        154: lambda: m.deadlock_detection(edges=[]),
        155: lambda: m.liveness_properties(states=["a", "b"], init="a", transitions=[["a", "b"]], goal="b"),
        156: lambda: m.safety_properties(states=["a", "bad"], init="a", transitions=[["a", "a"]], forbidden=["bad"]),
        157: lambda: m.architecture_as_data(components=[{"id": "api", "owner": "core"}], relations=[]),
        158: lambda: m.architecture_schema(version=1, components=["api"], relations=[]),
        159: lambda: m.architecture_graph(nodes=["api"], edges=[]),
        160: lambda: m.architecture_diff(left={"nodes": ["a"], "edges": []}, right={"nodes": ["a", "b"], "edges": []}, claim_changed=True),
        161: lambda: m.architecture_linter(nodes=[{"id": "api", "owner": "core"}], edges=[], rules=["owner_required"]),
        162: lambda: m.architecture_tester(nodes=["api"], edges=[], assertions=[{"kind": "exists", "id": "api"}]),
        163: lambda: m.architecture_compiler(nodes=["a", "b"], edges=[["a", "b"]]),
        164: lambda: m.architecture_simulator(nodes=["a", "b"], edges=[["a", "b"]], tokens={"a": 1, "b": 0}, steps=1),
        165: lambda: m.architecture_dependency_analyzer(nodes=["a", "b"], edges=[["a", "b"]], component="a", direction="out"),
        166: lambda: m.architecture_cycle_detector(nodes=["a"], edges=[]),
        167: lambda: m.architecture_dead_component_detector(nodes=["a", "b"], edges=[], roots=["a"]),
        168: lambda: m.architecture_duplication_detector(names=["a", "b"]),
        169: lambda: m.architecture_reachability_analyzer(nodes=["a", "b"], edges=[["a", "b"]], roots=["a"]),
        170: lambda: m.architectural_blast_radius(nodes=["a", "b"], edges=[["a", "b"]], changed="a"),
        171: lambda: m.architectural_complexity_metrics(nodes=["a", "b"], edges=[["a", "b"]]),
        172: lambda: m.architectural_cost_model(nodes=["a"], costs={"a": 2}),
        173: lambda: m.architectural_debt_ledger(entries=[{"id": "d1", "principal": 3, "prev_sha256": GENESIS}]),
        174: lambda: m.architectural_debt_interest(principal=10, rate=0.5),
        175: lambda: m.architectural_refactoring_planner(roots=["api"], dead=["old"], drop=["old"]),
        176: lambda: m.architectural_regression_detector(baseline={"cost": 3}, current={"cost": 3}, tolerance=0),
    }


def _bad_payloads():
    m = mod
    return {
        137: ("api_contract_rejects_global_consumer", lambda: m.proof_carrying_api_contract(contract_id="c", version=1, request_schema={"q": "string"}, response_schema={"ok": "bool"}, proof_term_sha256=SHA_A, consumer_scope="GLOBAL")),
        138: ("init_unknown", lambda: m.model_checking_fabric(states=["s"], init="missing", transitions=[], forbidden=[])),
        139: ("liveness_requires_fairness", lambda: m.tla_plus_provider(spec={"Init": "s", "Next": [], "Invariant": [], "states": ["s"], "properties": ["liveness"], "fairness": False})),
        140: ("apalache_value_out_of_bound", lambda: m.apalache_provider(bound=1, variables={"x": 4}, updates=[])),
        141: ("alloy_one_requires_exactly_one_tuple", lambda: m.alloy_provider(atoms=["A"], tuples=[], multiplicity="one")),
        142: ("dafny_postcondition_failed", lambda: m.dafny_provider(env={"x": 1}, pre=[{"var": "x", "op": ">=", "value": 0}], assigns={"x": 2}, post=[{"var": "x", "op": "==", "value": 9}])),
        143: ("smt_constraints_required", lambda: m.smt_provider(constraints=[], model={})),
        144: ("z3_unsupported_logic", lambda: m.z3_provider(logic="HORN", constraints=[{"left": "x", "op": ">", "right": 0}], model={"x": 1})),
        145: ("property_kind_unknown", lambda: m.property_based_testing(properties=[{"kind": "magic", "samples": [[1]]}])),
        146: ("hypothesis_seed_required", lambda: m.hypothesis_provider(seed="x", max_examples=1)),
        147: ("quickcheck_generator_unknown", lambda: m.quickcheck_style_provider(generator="float", trials=1, seed=1)),
        148: ("fuzz_corpus_required", lambda: m.fuzzing_fabric(corpus=[], oracle="no_nul")),
        149: ("libfuzzer_max_len_required", lambda: m.libfuzzer_provider(entrypoint="fuzz", max_len=0, corpus=["61"])),
        150: ("harness_must_be_identifier", lambda: m.cargo_fuzz_provider(crate="core", harness="bad-name")),
        151: ("dockerfile_required", lambda: m.oss_fuzz_compatibility(language="c", fuzz_targets=["t"], dockerfile="")),
        152: ("state_machine_event_unknown", lambda: m.state_machine_testing(start="a", transitions={"a": {}}, trace=["nope"], accept=["a"])),
        153: ("concurrency_threads_required", lambda: m.concurrency_model_checking(threads=[[{"op": "read", "var": "x"}]])),
        154: ("deadlock_edge_must_be_pair", lambda: m.deadlock_detection(edges=[["only"]])),
        155: ("goal_unknown", lambda: m.liveness_properties(states=["a"], init="a", transitions=[], goal="z")),
        156: ("safety_property_required", lambda: m.safety_properties(states=["a"], init="a", transitions=[], forbidden=[])),
        157: ("component_owner_required", lambda: m.architecture_as_data(components=[{"id": "api"}], relations=[])),
        158: ("architecture_schema_version_required", lambda: m.architecture_schema(version=0, components=["api"], relations=[])),
        159: ("edge_endpoint_unknown", lambda: m.architecture_graph(nodes=["a"], edges=[["a", "missing"]])),
        160: ("false_change_claim", lambda: m.architecture_diff(left={"nodes": ["a"], "edges": []}, right={"nodes": ["a"], "edges": []}, claim_changed=True)),
        161: ("lint_rule_unknown", lambda: m.architecture_linter(nodes=[{"id": "a", "owner": "o"}], edges=[], rules=["drop_database"])),
        162: ("architecture_assertion_failed", lambda: m.architecture_tester(nodes=["a"], edges=[], assertions=[{"kind": "exists", "id": "missing"}])),
        163: ("architecture_cycle", lambda: m.architecture_compiler(nodes=["a", "b"], edges=[["a", "b"], ["b", "a"]])),
        164: ("simulator_steps_required", lambda: m.architecture_simulator(nodes=["a"], edges=[], tokens={"a": 1}, steps=-1)),
        165: ("component_unknown", lambda: m.architecture_dependency_analyzer(nodes=["a"], edges=[], component="z", direction="out")),
        166: ("nodes_required", lambda: m.architecture_cycle_detector(nodes=[], edges=[])),
        167: ("roots_required", lambda: m.architecture_dead_component_detector(nodes=["a"], edges=[], roots=None)),
        168: ("duplication_names_required", lambda: m.architecture_duplication_detector(names=[])),
        169: ("root_unknown", lambda: m.architecture_reachability_analyzer(nodes=["a"], edges=[], roots=["z"])),
        170: ("changed_node_unknown", lambda: m.architectural_blast_radius(nodes=["a"], edges=[], changed="z")),
        171: ("nodes_required", lambda: m.architectural_complexity_metrics(nodes=[], edges=[])),
        172: ("negative_cost_forbidden", lambda: m.architectural_cost_model(nodes=["a"], costs={"a": -1})),
        173: ("debt_chain_broken", lambda: m.architectural_debt_ledger(entries=[{"id": "d1", "principal": 1, "prev_sha256": SHA_B}])),
        174: ("interest_rate_invalid", lambda: m.architectural_debt_interest(principal=1, rate=-0.2)),
        175: ("refactor_would_drop_root", lambda: m.architectural_refactoring_planner(roots=["api"], dead=["api"], drop=["api"])),
        176: ("regression_baseline_required", lambda: m.architectural_regression_detector(baseline={}, current={"cost": 1}, tolerance=0)),
    }


class D05RemainderTests(unittest.TestCase):
    def test_catalog_covers_137_through_176(self):
        self.assertEqual(set(mod.FUNCS), set(range(137, 177)))
        for cid, (name, _fn) in mod.FUNCS.items():
            self.assertTrue(name)
            self.assertNotEqual(name, "GLOBAL")


def _bind(cid: int):
    def test(self):
        result = _ok_payloads()[cid]()
        self.assertFalse(result["certification_granted"])
        self.assertFalse(result["global_certification"])
        self.assertFalse(result["theorem_claim"])
        self.assertEqual(len(result["record_sha256"]), 64)
        err, bad = _bad_payloads()[cid]
        with self.assertRaisesRegex(ValueError, err):
            bad()
    return test


for _cid in range(137, 177):
    setattr(D05RemainderTests, f"test_cap_{_cid:04d}", _bind(_cid))


if __name__ == "__main__":
    unittest.main()
