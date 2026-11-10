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


if __name__ == "__main__":
    unittest.main(verbosity=2)
