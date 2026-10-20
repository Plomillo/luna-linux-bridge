import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTINUATION = ROOT / "custosz_mision1_continuation_v1.py"
MISSION_CONTROL = HERE / "custoszv9_continuous_governor_v2.py"


class ContinuationControlContractTests(unittest.TestCase):
    def test_controller_uses_fail_closed_step_classification(self):
        source = CONTINUATION.read_text(encoding="utf-8")
        self.assertIn("if continuous_governor.result_blocks_step(result):", source)
        self.assertNotIn('if result.get("step_completion") is False:', source)

    def test_cajita_lane_runs_before_serial_wait_return(self):
        source = CONTINUATION.read_text(encoding="utf-8")
        tick = source[source.index("def tick():"):]
        lane = tick.index("continuous_governor.tick_cajita_priority_lane(")
        wait = tick.index('if wait > 0:')
        self.assertLess(lane, wait)
        self.assertIn('"parallel_lane": parallel_lane', tick)

    def test_mission_hash_is_pinned_and_no_automatic_certification(self):
        source = CONTINUATION.read_text(encoding="utf-8")
        lane = MISSION_CONTROL.read_text(encoding="utf-8")
        self.assertIn('MISSION_SHA = core.HS_MISSION', source)
        self.assertIn("CAJITA_LANE_MISSION_SHA256_MISMATCH", lane)
        self.assertIn('"certification": "NOT_GRANTED"', lane)
        self.assertIn('"mission_completion_claim": False', lane)

    def test_persistent_side_lane_is_versioned_and_does_not_overwrite_weights(self):
        lane = MISSION_CONTROL.read_text(encoding="utf-8")
        self.assertIn("cajita_priority_lane.json", lane)
        self.assertIn("cajita_candidates", lane)
        self.assertIn('"model_weights_modified": False', lane)
        self.assertIn('"source_shards_unchanged_by_size_and_mtime": unchanged', lane)


if __name__ == "__main__":
    unittest.main(verbosity=2)
