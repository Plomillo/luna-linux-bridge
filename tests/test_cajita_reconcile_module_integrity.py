from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from cajita_reconcile_module_integrity import canonical_tree_integrity


class CanonicalTreeIntegrityTests(unittest.TestCase):
    def test_tree_hash_is_order_independent(self):
        rows = [
            {"path": "b.bin", "bytes": 2, "sha256": "b" * 64},
            {"path": "a.json", "bytes": 1, "sha256": "a" * 64},
        ]
        self.assertEqual(canonical_tree_integrity(rows), canonical_tree_integrity(list(reversed(rows))))

    def test_tree_hash_counts_logical_source_bytes(self):
        rows = [
            {"path": "tokenizer.json", "bytes": 100, "sha256": "a" * 64},
            {"path": "runtime.py", "bytes": 25, "sha256": "b" * 64},
        ]
        result = canonical_tree_integrity(rows)
        self.assertEqual(result["file_count_excluding_module_descriptors"], 2)
        self.assertEqual(result["bytes_excluding_module_descriptors"], 125)
        self.assertEqual(len(result["sha256"]), 64)

    def test_duplicate_paths_are_rejected(self):
        rows = [
            {"path": "model.bin", "bytes": 1, "sha256": "a" * 64},
            {"path": "model.bin", "bytes": 1, "sha256": "a" * 64},
        ]
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            canonical_tree_integrity(rows)

    def test_malformed_digest_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA256_INVALID"):
            canonical_tree_integrity([{"path": "model.bin", "bytes": 1, "sha256": "not-a-digest"}])


if __name__ == "__main__":
    unittest.main()
