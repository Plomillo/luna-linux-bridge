import unittest
from pathlib import Path

from tools.louksnapg2_gpu_preflight import load_matrix, repair_gate, SHA_RE

ROOT = Path(__file__).resolve().parents[1]


class GpuRepairInfrastructureTests(unittest.TestCase):
    def test_matrix_declares_exactly_five_original_models(self):
        matrix = load_matrix(ROOT)
        self.assertEqual(len(matrix["targets"]), 5)
        self.assertEqual(
            matrix["governance"]["global_distribution_limit_bytes"], 490000000
        )
        self.assertIs(matrix["governance"]["original_weights_mutable"], False)

    def test_model_sources_are_not_reclassified_as_repaired(self):
        matrix = load_matrix(ROOT)
        statuses = {row["adapter_status"] for row in matrix["targets"].values()}
        self.assertTrue(statuses.issubset({"NOT_IMPLEMENTED", "EXPERIMENTAL_FAILED"}))

    def test_source_and_dataset_revisions_require_full_commit_hashes(self):
        good = "a" * 40
        self.assertTrue(SHA_RE.fullmatch(good))
        self.assertFalse(SHA_RE.fullmatch("a" * 39))
        self.assertFalse(SHA_RE.fullmatch("latest"))

    def test_repair_gate_fails_closed_for_current_registry_states(self):
        matrix = load_matrix(ROOT)
        for spec in matrix["targets"].values():
            blockers = repair_gate(spec, "a" * 40, "org/dataset", "b" * 40)
            self.assertIn("REPAIR_ADAPTER_NOT_IMPLEMENTED_AND_TESTED", blockers)

    def test_repair_gate_requires_dataset_and_source_pins(self):
        spec = {"adapter_status": "IMPLEMENTED_AND_TESTED"}
        blockers = repair_gate(spec, "", "", "latest")
        self.assertIn("SOURCE_REVISION_NOT_PINNED_TO_40_HEX_SHA", blockers)
        self.assertIn("TRAINING_DATASET_ID_MISSING", blockers)
        self.assertIn(
            "TRAINING_DATASET_REVISION_NOT_PINNED_TO_40_HEX_SHA", blockers
        )


if __name__ == "__main__":
    unittest.main()
