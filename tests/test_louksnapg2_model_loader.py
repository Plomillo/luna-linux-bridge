from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import louksnapg2_model_loader as loader


class ExternalizedModelLoaderTests(unittest.TestCase):
    def setUp(self):
        self.payloads = {
            "QWEN3_0_6B_Q2_K": b"qwen fixture bytes",
            "WHISPER_TINY_Q5_1": b"whisper fixture bytes",
        }
        self.specs = {
            model_id: {
                "path": f"models/{model_id}.bin",
                "repo": "trusted/example",
                "revision": "1" * 40,
                "file": f"{model_id}.bin",
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for model_id, payload in self.payloads.items()
        }
        self.root = tempfile.TemporaryDirectory()
        self.runtime_root = Path(self.root.name)

    def tearDown(self):
        self.root.cleanup()

    def fake_response(self, payload: bytes):
        response = mock.MagicMock()
        response.headers = {"Content-Length": str(len(payload))}
        response.geturl.return_value = "https://cas-bridge.xethub.hf.co/object/pinned"
        response.read.side_effect = [payload, b""]
        context = mock.MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        return response

    def test_registry_binds_two_expected_model_domains_and_pinned_revisions(self):
        with mock.patch.dict("louksnapg2_model_loader.EXPECTED_MODELS", self.specs, clear=True):
            registry = loader.model_registry()
        self.assertEqual(registry["activation_policy"], "EXPLICIT_MATERIALIZE_ONLY")
        self.assertEqual(
            {row["id"] for row in registry["models"]},
            {"QWEN3_0_6B_Q2_K", "WHISPER_TINY_Q5_1"},
        )
        self.assertTrue(all(len(row["revision"]) == 40 for row in registry["models"]))

    def test_url_pins_https_repository_revision_and_filename(self):
        with mock.patch.dict("louksnapg2_model_loader.EXPECTED_MODELS", self.specs, clear=True):
            registry = loader.model_registry()
        url = loader.source_url(registry["models"][0])
        self.assertTrue(url.startswith("https://huggingface.co/trusted/example/resolve/"))
        self.assertIn("1" * 40, url)
        self.assertTrue(url.endswith(registry["models"][0]["file"]))

    def test_materialization_streams_and_verifies_exact_bytes_and_hashes(self):
        with mock.patch.dict("louksnapg2_model_loader.EXPECTED_MODELS", self.specs, clear=True):
            with mock.patch(
                "urllib.request.urlopen",
                side_effect=[self.fake_response(self.payloads["QWEN3_0_6B_Q2_K"]),
                             self.fake_response(self.payloads["WHISPER_TINY_Q5_1"])],
            ):
                evidence = loader.materialize_models(self.runtime_root)
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(len(evidence["models"]), 2)
        for model_id, payload in self.payloads.items():
            target = self.runtime_root / "models" / f"{model_id}.bin"
            self.assertEqual(target.read_bytes(), payload)
            record = next(row for row in evidence["models"] if row["model_id"] == model_id)
            self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest())

    def test_wrong_hash_never_commits_model_file(self):
        altered = b"changed fixture payload"
        with mock.patch.dict("louksnapg2_model_loader.EXPECTED_MODELS", self.specs, clear=True):
            row = loader.model_registry()["models"][0]
            row = {**row, "bytes": len(altered), "sha256": "0" * 64}
            target = self.runtime_root / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            with mock.patch("urllib.request.urlopen", return_value=self.fake_response(altered)):
                with self.assertRaisesRegex(loader.ModelMaterializationError, "MODEL_SHA256_MISMATCH"):
                    loader._download(row, target)
            self.assertFalse(target.exists())

    def test_existing_wrong_payload_is_not_overwritten(self):
        with mock.patch.dict("louksnapg2_model_loader.EXPECTED_MODELS", self.specs, clear=True):
            first = self.specs["QWEN3_0_6B_Q2_K"]
            target = self.runtime_root / first["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"unexpected")
            with self.assertRaisesRegex(loader.ModelMaterializationError, "MODEL_CACHE_IDENTITY_MISMATCH"):
                loader.materialize_models(self.runtime_root)
            self.assertEqual(target.read_bytes(), b"unexpected")

    def test_model_directory_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.runtime_root / "models").symlink_to(Path(outside), target_is_directory=True)
            with mock.patch.dict("louksnapg2_model_loader.EXPECTED_MODELS", self.specs, clear=True):
                with self.assertRaisesRegex(loader.ModelMaterializationError, "MODEL_DIRECTORY_SYMLINK_FORBIDDEN"):
                    loader.materialize_models(self.runtime_root)


if __name__ == "__main__":
    unittest.main()
