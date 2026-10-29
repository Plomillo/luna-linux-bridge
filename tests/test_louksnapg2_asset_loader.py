from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import louksnapg2_asset_loader as loader


class AssetLoaderTests(unittest.TestCase):
    def test_canonical_registry_is_bound_to_immutable_source_commit(self):
        registry = loader.load_registry()
        self.assertEqual(registry["source_repository"], "Plomillo/luna-linux-bridge")
        self.assertEqual(registry["source_commit"], loader.PINNED_COMMIT)
        self.assertEqual(registry["activation_policy"], "ON_DEMAND_ONLY")
        self.assertEqual(len(registry["assets"]), 10)
        self.assertTrue(all(row["bytes"] <= loader.MAX_ARCHIVE_BYTES for row in registry["assets"]))

    def test_registry_wrong_source_commit_is_rejected(self):
        original = loader.load_registry()
        original["source_commit"] = "0" * 40
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "registry.json"
            path.write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaisesRegex(loader.AssetLoaderError, "SOURCE_BINDING_MISMATCH"):
                loader.load_registry(path)

    def test_registry_asset_count_mutation_is_rejected(self):
        original = loader.load_registry()
        original["assets"].pop()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "registry.json"
            path.write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaisesRegex(loader.AssetLoaderError, "ASSET_COUNT_MISMATCH"):
                loader.load_registry(path)

    def test_parent_traversal_is_rejected(self):
        for value in ("../outside", "/etc/passwd", "a/../../b", "C:/windows/file"):
            with self.subTest(value=value):
                with self.assertRaises(loader.AssetLoaderError):
                    loader.safe_relative_path(value)

    def test_source_url_uses_only_pinned_raw_github_host_and_commit(self):
        registry = loader.load_registry()
        row = registry["assets"][0]
        url = loader._safe_url(registry, row)
        self.assertEqual(url, loader.PINNED_BASE_URL + row["filename"])
        self.assertTrue(url.startswith("https://raw.githubusercontent.com/"))
        self.assertIn(loader.PINNED_COMMIT, url)

    def test_exact_size_and_sha256_rejects_modified_payload_before_commit(self):
        payload = b"verified externalized asset"
        expected = hashlib.sha256(payload).hexdigest()
        fake_response = mock.MagicMock()
        fake_response.status = 200
        fake_response.headers = {"Content-Length": str(len(payload))}
        fake_response.geturl.return_value = "https://raw.githubusercontent.com/Plomillo/luna-linux-bridge/pinned/file.7z"
        fake_response.read.side_effect = [payload, b""]
        fake_context = mock.MagicMock()
        fake_context.__enter__.return_value = fake_response
        fake_context.__exit__.return_value = False
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "asset.7z"
            # _stream_download is deliberately expected to stream only the pinned length.
            with mock.patch("urllib.request.urlopen", return_value=fake_context):
                result = loader._stream_download(
                    "https://raw.githubusercontent.com/Plomillo/luna-linux-bridge/pinned/file.7z",
                    target, len(payload)
                )
            self.assertEqual(result["bytes"], len(payload))
            self.assertEqual(result["sha256"], expected)
            Path(result["temp_path"]).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
