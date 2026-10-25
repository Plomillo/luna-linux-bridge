from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "cajita-luna-runtime"))

import cajita_runtime
import cajita_tokenizer_materializer


class RuntimeTokenizerSelftestTests(unittest.TestCase):
    def test_missing_raw_tokenizer_is_accepted_only_when_manifest_and_gzip_are_hash_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rel = "1. Cerebro/tokenizer.json"
            source = root / rel
            source.parent.mkdir(parents=True)
            # Highly repetitive content gives gzip a deterministic size benefit.
            source.write_bytes((b'{"tokens":["verified-token"],"version":"1.0"}\n' * 12000))
            manifest = cajita_tokenizer_materializer.prepare_compressed_tokenizers(root, (rel,))
            entry = manifest["entries"][0]
            self.assertTrue(entry["packed"])
            source.unlink()

            observed = cajita_runtime.asset_presence(root, rel)
            self.assertTrue(observed["present"])
            self.assertEqual(observed["representation"], "GZIP_HASH_PINNED_TOKENIZER")
            self.assertEqual(observed["sha256"], entry["source_sha256"])
            self.assertEqual(observed["compressed_sha256"], entry["compressed_sha256"])

    def test_corrupted_compressed_tokenizer_stays_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rel = "3. Transcripción/tokenizer.json"
            source = root / rel
            source.parent.mkdir(parents=True)
            source.write_bytes((b'{"vocabulary":["safe-token"],"version":"1.0"}\n' * 12000))
            manifest = cajita_tokenizer_materializer.prepare_compressed_tokenizers(root, (rel,))
            source.unlink()
            packed = root / manifest["entries"][0]["compressed_path"]
            packed.write_bytes(packed.read_bytes() + b"tamper")

            observed = cajita_runtime.asset_presence(root, rel)
            self.assertFalse(observed["present"])
            self.assertEqual(observed["representation"], "COMPRESSED_TOKENIZER_VALIDATION_FAILED")
            self.assertIn("TOKENIZER_COMPRESSED_SIZE_MISMATCH", observed["validation_error"])

    def test_raw_tokenizer_takes_precedence_when_present_and_regular(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rel = "1. Cerebro/tokenizer.json"
            source = root / rel
            source.parent.mkdir(parents=True)
            source.write_bytes(b'{"raw":"present"}\n')
            observed = cajita_runtime.asset_presence(root, rel)
            self.assertTrue(observed["present"])
            self.assertEqual(observed["representation"], "RAW_FILE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
