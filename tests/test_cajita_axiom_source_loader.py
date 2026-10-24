from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from cajita_axiom_source_loader import verify_binding


class AxiomBindingTests(unittest.TestCase):
    def test_verified_source_prefix_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "install"
            multi = root / "cajita-luna-runtime" / "2. Orquestación" / "Multi + Interdisciplinar"
            multi.mkdir(parents=True)
            runtime = root / "cajita-luna-runtime"
            prefix = b"protected architecture"
            appendix = b"runtime appendix"
            doc = root / "Louksna1.md"
            doc.write_bytes(prefix + appendix)
            digest = lambda x: hashlib.sha256(x).hexdigest()
            (multi / "axiom_interdisciplinary_binding.json").write_text(json.dumps({
                "companion_artifact": {"sha256": digest(prefix + appendix)},
                "protected_architecture_prefix": {"bytes": len(prefix), "sha256": digest(prefix)},
                "target": {"id": "D02_MULTI_INTERDISCIPLINAR", "engine_ids": ["E06", "E07"]},
                "axiom_inventory": {"range": "AX0001-AX12414", "declared_materialized_count": 11757, "declared_gap_count": 657},
                "block_inventory": {"range": "B1-B134", "count": 134},
                "framework_count": 18
            }), encoding="utf-8")
            result = verify_binding(runtime)
            self.assertEqual(result["status"], "PASS_SOURCE_PREFIX_VERIFIED")
            self.assertEqual(result["target"]["id"], "D02_MULTI_INTERDISCIPLINAR")

    def test_tampered_companion_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "install"
            multi = root / "cajita-luna-runtime" / "2. Orquestación" / "Multi + Interdisciplinar"
            multi.mkdir(parents=True)
            runtime = root / "cajita-luna-runtime"
            doc = root / "Louksna1.md"
            doc.write_bytes(b"altered")
            (multi / "axiom_interdisciplinary_binding.json").write_text(json.dumps({
                "companion_artifact": {"sha256": "0" * 64},
                "protected_architecture_prefix": {"bytes": 1, "sha256": "0" * 64},
                "target": {"id": "D02_MULTI_INTERDISCIPLINAR", "engine_ids": []},
                "axiom_inventory": {}, "block_inventory": {}, "framework_count": 18
            }), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "COMPANION_HASH_MISMATCH"):
                verify_binding(runtime)


if __name__ == "__main__":
    unittest.main()
