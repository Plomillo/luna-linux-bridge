from __future__ import annotations

import hashlib
import json
import pathlib
import tempfile
import unittest
from unittest import mock

import apply_engine_overlay_v1 as installer
import checkpoint_v1


class AdditiveOverlayInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="lunita-overlay-test-")
        self.base = pathlib.Path(self.temporary.name)
        self.rootfs = self.base / "rootfs"
        self.rootfs.mkdir()
        self.launcher = self.rootfs / "agent/lunita.py"
        self.launcher.parent.mkdir(parents=True)
        self.launcher.write_text("# candidate launcher test fixture\n", encoding="utf-8")
        self.source = self.base / "source"
        self.source.mkdir()
        for filename in installer.FILES:
            (self.source / filename).write_text(f"additive fixture {filename}\n", encoding="utf-8")
        vendor = self.source / "vendor/python3.12/site-packages"
        vendor.mkdir(parents=True)
        (vendor / "runtime_fixture.py").write_text("VENDORED_RUNTIME = True\n", encoding="utf-8")
        model_cache = self.source / "model-cache/fastembed"
        model_cache.mkdir(parents=True)
        (model_cache / "model-fixture.bin").write_bytes(b"hash-bound-model-fixture")
        (self.rootfs / "etc").mkdir()
        (self.rootfs / "etc/os-release").write_text("ID=ubuntu\nVERSION_ID=24.04\n", encoding="utf-8")
        self.checkpoint = self.base / "checkpoint"
        checkpoint = checkpoint_v1.create_checkpoint(self.rootfs, self.checkpoint)
        self.manifest = self.checkpoint / "MANIFEST.json"
        self.checkpoint_receipt = pathlib.Path(checkpoint["receipt_path"])
        self.launcher_digest = hashlib.sha256(self.launcher.read_bytes()).hexdigest()
        self.hash_patch = mock.patch.object(installer, "EXPECTED_LAUNCHER_SHA256", self.launcher_digest)
        self.hash_patch.start()
        self.addCleanup(self.hash_patch.stop)

    def tearDown(self):
        self.temporary.cleanup()

    def apply(self, **kwargs):
        arguments = {
            "rootfs": self.rootfs,
            "source_dir": self.source,
            "checkpoint_receipt": self.checkpoint_receipt,
            "candidate_id": installer.EXPECTED_CANDIDATE_ID,
            "apply": False,
        }
        arguments.update(kwargs)
        return installer.apply_overlay(**arguments)

    def test_dry_run_checks_hashes_and_does_not_mutate(self):
        result = self.apply()
        target = self.rootfs / installer.OVERLAY_RELATIVE_PATH
        self.assertEqual("DRY_RUN_PASS_NO_MUTATION", result["status"])
        self.assertFalse(result["mutated"])
        self.assertFalse(target.exists())
        self.assertFalse(target.parent.exists())

    def test_apply_creates_new_directory_with_exact_hashes_only(self):
        result = self.apply(apply=True)
        target = self.rootfs / installer.OVERLAY_RELATIVE_PATH
        self.assertEqual("APPLIED_ADDITIVELY_NOT_CERTIFIED", result["status"])
        self.assertTrue(target.is_dir())
        for filename in installer.FILES:
            self.assertEqual(
                hashlib.sha256((self.source / filename).read_bytes()).hexdigest(),
                hashlib.sha256((target / filename).read_bytes()).hexdigest(),
            )
        receipt = json.loads((target / "OVERLAY_APPLY_RECEIPT.json").read_text(encoding="utf-8"))
        self.assertEqual("NOT_GRANTED", receipt["certification"])
        self.assertFalse(receipt["launcher_mutated"])
        self.assertFalse(receipt["model_weights_mutated"])
        self.assertFalse(receipt["frozen_g06_mutated"])
        self.assertFalse(receipt["canonical_g08_mutated"])

    def test_reapplication_is_denied_without_overwrite(self):
        self.apply(apply=True)
        target = self.rootfs / installer.OVERLAY_RELATIVE_PATH
        before = hashlib.sha256((target / "OVERLAY_APPLY_RECEIPT.json").read_bytes()).hexdigest()
        with self.assertRaises(installer.GateError):
            self.apply(apply=True)
        after = hashlib.sha256((target / "OVERLAY_APPLY_RECEIPT.json").read_bytes()).hexdigest()
        self.assertEqual(before, after)

    def test_checkpoint_directory_inside_rootfs_is_denied(self):
        with self.assertRaises(checkpoint_v1.CheckpointError):
            checkpoint_v1.create_checkpoint(
                self.rootfs,
                self.rootfs / "var/lib/lunita/checkpoints",
            )

    def test_checkpoint_directory_containing_rootfs_is_denied(self):
        with self.assertRaises(checkpoint_v1.CheckpointError):
            checkpoint_v1.create_checkpoint(self.rootfs, self.base)

    def test_checkpoint_does_not_require_external_worker_identity(self):
        receipt = json.loads(self.checkpoint_receipt.read_text(encoding="utf-8"))
        receipt.pop("worker_version", None)
        self.checkpoint_receipt.write_text(json.dumps(receipt), encoding="utf-8")
        result = self.apply()
        self.assertEqual("DRY_RUN_PASS_NO_MUTATION", result["status"])

    def test_launcher_hash_mismatch_is_denied(self):
        self.launcher.write_text("tampered launcher\n", encoding="utf-8")
        with self.assertRaises(installer.GateError):
            self.apply()
        self.assertFalse((self.rootfs / installer.OVERLAY_RELATIVE_PATH).exists())

    def test_missing_checkpoint_is_denied(self):
        self.checkpoint_receipt.unlink()
        with self.assertRaises(FileNotFoundError):
            self.apply()
        self.assertFalse((self.rootfs / installer.OVERLAY_RELATIVE_PATH).exists())

    def test_checkpoint_manifest_tampering_is_denied(self):
        self.manifest.write_text('{"checkpoint":"modified"}\n', encoding="utf-8")
        with self.assertRaises(installer.GateError):
            self.apply()
        self.assertFalse((self.rootfs / installer.OVERLAY_RELATIVE_PATH).exists())


    def test_checkpoint_is_bound_to_exact_rootfs_and_rejects_post_checkpoint_mutation(self):
        protected_file = self.rootfs / "etc/os-release"
        protected_file.write_text("ID=ubuntu\nVERSION_ID=24.04\nBUILD_ID=changed-after-checkpoint\n", encoding="utf-8")
        with self.assertRaises(installer.GateError):
            self.apply()
        self.assertFalse((self.rootfs / installer.OVERLAY_RELATIVE_PATH).exists())

    def test_checkpoint_cannot_be_replayed_against_a_different_rootfs_path(self):
        other_rootfs = self.base / "other-rootfs"
        import shutil
        shutil.copytree(self.rootfs, other_rootfs, symlinks=True)
        with self.assertRaises(installer.GateError):
            self.apply(rootfs=other_rootfs)
        self.assertFalse((other_rootfs / installer.OVERLAY_RELATIVE_PATH).exists())

    def test_manifest_content_cannot_be_substituted_even_with_a_recomputed_receipt_hash(self):
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["rootfs_path"] = str(self.base / "attacker-rootfs")
        self.manifest.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        receipt = json.loads(self.checkpoint_receipt.read_text(encoding="utf-8"))
        receipt["checkpoint_manifest_sha256"] = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        self.checkpoint_receipt.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaises(installer.GateError):
            self.apply()
        self.assertFalse((self.rootfs / installer.OVERLAY_RELATIVE_PATH).exists())

    def test_symlink_rootfs_is_denied(self):
        alias = self.base / "rootfs-alias"
        alias.symlink_to(self.rootfs, target_is_directory=True)
        with self.assertRaises(installer.GateError):
            installer.apply_overlay(alias, self.source, self.checkpoint_receipt,
                                    installer.EXPECTED_CANDIDATE_ID, False)

    def test_symlinked_target_parent_is_denied(self):
        engines = self.rootfs / "engines"
        engines.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(installer.GateError):
            self.apply()

    def test_missing_payload_is_denied(self):
        (self.source / "engine_runtime_v1.py").unlink()
        with self.assertRaises(installer.GateError):
            self.apply()


if __name__ == "__main__":
    unittest.main(verbosity=2)
