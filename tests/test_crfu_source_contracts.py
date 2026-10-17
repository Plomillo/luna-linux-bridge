from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_crfu_source_contracts.py"
SPEC = importlib.util.spec_from_file_location("check_crfu_source_contracts_test", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("SOURCE_CONFORMANCE_CHECKER_IMPORT_FAILED")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class CRFUSourceContractConformanceTests(unittest.TestCase):
    def test_current_source_models_are_structurally_bound(self):
        result = checker.validate(ROOT, "a" * 40)
        self.assertEqual(result["result"], "PASS_STRUCTURAL_SOURCE_CONFORMANCE", result["failures"])
        self.assertFalse(result["universal_refinement_proven"])
        queue = next(row for row in result["contracts"] if row.get("contract") == "MISSION_QUEUE_FINITE_TRANSITION_GRAPH")
        self.assertEqual(queue["comparison"], "EXACT_FINITE_EDGE_SET")
        self.assertEqual(queue["runtime_edge_count"], queue["formal_edge_count"])

    def test_queue_model_drift_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in ("custoszv9/crfu/event_queue.py", "formal/crfu/MissionQueueSemantics.agda"):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text((ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8")
            model = root / "formal/crfu/MissionQueueSemantics.agda"
            model.write_text(model.read_text(encoding="utf-8").replace(
                "received-preflight : RECEIVED ↝ PREFLIGHT",
                "received-preflight : RECEIVED ↝ COMPLETED",
            ), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "QUEUE_TRANSITION_GRAPH_DRIFT"):
                checker.check_queue_graph(root)


if __name__ == "__main__":
    unittest.main()
