from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cajita_externalized_packaging import materialize_registered_asset
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


class ExternalizedJenaInputTests(unittest.TestCase):
    def _fixture(self, root: Path, declared_sha: str | None = None):
        root.mkdir(parents=True, exist_ok=True)
        payload = b"test-container-bytes-not-a-real-archive"
        digest = hashlib.sha256(payload).hexdigest()
        (root / "test-jena.7z").write_bytes(payload)
        expected_sha = declared_sha or digest
        placement = {
            "assets": [{
                "id": "APACHE_JENA_6_2_0",
                "expanded_path": "cajita-luna-runtime/APACHE_JENA_6_2_0",
                "expanded_bytes": 123,
                "expanded_file_count": 7,
                "expanded_tree_sha256": "a" * 64,
                "container_sha256": expected_sha,
                "container_size_bytes": len(payload),
                "compact_runtime_container": {
                    "path": "cajita-luna-runtime/test-jena.7z",
                    "sha256": expected_sha,
                    "size_bytes": len(payload),
                },
            }]
        }
        (root / "EXTERNALIZED_ASSET_PLACEMENT.json").write_text(
            json.dumps(placement), encoding="utf-8"
        )
        return {"bytes": 123, "file_count": 7, "tree_sha256": "a" * 64}, digest

    def test_registered_jena_container_is_hash_bound_before_extraction(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "runtime"
            expected_tree, digest = self._fixture(root)
            destination = Path(temp_name) / "extracted" / "jena"
            with patch("cajita_externalized_packaging._extract_raw_tree", return_value=expected_tree) as extract:
                result = materialize_registered_asset(root, "APACHE_JENA_6_2_0", destination)
            self.assertEqual(result["status"], "PASS_REGISTERED_CONTAINER_RECONSTRUCTION")
            self.assertEqual(result["container_sha256"], digest)
            self.assertEqual(result["expanded_tree_sha256"], expected_tree["tree_sha256"])
            self.assertEqual(extract.call_count, 1)

    def test_tampered_registered_jena_container_fails_before_extraction(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "runtime"
            self._fixture(root, declared_sha="0" * 64)
            destination = Path(temp_name) / "extracted" / "jena"
            with patch("cajita_externalized_packaging._extract_raw_tree") as extract:
                with self.assertRaisesRegex(RuntimeError, "EXTERNALIZED_CONTAINER_IDENTITY_MISMATCH"):
                    materialize_registered_asset(root, "APACHE_JENA_6_2_0", destination)
            extract.assert_not_called()


if __name__ == "__main__":
    unittest.main()
