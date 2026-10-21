"""D05 proof-lifecycle tests for capabilities 133-136."""
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "domains" / "D05_proof_lifecycle.py"
spec = importlib.util.spec_from_file_location("d05_proof_lifecycle", MODULE_PATH)
lifecycle = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lifecycle
spec.loader.exec_module(lifecycle)

class D05ProofLifecycleTests(unittest.TestCase):
    def test_invalidate_proof_closure_records_changed_and_dependents(self):
        rec = lifecycle.invalidate_proof_closure(
            graph_sha256="a" * 64,
            changed_node_ids=["A"],
            invalidated_all=["A", "L", "T"],
        )
        self.assertEqual(rec["decision"], "INVALIDATION_CLOSURE_RECORDED")
        self.assertFalse(rec["theorem_claim"])
        self.assertFalse(rec["certification_granted"])
        with self.assertRaisesRegex(ValueError, "changed_must_be_subset_of_invalidated"):
            lifecycle.invalidate_proof_closure(graph_sha256="a" * 64, changed_node_ids=["X"], invalidated_all=["A"])

    def test_proof_carrying_artifact_rejects_global_claim(self):
        art = lifecycle.build_proof_carrying_artifact(
            artifact_id="art-1", proof_term_sha256="a" * 64, source_sha256="b" * 64, claim_scope="SCOPED"
        )
        self.assertEqual(art["decision"], "PROOF_BOUND_TO_ARTIFACT_DESCRIPTOR")
        self.assertFalse(art["global_certification"])
        with self.assertRaisesRegex(ValueError, "proof_carrying_artifact_must_not_claim_global"):
            lifecycle.build_proof_carrying_artifact(
                artifact_id="art-2", proof_term_sha256="a" * 64, source_sha256="b" * 64, claim_scope="GLOBAL"
            )

    def test_bind_proof_carrying_configuration_is_hash_bound(self):
        cfg = lifecycle.bind_proof_carrying_configuration(
            config_id="cfg-1", config_sha256="c" * 64, proof_artifact_sha256="d" * 64
        )
        self.assertEqual(cfg["decision"], "CONFIG_BOUND_TO_PROOF_DESCRIPTOR")
        self.assertFalse(cfg["theorem_claim"])
        with self.assertRaisesRegex(ValueError, "config_sha256_must_be_lowercase_sha256"):
            lifecycle.bind_proof_carrying_configuration(
                config_id="cfg-bad", config_sha256="not-a-hash", proof_artifact_sha256="d" * 64
            )

    def test_record_proof_carrying_migration_requires_distinct_states(self):
        mig = lifecycle.record_proof_carrying_migration(
            migration_id="mig-1", from_sha256="e" * 64, to_sha256="f" * 64, proof_artifact_sha256="d" * 64
        )
        self.assertEqual(mig["decision"], "MIGRATION_BOUND_TO_PROOF_DESCRIPTOR")
        self.assertFalse(mig["global_certification"])
        with self.assertRaisesRegex(ValueError, "migration_requires_distinct_states"):
            lifecycle.record_proof_carrying_migration(
                migration_id="mig-same", from_sha256="e" * 64, to_sha256="e" * 64, proof_artifact_sha256="d" * 64
            )

if __name__ == "__main__":
    unittest.main()
