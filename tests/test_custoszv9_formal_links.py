from __future__ import annotations

import hashlib
import unittest

from custoszv9.crfu.contracts import RuntimeContract, run_composed_contracts
from custoszv9.crfu.migration import MigrationWitness, validate_migration_witness


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestFormalRuntimeLinks(unittest.TestCase):
    def test_hoare_style_composition_requires_the_intermediate_bridge(self):
        first = RuntimeContract(
            "increment",
            lambda x: type(x) is int and x >= 0,
            lambda x: x + 1,
            lambda before, after: after == before + 1,
        )
        second = RuntimeContract(
            "double",
            lambda x: type(x) is int and x >= 1,
            lambda x: x * 2,
            lambda before, after: after == before * 2,
        )
        result = run_composed_contracts(first, second, lambda before, middle: middle == before + 1, 1)
        self.assertEqual(result["status"], "PASS_FOR_DECLARED_CONTRACTS")
        self.assertEqual(result["intermediate_state"], 2)
        self.assertEqual(result["final_state"], 4)
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["certification_propagation"])
        self.assertFalse(result["authority_transfer"])

    def test_contract_composition_holds_if_bridge_fails_and_second_is_not_called(self):
        called = []
        first = RuntimeContract("first", lambda x: True, lambda x: x + 1, lambda x, y: True)
        second = RuntimeContract(
            "second", lambda x: True,
            lambda x: called.append("execute") or x + 1,
            lambda x, y: True,
        )
        result = run_composed_contracts(first, second, lambda before, middle: False, 1)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["reason"], "POST_PRE_BRIDGE_NOT_ESTABLISHED")
        self.assertEqual(called, [])

    def test_contract_composition_fails_closed_on_postcondition_failure(self):
        first = RuntimeContract("first", lambda x: True, lambda x: x + 1, lambda x, y: False)
        second = RuntimeContract("second", lambda x: True, lambda x: x + 1, lambda x, y: True)
        result = run_composed_contracts(first, second, lambda before, middle: True, 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["reason"], "FIRST_POSTCONDITION_FAILED")
        self.assertFalse(result["certification_propagation"])

    def test_contract_composition_rejects_non_boolean_callback_results(self):
        first = RuntimeContract("first", lambda x: 1, lambda x: x + 1, lambda x, y: True)
        second = RuntimeContract("second", lambda x: True, lambda x: x + 1, lambda x, y: True)
        result = run_composed_contracts(first, second, lambda before, middle: True, 1)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["reason"], "FIRST_PRECONDITION_NOT_SATISFIED")

    def test_migration_witness_binds_exact_artifacts_and_declared_invariant(self):
        source = b"runtime-state-v1"
        target = b"runtime-state-v2"
        witness = MigrationWitness(
            source_version="v1",
            target_version="v2",
            source_artifact_sha256=sha(source),
            target_artifact_sha256=sha(target),
            invariant_id="task-id-and-journal-chain-preserved",
            invariant_proof_sha256=sha(b"reviewed invariant proof"),
            proof_status="VERIFIED",
            producer_identity="migration-producer",
            verifier_identity="independent-verifier",
            rollback_artifact_sha256=sha(b"rollback-v1"),
        )
        result = validate_migration_witness(
            witness, source, target,
            source_invariant_holds=True, target_invariant_holds=True,
        )
        self.assertEqual(result["status"], "PASS_FOR_DECLARED_INVARIANT")
        self.assertEqual(result["source_version"], "v1")
        self.assertEqual(result["target_version"], "v2")
        self.assertFalse(result["certification_propagation"])
        self.assertFalse(result["authority_transfer"])
        self.assertFalse(result["universal_migration_refinement_proven"])

    def test_migration_rejects_bytes_that_do_not_match_the_witness(self):
        source = b"runtime-state-v1"
        target = b"runtime-state-v2"
        witness = MigrationWitness(
            "v1", "v2", sha(source), sha(target), "invariant",
            sha(b"proof"), "VERIFIED", "producer", "reviewer", sha(b"rollback"),
        )
        result = validate_migration_witness(
            witness, source, b"tampered",
            source_invariant_holds=True, target_invariant_holds=True,
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["reason"], "MIGRATION_TARGET_ARTIFACT_MISMATCH")

    def test_migration_requires_an_independent_verifier_and_rollback_digest(self):
        source = b"source"
        target = b"target"
        base = dict(
            source_version="v1",
            target_version="v2",
            source_artifact_sha256=sha(source),
            target_artifact_sha256=sha(target),
            invariant_id="invariant",
            invariant_proof_sha256=sha(b"proof"),
            proof_status="VERIFIED",
            producer_identity="same",
            verifier_identity="same",
            rollback_artifact_sha256=sha(b"rollback"),
        )
        same_actor = validate_migration_witness(
            MigrationWitness(**base), source, target,
            source_invariant_holds=True, target_invariant_holds=True,
        )
        self.assertEqual(same_actor["status"], "HOLD")
        self.assertEqual(same_actor["reason"], "MIGRATION_REQUIRES_INDEPENDENT_VERIFIER")

        missing_rollback = {**base, "producer_identity":"producer", "verifier_identity":"reviewer",
                            "rollback_artifact_sha256":"not-a-digest"}
        no_rollback = validate_migration_witness(
            MigrationWitness(**missing_rollback), source, target,
            source_invariant_holds=True, target_invariant_holds=True,
        )
        self.assertEqual(no_rollback["status"], "HOLD")
        self.assertEqual(no_rollback["reason"], "MIGRATION_DIGEST_INVALID")


if __name__ == "__main__":
    unittest.main()
