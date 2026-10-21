import json
import pathlib
import unittest

HOME = pathlib.Path("/home/diegoignacionorambuenamiranda")
LANE = HOME / "PROYECTOS/1. PROYECTOS PRIORITARIOS/5. CUSTOSZ/0. CUSTOSZ  - OPERADOR/CUSTOSZ_CONTINUITY_V1/state/jobs/inteldoc_global_30mb_corrective_v7"
MISSION = json.loads((LANE / "INTELDOC_GLOBAL_30MB_CORRECTIVE_MISSION.json").read_text(encoding="utf-8"))

class CorrectiveMissionContract(unittest.TestCase):
    def test_exactly_five_original_sources_are_pinned(self):
        items = MISSION["inventory"]["pinned_originals"]
        self.assertEqual(len(items), 5)
        self.assertEqual(sum(x["bytes"] for x in items), 571137710)
        self.assertEqual(len({x["id"] for x in items}), 5)
        self.assertTrue(all(len(x["sha256"]) == 64 for x in items))

    def test_global_cap_decimal_and_strict(self):
        self.assertEqual(MISSION["global_limit"]["hard_cap_bytes"], 30000000)
        self.assertTrue(MISSION["execution_controls"]["fail_closed"])
        self.assertTrue(MISSION["execution_controls"]["source_modification"] == "FORBIDDEN")

    def test_runtime_tests_remain_deferred(self):
        self.assertEqual(MISSION["execution_controls"]["functional_smoke"], "DEFERRED_UNTIL_ALL_ARTIFACT_QUANTIZATION_FINISHED")
        self.assertEqual(MISSION["execution_controls"]["certification"], "NOT_GRANTED")

    def test_separates_direct_gguf_outputs_from_compact_option(self):
        strategy = MISSION["candidate_strategy"]
        self.assertIn("direct per-file", strategy["docling_text_gguf"].lower())
        self.assertIn("direct per-file", strategy["docling_mmproj_gguf"].lower())
        self.assertIn("separate option", strategy["compact_comparison"].lower())

    def test_worker_creates_candidate_parents_before_copy(self):
        worker = (LANE / "inteldoc_five_artifact_corrective_worker_v5.py").read_text(encoding="utf-8")
        self.assertIn("calibre_best.parent.mkdir(parents=True, exist_ok=True)", worker)
        self.assertIn("rec_src_best.parent.mkdir(parents=True, exist_ok=True)", worker)
        self.assertIn("wheel_best.parent.mkdir(parents=True, exist_ok=True)", worker)


    def test_text_gguf_uses_q2_k_without_imatrix(self):
        worker = (LANE / "inteldoc_five_artifact_corrective_worker_v5.py").read_text(encoding="utf-8")
        self.assertIn('text_out = direct / "docling" / "granite-docling-258M-Q2_K.gguf"', worker)
        self.assertIn('text_metrics = run_quantizer(gguf_text, text_out, "Q2_K")', worker)
        self.assertNotIn('text_metrics = run_quantizer(gguf_text, text_out, "IQ1_S")', worker)

    def test_prior_candidates_are_hash_pinned_before_reuse(self):
        worker = (LANE / "inteldoc_five_artifact_corrective_worker_v5.py").read_text(encoding="utf-8")
        self.assertIn("PRIOR_SOURCE_CANDIDATE_PIN_MISMATCH", worker)
        self.assertIn("PRIOR_WHEEL_CANDIDATE_PIN_MISMATCH", worker)
        self.assertIn('["xz", "-t", str(prior_source_candidate)]', worker)

if __name__ == "__main__":
    unittest.main()
