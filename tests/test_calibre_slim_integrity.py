from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[1]
LAUNCHER = REPOSITORY / "cajita-luna-runtime" / "5. Inteligencia documental" / "Conversión documental" / "Calibre Slim" / "calibre-slim-convert.py"
SPEC = importlib.util.spec_from_file_location("calibre_slim_launcher_under_test", LAUNCHER)
assert SPEC and SPEC.loader
launcher = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = launcher
SPEC.loader.exec_module(launcher)

LOCK = {
    "schema": "CAJITA_CALIBRE_SLIM_SOURCE_LOCK/1.0",
    "candidate_id": "CAJITA_CALIBRE_SLIM_PDF_EPUB_V2_20261024",
    "upstream_repository": "https://github.com/kovidgoyal/calibre",
    "tag": "v9.17.0",
    "tag_object_sha": "58cfea71a2c2d893b853d73ca586ec9b28f7b2ba",
    "tag_signature_status": {"reported_by_github": "verified"},
    "commit_sha": "e6b9e09472f6e63f8a12bf376eb54836042f0f5f",
    "artifacts": [
        {"id":"CALIBRE_V9_17_0_LINUX_X86_64_BINARY","url":"https://github.com/kovidgoyal/calibre/releases/download/v9.17.0/calibre-9.17.0-x86_64.txz","filename":"calibre-9.17.0-x86_64.txz","size_bytes":201590724,"sha256":"953e4512a6482848cd803c88b6d942e6afca65dc3b67c7d1353ae048d616de53"},
        {"id":"CALIBRE_V9_17_0_SOURCE","url":"https://github.com/kovidgoyal/calibre/releases/download/v9.17.0/calibre-9.17.0.tar.xz","filename":"calibre-9.17.0.tar.xz","size_bytes":50661596,"sha256":"07507ea8ace5f8a0f768c13afdb799ad685a636c1cdbd8b11162ddb419743be5"}
    ],
}


def build_archive(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, mode="w:xz") as archive:
        for name, payload in members.items():
            item = tarfile.TarInfo(name)
            item.type = tarfile.REGTYPE
            item.mode = 0o644
            item.size = len(payload)
            archive.addfile(item, io.BytesIO(payload))


