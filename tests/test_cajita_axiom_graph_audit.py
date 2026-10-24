from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from cajita_axiom_graph_audit import (
    END_HEADING,
    HEADING,
    legacy_census,
    expected_block,
    parse_legacy,
    parse_materialized,
    validate_materialized,
)


def row(axiom_id: str, class_name: str, first_text: str, block: int, trace_id: str | None = None) -> str:
    trace = trace_id or f"TRACE-V11-B{block:03d}::{axiom_id}"
    return "  " + axiom_id.ljust(18) + class_name.ljust(18) + first_text.ljust(21) + trace


class AxiomGraphAuditTests(unittest.TestCase):
    def test_materialized_rows_preserve_content_trace_and_line_provenance(self):
        text = "\n".join([
            HEADING,
            row("AX02415", "IDENTITY", "The canonical", 15),
            " " * 38 + "subject of".ljust(21),
            " " * 38 + "Criminology SHALL".ljust(21),
            " " * 38 + "remain bounded.".ljust(21),
            "",
            row("AX02416", "IDENTITY", "Claims attributed", 15),
            " " * 38 + "to Criminology".ljust(21),
            END_HEADING,
        ])
        records = parse_materialized(text)
        self.assertEqual([r["id"] for r in records], ["AX02415", "AX02416"])
        self.assertEqual(records[0]["block"], "B015")
        self.assertEqual(records[0]["trace"], "TRACE-V11-B015::AX02415")
        self.assertIn("Criminology SHALL", records[0]["text"])
        self.assertGreater(records[0]["line"], 1)

    def test_mismatched_trace_fails_closed(self):
        text = "\n".join([
            HEADING,
            row("AX02415", "IDENTITY", "The canonical", 15, "TRACE-V11-B015::AX02416"),
            END_HEADING,
        ])
        with self.assertRaisesRegex(ValueError, "AXIOM_ROW_TRACE_MISMATCH"):
            parse_materialized(text)

    def test_legacy_census_reports_duplicates_without_rewriting_source(self):
        rows = parse_legacy("id: AX0001\nid: AX0003\nid: AX0003\n")
        result = legacy_census(rows)
        self.assertEqual(result["definition_records"], 3)
        self.assertEqual(result["distinct_numeric_ids"], 2)
        self.assertEqual(result["repeated_definition_records"], 1)
        self.assertEqual(result["numeric_gaps_1_2414"], 2412)

    def test_block_allocation_boundaries_are_deterministic(self):
        self.assertEqual(expected_block(2415), 15)
        self.assertEqual(expected_block(5774), 54)
        self.assertEqual(expected_block(5775), 55)
        self.assertEqual(expected_block(12414), 134)
        with self.assertRaisesRegex(ValueError, "AXIOM_OUTSIDE_MATERIALIZED_RANGE"):
            expected_block(2414)

    def test_full_materialized_range_has_10000_unique_ids_and_120_blocks(self):
        records = []
        for n in range(2415, 12415):
            block = expected_block(n)
            aid = f"AX{n:05d}"
            records.append({"id": aid, "numeric": n, "class": "IDENTITY",
                            "text": f"proposition {n}", "trace": f"TRACE-V11-B{block:03d}::{aid}",
                            "block": f"B{block:03d}", "line": n})
        result = validate_materialized(records)
        self.assertEqual(result["record_count"], 10000)
        self.assertEqual(result["block_count"], 120)
        self.assertTrue(result["contiguous"])
        self.assertEqual(result["block_counts"]["B015"], 84)
        self.assertEqual(result["block_counts"]["B134"], 83)


if __name__ == "__main__":
    unittest.main()
