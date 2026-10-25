from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[1]
RUNTIME = REPOSITORY / "cajita-luna-runtime"
sys.path.insert(0, str(RUNTIME))

import cajita_tokenizer_materializer as materializer


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_tree_hash(rows: list[dict]) -> str:
    ordered = sorted(rows, key=lambda item: item["path"].encode("utf-8"))
    raw = json.dumps(ordered, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return digest(raw)


class _FakeLoader:
    @classmethod
    def from_pretrained(cls, model_path, **kwargs):
        model = Path(model_path)
        return {
            "model_path": model,
            "tokenizer": (model / "tokenizer.json").read_bytes(),
            "config": (model / "config.json").read_bytes(),
            "kwargs": kwargs,
        }


class _AlternateProcessor:
    @classmethod
    def from_pretrained(cls, model_path, **kwargs):
        model = Path(model_path)
        return {"config": (model / "config.json").read_bytes(), "kwargs": kwargs}


class TokenizerMaterializerTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, bytes]:
        model = root / "D01" / "Cerebro"
        model.mkdir(parents=True)
        # Repeated token entries ensure this fixture exercises actual size savings.
        original = json.dumps({"version": "1.0", "tokens": [f"token-{i:06d}" for i in range(9000)]},
                              separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        (model / "tokenizer.json").write_bytes(original)
        (model / "config.json").write_bytes(b'{"model_type":"test"}\n')
        return model, original

    def test_gzip_is_lossless_deterministic_and_keeps_source_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, original = self._fixture(root)
            rel = (model.relative_to(root) / "tokenizer.json").as_posix()
            first = materializer.prepare_compressed_tokenizers(root, (rel,))
            packed = model / "tokenizer.json.gz"
            first_bytes = packed.read_bytes()
            second = materializer.prepare_compressed_tokenizers(root, (rel,))
            self.assertEqual(packed.read_bytes(), first_bytes)
            self.assertEqual((model / "tokenizer.json").read_bytes(), original)
            entry = second["entries"][0]
            self.assertTrue(entry["packed"])
            self.assertEqual(entry["source_bytes"], len(original))
            self.assertEqual(entry["source_sha256"], digest(original))
            self.assertEqual(gzip_decompress(first_bytes), original)
            self.assertLess(entry["compressed_bytes"], entry["source_bytes"])
            self.assertEqual(entry["compressed_sha256"], digest(first_bytes))
            self.assertEqual(second["source_bytes_total"] - second["compressed_bytes_total"],
                             second["bytes_saved_total"])

    def test_compressed_view_loads_identical_tokenizer_after_raw_source_is_omitted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, original = self._fixture(root)
            rel = (model.relative_to(root) / "tokenizer.json").as_posix()
            materializer.prepare_compressed_tokenizers(root, (rel,))
            raw_path = model / "tokenizer.json"
            raw_path.unlink()
            result = materializer.load_pretrained_with_compressed_tokenizer(
                model, _FakeLoader, local_files_only=True, trust_remote_code=False
            )
            self.assertEqual(result["tokenizer"], original)
            self.assertEqual(result["config"], b'{"model_type":"test"}\n')
            self.assertTrue(result["kwargs"]["local_files_only"])
            self.assertFalse(result["model_path"].exists())
            self.assertFalse(raw_path.exists())

    def test_tree_hash_is_identical_before_and_after_tokenizer_compression(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, original = self._fixture(root)
            rel = (model.relative_to(root) / "tokenizer.json").as_posix()
            manifest = materializer.prepare_compressed_tokenizers(root, (rel,))
            entry = manifest["entries"][0]
            source_rows = [
                {"path": "config.json", "bytes": (model / "config.json").stat().st_size,
                 "sha256": materializer.sha256_file(model / "config.json")},
                {"path": "tokenizer.json", "bytes": len(original), "sha256": digest(original)},
                {"path": "tokenizer.json.gz", "bytes": (model / "tokenizer.json.gz").stat().st_size,
                 "sha256": materializer.sha256_file(model / "tokenizer.json.gz")},
            ]
            source_tree = materializer.tokenizer_tree_rows(model, root, source_rows)
            (model / "tokenizer.json").unlink()
            package_rows = [
                {"path": "config.json", "bytes": (model / "config.json").stat().st_size,
                 "sha256": materializer.sha256_file(model / "config.json")},
                {"path": "tokenizer.json.gz", "bytes": (model / "tokenizer.json.gz").stat().st_size,
                 "sha256": materializer.sha256_file(model / "tokenizer.json.gz")},
            ]
            package_tree = materializer.tokenizer_tree_rows(model, root, package_rows)
            self.assertEqual(source_tree, package_tree)
            self.assertEqual(canonical_tree_hash(source_tree), canonical_tree_hash(package_tree))
            self.assertEqual(package_tree[-1]["path"], "tokenizer.json")
            self.assertEqual(package_tree[-1]["sha256"], entry["source_sha256"])

    def test_processor_without_tokenizer_json_uses_original_local_loader(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, _ = self._fixture(root)
            rel = (model.relative_to(root) / "tokenizer.json").as_posix()
            materializer.prepare_compressed_tokenizers(root, (rel,))
            alternate = root / "4. Traductor Inteligente" / "Traducción general"
            alternate.mkdir(parents=True)
            (alternate / "config.json").write_bytes(b'{"processor":"sentencepiece"}\\n')
            result = materializer.load_pretrained_with_compressed_tokenizer(
                alternate, _AlternateProcessor, local_files_only=True
            )
            self.assertEqual(result["config"], b'{"processor":"sentencepiece"}\\n')
            self.assertTrue(result["kwargs"]["local_files_only"])

    def test_tampered_compressed_payload_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, _ = self._fixture(root)
            rel = (model.relative_to(root) / "tokenizer.json").as_posix()
            manifest = materializer.prepare_compressed_tokenizers(root, (rel,))
            packed = model / "tokenizer.json.gz"
            packed.write_bytes(packed.read_bytes() + b"x")
            with self.assertRaisesRegex(materializer.TokenizerMaterializationError, "TOKENIZER_COMPRESSED_SIZE_MISMATCH|TOKENIZER_COMPRESSED_SHA_MISMATCH"):
                materializer.load_tokenizer_manifest(root)

    def test_source_tampering_fails_closed_before_loader_invocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, _ = self._fixture(root)
            rel = (model.relative_to(root) / "tokenizer.json").as_posix()
            materializer.prepare_compressed_tokenizers(root, (rel,))
            (model / "tokenizer.json").write_bytes(b'{"changed":true}')
            with self.assertRaisesRegex(materializer.TokenizerMaterializationError, "TOKENIZER_SOURCE_IDENTITY_MISMATCH"):
                materializer.load_pretrained_with_compressed_tokenizer(model, _FakeLoader)


def gzip_decompress(value: bytes) -> bytes:
    import gzip
    return gzip.decompress(value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