class CalibreSlimIntegrityTests(unittest.TestCase):
    def setUp(self):
        launcher.ARCHIVE_NAME = "calibre-slim-overlay.tar.xz"
        self.temp = tempfile.TemporaryDirectory(prefix="calibre-slim-integrity-")
        self.addCleanup(self.temp.cleanup)
        self.here = Path(self.temp.name)
        self.archive = self.here / launcher.ARCHIVE_NAME
        self.members = {
            "source/calibre/customize/builtins.py": b"# pinned Calibre overlay fixture\n",
            "source/calibre/__init__.py": b"__version__ = '9.17.0'\n",
            "evidence/overlay-lock.json": b'{"schema":"fixture"}\n',
        }
        build_archive(self.archive, self.members)
        launcher.ARCHIVE_BYTES = self.archive.stat().st_size
        launcher.ARCHIVE_SHA256 = hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def test_first_materialization_is_hash_bound_to_pinned_archive(self):
        source = launcher.materialize_overlay(self.here)
        self.assertTrue((source / "calibre" / "customize" / "builtins.py").is_file())
        self.assertEqual(
            hashlib.sha256((source / "calibre" / "customize" / "builtins.py").read_bytes()).hexdigest(),
            hashlib.sha256(self.members["source/calibre/customize/builtins.py"]).hexdigest(),
        )
        self.assertEqual(launcher.materialize_overlay(self.here), source)

    def test_tampered_cached_file_is_rejected_on_every_invocation(self):
        source = launcher.materialize_overlay(self.here)
        target = source / "calibre" / "customize" / "builtins.py"
        target.write_bytes(b"# modified after first extraction\n")
        with self.assertRaisesRegex(RuntimeError, "MATERIALIZED_OVERLAY_TREE_HASH_MISMATCH"):
            launcher.materialize_overlay(self.here)

    def test_unexpected_cached_file_is_rejected(self):
        source = launcher.materialize_overlay(self.here)
        (source / "unauthorized.py").write_text("pass\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "MATERIALIZED_OVERLAY_TREE_HASH_MISMATCH"):
            launcher.materialize_overlay(self.here)

    def test_cached_overlay_symlink_is_rejected(self):
        outside = self.here / "outside"
        outside.mkdir()
        (outside / "source").mkdir()
        (outside / "source" / "calibre").mkdir()
        (outside / "source" / "calibre" / "customize").mkdir()
        (outside / "source" / "calibre" / "customize" / "builtins.py").write_text("pass\n")
        cache = self.here / ".calibre-slim-overlay"
        cache.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "MATERIALIZED_OVERLAY_CACHE_UNSAFE"):
            launcher.materialize_overlay(self.here)

    def test_archive_hash_is_checked_even_when_cache_already_exists(self):
        launcher.materialize_overlay(self.here)
        self.archive.write_bytes(b"tampered")
        with self.assertRaisesRegex(RuntimeError, "archive size mismatch|archive SHA-256 mismatch"):
            launcher.materialize_overlay(self.here)

    def test_archive_path_traversal_is_rejected(self):
        bad = self.here / "bad.tar.xz"
        build_archive(bad, {"../escape.py": b"pass\n"})
        launcher.ARCHIVE_NAME = bad.name
        launcher.ARCHIVE_BYTES = bad.stat().st_size
        launcher.ARCHIVE_SHA256 = hashlib.sha256(bad.read_bytes()).hexdigest()
        with self.assertRaisesRegex(RuntimeError, "unsafe archive path"):
            launcher.materialize_overlay(self.here)

    def test_external_converter_must_report_pinned_upstream_version(self):
        lock = self.here / "source-lock.json"
        lock.write_text(json.dumps(LOCK), encoding="utf-8")
        converter = self.here / "ebook-convert"
        converter.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        converter.chmod(0o755)
        valid = SimpleNamespace(returncode=0, stdout="ebook-convert (calibre 9.17.0)\n")
        with patch.object(launcher.subprocess, "run", return_value=valid):
            result = launcher.verify_pinned_converter(str(converter), self.here)
        self.assertEqual(result["status"], "PASS_PINNED_VERSION")
        self.assertEqual(result["expected_version"], "9.17.0")

    def test_wrong_external_converter_version_fails_closed(self):
        lock = self.here / "source-lock.json"
        lock.write_text(json.dumps(LOCK), encoding="utf-8")
        converter = self.here / "ebook-convert"
        converter.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        converter.chmod(0o755)
        wrong = SimpleNamespace(returncode=0, stdout="ebook-convert (calibre 9.14.0)\n")
        with patch.object(launcher.subprocess, "run", return_value=wrong):
            with self.assertRaisesRegex(RuntimeError, "CALIBRE_RUNTIME_VERSION_MISMATCH"):
                launcher.verify_pinned_converter(str(converter), self.here)

    def test_wrong_official_tag_object_in_lock_fails_closed(self):
        lock = json.loads(json.dumps(LOCK))
        lock["tag_object_sha"] = "0" * 40
        (self.here / "source-lock.json").write_text(json.dumps(lock), encoding="utf-8")
        converter = self.here / "ebook-convert"
        converter.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        converter.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, "CALIBRE_SOURCE_LOCK_IDENTITY_MISMATCH"):
            launcher.verify_pinned_converter(str(converter), self.here)

    def test_official_release_asset_digest_and_size_are_locked(self):
        for field, bad_value in (("sha256", "0" * 64), ("size_bytes", 1)):
            with self.subTest(field=field):
                lock = json.loads(json.dumps(LOCK))
                lock["artifacts"][0][field] = bad_value
                (self.here / "source-lock.json").write_text(json.dumps(lock), encoding="utf-8")
                converter = self.here / "ebook-convert"
                converter.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                converter.chmod(0o755)
                with self.assertRaisesRegex(RuntimeError, "CALIBRE_SOURCE_LOCK_ARTIFACT_IDENTITY_MISMATCH"):
                    launcher.verify_pinned_converter(str(converter), self.here)

    def test_nonexact_calibre_versions_fail_closed(self):
        lock_path = self.here / "source-lock.json"
        lock_path.write_text(json.dumps(LOCK), encoding="utf-8")
        converter = self.here / "ebook-convert"
        converter.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        converter.chmod(0o755)
        for output in ("ebook-convert (calibre 19.17.0)\\n", "ebook-convert (calibre 9.17.00)\\n"):
            with self.subTest(output=output):
                with patch.object(launcher.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=output)):
                    with self.assertRaisesRegex(RuntimeError, "CALIBRE_RUNTIME_VERSION_MISMATCH"):
                        launcher.verify_pinned_converter(str(converter), self.here)

    def test_wrong_official_source_commit_in_lock_fails_closed(self):
        lock = dict(LOCK)
        lock["commit_sha"] = "0" * 40
        (self.here / "source-lock.json").write_text(json.dumps(lock), encoding="utf-8")
        converter = self.here / "ebook-convert"
        converter.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        converter.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, "CALIBRE_SOURCE_LOCK_IDENTITY_MISMATCH"):
            launcher.verify_pinned_converter(str(converter), self.here)


if __name__ == "__main__":
    unittest.main(verbosity=2)
