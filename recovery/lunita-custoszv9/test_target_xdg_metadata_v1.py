from __future__ import annotations

import json
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

RUNTIME_DIR = pathlib.Path(__file__).parent / "runtime_engines_v1"
sys.path.insert(0, str(RUNTIME_DIR))

import target_runtime_acceptance_v1 as target


class TargetXDGMetadataGateTests(unittest.TestCase):
    def setUp(self):
        self.path = pathlib.Path("/tmp/lunita-rootfs/tmp/lunita-xdg/audit")

    @mock.patch.object(target.subprocess, "run")
    def test_private_directory_is_inspected_with_read_only_root_lstat(self, run):
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout=json.dumps({
                "is_symlink": False,
                "is_directory": True,
                "uid": 1000,
                "gid": 1000,
                "mode": 0o700,
            }),
            stderr="",
        )

        result = target.inspect_rootfs_directory_as_root(self.path, "audit directory")

        self.assertEqual(1000, result["uid"])
        self.assertEqual(1000, result["gid"])
        self.assertEqual(0o700, result["mode"])
        command = run.call_args.args[0]
        self.assertEqual(["sudo", "-n", "/usr/bin/python3"], command[:3])
        self.assertEqual(str(self.path), command[-1])
        self.assertTrue(run.call_args.kwargs["check"] is False)

    @mock.patch.object(target.subprocess, "run")
    def test_wrong_owner_or_mode_is_denied(self, run):
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout=json.dumps({
                "is_symlink": False,
                "is_directory": True,
                "uid": 0,
                "gid": 0,
                "mode": 0o755,
            }),
            stderr="",
        )
        with self.assertRaises(target.TargetGateError):
            target.inspect_rootfs_directory_as_root(self.path, "audit directory")

    @mock.patch.object(target.subprocess, "run")
    def test_symlink_is_denied(self, run):
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout=json.dumps({
                "is_symlink": True,
                "is_directory": False,
                "uid": 1000,
                "gid": 1000,
                "mode": 0o700,
            }),
            stderr="",
        )
        with self.assertRaises(target.TargetGateError):
            target.inspect_rootfs_directory_as_root(self.path, "audit directory")

    @mock.patch.object(target.subprocess, "run")
    def test_privileged_inspection_failure_fails_closed(self, run):
        run.return_value = SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="sudo: a password is required",
        )
        with self.assertRaisesRegex(target.TargetGateError, "Privileged read-only lstat failed"):
            target.inspect_rootfs_directory_as_root(self.path, "audit directory")


class TargetXDGFileMetadataGateTests(unittest.TestCase):
    def setUp(self):
        self.path = pathlib.Path(
            "/tmp/lunita-rootfs/tmp/lunita-xdg/audit/engine-execution.jsonl"
        )
        self.valid_metadata = {
            "is_symlink": False,
            "is_regular_file": True,
            "uid": 1000,
            "gid": 1000,
            "mode": 0o600,
            "size": 128,
            "sha256": "a" * 64,
        }

    @mock.patch.object(target.subprocess, "run")
    def test_private_audit_file_is_read_and_hashed_with_privileged_read_only_open(self, run):
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout=json.dumps(self.valid_metadata),
            stderr="",
        )

        result = target.inspect_rootfs_regular_file_as_root(
            self.path, "engine audit log"
        )

        self.assertEqual(1000, result["uid"])
        self.assertEqual(1000, result["gid"])
        self.assertEqual(0o600, result["mode"])
        self.assertEqual(128, result["size"])
        self.assertEqual("a" * 64, result["sha256"])
        command = run.call_args.args[0]
        self.assertEqual(["sudo", "-n", "/usr/bin/python3", "-c"], command[:4])
        self.assertEqual(str(self.path), command[-1])
        inspector = command[4]
        self.assertIn("os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK", inspector)
        self.assertIn("os.fstat(fd)", inspector)
        self.assertNotIn("O_WRONLY", inspector)
        self.assertNotIn("O_APPEND", inspector)
        self.assertNotIn("chmod", inspector)
        self.assertFalse(run.call_args.kwargs["check"])

    @mock.patch.object(target.subprocess, "run")
    def test_wrong_owner_or_mode_is_denied(self, run):
        for updates in (
            {"uid": 0, "gid": 0},
            {"mode": 0o644},
        ):
            with self.subTest(updates=updates):
                metadata = dict(self.valid_metadata)
                metadata.update(updates)
                run.return_value = SimpleNamespace(
                    returncode=0, stdout=json.dumps(metadata), stderr=""
                )
                with self.assertRaises(target.TargetGateError):
                    target.inspect_rootfs_regular_file_as_root(
                        self.path, "engine audit log"
                    )

    @mock.patch.object(target.subprocess, "run")
    def test_symlink_or_non_regular_file_is_denied(self, run):
        for updates in (
            {"is_symlink": True, "is_regular_file": False},
            {"is_symlink": False, "is_regular_file": False},
        ):
            with self.subTest(updates=updates):
                metadata = dict(self.valid_metadata)
                metadata.update(updates)
                run.return_value = SimpleNamespace(
                    returncode=0, stdout=json.dumps(metadata), stderr=""
                )
                with self.assertRaises(target.TargetGateError):
                    target.inspect_rootfs_regular_file_as_root(
                        self.path, "engine audit log"
                    )

    @mock.patch.object(target.subprocess, "run")
    def test_empty_file_or_invalid_digest_is_denied(self, run):
        for updates in (
            {"size": 0},
            {"sha256": "not-a-sha256"},
        ):
            with self.subTest(updates=updates):
                metadata = dict(self.valid_metadata)
                metadata.update(updates)
                run.return_value = SimpleNamespace(
                    returncode=0, stdout=json.dumps(metadata), stderr=""
                )
                with self.assertRaises(target.TargetGateError):
                    target.inspect_rootfs_regular_file_as_root(
                        self.path, "engine audit log"
                    )

    @mock.patch.object(target.subprocess, "run")
    def test_privileged_file_inspection_failure_fails_closed(self, run):
        run.return_value = SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="sudo: a password is required",
        )
        with self.assertRaisesRegex(
            target.TargetGateError, "Privileged read-only file inspection failed"
        ):
            target.inspect_rootfs_regular_file_as_root(
                self.path, "engine audit log"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
