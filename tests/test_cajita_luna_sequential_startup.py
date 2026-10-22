import json
import tempfile
import unittest
from pathlib import Path

import cajita_luna_sequential_startup as sut


class SequentialStartupTests(unittest.TestCase):
    def test_block_sequence_is_canonical(self):
        rows = [
            {"block_id": block_id, "status": ("PASS" if i < 2 else "HOLD")}
            for i, (block_id, _) in enumerate(sut.BLOCKS[:3])
        ]
        rows.extend(
            {"block_id": block_id, "status": "NOT_STARTED_PREDECESSOR_HOLD"}
            for block_id, _ in sut.BLOCKS[3:]
        )
        self.assertTrue(sut.validate_block_order(rows))

    def test_out_of_order_blocks_fail_closed(self):
        rows = [{"block_id": "B2", "status": "PASS"}, {"block_id": "B1", "status": "PASS"}]
        self.assertFalse(sut.validate_block_order(rows))

    def test_later_block_cannot_run_after_hold(self):
        rows = [
            {"block_id": "B1", "status": "PASS"},
            {"block_id": "B2", "status": "HOLD"},
            {"block_id": "B3", "status": "PASS"},
        ]
        self.assertFalse(sut.validate_block_order(rows))

    def test_custos_inactive_blocks_transformations(self):
        status = {"active_authorized": False, "certification": "NOT_GRANTED"}
        self.assertFalse(sut.transformations_allowed(status, "PASS", "READY_FOR_CONTROLLED_OPTIMIZATION"))

    def test_passes_require_all_independent_gates(self):
        status = {"active_authorized": True, "certification": "GRANTED"}
        self.assertTrue(sut.transformations_allowed(status, "PASS", "READY_FOR_CONTROLLED_OPTIMIZATION"))
        self.assertFalse(sut.transformations_allowed(status, "HOLD", "READY_FOR_CONTROLLED_OPTIMIZATION"))
        self.assertFalse(sut.transformations_allowed(status, "PASS", "BLOCKED"))

    def test_hash_chained_events_detect_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "events.jsonl"
            sut.append_event(path, {"timestamp_utc": "2026-10-22T00:00:00Z", "event_type": "A", "payload": {"n": 1}})
            sut.append_event(path, {"timestamp_utc": "2026-10-22T00:00:01Z", "event_type": "B", "payload": {"n": 2}})
            self.assertTrue(sut.validate_event_ledger(path))
            lines = path.read_text(encoding="utf-8").splitlines()
            row = json.loads(lines[0])
            row["payload"]["n"] = 99
            lines[0] = json.dumps(row)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.assertFalse(sut.validate_event_ledger(path))

    def test_domain_matrix_is_exactly_22(self):
        self.assertEqual(len(sut.EXPECTED_DOMAINS), 22)
        self.assertEqual(sut.EXPECTED_DOMAINS[0], "D01")
        self.assertEqual(sut.EXPECTED_DOMAINS[-1], "D22")

    def test_resource_budget_is_one_gibibyte(self):
        self.assertEqual(sut.RAM_BUDGET_BYTES, 1024**3)
        self.assertLessEqual(sut.CONTROLLER_AS_BYTES + sut.CHILD_AS_BYTES, sut.RAM_BUDGET_BYTES)


if __name__ == "__main__":
    unittest.main()
