from __future__ import annotations

import hashlib
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

import lunita_beta_v1_8 as launcher
import engine_runtime_v1 as engine


class LunitaBetaV18Tests(unittest.TestCase):
    def test_runtime_environment_is_overlay_scoped(self):
        env = launcher.runtime_environment({})
        expected_overlay = launcher.OVERLAY
        python_paths = env["PYTHONPATH"].split(os.pathsep)
        self.assertEqual(
            str(expected_overlay / "vendor/python3.12/site-packages"), python_paths[0]
        )
        self.assertEqual(str(expected_overlay), python_paths[1])
        self.assertEqual(
            str(expected_overlay / "model-cache/fastembed"),
            env["LUNITA_FASTEMBED_CACHE"],
        )
        self.assertEqual("/var/lib/lunita/vectors", env["LUNITA_VECTOR_DB_PATH"])
        self.assertEqual("1", env["HF_HUB_DISABLE_TELEMETRY"])
        self.assertEqual("1", env["HF_HUB_OFFLINE"])
        self.assertEqual("1", env["TRANSFORMERS_OFFLINE"])

    def test_v17_legacy_launcher_path_matches_real_candidate_rootfs(self):
        self.assertEqual(launcher.ROOT / "agent/lunita.py", launcher.LEGACY_LAUNCHER)

    def test_v17_legacy_launcher_digest_is_explicitly_pinned(self):
        self.assertEqual(64, len(launcher.LEGACY_SHA256))
        self.assertEqual("46efd711729c344e7efba9ce2503127c48f0b88207cc5a17311ff1d555b075b2",
                         launcher.LEGACY_SHA256)

    def test_status_reports_candidate_not_certification(self):
        status = launcher.engine_status()
        self.assertEqual("RUNTIME_CANDIDATE", status["status"])
        self.assertEqual("NOT_GRANTED", status["canonical_certification"])
        self.assertEqual(15, status["engine_registry"]["engine_count"])
        self.assertEqual(14, len(status["command_agents"]))

    def test_instrument_labels_are_display_only_and_preserve_runtime_bindings(self):
        status = launcher.engine_status()
        instruments = status["instrument_registry"]
        self.assertEqual("Brújula giroscópica", instruments["BRUJULA"]["display_label"])
        self.assertEqual("/opt/lunita/instruments/brujula", instruments["BRUJULA"]["runtime_path"])
        self.assertEqual("brujula-self-test", instruments["BRUJULA"]["smoke_test_command"])
        self.assertEqual("Sacapuntas", instruments["JAMOVI"]["display_label"])
        self.assertEqual("org.jamovi.jamovi", instruments["JAMOVI"]["application_id"])
        self.assertEqual("jamovi-self-test", instruments["JAMOVI"]["smoke_test_command"])
        self.assertEqual("Lupa", instruments["JASP"]["display_label"])
        self.assertEqual("org.jaspstats.JASP", instruments["JASP"]["application_id"])
        self.assertEqual("jasp-self-test", instruments["JASP"]["smoke_test_command"])
        self.assertEqual(15, status["engine_registry"]["engine_count"])
        self.assertEqual(14, len(status["command_agents"]))
        self.assertEqual("NOT_GRANTED", status["canonical_certification"])

    def test_execution_audit_is_append_only_hash_chained_and_redacts_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            audit = pathlib.Path(temporary) / "audit" / "engine.jsonl"
            request = {
                "command": "/play AE", "agent": "Ancapi", "engine_id": "E15",
                "payload": {"private_prompt": "DO_NOT_STORE_RAW_PROMPT"},
            }
            result = {"status": "PASS_ENGINE_OPERATION", "result": {"status": "PASS_CONSENSUS"}}
            with mock.patch.dict(os.environ, {"LUNITA_ENGINE_AUDIT_LOG": str(audit)}):
                first = launcher.append_execution_audit(request, result)
                second = launcher.append_execution_audit(request, result)
            lines = audit.read_text(encoding="utf-8").splitlines()
            records = [json.loads(line) for line in lines]
            verified = engine.verify_provenance_chain(records)
            self.assertEqual("PASS_PROVENANCE_CHAIN", verified["status"])
            self.assertEqual(2, verified["event_count"])
            self.assertEqual(first["event_hash"], second["previous_hash"])
            self.assertEqual(
                hashlib.sha256(json.dumps(request, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")).encode("utf-8")).hexdigest(),
                records[0]["event"]["request_sha256"],
            )
            self.assertNotIn("DO_NOT_STORE_RAW_PROMPT", audit.read_text(encoding="utf-8"))

    def test_execution_audit_fails_closed_on_tampered_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            audit = pathlib.Path(temporary) / "audit" / "engine.jsonl"
            request = {"command": "/play AE", "agent": "Ancapi", "engine_id": "E15", "payload": {}}
            result = {"status": "PASS_ENGINE_OPERATION"}
            with mock.patch.dict(os.environ, {"LUNITA_ENGINE_AUDIT_LOG": str(audit)}):
                launcher.append_execution_audit(request, result)
                records = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
                records[0]["event"]["result_status"] = "FORGED"
                audit.write_text(json.dumps(records[0], sort_keys=True) + "\n", encoding="utf-8")
                before = audit.read_bytes()
                with self.assertRaises(RuntimeError):
                    launcher.append_execution_audit(request, result)
                self.assertEqual(before, audit.read_bytes())

    def test_legacy_delegation_does_not_inject_vendor_python_packages(self):
        vendor = str(launcher.OVERLAY / "vendor/python3.12/site-packages")
        overlay = str(launcher.OVERLAY)
        custom = "/opt/custom/python"
        with tempfile.TemporaryDirectory() as temporary:
            legacy = pathlib.Path(temporary) / "lunita.py"
            legacy.write_bytes(b"immutable beta v1.7 test fixture")
            legacy_sha = hashlib.sha256(legacy.read_bytes()).hexdigest()
            inherited_pythonpath = os.pathsep.join([vendor, overlay, custom])
            with mock.patch.object(launcher, "LEGACY_LAUNCHER", legacy), \
                 mock.patch.object(launcher, "LEGACY_SHA256", legacy_sha), \
                 mock.patch.dict(os.environ, {
                     "PYTHONPATH": inherited_pythonpath,
                     # Exercise the direct host-delegation branch, not target chroot.
                     "LUNITA_TARGET_ROOTFS": "",
                 }), \
                 mock.patch.object(launcher.subprocess, "run",
                                   return_value=type("R", (), {"returncode": 0})()) as run:
                self.assertEqual(0, launcher.run_legacy(["r-self-test"]))
            kwargs = run.call_args.kwargs
            child_paths = kwargs["env"].get("PYTHONPATH", "").split(os.pathsep)
            self.assertNotIn(vendor, child_paths)
            self.assertNotIn(overlay, child_paths)
            self.assertEqual([custom], child_paths)
            self.assertEqual("1", kwargs["env"].get("HF_HUB_OFFLINE", "1"))
            self.assertEqual([str(legacy), "r-self-test"], run.call_args.args[0][1:])

    def test_legacy_delegation_uses_guest_path_inside_target_rootfs(self):
        with tempfile.TemporaryDirectory(prefix="lunita-legacy-rootfs-") as temporary:
            rootfs = pathlib.Path(temporary)
            legacy = rootfs / "opt/lunita/agent/lunita.py"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"immutable beta v1.7 target fixture")
            legacy_sha = hashlib.sha256(legacy.read_bytes()).hexdigest()
            inherited_pythonpath = os.pathsep.join([
                str(launcher.OVERLAY / "vendor/python3.12/site-packages"),
                str(launcher.OVERLAY),
            ])
            with mock.patch.object(launcher, "LEGACY_LAUNCHER", legacy), \
                 mock.patch.object(launcher, "LEGACY_SHA256", legacy_sha), \
                 mock.patch.dict(os.environ, {
                     "LUNITA_TARGET_ROOTFS": str(rootfs),
                     "LUNITA_IN_PIVOT_ROOT": "0",
                     "GITHUB_RUN_ID": "43341112917",
                     "GITHUB_RUN_ATTEMPT": "1",
                     "HOST_BIND_NAME": "lunita-host-43341112917-1",
                     "XDG_RUNTIME_DIR": "/run/lunita-host-43341112917-1-runtime-1000",
                     "PYTHONPATH": inherited_pythonpath,
                 }), \
                 mock.patch.object(
                     launcher.subprocess, "run",
                     return_value=type("R", (), {"returncode": 0})(),
                 ) as run:
                self.assertEqual(0, launcher.run_legacy(["r-self-test"]))

            command = run.call_args.args[0]
            self.assertEqual(
                ["sudo", "-n", "chroot", "--userspec=1000:1000",
                 str(rootfs), "/usr/bin/env", "-C", "/tmp"],
                command[:8],
            )
            self.assertIn("XDG_RUNTIME_DIR=/run/lunita-host-43341112917-1-runtime-1000", command)
            self.assertNotIn("XDG_RUNTIME_DIR=/run/lunita-runtime-1000", command)
            python_index = command.index("/usr/bin/python3.12")
            self.assertEqual(
                ["/opt/lunita/agent/lunita.py", "r-self-test"],
                command[python_index + 1:],
            )
            self.assertNotIn("PYTHONPATH", run.call_args.kwargs["env"])

    def test_legacy_delegation_in_pivot_root_drops_uid_without_chroot(self):
        with tempfile.TemporaryDirectory(prefix="lunita-pivot-root-") as temporary:
            legacy = pathlib.Path(temporary) / "opt/lunita/agent/lunita.py"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"immutable beta v1.7 pivot-root fixture")
            legacy_sha = hashlib.sha256(legacy.read_bytes()).hexdigest()
            with mock.patch.object(launcher, "LEGACY_LAUNCHER", legacy), \
                 mock.patch.object(launcher, "LEGACY_SHA256", legacy_sha), \
                 mock.patch.dict(os.environ, {
                     "LUNITA_TARGET_ROOTFS": "/",
                     "LUNITA_IN_PIVOT_ROOT": "1",
                     "GITHUB_RUN_ID": "43341112917",
                     "GITHUB_RUN_ATTEMPT": "1",
                     "HOST_BIND_NAME": "lunita-host-43341112917-1",
                     "XDG_RUNTIME_DIR": "/run/lunita-host-43341112917-1-runtime-1000",
                     "PYTHONPATH": "",
                 }), \
                 mock.patch.object(launcher.os, "geteuid", return_value=0), \
                 mock.patch.object(
                     launcher.subprocess, "run",
                     return_value=type("R", (), {"returncode": 0})(),
                 ) as run:
                self.assertEqual(0, launcher.run_legacy(["jamovi-self-test"]))
            command = run.call_args.args[0]
            self.assertEqual(
                ["/usr/bin/setpriv", "--reuid=1000", "--regid=1000", "--clear-groups"],
                command[:4],
            )
            self.assertNotIn("chroot", command)
            self.assertIn("XDG_RUNTIME_DIR=/run/lunita-host-43341112917-1-runtime-1000", command)
            self.assertNotIn("XDG_RUNTIME_DIR=/run/lunita-runtime-1000", command)
            python_index = command.index("/usr/bin/python3.12")
            self.assertTrue(command[python_index + 1].endswith("/opt/lunita/agent/lunita.py"))
            self.assertEqual(["jamovi-self-test"], command[python_index + 2:])
            self.assertNotIn("PYTHONPATH", run.call_args.kwargs["env"])

    def test_legacy_target_delegation_rejects_missing_workflow_runtime_identity(self):
        with tempfile.TemporaryDirectory(prefix="lunita-legacy-identity-") as temporary:
            rootfs = pathlib.Path(temporary)
            legacy = rootfs / "opt/lunita/agent/lunita.py"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"immutable beta v1.7 identity fixture")
            legacy_sha = hashlib.sha256(legacy.read_bytes()).hexdigest()
            with (
                mock.patch.object(launcher, "LEGACY_LAUNCHER", legacy),
                mock.patch.object(launcher, "LEGACY_SHA256", legacy_sha),
                mock.patch.dict(os.environ, {"LUNITA_TARGET_ROOTFS": str(rootfs)}, clear=True),
                mock.patch.object(launcher.subprocess, "run") as run,
            ):
                self.assertEqual(5, launcher.run_legacy(["jamovi-self-test"]))
            run.assert_not_called()

    def test_legacy_target_delegation_rejects_runtime_path_from_another_attempt(self):
        with tempfile.TemporaryDirectory(prefix="lunita-legacy-runtime-") as temporary:
            rootfs = pathlib.Path(temporary)
            legacy = rootfs / "opt/lunita/agent/lunita.py"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"immutable beta v1.7 runtime fixture")
            legacy_sha = hashlib.sha256(legacy.read_bytes()).hexdigest()
            with (
                mock.patch.object(launcher, "LEGACY_LAUNCHER", legacy),
                mock.patch.object(launcher, "LEGACY_SHA256", legacy_sha),
                mock.patch.dict(os.environ, {
                    "LUNITA_TARGET_ROOTFS": str(rootfs),
                    "GITHUB_RUN_ID": "43341112917",
                    "GITHUB_RUN_ATTEMPT": "1",
                    "HOST_BIND_NAME": "lunita-host-43341112917-1",
                    "XDG_RUNTIME_DIR": "/run/lunita-runtime-1000",
                }, clear=True),
                mock.patch.object(launcher.subprocess, "run") as run,
            ):
                self.assertEqual(5, launcher.run_legacy(["jamovi-self-test"]))
            run.assert_not_called()

    def test_legacy_delegation_outside_declared_target_rootfs_is_denied(self):
        with tempfile.TemporaryDirectory(prefix="lunita-rootfs-") as rootfs_dir, \
             tempfile.TemporaryDirectory(prefix="lunita-outside-") as outside_dir:
            rootfs = pathlib.Path(rootfs_dir)
            legacy = pathlib.Path(outside_dir) / "lunita.py"
            legacy.write_bytes(b"immutable beta v1.7 outside fixture")
            legacy_sha = hashlib.sha256(legacy.read_bytes()).hexdigest()
            with mock.patch.object(launcher, "LEGACY_LAUNCHER", legacy), \
                 mock.patch.object(launcher, "LEGACY_SHA256", legacy_sha), \
                 mock.patch.dict(os.environ, {"LUNITA_TARGET_ROOTFS": str(rootfs)}), \
                 mock.patch.object(launcher.subprocess, "run") as run:
                self.assertEqual(5, launcher.run_legacy(["r-self-test"]))
            run.assert_not_called()

    def test_legacy_hash_verifier_detects_modified_launcher(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate = pathlib.Path(temporary) / "lunita_beta_v1_7.py"
            candidate.write_text("legacy fixture\n", encoding="utf-8")
            expected = hashlib.sha256(candidate.read_bytes()).hexdigest()
            with mock.patch.object(launcher, "LEGACY_LAUNCHER", candidate), \
                 mock.patch.object(launcher, "LEGACY_SHA256", expected):
                self.assertEqual(expected, launcher.sha256_file(candidate))
            with mock.patch.object(launcher, "LEGACY_LAUNCHER", candidate), \
                 mock.patch.object(launcher, "LEGACY_SHA256", "0" * 64):
                self.assertNotEqual(launcher.LEGACY_SHA256, launcher.sha256_file(candidate))


if __name__ == "__main__":
    unittest.main(verbosity=2)
