from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from cajita_architecture_binding import _rows


class LouksnapG2ArchitectureBindingRegressionTests(unittest.TestCase):
    def test_tokenizer_materializer_is_loaded_from_the_exact_runtime_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "runtime"
            module = runtime / "D01_CEREBRO"
            module.mkdir(parents=True)
            payload = b"engine source bytes"
            (module / "engine.py").write_bytes(payload)
            (runtime / "CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json").write_text(
                json.dumps({
                    "schema": "CAJITA_COMPRESSED_TOKENIZER_MANIFEST/1.0",
                    "entries": [],
                }),
                encoding="utf-8",
            )
            (runtime / "cajita_tokenizer_materializer.py").write_text(
                "class TokenizerMaterializationError(RuntimeError):\\n"
                "    pass\\n"
                "def tokenizer_tree_rows(root, runtime, rows):\\n"
                "    return rows\\n",
                encoding="utf-8",
            )
            rows = _rows(module, runtime)
            self.assertEqual(rows, [{
                "path": "engine.py",
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }])

    def test_missing_materializer_fails_with_explicit_reason_not_unboundlocalerror(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "runtime"
            module = runtime / "D01_CEREBRO"
            module.mkdir(parents=True)
            (module / "engine.py").write_text("pass\n", encoding="utf-8")
            (runtime / "CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json").write_text(
                json.dumps({
                    "schema": "CAJITA_COMPRESSED_TOKENIZER_MANIFEST/1.0",
                    "entries": [],
                }),
                encoding="utf-8",
            )
            (runtime / "cajita_tokenizer_materializer.py").write_text("# placeholder\n", encoding="utf-8")
            (runtime / "cajita_tokenizer_materializer.py").unlink()
            with self.assertRaisesRegex(RuntimeError, "TARGET_MODULE_TOKENIZER_MATERIALIZER_MISSING_OR_UNSAFE"):
                _rows(module, runtime)


if __name__ == "__main__":
    unittest.main()
