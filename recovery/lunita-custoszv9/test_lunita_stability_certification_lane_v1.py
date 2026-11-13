import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

try:
    import custosz_lunita_stability_certification_lane_v1 as lane
except ModuleNotFoundError:
    import lunita_stability_certification_lane_v1 as lane


class DpkgDependencyTests(unittest.TestCase):
    def test_declared_dependencies_resolve_to_installed_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "status"
            p.write_text(
                "Package: base-files\nStatus: install ok installed\nVersion: 1\nDepends: libc6 (>= 2.0)\n\n"
                "Package: libc6\nStatus: install ok installed\nVersion: 2.4\n\n",
                encoding="utf-8",
            )
            result = lane.parse_dpkg_status(p)
        self.assertEqual("PASS_DECLARED_PACKAGE_DEPENDENCIES_RESOLVED", result["status"])
        self.assertEqual(2, result["installed_package_count"])
        self.assertEqual(0, result["unresolved_dependency_count"])

    def test_missing_declared_dependency_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "status"
            p.write_text(
                "Package: app\nStatus: install ok installed\nVersion: 1\nDepends: absent-runtime (>= 1.0)\n\n",
                encoding="utf-8",
            )
            result = lane.parse_dpkg_status(p)
        self.assertEqual("BLOCKED_UNRESOLVED_PACKAGE_DEPENDENCIES", result["status"])
        self.assertEqual(1, result["unresolved_dependency_count"])

    def test_installed_package_with_insufficient_version_does_not_resolve_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "status"
            p.write_text(
                "Package: app\nStatus: install ok installed\nVersion: 1\nDepends: libc6 (>= 2.2)\n\n"
                "Package: libc6\nStatus: install ok installed\nVersion: 2.0\n\n",
                encoding="utf-8",
            )
            result = lane.parse_dpkg_status(p)
        self.assertEqual("BLOCKED_UNRESOLVED_PACKAGE_DEPENDENCIES", result["status"])
        self.assertEqual(1, result["unresolved_dependency_count"])
        self.assertEqual("MISSING_PACKAGE_OR_UNSATISFIED_VERSION_CONSTRAINT", result["unresolved_dependencies"][0]["reason"])


class RootfsInventoryTests(unittest.TestCase):
    def test_inventory_hashes_regular_files_and_records_symlink_without_following(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            rootfs = base / "rootfs"
            (rootfs / "var/lib/dpkg").mkdir(parents=True)
            (rootfs / "etc").mkdir()
            (rootfs / "opt/lunita/agent").mkdir(parents=True)
            (rootfs / "usr/bin").mkdir(parents=True)
            (rootfs / "var/lib/dpkg/status").write_text(
                "Package: base-files\nStatus: install ok installed\nVersion: 1\n\n", encoding="utf-8"
            )
            (rootfs / "etc/os-release").write_text("ID=ubuntu\nVERSION_ID=\"24.04\"\n", encoding="utf-8")
            (rootfs / "opt/lunita/agent/lunita.py").write_text("print('candidate')\n", encoding="utf-8")
            (rootfs / "usr/bin/probe").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (rootfs / "bin").symlink_to("usr/bin", target_is_directory=True)
            evidence = base / "evidence"
            with mock.patch.object(lane, "ROOTFS", rootfs), mock.patch.object(lane, "EVIDENCE", base / "evidence"):
                result = lane.build_rootfs_inventory()
            self.assertEqual("PASS_ROOTFS_INVENTORY_AND_DEPENDENCY_CLOSURE", result["status"])
            self.assertTrue(result["tree_stable_during_scan"])
            self.assertTrue(pathlib.Path(result["manifest_path"]).is_file())
            rows = [json.loads(x) for x in pathlib.Path(result["manifest_path"]).read_text().splitlines()]
            link = next(x for x in rows if x["path"] == "bin")
            self.assertEqual("symlink", link["type"])
            self.assertEqual("usr/bin", link["symlink_target"])
            launcher = next(x for x in rows if x["path"] == "opt/lunita/agent/lunita.py")
            self.assertEqual(hashlib.sha256(b"print('candidate')\n").hexdigest(), launcher["sha256"])

    def test_privileged_read_only_hash_fallback_is_hash_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "protected"
            path.write_bytes(b"protected candidate file")
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            with mock.patch.object(lane, "ROOTFS", pathlib.Path(tmp)):
                with mock.patch.object(pathlib.Path, "open", side_effect=PermissionError("EACCES")):
                    with mock.patch.object(lane.shutil, "which", side_effect=lambda name: "/usr/bin/" + name):
                        with mock.patch.object(lane.subprocess, "run", return_value=type("R", (), {
                            "returncode": 0, "stdout": expected + "  " + str(path) + "\n", "stderr": ""
                        })()) as run:
                            digest, method = lane.hash_regular_file_read_only(path)
            self.assertEqual(expected, digest)
            self.assertEqual("SUDO_NONINTERACTIVE_READ_ONLY_SHA256SUM", method)
            self.assertIn("-n", run.call_args.args[0])
            self.assertTrue(any(str(part).endswith("sha256sum") for part in run.call_args.args[0]))

    def test_privileged_read_only_hash_fails_closed_without_sudo_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "protected"
            path.write_bytes(b"protected candidate file")
            with mock.patch.object(lane, "ROOTFS", pathlib.Path(tmp)):
                with mock.patch.object(pathlib.Path, "open", side_effect=PermissionError("EACCES")):
                    with mock.patch.object(lane.shutil, "which", side_effect=lambda name: "/usr/bin/" + name):
                        with mock.patch.object(lane.subprocess, "run", return_value=type("R", (), {
                            "returncode": 1, "stdout": "", "stderr": "sudo: a password is required"
                        })()):
                            with self.assertRaises(PermissionError):
                                lane.hash_regular_file_read_only(path)

    def test_missing_rootfs_never_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            with mock.patch.object(lane, "ROOTFS", base / "missing"), mock.patch.object(lane, "EVIDENCE", base / "evidence"):
                result = lane.build_rootfs_inventory()
        self.assertEqual("BLOCKED_ROOTFS_MISSING", result["status"])


class CertificationGateTests(unittest.TestCase):
    def test_failed_jasp_artifacts_remain_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            evidence = out / "evidence"
            evidence.mkdir()
            (out / "JASP_UNITTEST_FLATPAK_20261020.log").write_text("JASP_UNITTEST_RC=1\n", encoding="utf-8")
            (out / "JASP_UNITTEST_RELIABILITY_20261020.log").write_text("JASP_RELIABILITY_UNITTEST_RC=1\n", encoding="utf-8")
            (out / "JASP_UNITTEST_WEIGHT_GAIN_20261020.log").write_text("JASP_WEIGHT_GAIN_UNITTEST_RC=1\n", encoding="utf-8")
            (out / "JASP_UNITTEST_ROUNDTRIP_DEATH_PENALTY_20261020.json").write_text(json.dumps({
                "strict_rerun_after_save": {"status": "FAIL", "returncode": 1},
                "original_sample_unchanged": True,
            }), encoding="utf-8")
            with mock.patch.object(lane, "OUT", out), mock.patch.object(lane, "EVIDENCE", evidence):
                result = lane.latest_jasp_evidence()
        self.assertEqual("BLOCKED_JASP_PACKAGED_FIXTURE_NONREGRESSION", result["status"])
        self.assertTrue(all(x["status"] == "BLOCKED" and x["returncode"] == 1 for x in result["cases"].values()))

    def test_worker_preflight_failure_is_not_downgraded_to_not_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out, evidence = base / "out", base / "evidence"
            out.mkdir()
            evidence.mkdir()
            suite = evidence / "jasp_suite_20261112T000000Z.json"
            suite.write_text(json.dumps({
                "schema": "CUSTOSZ_LUNITA_JASP_AUTOMATED_REGRESSION_SUITE/1.0",
                "status": "BLOCKED_JASP_PIN_MISMATCH",
                "app_commit_probe": {
                    "returncode": 0,
                    "actual_commit": "0" * 64,
                    "expected_commit": "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7",
                },
                "tests": {},
            }), encoding="utf-8")
            with mock.patch.object(lane, "OUT", out), mock.patch.object(lane, "EVIDENCE", evidence):
                result = lane.latest_jasp_evidence()
            self.assertEqual("BLOCKED_JASP_PACKAGED_FIXTURE_NONREGRESSION", result["status"])
            self.assertEqual("BLOCKED_JASP_PIN_MISMATCH", result["worker_evidence"]["status"])
            self.assertEqual(0, result["worker_evidence"]["case_count"])
            for case in result["cases"].values():
                self.assertEqual("BLOCKED", case["status"])
                self.assertEqual("BLOCKED_WORKER_DID_NOT_REACH_CASE", case["case_status"])
                self.assertEqual("BLOCKED_JASP_PIN_MISMATCH", case["worker_status"])
                self.assertEqual(str(suite), case["evidence_path"])
                self.assertEqual(lane.sha_file(suite), case["evidence_sha256"])

    def test_worker_exit_without_receipt_is_explicitly_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out, evidence = base / "out", base / "evidence"
            out.mkdir()
            evidence.mkdir()
            receipt = {
                "status": "BLOCKED_JASP_WORKER_EXIT_WITHOUT_RECEIPT",
                "pid": 4312,
            }
            with mock.patch.object(lane, "OUT", out), mock.patch.object(lane, "EVIDENCE", evidence):
                result = lane.latest_jasp_evidence(receipt)
            self.assertEqual("BLOCKED_JASP_PACKAGED_FIXTURE_NONREGRESSION", result["status"])
            for case in result["cases"].values():
                self.assertEqual("BLOCKED", case["status"])
                self.assertEqual("BLOCKED_JASP_WORKER_EXIT_WITHOUT_RECEIPT", case["worker_status"])

    def test_independent_report_does_not_pass_with_missing_inventory_and_jasp_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            candidate = base / "candidate"
            rootfs = candidate / "rootfs"
            (rootfs / "opt/lunita/agent").mkdir(parents=True)
            launcher = rootfs / "opt/lunita/agent/lunita.py"
            launcher.write_text("candidate", encoding="utf-8")
            runtime = candidate / "BETA_RUNTIME_FUNCTIONAL_TESTS.json"
            runtime.write_text(json.dumps({
                "schema": "CUSTOSZ_LUNITA_BETA_RUNTIME_FUNCTIONAL_TESTS/1.0",
                "candidate_id": "G06_REBUILD_CANDIDATE_R1", "status": "PASS_RUNTIME_TESTS",
                "all_tests_pass": True, "frozen_g06_mutated": False, "canonical_g08_bindings_mutated": False,
                "candidate": {"beta_launcher_sha256": lane.sha_file(launcher)},
            }), encoding="utf-8")
            independent = candidate / "BETA_INDEPENDENT_VALIDATION.json"
            independent.write_text("{}", encoding="utf-8")
            mission = base / "MISION1.txt"
            mission.write_text("test mission identity", encoding="utf-8")
            mission_sha = hashlib.sha256(mission.read_bytes()).hexdigest()
            jasp = {"status": "BLOCKED_JASP_PACKAGED_FIXTURE_NONREGRESSION", "cases": {}, "next_action": "rerun"}
            with mock.patch.object(lane, "CANDIDATE", candidate), mock.patch.object(lane, "ROOTFS", rootfs), \
                 mock.patch.object(lane, "RUNTIME_REPORT", runtime), mock.patch.object(lane, "INDEPENDENT_REPORT", independent), \
                 mock.patch.object(lane, "MISSION_PATH", mission), mock.patch.object(lane, "MISSION_SHA", mission_sha):
                result = lane.update_independent_report(None, jasp)
        self.assertEqual("BLOCKED_REQUIRED_REGRESSION_OR_INVENTORY", result["status"])
        self.assertIn("candidate_rootfs_inventory_and_dependency_manifest", result["open_items"])
        self.assertIn("jasp_packaged_fixture_nonregression", result["open_items"])
        self.assertFalse(result["mission_completion_claim"])

    def test_independent_report_fails_closed_when_jasp_evidence_path_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            candidate = base / "candidate"
            rootfs = candidate / "rootfs"
            (rootfs / "opt/lunita/agent").mkdir(parents=True)
            launcher = rootfs / "opt/lunita/agent/lunita.py"
            launcher.write_text("candidate", encoding="utf-8")
            runtime = candidate / "BETA_RUNTIME_FUNCTIONAL_TESTS.json"
            runtime.write_text(json.dumps({
                "schema": "CUSTOSZ_LUNITA_BETA_RUNTIME_FUNCTIONAL_TESTS/1.0",
                "candidate_id": "G06_REBUILD_CANDIDATE_R1", "status": "PASS_RUNTIME_TESTS",
                "all_tests_pass": True, "frozen_g06_mutated": False, "canonical_g08_bindings_mutated": False,
                "candidate": {"beta_launcher_sha256": lane.sha_file(launcher)},
            }), encoding="utf-8")
            independent = candidate / "BETA_INDEPENDENT_VALIDATION.json"
            independent.write_text("{}", encoding="utf-8")
            mission = base / "MISION1.txt"
            mission.write_text("test mission identity", encoding="utf-8")
            mission_sha = hashlib.sha256(mission.read_bytes()).hexdigest()
            cases = {
                "flatpak_launch": {
                    "status": "PASS", "returncode": 0, "evidence_path": None,
                    "evidence_sha256": "0" * 64,
                },
                "reliability": {"status": "BLOCKED", "returncode": 1, "evidence_path": None},
                "weight_gain": {"status": "BLOCKED", "returncode": 1, "evidence_path": None},
                "death_penalty_roundtrip": {"status": "BLOCKED", "returncode": 1, "evidence_path": None},
            }
            jasp = {
                "status": "PASS_JASP_PACKAGED_FIXTURE_NONREGRESSION",
                "cases": cases,
                "next_action": "invalid evidence path must block",
            }
            with mock.patch.object(lane, "CANDIDATE", candidate), mock.patch.object(lane, "ROOTFS", rootfs), \
                 mock.patch.object(lane, "RUNTIME_REPORT", runtime), mock.patch.object(lane, "INDEPENDENT_REPORT", independent), \
                 mock.patch.object(lane, "MISSION_PATH", mission), mock.patch.object(lane, "MISSION_SHA", mission_sha):
                result = lane.update_independent_report(None, jasp)
        check = result["checks"]["jasp_packaged_fixture_nonregression"]
        self.assertEqual("BLOCKED", check["status"])
        self.assertFalse(check["all_case_evidence_hashes_current"])
        self.assertIn("jasp_packaged_fixture_nonregression", result["open_items"])
        self.assertFalse(result["mission_completion_claim"])

    def test_stable_release_waits_for_hash_bound_s32_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out = base / "out"
            out.mkdir()
            candidate = base / "candidate"
            candidate.mkdir()
            runtime = candidate / "runtime.json"
            runtime.write_text(json.dumps({"schema": "CUSTOSZ_LUNITA_BETA_RUNTIME_FUNCTIONAL_TESTS/1.0",
                                            "candidate_id": "G06_REBUILD_CANDIDATE_R1",
                                            "status": "PASS_RUNTIME_TESTS", "all_tests_pass": True}), encoding="utf-8")
            target_receipt = candidate / "target-v1.8-runtime.json"
            target_receipt.write_text(json.dumps({
                "schema": "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0",
                "status": "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED",
                "candidate_id": "G06_REBUILD_CANDIDATE_R1",
                "workflow_identity": {
                    "run_id": "43337415331",
                    "run_attempt": "1",
                    "host_bind_name": "lunita-host-43337415331-1",
                    "xdg_runtime_dir": "/run/lunita-host-43337415331-1-runtime-1000",
                },
                "xdg_runtime_dir": {
                    "status": "PASS_XDG_RUNTIME_DIR_UID1000_PRIVATE",
                    "path": "/run/lunita-host-43337415331-1-runtime-1000",
                    "mode_octal": "0o700",
                },
                "certification": "NOT_GRANTED",
                "canonical_g06_certification": "NOT_GRANTED",
                "canonical_g08_binding_mutation": False,
            }), encoding="utf-8")
            independent = candidate / "independent.json"
            independent.write_text(json.dumps({
                "schema": "CUSTOSZ_LUNITA_BETA_INDEPENDENT_VALIDATION/1.0",
                "candidate_id": "G06_REBUILD_CANDIDATE_R1", "mission_sha256": lane.MISSION_SHA,
                "status": "PASS_INDEPENDENT_VALIDATION",
                "runtime_report_sha256": lane.sha_file(runtime),
                "checks": {
                    "rootfs": {"status": "PASS", "returncode": 0},
                    "jasp": {"status": "PASS", "returncode": 0},
                    "target_v1_8_runtime_acceptance_e01_e15_int8": {
                        "status": "PASS", "receipt_path": str(target_receipt),
                        "receipt_sha256": lane.sha_file(target_receipt),
                    },
                },
                "frozen_g06_mutated": False, "canonical_g08_bindings_mutated": False,
            }), encoding="utf-8")
            with mock.patch.object(lane, "OUT", out), mock.patch.object(lane, "RUNTIME_REPORT", runtime), \
                 mock.patch.object(lane, "INDEPENDENT_REPORT", independent):
                result = lane.stable_release_gate()
        self.assertEqual("WAITING_FOR_S32_BOUND_CERTIFICATION_RECEIPT", result["status"])
        self.assertEqual("NOT_GRANTED", result["certification"])


class DirectV18S32IssuerTests(unittest.TestCase):
    @staticmethod
    def valid_manifest():
        return {
            "schema": "LUNITA_CANDIDATE_FREEZE/1.0",
            "candidate_id": "G06_REBUILD_CANDIDATE_R1",
            "version": "1.8.0",
            "freeze_status": "FROZEN_CANDIDATE_NOT_CERTIFIED",
            "preserved_baseline": {
                "frozen_g06_mutated": False,
                "canonical_g08_bindings_mutated": False,
                "legacy_v1_7_launcher_replaced": False,
            },
        }

    def prepare_valid_evidence(self, base):
        out = base / "outputs"
        out.mkdir()
        manifest = base / "LUNITA_V1_8_CANDIDATE_FREEZE.json"
        manifest.write_text(json.dumps(self.valid_manifest()), encoding="utf-8")
        target = base / "LUNITA_TARGET_RUNTIME_ACCEPTANCE_test.json"
        target.write_text(json.dumps({
            "schema": "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0",
            "status": "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED",
            "candidate_id": "G06_REBUILD_CANDIDATE_R1",
            "workflow_identity": {
                "run_id": "43337415331",
                "run_attempt": "1",
                "host_bind_name": "lunita-host-43337415331-1",
                "xdg_runtime_dir": "/run/lunita-host-43337415331-1-runtime-1000",
            },
            "xdg_runtime_dir": {
                "status": "PASS_XDG_RUNTIME_DIR_UID1000_PRIVATE",
                "path": "/run/lunita-host-43337415331-1-runtime-1000",
                "mode_octal": "0o700",
            },
            "certification": "NOT_GRANTED",
            "canonical_g06_certification": "NOT_GRANTED",
            "canonical_g08_binding_mutation": False,
        }), encoding="utf-8")
        independent = base / "BETA_INDEPENDENT_VALIDATION.json"
        target_sha = lane.sha_file(target)
        manifest_sha = lane.sha_file(manifest)
        image = base / "LUNITA.squashfs"
        image.write_bytes(b"verified target image")
        image_sha = lane.sha_file(image)
        checksum = base / "LUNITA.squashfs.sha256"
        checksum.write_text(f"{image_sha}  {image.name}\n", encoding="ascii")
        package = base / "LUNITA_SQUASHFS_PACKAGE_RECEIPT.json"
        package.write_text(json.dumps({
            "schema": "LUNITA_SQUASHFS_PACKAGE_RECEIPT/1.0",
            "status": "PASS_SQUASHFS_PACKAGE_AND_ROUNDTRIP_NOT_CERTIFIED",
            "candidate_id": "G06_REBUILD_CANDIDATE_R1", "version": "1.8.0",
            "image_name": image.name, "image_sha256": image_sha, "image_bytes": image.stat().st_size,
            "roundtrip_manifest_match": True, "source_rootfs_unchanged": True,
            "target_runtime_receipt_path": str(target), "target_runtime_receipt_sha256": target_sha,
            "target_runtime_status": "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED",
            "mksquashfs": "PASS", "unsquashfs_superblock": "PASS", "unsquashfs_roundtrip": "PASS",
            "certification": "NOT_GRANTED", "g23": "NOT_GRANTED", "g24": "NOT_GRANTED",
        }), encoding="utf-8")
        package_sha = lane.sha_file(package)
        checksum_sha = lane.sha_file(checksum)
        required = {
            "candidate_manifest_identity_sha256",
            "runtime_report_and_launcher_identity",
            "target_v1_8_runtime_acceptance_e01_e15_int8",
            "candidate_rootfs_inventory_and_dependency_manifest",
            "jasp_packaged_fixture_nonregression",
            "jasp_process_tree_lifecycle",
            "jasp_post_mutation_runtime_identity",
            "squashfs_image_and_package_binding",
        }
        checks = {name: {"status": "PASS", "returncode": 0} for name in required}
        jasp_binary_sha = "a" * 64
        flatpak_runtime_commit = "b" * 64
        invocation_cases = [
            "flatpak_launch", "reliability", "weight_gain",
            "death_penalty_save", "death_penalty_rerun",
        ]
        process_invocations = [
            {
                "schema": "LUNITA_JASP_PROCESS_TREE_RECEIPT/1.0",
                "status": "PASS_PROCESS_GROUP_CLOSED",
                "run_id": "43337415331",
                "run_attempt": "1",
                "case_id": case_id,
                "invocation_id": f"{index:032x}",
                "process_group_id": 300 + index,
                "session_id": 300 + index,
                "executable_sha256": jasp_binary_sha,
                "runtime_ostree_commit": flatpak_runtime_commit,
                "command_sha256": "c" * 64,
                "timeout_seconds": 180,
                "started_at_utc": "2026-11-13T00:00:00Z",
                "finished_at_utc": "2026-11-13T00:00:01Z",
                "returncode": 0,
                "timeout_triggered": False,
                "termination_signals": [],
                "remaining_live_pids": [],
                "process_group_closed": True,
                "captured_output_sha256": "d" * 64,
                "captured_output_bytes": 0,
            }
            for index, case_id in enumerate(invocation_cases, start=1)
        ]
        checks["jasp_post_mutation_runtime_identity"] = {
            "status": "PASS", "returncode": 0,
            "jasp_binary_sha256": jasp_binary_sha,
            "flatpak_runtime_commit": flatpak_runtime_commit,
        }
        checks["jasp_process_tree_lifecycle"] = {
            "status": "PASS", "returncode": 0,
            "invocation_count": 5, "expected_invocation_count": 5,
            "unique_invocation_id_count": 5,
            "workflow_identity": {"run_id": "43337415331", "run_attempt": "1"},
            "jasp_binary_sha256": jasp_binary_sha,
            "flatpak_runtime_ostree_commit": flatpak_runtime_commit,
            "invocations": process_invocations,
        }
        checks["candidate_manifest_identity_sha256"]["sha256"] = manifest_sha
        checks["target_v1_8_runtime_acceptance_e01_e15_int8"].update({
            "receipt_path": str(target), "receipt_sha256": target_sha,
        })
        checks["squashfs_image_and_package_binding"] = {
            "status": "PASS", "returncode": 0,
            "image_path": str(image), "image_sha256": image_sha, "image_bytes": image.stat().st_size,
            "checksum_path": str(checksum), "checksum_sha256": checksum_sha,
            "package_receipt_path": str(package), "package_receipt_sha256": package_sha,
            "candidate_manifest_path": str(manifest), "candidate_manifest_sha256": manifest_sha,
            "evidence": {str(image): image_sha, str(checksum): checksum_sha,
                         str(package): package_sha, str(manifest): manifest_sha},
        }
        independent.write_text(json.dumps({
            "schema": "CUSTOSZ_LUNITA_BETA_INDEPENDENT_VALIDATION/1.0",
            "candidate_id": "G06_REBUILD_CANDIDATE_R1",
            "certification_profile": "V1_8_DIRECT",
            "candidate_manifest_sha256": manifest_sha,
            "squashfs_image_path": str(image), "squashfs_image_sha256": image_sha,
            "squashfs_image_bytes": image.stat().st_size,
            "squashfs_checksum_path": str(checksum), "squashfs_checksum_sha256": checksum_sha,
            "squashfs_package_receipt_path": str(package), "squashfs_package_receipt_sha256": package_sha,
            "status": "PASS_INDEPENDENT_VALIDATION",
            "runtime_report_path": str(target), "runtime_report_sha256": target_sha,
            "checks": checks, "frozen_g06_mutated": False, "canonical_g08_bindings_mutated": False,
        }), encoding="utf-8")
        target_acceptance = {
            "status": "PASS_TARGET_RUNTIME_ACCEPTANCE",
            "receipt_path": str(target),
            "receipt_sha256": target_sha,
            "candidate_id": "G06_REBUILD_CANDIDATE_R1",
            "workflow_identity": {"run_id": "43337415331", "run_attempt": "1"},
            "canonical_g08_binding_mutation": False,
        }
        return out, manifest, target, independent, target_acceptance, image, checksum, package

    def test_s32_issues_hash_bound_receipt_and_unlocks_candidate_stable_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out, manifest, target, independent, acceptance, image, checksum, package = self.prepare_valid_evidence(base)
            with mock.patch.dict(lane.os.environ, {"GITHUB_RUN_ID": "43337415331", "GITHUB_RUN_ATTEMPT": "1"}), \
                 mock.patch.object(lane, "CERTIFICATION_PROFILE", "V1_8_DIRECT"), \
                 mock.patch.object(lane, "CANDIDATE_MANIFEST", manifest), \
                 mock.patch.object(lane, "SQUASHFS_IMAGE", image), \
                 mock.patch.object(lane, "SQUASHFS_CHECKSUM", checksum), \
                 mock.patch.object(lane, "SQUASHFS_PACKAGE_RECEIPT", package), \
                 mock.patch.object(lane, "TARGET_RUNTIME_RECEIPT_DIR", target.parent), \
                 mock.patch.object(lane, "INDEPENDENT_REPORT", independent), \
                 mock.patch.object(lane, "OUT", out), \
                 mock.patch.object(lane, "latest_target_runtime_acceptance", return_value=acceptance):
                first = lane.issue_s32_independent_beta_validation_receipt()
                second = lane.issue_s32_independent_beta_validation_receipt()
                gate = lane.stable_release_gate()
            self.assertEqual("BETA_OPERATIONAL_CERTIFIED", first["status"])
            self.assertEqual(first["receipt_path"], second["receipt_path"])
            self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])
            receipt = json.loads(pathlib.Path(first["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual("BETA_OPERATIONAL_CERTIFIED", receipt["status"])
            self.assertEqual(lane.sha_file(independent), receipt["evidence"]["independent_report_sha256"])
            self.assertEqual(lane.sha_file(target), receipt["evidence"]["target_runtime_receipt_sha256"])
            self.assertEqual("NOT_GRANTED", receipt["canonical_g06_certification"])
            self.assertEqual("NOT_GRANTED", receipt["g23_status"])
            self.assertEqual("NOT_GRANTED", receipt["g24_status"])
            self.assertEqual("STABLE_RELEASE_ELIGIBLE", gate["status"])

    def test_s32_blocks_when_a_jasp_process_tree_receipt_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out, manifest, target, independent, acceptance, image, checksum, package = self.prepare_valid_evidence(base)
            report = json.loads(independent.read_text(encoding="utf-8"))
            process_check = report["checks"]["jasp_process_tree_lifecycle"]
            process_check["invocations"].pop()
            process_check["invocation_count"] = 4
            process_check["unique_invocation_id_count"] = 4
            independent.write_text(json.dumps(report), encoding="utf-8")
            with mock.patch.dict(lane.os.environ, {"GITHUB_RUN_ID": "43337415331", "GITHUB_RUN_ATTEMPT": "1"}), \
                 mock.patch.object(lane, "CERTIFICATION_PROFILE", "V1_8_DIRECT"), \
                 mock.patch.object(lane, "CANDIDATE_MANIFEST", manifest), \
                 mock.patch.object(lane, "SQUASHFS_IMAGE", image), \
                 mock.patch.object(lane, "SQUASHFS_CHECKSUM", checksum), \
                 mock.patch.object(lane, "SQUASHFS_PACKAGE_RECEIPT", package), \
                 mock.patch.object(lane, "TARGET_RUNTIME_RECEIPT_DIR", target.parent), \
                 mock.patch.object(lane, "INDEPENDENT_REPORT", independent), \
                 mock.patch.object(lane, "OUT", out), \
                 mock.patch.object(lane, "latest_target_runtime_acceptance", return_value=acceptance):
                result = lane.issue_s32_independent_beta_validation_receipt()
            self.assertEqual("BLOCKED_JASP_PROCESS_TREE_RECEIPTS", result["status"])
            self.assertEqual("NOT_GRANTED", result["certification"])
    def test_s32_never_issues_when_independent_report_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out, manifest, target, independent, acceptance, image, checksum, package = self.prepare_valid_evidence(base)
            report = json.loads(independent.read_text(encoding="utf-8"))
            report["status"] = "BLOCKED_REQUIRED_REGRESSION_OR_INVENTORY"
            independent.write_text(json.dumps(report), encoding="utf-8")
            with mock.patch.object(lane, "CERTIFICATION_PROFILE", "V1_8_DIRECT"), \
                 mock.patch.object(lane, "CANDIDATE_MANIFEST", manifest), \
                 mock.patch.object(lane, "SQUASHFS_IMAGE", image), \
                 mock.patch.object(lane, "SQUASHFS_CHECKSUM", checksum), \
                 mock.patch.object(lane, "SQUASHFS_PACKAGE_RECEIPT", package), \
                 mock.patch.object(lane, "INDEPENDENT_REPORT", independent), \
                 mock.patch.object(lane, "OUT", out), \
                 mock.patch.object(lane, "latest_target_runtime_acceptance", return_value=acceptance):
                result = lane.issue_s32_independent_beta_validation_receipt()
            self.assertEqual("BLOCKED_INDEPENDENT_VALIDATION", result["status"])
            self.assertEqual([], list(out.glob("S32_INDEPENDENT_BETA_VALIDATION_AND_RECEIPT_*.json")))


if __name__ == "__main__":
    unittest.main()


class JaspDeterministicFixtureTests(unittest.TestCase):
    @staticmethod
    def write_fixture(path, options_list):
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "analyses.json",
                json.dumps({"analyses": [{"analysisId": f"analysis-{i}", "options": option}
                                         for i, option in enumerate(options_list)]}),
            )
            archive.writestr("data/data.bin", b"immutable data payload")

    def test_clone_changes_only_one_native_seed_option_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            source = base / "Death Penalty.jasp"
            clone = base / "Death Penalty_seeded.jasp"
            receipt_path = base / "evidence" / "fixture_receipt.json"
            self.write_fixture(source, [{"setSeed": False, "seed": 1, "other": "preserved"}])
            source_sha = lane.sha_file(source)
            receipt = lane.prepare_deterministic_fixture(
                source, clone, receipt_path, source_sha
            )
            self.assertTrue(receipt["source_unchanged"])
            self.assertEqual(source_sha, lane.sha_file(source))
            self.assertNotEqual(source_sha, lane.sha_file(clone))
            self.assertEqual("/analyses/0/options", receipt["changed_json_pointer"])
            self.assertTrue(lane.verify_deterministic_fixture_receipt(receipt, source_sha))
            with zipfile.ZipFile(source) as original, zipfile.ZipFile(clone) as seeded:
                original_names = sorted(original.namelist())
                self.assertEqual(original_names, sorted(seeded.namelist()))
                self.assertEqual(original.read("data/data.bin"), seeded.read("data/data.bin"))
                original_json = json.loads(original.read("analyses.json"))
                seeded_json = json.loads(seeded.read("analyses.json"))
                self.assertEqual(False, original_json["analyses"][0]["options"]["setSeed"])
                self.assertEqual(True, seeded_json["analyses"][0]["options"]["setSeed"])
                self.assertEqual(1, seeded_json["analyses"][0]["options"]["seed"])
                self.assertEqual("preserved", seeded_json["analyses"][0]["options"]["other"])
            receipt["receipt_sha256"] = "0" * 64
            self.assertFalse(lane.verify_deterministic_fixture_receipt(receipt, source_sha))

    def test_ignores_seed_copies_in_saved_results_and_changes_only_active_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            source = base / "Death Penalty.jasp"
            clone = base / "Death Penalty_seeded.jasp"
            receipt_path = base / "evidence" / "fixture_receipt.json"
            active = {
                "analyses": [{
                    "id": 2,
                    "name": "RegressionLogLinearBayesian",
                    "dynamicModule": {"moduleName": "jaspFrequencies"},
                    "options": {"setSeed": False, "seed": 1, "other": "preserved"},
                }]
            }
            saved_results = {
                "options": [
                    {"setSeed": False, "seed": 1},
                    {"nested": {"setSeed": False, "seed": 1}},
                    {"another": [{"setSeed": False, "seed": 1}]},
                ],
                "results": {"modelsVisited": 4},
            }
            results_bytes = json.dumps(saved_results, sort_keys=True).encode("utf-8")
            with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("analyses.json", json.dumps(active).encode("utf-8"))
                archive.writestr("resources/2/jaspResults.json", results_bytes)
                archive.writestr("data/data.bin", b"immutable data payload")

            source_sha = lane.sha_file(source)
            inspection = lane.inspect_seed_option(source)
            self.assertEqual("analyses.json", inspection["active_configuration_member"])
            self.assertEqual(1, inspection["seed_option_match_count"])
            self.assertEqual("/analyses/0/options", inspection["matches"][0]["json_pointer"])

            receipt = lane.prepare_deterministic_fixture(source, clone, receipt_path, source_sha)
            self.assertTrue(lane.verify_deterministic_fixture_receipt(receipt, source_sha))
            self.assertEqual("analyses.json", receipt["changed_archive_member"])
            self.assertEqual(2, receipt["unchanged_non_active_member_count"])
            self.assertFalse(receipt["result_output_members_changed"])
            with zipfile.ZipFile(source, "r") as original, zipfile.ZipFile(clone, "r") as seeded:
                self.assertEqual(results_bytes, seeded.read("resources/2/jaspResults.json"))
                self.assertEqual(original.read("resources/2/jaspResults.json"),
                                 seeded.read("resources/2/jaspResults.json"))
                self.assertEqual(original.read("data/data.bin"), seeded.read("data/data.bin"))
                seeded_active = json.loads(seeded.read("analyses.json"))
                self.assertIs(seeded_active["analyses"][0]["options"]["setSeed"], True)
                self.assertEqual(1, seeded_active["analyses"][0]["options"]["seed"])
                self.assertEqual("preserved", seeded_active["analyses"][0]["options"]["other"])

    def test_ambiguous_or_missing_seed_options_fail_closed(self):
        for options in (
            [{"setSeed": False, "seed": 1}, {"setSeed": False, "seed": 1}],
            [{"setSeed": False, "seed": 2}],
        ):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as tmp:
                base = pathlib.Path(tmp)
                source = base / "Death Penalty.jasp"
                clone = base / "clone.jasp"
                receipt = base / "receipt.json"
                self.write_fixture(source, options)
                with self.assertRaises(lane.FixtureError):
                    lane.prepare_deterministic_fixture(
                        source, clone, receipt, lane.sha_file(source)
                    )
                self.assertFalse(clone.exists())
                self.assertFalse(receipt.exists())


class BoundedProcessTreeTests(unittest.TestCase):
    def test_timeout_terminates_descendants_without_waiting_for_inherited_output_pipe(self):
        child_code = "import time; time.sleep(60)"
        parent_code = (
            "import os, subprocess, sys, time; "
            f"child = subprocess.Popen([sys.executable, '-c', {json.dumps(child_code)}]); "
            "print(os.getpid(), child.pid, flush=True); "
            "time.sleep(60)"
        )
        started = lane.time.monotonic()
        test_env = lane.os.environ.copy()
        test_env.update({"GITHUB_RUN_ID": "12345", "GITHUB_RUN_ATTEMPT": "1"})
        with self.assertRaises(lane.subprocess.TimeoutExpired) as caught:
            lane.run_bounded_process_tree(
                [sys.executable, "-c", parent_code],
                env=test_env,
                timeout=1.0,
                case_id="process_tree_timeout",
                executable_sha256="b" * 64,
                runtime_ostree_commit="c" * 64,
            )
        self.assertLess(lane.time.monotonic() - started, 8.0)
        output = caught.exception.output
        if isinstance(output, bytes):
            output = output.decode("utf-8", "replace")
        parent_pid, child_pid = (int(value) for value in output.strip().splitlines()[-1].split())

        def is_running(pid):
            stat = pathlib.Path(f"/proc/{pid}/stat")
            if not stat.is_file():
                return False
            try:
                state = stat.read_text(encoding="ascii").rsplit(")", 1)[1].strip().split()[0]
                return state != "Z"
            except (OSError, IndexError):
                return False

        deadline = lane.time.monotonic() + 2.0
        while lane.time.monotonic() < deadline and (is_running(parent_pid) or is_running(child_pid)):
            lane.time.sleep(0.05)
        self.assertFalse(is_running(parent_pid))
        self.assertFalse(is_running(child_pid))
        receipt = caught.exception.process_tree_receipt
        self.assertEqual("LUNITA_JASP_PROCESS_TREE_RECEIPT/1.0", receipt["schema"])
        self.assertEqual("BLOCKED_TIMEOUT_PROCESS_GROUP_CLOSED", receipt["status"])
        self.assertEqual("12345", receipt["run_id"])
        self.assertEqual("1", receipt["run_attempt"])
        self.assertEqual("process_tree_timeout", receipt["case_id"])
        self.assertTrue(receipt["process_group_closed"])
        self.assertEqual([], receipt["remaining_live_pids"])

    def test_normal_exit_returns_hash_bound_process_group_receipt(self):
        test_env = lane.os.environ.copy()
        test_env.update({"GITHUB_RUN_ID": "12346", "GITHUB_RUN_ATTEMPT": "2"})
        command = [sys.executable, "-c", "print('jasp-clean-exit')"]
        completed = lane.run_bounded_process_tree(
            command,
            env=test_env,
            timeout=3,
            case_id="clean_exit",
            executable_sha256="d" * 64,
            runtime_ostree_commit="e" * 64,
        )
        self.assertEqual(0, completed.returncode)
        self.assertEqual("jasp-clean-exit\n", completed.stdout)
        receipt = completed.process_tree_receipt
        self.assertEqual("PASS_PROCESS_GROUP_CLOSED", receipt["status"])
        self.assertTrue(lane.validate_process_tree_receipt(
            receipt,
            command=command,
            env=test_env,
            timeout=3,
            case_id="clean_exit",
            executable_sha256="d" * 64,
            runtime_ostree_commit="e" * 64,
            stdout=completed.stdout,
            returncode=0,
        ))


class JaspRunnerTests(unittest.TestCase):
    def test_runner_pins_commit_and_records_each_real_return_code(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out = base / "out"
            out.mkdir()
            report = base / "evidence" / "jasp-suite.json"
            rootfs = base / "rootfs"
            source_fixture = rootfs / (
                "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/"
                "Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp"
            )
            JaspDeterministicFixtureTests.write_fixture(
                source_fixture, [{"setSeed": False, "seed": 1}]
            )
            source_sha = lane.sha_file(source_fixture)
            original_alias = rootfs / (
                "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/"
                "lunita-fixtures/DeathPenalty.jasp"
            )
            original_alias.parent.mkdir(parents=True, exist_ok=True)
            original_alias.symlink_to(source_fixture)

            banner = (
                "Starting JASP 0.98.8 from commit "
                "b6cd3b0310be4e18e1b673ac11f14e55615c8fa1\n"
            )
            fresh_rows = (
                "Row: | h: Model Comparison | \n"
                "Row: | h: Models | \n"
                "Row: | Model A | 0.500 | 1.000 | \n"
                "Row: | Note.Total number of models visited = 1 | \n"
                "Footer:\n"
            )
            responses = [
                SimpleNamespace(returncode=0, stdout="83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7\n", stderr=""),
                SimpleNamespace(returncode=0, stdout=banner + "flatpak baseline pass\n", stderr=""),
                SimpleNamespace(returncode=1, stdout=banner + "numeric delta\n", stderr=""),
                SimpleNamespace(returncode=0, stdout=banner + "flatpak baseline pass\n", stderr=""),
                SimpleNamespace(returncode=0, stdout=banner + fresh_rows, stderr=""),
                SimpleNamespace(returncode=0, stdout=banner + fresh_rows, stderr=""),
            ]
            response_iter = iter(responses)

            def fake_run(*args, **kwargs):
                return next(response_iter)

            with (
                mock.patch.object(lane, "OUT", out),
                mock.patch.dict(lane.os.environ, {"GITHUB_RUN_ID": "43409900123", "GITHUB_RUN_ATTEMPT": "2"}),
                mock.patch.object(lane, "ROOTFS", rootfs),
                mock.patch.object(lane, "DEATH_PENALTY_SOURCE_SHA256", source_sha),
                mock.patch.object(lane, "verify_jasp_runtime_mutation_receipt", return_value={
                    "status": "PASS", "returncode": 0, "receipt_sha256": "a" * 64,
                    "jasp_binary_sha256": "b" * 64, "flatpak_runtime_commit": "c" * 64,
                    "flatpak_sdk_commit": "d" * 64, "evidence": {},
                }),
                mock.patch.object(lane.subprocess, "run", side_effect=fake_run) as runner,
                mock.patch.object(lane, "run_bounded_process_tree", side_effect=fake_run) as bounded_runner,
                mock.patch.object(lane, "validate_process_tree_receipt", return_value=True),
            ):
                result = lane.run_jasp_regression_suite(report)

            self.assertEqual("BLOCKED_JASP_REGRESSION", result["status"])
            self.assertEqual(1, runner.call_count)
            self.assertTrue(result["workflow_identity_valid"])
            self.assertEqual({"run_id": "43409900123", "run_attempt": "2"}, result["workflow_identity"])
            self.assertEqual(5, bounded_runner.call_count)
            for call in bounded_runner.call_args_list:
                self.assertEqual("offscreen", call.kwargs["env"].get("QT_QPA_PLATFORM"))
                self.assertEqual("43409900123", call.kwargs["env"].get("GITHUB_RUN_ID"))
                self.assertEqual("2", call.kwargs["env"].get("GITHUB_RUN_ATTEMPT"))
                self.assertEqual(300, call.kwargs["timeout"])
                self.assertNotIn("-platform", call.args[0])
                self.assertNotIn("--timeOut=2", call.args[0])

            jasp_calls = [call.args[0] for call in bounded_runner.call_args_list if "--unitTest" in call.args[0]]
            self.assertEqual(5, len(jasp_calls))
            self.assertTrue(all(
                command[command.index("org.jaspstats.JASP") + 1] == "--unitTest"
                for command in jasp_calls
            ))
            self.assertTrue(all("--hide" not in command for command in jasp_calls))

            flatpak_command = result["tests"]["flatpak_launch"]["command"]
            self.assertFalse(any("RPROFILE" in arg or "SEED_HOOK" in arg for arg in flatpak_command))
            seeded_share = next(
                (arg for arg in flatpak_command
                 if arg.startswith("--filesystem=") and "flatpak-launch-seeded-fixture" in arg),
                None,
            )
            self.assertIsNotNone(seeded_share)
            self.assertTrue(any("DeathPenalty_seeded.jasp" in arg for arg in flatpak_command))
            seeded_receipt = result["tests"]["flatpak_launch"]["deterministic_fixture_receipt"]
            self.assertTrue(result["tests"]["flatpak_launch"]["deterministic_fixture_receipt_valid"])
            self.assertEqual(
                seeded_receipt["clone_sha256"],
                result["tests"]["flatpak_launch"]["deterministic_fixture_clone_sha256_after_execution"],
            )
            self.assertTrue(result["tests"]["flatpak_launch"]["deterministic_fixture_clone_unchanged_after_execution"])
            flatpak_log = pathlib.Path(result["tests"]["flatpak_launch"]["log_path"]).read_text()
            self.assertIn(
                f"DETERMINISTIC_FIXTURE_CLONE_SHA256_AFTER_EXECUTION={seeded_receipt['clone_sha256']}",
                flatpak_log.splitlines(),
            )
            self.assertIn("DETERMINISTIC_FIXTURE_CLONE_UNCHANGED_AFTER_EXECUTION=TRUE", flatpak_log.splitlines())
            self.assertEqual({"setSeed": False, "seed": 1}, seeded_receipt["before"])
            self.assertEqual({"setSeed": True, "seed": 1}, seeded_receipt["after"])
            self.assertEqual("analyses.json", seeded_receipt["changed_archive_member"])
            self.assertFalse(seeded_receipt["reference_results_modified"])
            self.assertNotEqual(source_sha, seeded_receipt["clone_sha256"])
            self.assertEqual(str(source_fixture), result["tests"]["flatpak_launch"]["original_fixture_path"])
            self.assertEqual(source_sha, result["tests"]["flatpak_launch"]["original_fixture_sha256"])
            self.assertTrue(result["tests"]["flatpak_launch"]["original_fixture_alias_valid"])
            self.assertEqual("PASS", result["tests"]["flatpak_launch"]["status"])
            self.assertEqual(1, result["tests"]["reliability"]["returncode"])
            self.assertEqual("BLOCKED", result["tests"]["reliability"]["status"])
            self.assertIn(
                "JASP_RELIABILITY_UNITTEST_RC=1",
                pathlib.Path(result["tests"]["reliability"]["log_path"]).read_text()
            )
            self.assertEqual("PASS_JASP_STRICT_ROUNDTRIP", result["roundtrip_gate"]["status"])
            self.assertEqual("PASS_DETERMINISTIC_REPLAY", result["roundtrip_gate"]["deterministic_replay_status"])
            self.assertEqual("PASS", result["roundtrip_gate"]["runtime_identity_status"])
            self.assertEqual(
                result["roundtrip_gate"]["save_actual_result_rows_sha256"],
                result["roundtrip_gate"]["rerun_actual_result_rows_sha256"],
            )
            self.assertTrue(result["roundtrip_gate"]["original_sample_unchanged"])
            self.assertTrue(result["roundtrip_gate"]["temporary_fixture_removed_after_test"])
            self.assertTrue(report.is_file())




    def test_post_execution_seeded_clone_mutation_blocks_flatpak_launch(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out = base / "out"
            out.mkdir()
            report = base / "evidence" / "jasp-suite.json"
            rootfs = base / "rootfs"
            source_fixture = rootfs / (
                "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/"
                "Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp"
            )
            JaspDeterministicFixtureTests.write_fixture(
                source_fixture, [{"setSeed": False, "seed": 1}]
            )
            source_sha = lane.sha_file(source_fixture)
            original_alias = rootfs / (
                "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/"
                "lunita-fixtures/DeathPenalty.jasp"
            )
            original_alias.parent.mkdir(parents=True, exist_ok=True)
            original_alias.symlink_to(source_fixture)

            banner = (
                "Starting JASP 0.98.8 from commit "
                "b6cd3b0310be4e18e1b673ac11f14e55615c8fa1\n"
            )
            fresh_rows = (
                "Row: | h: Model Comparison | \n"
                "Row: | h: Models | \n"
                "Row: | Model A | 0.500 | 1.000 | \n"
                "Row: | Note.Total number of models visited = 1 | \n"
                "Footer:\n"
            )
            responses = iter([
                SimpleNamespace(returncode=0, stdout="83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7\n", stderr=""),
                SimpleNamespace(returncode=0, stdout=banner + fresh_rows, stderr=""),
                SimpleNamespace(returncode=0, stdout=banner + fresh_rows, stderr=""),
                SimpleNamespace(returncode=0, stdout=banner + fresh_rows, stderr=""),
                SimpleNamespace(returncode=0, stdout=banner + fresh_rows, stderr=""),
                SimpleNamespace(returncode=0, stdout=banner + fresh_rows, stderr=""),
            ])

            def fake_bounded(command, **kwargs):
                completed = next(responses)
                if kwargs.get("case_id") == "flatpak_launch":
                    clone = pathlib.Path(command[command.index("--unitTest") + 1])
                    clone.write_bytes(clone.read_bytes() + b"\nmutated after process exit")
                return completed

            with (
                mock.patch.dict(lane.os.environ, {"GITHUB_RUN_ID": "43409900123", "GITHUB_RUN_ATTEMPT": "2"}),
                mock.patch.object(lane, "ROOTFS", rootfs),
                mock.patch.object(lane, "DEATH_PENALTY_SOURCE_SHA256", source_sha),
                mock.patch.object(lane, "verify_jasp_runtime_mutation_receipt", return_value={
                    "status": "PASS", "returncode": 0, "receipt_sha256": "a" * 64,
                    "jasp_binary_sha256": "b" * 64, "flatpak_runtime_commit": "c" * 64,
                    "flatpak_sdk_commit": "d" * 64, "evidence": {},
                }),
                mock.patch.object(lane.subprocess, "run", return_value=next(responses)),
                mock.patch.object(lane, "run_bounded_process_tree", side_effect=fake_bounded),
                mock.patch.object(lane, "validate_process_tree_receipt", return_value=True),
            ):
                result = lane.run_jasp_regression_suite(report)

            flatpak = result["tests"]["flatpak_launch"]
            receipt = flatpak["deterministic_fixture_receipt"]
            self.assertEqual("BLOCKED", flatpak["status"])
            self.assertFalse(flatpak["deterministic_fixture_clone_unchanged_after_execution"])
            self.assertNotEqual(
                receipt["clone_sha256"],
                flatpak["deterministic_fixture_clone_sha256_after_execution"],
            )
            log = pathlib.Path(flatpak["log_path"]).read_text()
            self.assertIn("DETERMINISTIC_FIXTURE_CLONE_UNCHANGED_AFTER_EXECUTION=FALSE", log.splitlines())
            self.assertEqual("BLOCKED_JASP_REGRESSION", result["status"])


class JaspStrictRoundtripPositiveTests(unittest.TestCase):
    def test_roundtrip_passes_when_native_seed_clone_is_stable(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out = base / "out"
            out.mkdir()
            rootfs = base / "rootfs"
            source = rootfs / (
                "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/"
                "Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp"
            )
            JaspDeterministicFixtureTests.write_fixture(
                source, [{"setSeed": False, "seed": 1}]
            )
            source_sha = lane.sha_file(source)
            banner = (
                "Starting JASP 0.98.8 from commit "
                "b6cd3b0310be4e18e1b673ac11f14e55615c8fa1\n"
            )
            fresh_rows = (
                "Row: | h: Model Comparison | \n"
                "Row: | h: Models | \n"
                "Row: | Model A | 0.500 | 1.000 | \n"
                "Row: | Note.Total number of models visited = 1 | \n"
                "Footer:\n"
            )
            responses = [
                SimpleNamespace(returncode=0, stdout=banner + fresh_rows, stderr=""),
                SimpleNamespace(returncode=0, stdout=banner + fresh_rows, stderr=""),
            ]
            response_iter = iter(responses)
            with (
                mock.patch.object(lane, "OUT", out),
                mock.patch.object(lane, "ROOTFS", rootfs),
                mock.patch.object(lane, "DEATH_PENALTY_SOURCE_SHA256", source_sha),
                mock.patch.object(lane, "run_bounded_process_tree", side_effect=lambda *a, **k: next(response_iter)) as runner,
                mock.patch.object(lane, "validate_process_tree_receipt", return_value=True),
            ):
                result = lane.run_death_penalty_roundtrip(
                    "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7",
                    {"QT_QPA_PLATFORM": "offscreen"},
                    "POSITIVE_TEST",
                )
            self.assertEqual(2, runner.call_count)
            self.assertEqual("PASS_JASP_STRICT_ROUNDTRIP", result["status"])
            self.assertEqual("PASS_DETERMINISTIC_REPLAY", result["deterministic_replay_status"])
            self.assertEqual("PASS", result["runtime_identity_status"])
            self.assertEqual("PASS_REFERENCE_AND_REPLAY", result["save_run"]["status"])
            self.assertEqual("PASS_REFERENCE_AND_REPLAY", result["strict_rerun_after_save"]["status"])
            self.assertEqual(
                result["save_actual_result_rows_sha256"],
                result["rerun_actual_result_rows_sha256"],
            )
            self.assertTrue(result["deterministic_fixture_receipt_valid"])
            self.assertTrue(result["original_sample_unchanged"])
            self.assertTrue(result["temporary_fixture_removed_after_test"])
            self.assertTrue(result["temporary_fixture_stable_after_save_and_rerun"])


class TargetRuntimeEvidenceGateTests(unittest.TestCase):
    @staticmethod
    def valid_target_receipt():
        return {
            "schema": "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0",
            "status": "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED",
            "candidate_id": "G06_REBUILD_CANDIDATE_R1",
            "workflow_identity": {
                "run_id": "43337415331",
                "run_attempt": "1",
                "host_bind_name": "lunita-host-43337415331-1",
                "xdg_runtime_dir": "/run/lunita-host-43337415331-1-runtime-1000",
            },
            "xdg_runtime_dir": {
                "status": "PASS_XDG_RUNTIME_DIR_UID1000_PRIVATE",
                "path": "/run/lunita-host-43337415331-1-runtime-1000",
                "mode_octal": "0o700",
            },
            "certification": "NOT_GRANTED",
            "canonical_g06_certification": "NOT_GRANTED",
            "canonical_g08_binding_mutation": False,
            "overlay_integrity": {
                "status": "PASS_OVERLAY_INTEGRITY",
                "frozen_g06_mutated": False,
                "canonical_g08_mutated": False,
            },
            "e04_quantization": {"status": "PASS_E04_INT8_QUALITY_GATE"},
            "qwen_e01": {"status": "PASS_E01_QWEN_INFERENCE"},
            "engine_acceptance_tests": {
                "status": "PASS", "tests_run": 25, "skipped": 0,
                "engine_ids_covered": [f"E{i:02d}" for i in range(2, 16)],
                "command_route_matrix_test_present": True,
            },
            "legacy_application_smokes": {
                "status": "PASS_LEGACY_APPLICATION_SMOKES",
                "commands": {
                    "brujula-self-test": {"status": "PASS", "returncode": 0},
                    "r-self-test": {"status": "PASS", "returncode": 0},
                    "jamovi-self-test": {"status": "PASS", "returncode": 0},
                    "jasp-self-test": {"status": "PASS", "returncode": 0},
                    "fault model-missing": {"status": "PASS", "returncode": 0},
                    "fault model-corrupted": {"status": "PASS", "returncode": 0},
                    "fault dependency-missing": {"status": "PASS", "returncode": 0},
                    "fault permission-denied": {"status": "PASS", "returncode": 0},
                    "fault low-memory": {"status": "PASS", "returncode": 0},
                    "fault process-crash": {"status": "PASS", "returncode": 0},
                    "fault browser-crash": {"status": "PASS", "returncode": 0},
                    "fault tool-failure": {"status": "PASS", "returncode": 0},
                    "fault invalid-input": {"status": "PASS", "returncode": 0},
                    "fault interrupted-execution": {"status": "PASS", "returncode": 0},
                    "fault restart": {"status": "PASS", "returncode": 0},
                },
            },
        }

    def test_target_runtime_receipt_requires_all_motors_and_legacy_smokes(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp) / "target-receipts"
            directory.mkdir()
            path = directory / "LUNITA_TARGET_RUNTIME_ACCEPTANCE_test.json"
            path.write_text(json.dumps(self.valid_target_receipt()), encoding="utf-8")
            with mock.patch.object(lane, "TARGET_RUNTIME_RECEIPT_DIR", directory):
                result = lane.latest_target_runtime_acceptance()
            self.assertEqual("PASS_TARGET_RUNTIME_ACCEPTANCE", result["status"])
            self.assertEqual("43337415331", result["workflow_identity"]["run_id"])
            self.assertEqual("1", result["workflow_identity"]["run_attempt"])
            self.assertEqual("PASS_XDG_RUNTIME_DIR_UID1000_PRIVATE", result["xdg_runtime_dir"]["status"])
            self.assertEqual(25, result["engine_acceptance_tests"]["tests_run"])
            self.assertEqual("PASS_E01_QWEN_INFERENCE", result["qwen_e01"]["status"])
            self.assertEqual("PASS_E04_INT8_QUALITY_GATE", result["e04_quantization"]["status"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), result["receipt_sha256"])

    def test_target_runtime_receipt_rejects_missing_workflow_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp) / "target-receipts"
            directory.mkdir()
            receipt = self.valid_target_receipt()
            receipt.pop("workflow_identity")
            (directory / "LUNITA_TARGET_RUNTIME_ACCEPTANCE_test.json").write_text(
                json.dumps(receipt), encoding="utf-8")
            with mock.patch.object(lane, "TARGET_RUNTIME_RECEIPT_DIR", directory):
                result = lane.latest_target_runtime_acceptance()
            self.assertEqual("BLOCKED_TARGET_RUNTIME_RECEIPT_INVALID", result["status"])
            self.assertEqual("WORKFLOW_IDENTITY_MISSING_OR_INVALID", result["reason"])

    def test_target_runtime_receipt_rejects_identity_attempt_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp) / "target-receipts"
            directory.mkdir()
            receipt = self.valid_target_receipt()
            receipt["workflow_identity"]["run_attempt"] = "2"
            (directory / "LUNITA_TARGET_RUNTIME_ACCEPTANCE_test.json").write_text(
                json.dumps(receipt), encoding="utf-8")
            with mock.patch.object(lane, "TARGET_RUNTIME_RECEIPT_DIR", directory):
                result = lane.latest_target_runtime_acceptance()
            self.assertEqual("BLOCKED_TARGET_RUNTIME_RECEIPT_INVALID", result["status"])
            self.assertEqual("WORKFLOW_IDENTITY_RUNTIME_BINDING_MISMATCH", result["reason"])

    def test_newest_failed_target_receipt_cannot_fall_back_to_an_older_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp) / "target-receipts"
            directory.mkdir()
            older = directory / "LUNITA_TARGET_RUNTIME_ACCEPTANCE_older.json"
            newer = directory / "LUNITA_TARGET_RUNTIME_ACCEPTANCE_newer.json"
            older.write_text(json.dumps(self.valid_target_receipt()), encoding="utf-8")
            newer.write_text(json.dumps({"schema": "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0",
                                         "status": "BLOCKED_E01_QWEN"}), encoding="utf-8")
            import os, time
            os.utime(older, (1000, 1000))
            os.utime(newer, (2000, 2000))
            with mock.patch.object(lane, "TARGET_RUNTIME_RECEIPT_DIR", directory):
                result = lane.latest_target_runtime_acceptance()
            self.assertEqual("BLOCKED_TARGET_RUNTIME_RECEIPT_INVALID", result["status"])
            self.assertEqual(str(newer), result["receipt_path"])

    def test_target_runtime_receipt_rejects_missing_e01(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp) / "target-receipts"
            directory.mkdir()
            receipt = self.valid_target_receipt()
            receipt["qwen_e01"] = {"status": "BLOCKED"}
            (directory / "LUNITA_TARGET_RUNTIME_ACCEPTANCE_test.json").write_text(
                json.dumps(receipt), encoding="utf-8")
            with mock.patch.object(lane, "TARGET_RUNTIME_RECEIPT_DIR", directory):
                result = lane.latest_target_runtime_acceptance()
            self.assertEqual("BLOCKED_TARGET_RUNTIME_RECEIPT_INVALID", result["status"])

    def test_target_runtime_receipt_rejects_skipped_engine_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp) / "target-receipts"
            directory.mkdir()
            receipt = self.valid_target_receipt()
            receipt["engine_acceptance_tests"]["skipped"] = 1
            (directory / "LUNITA_TARGET_RUNTIME_ACCEPTANCE_test.json").write_text(
                json.dumps(receipt), encoding="utf-8")
            with mock.patch.object(lane, "TARGET_RUNTIME_RECEIPT_DIR", directory):
                result = lane.latest_target_runtime_acceptance()
            self.assertEqual("BLOCKED_TARGET_RUNTIME_RECEIPT_INVALID", result["status"])

    def test_independent_report_blocks_without_target_runtime_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(lane, "TARGET_RUNTIME_RECEIPT_DIR", pathlib.Path(tmp) / "missing"), \
                 mock.patch.object(lane, "INDEPENDENT_REPORT", pathlib.Path(tmp) / "old-independent.json"), \
                 mock.patch.object(lane, "RUNTIME_REPORT", pathlib.Path(tmp) / "runtime.json"), \
                 mock.patch.object(lane, "MISSION_PATH", pathlib.Path(tmp) / "MISION1.txt"):
                report = lane.update_independent_report(
                    None, {"status": "BLOCKED_JASP_REGRESSION", "cases": {}}
                )
            check = report["checks"]["target_v1_8_runtime_acceptance_e01_e15_int8"]
            self.assertEqual("BLOCKED", check["status"])
            self.assertEqual("BLOCKED_TARGET_RUNTIME_RECEIPT_MISSING", check["details"])
            self.assertIn("target_v1_8_runtime_acceptance_e01_e15_int8", report["open_items"])

    def test_stable_release_is_blocked_without_hash_bound_target_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            runtime_path = root / "runtime.json"
            runtime_path.write_text(json.dumps({
                "schema": "CUSTOSZ_LUNITA_BETA_RUNTIME_FUNCTIONAL_TESTS/1.0",
                "candidate_id": "G06_REBUILD_CANDIDATE_R1",
            }), encoding="utf-8")
            report_path = root / "independent.json"
            report = {
                "schema": "CUSTOSZ_LUNITA_BETA_INDEPENDENT_VALIDATION/1.0",
                "candidate_id": "G06_REBUILD_CANDIDATE_R1",
                "mission_sha256": lane.MISSION_SHA,
                "status": "PASS_INDEPENDENT_VALIDATION",
                "checks": {"baseline_check": {"status": "PASS"}},
                "runtime_report_sha256": hashlib.sha256(runtime_path.read_bytes()).hexdigest(),
                "frozen_g06_mutated": False,
                "canonical_g08_bindings_mutated": False,
            }
            report_path.write_text(json.dumps(report), encoding="utf-8")
            with mock.patch.object(lane, "INDEPENDENT_REPORT", report_path), \
                 mock.patch.object(lane, "RUNTIME_REPORT", runtime_path), \
                 mock.patch.object(lane, "OUT", root / "outputs"):
                result = lane.stable_release_gate()
            self.assertEqual("BLOCKED_TARGET_V1_8_RUNTIME_BINDING", result["status"])
            self.assertEqual("NOT_GRANTED", result["certification"])


class StableReleaseReceiptTests(unittest.TestCase):
    def test_release_receipt_is_immutable_and_current_pointer_requires_revalidation(self):
        with tempfile.TemporaryDirectory() as tmp:
            st = pathlib.Path(tmp) / "state"
            gate = {
                "status": "STABLE_RELEASE_ELIGIBLE", "version": "1.8.0", "release_name": "LUNITA_STABLE_1_8",
                "candidate_id": "G06_REBUILD_CANDIDATE_R1", "runtime_report_sha256": "1" * 64,
                "independent_report_sha256": "2" * 64,
                "s32_receipt": {"path": "/tmp/s32.json", "sha256": "3" * 64},
                "rootfs_path": "/tmp/candidate/rootfs", "frozen_g06_mutated": False,
                "canonical_g08_bindings_mutated": False, "certification_scope": "VERSIONED_DERIVED_CANDIDATE_ONLY",
                "mission_completion_claim": False,
            }
            with mock.patch.object(lane, "ST", st):
                first = lane.persist_stable_release_status(gate)
                receipt = pathlib.Path(first["release_receipt_path"])
                original_bytes = receipt.read_bytes()
                second = lane.persist_stable_release_status({"status": "BLOCKED_INDEPENDENT_VALIDATION"})
                pointer = json.loads(pathlib.Path(second["current_status_path"]).read_text())
            self.assertEqual("CERTIFIED_STABLE_RELEASE_ACTIVE", first["status"])
            self.assertEqual("LUNITA_STABLE_1_8", first["release_name"])
            self.assertEqual("1.8.0", json.loads(original_bytes)["version"])
            self.assertEqual("LUNITA_STABLE_1_8", json.loads(original_bytes)["release_name"])
            self.assertEqual("REVALIDATION_REQUIRED", second["status"])
            self.assertEqual(original_bytes, receipt.read_bytes())
            self.assertEqual("REVALIDATION_REQUIRED", pointer["status"])
            self.assertEqual("LUNITA_STABLE_1_8", pointer["release_name"])
            self.assertEqual("CERTIFIED_STABLE_RELEASE", json.loads(original_bytes)["status"])

class DirectV18CertificationProfileTests(unittest.TestCase):
    @staticmethod
    def frozen_manifest():
        return {
            "schema": "LUNITA_CANDIDATE_FREEZE/1.0",
            "candidate_id": "G06_REBUILD_CANDIDATE_R1",
            "version": "1.8.0",
            "freeze_status": "FROZEN_CANDIDATE_NOT_CERTIFIED",
            "preserved_baseline": {
                "frozen_g06_mutated": False,
                "canonical_g08_bindings_mutated": False,
                "legacy_v1_7_launcher_replaced": False,
            },
        }

    def test_direct_independent_report_uses_v18_receipt_without_v17_mission_or_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            rootfs = base / "rootfs"
            launcher = rootfs / "opt/lunita/agent/lunita.py"
            launcher.parent.mkdir(parents=True)
            launcher.write_bytes(b"pinned legacy launcher")
            manifest = base / "LUNITA_V1_8_CANDIDATE_FREEZE.json"
            manifest.write_text(json.dumps(self.frozen_manifest()), encoding="utf-8")
            receipt = base / "LUNITA_TARGET_RUNTIME_ACCEPTANCE_test.json"
            receipt.write_text(json.dumps({"schema": "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0"}), encoding="utf-8")
            independent = base / "independent.json"
            independent.write_text(json.dumps({
                "checks": {"legacy_v17_unbound_pass": {"status": "PASS", "returncode": 0}}
            }), encoding="utf-8")
            target = {
                "status": "PASS_TARGET_RUNTIME_ACCEPTANCE",
                "receipt_path": str(receipt),
                "receipt_sha256": lane.sha_file(receipt),
                "overlay_integrity": {
                    "status": "PASS_OVERLAY_INTEGRITY",
                    "legacy_launcher_sha256": lane.sha_file(launcher),
                    "frozen_g06_mutated": False,
                    "canonical_g08_mutated": False,
                },
                "e04_quantization": {"status": "PASS_E04_INT8_QUALITY_GATE"},
                "qwen_e01": {"status": "PASS_E01_QWEN_INFERENCE"},
                "engine_acceptance_tests": {"tests_run": 25},
                "legacy_application_smokes": {"status": "PASS_LEGACY_APPLICATION_SMOKES"},
            }
            with mock.patch.object(lane, "CERTIFICATION_PROFILE", "V1_8_DIRECT"), \
                 mock.patch.object(lane, "CANDIDATE_MANIFEST", manifest), \
                 mock.patch.object(lane, "ROOTFS", rootfs), \
                 mock.patch.object(lane, "RUNTIME_REPORT", base / "missing-v17-runtime.json"), \
                 mock.patch.object(lane, "INDEPENDENT_REPORT", independent), \
                 mock.patch.object(lane, "MISSION_PATH", base / "missing-MISION1.txt"), \
                 mock.patch.object(lane, "latest_target_runtime_acceptance", return_value=target):
                report = lane.update_independent_report(
                    None, {"status": "BLOCKED_JASP_PACKAGED_FIXTURE_NONREGRESSION", "cases": {}}
                )
            checks = report["checks"]
            self.assertEqual("PASS", checks["candidate_manifest_identity_sha256"]["status"])
            self.assertEqual("PASS", checks["runtime_report_and_launcher_identity"]["status"])
            self.assertEqual("PASS", checks["target_v1_8_runtime_acceptance_e01_e15_int8"]["status"])
            self.assertNotIn("MISION1_identity_sha256", checks)
            self.assertNotIn("legacy_v17_unbound_pass", checks)
            self.assertEqual(str(receipt), report["runtime_report_path"])
            self.assertEqual(lane.sha_file(receipt), report["runtime_report_sha256"])
            self.assertEqual("V1_8_DIRECT", report["certification_profile"])
            self.assertEqual("BLOCKED_REQUIRED_REGRESSION_OR_INVENTORY", report["status"])

    def test_direct_stable_gate_uses_v18_receipt_and_still_requires_s32(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            receipts = base / "target-receipts"
            receipts.mkdir()
            target_data = TargetRuntimeEvidenceGateTests.valid_target_receipt()
            run_id = target_data["workflow_identity"]["run_id"]
            run_attempt = target_data["workflow_identity"]["run_attempt"]
            receipt = receipts / "LUNITA_TARGET_RUNTIME_ACCEPTANCE_test.json"
            receipt.write_text(json.dumps(target_data), encoding="utf-8")
            manifest = base / "LUNITA_V1_8_CANDIDATE_FREEZE.json"
            manifest.write_text(json.dumps(self.frozen_manifest()), encoding="utf-8")
            image = base / "LUNITA.squashfs"
            image.write_bytes(b"verified stable-gate target image")
            image_sha = lane.sha_file(image)
            checksum = base / "LUNITA.squashfs.sha256"
            checksum.write_text(f"{image_sha}  {image.name}\n", encoding="ascii")
            package = base / "LUNITA_SQUASHFS_PACKAGE_RECEIPT.json"
            target_sha = lane.sha_file(receipt)
            package.write_text(json.dumps({
                "schema": "LUNITA_SQUASHFS_PACKAGE_RECEIPT/1.0",
                "status": "PASS_SQUASHFS_PACKAGE_AND_ROUNDTRIP_NOT_CERTIFIED",
                "candidate_id": "G06_REBUILD_CANDIDATE_R1", "version": "1.8.0",
                "image_name": image.name, "image_sha256": image_sha, "image_bytes": image.stat().st_size,
                "roundtrip_manifest_match": True, "source_rootfs_unchanged": True,
                "target_runtime_receipt_path": str(receipt), "target_runtime_receipt_sha256": target_sha,
                "target_runtime_status": "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED",
                "mksquashfs": "PASS", "unsquashfs_superblock": "PASS", "unsquashfs_roundtrip": "PASS",
            }), encoding="utf-8")
            package_sha = lane.sha_file(package)
            checksum_sha = lane.sha_file(checksum)
            manifest_sha = lane.sha_file(manifest)
            image_check = {
                "status": "PASS", "returncode": 0,
                "image_path": str(image), "image_sha256": image_sha, "image_bytes": image.stat().st_size,
                "checksum_path": str(checksum), "checksum_sha256": checksum_sha,
                "package_receipt_path": str(package), "package_receipt_sha256": package_sha,
                "candidate_manifest_path": str(manifest), "candidate_manifest_sha256": manifest_sha,
                "evidence": {str(image): image_sha, str(checksum): checksum_sha,
                             str(package): package_sha, str(manifest): manifest_sha},
            }
            executable_sha = "a" * 64
            runtime_commit = "b" * 64
            process_cases = [
                "flatpak_launch", "reliability", "weight_gain",
                "death_penalty_save", "death_penalty_rerun",
            ]
            process_invocations = [
                {
                    "schema": "LUNITA_JASP_PROCESS_TREE_RECEIPT/1.0",
                    "status": "PASS_PROCESS_GROUP_CLOSED",
                    "run_id": run_id,
                    "run_attempt": run_attempt,
                    "case_id": case_id,
                    "invocation_id": f"{index:032x}",
                    "process_group_id": 400 + index,
                    "session_id": 400 + index,
                    "executable_sha256": executable_sha,
                    "runtime_ostree_commit": runtime_commit,
                    "command_sha256": "c" * 64,
                    "timeout_seconds": 180,
                    "started_at_utc": "2026-11-13T00:00:00Z",
                    "finished_at_utc": "2026-11-13T00:00:01Z",
                    "returncode": 0,
                    "timeout_triggered": False,
                    "termination_signals": [],
                    "remaining_live_pids": [],
                    "process_group_closed": True,
                    "captured_output_sha256": "d" * 64,
                    "captured_output_bytes": 0,
                }
                for index, case_id in enumerate(process_cases, start=1)
            ]
            independent = base / "independent.json"
            independent.write_text(json.dumps({
                "schema": "CUSTOSZ_LUNITA_BETA_INDEPENDENT_VALIDATION/1.0",
                "candidate_id": "G06_REBUILD_CANDIDATE_R1",
                "certification_profile": "V1_8_DIRECT",
                "candidate_manifest_sha256": manifest_sha,
                "squashfs_image_path": str(image), "squashfs_image_sha256": image_sha,
                "squashfs_image_bytes": image.stat().st_size,
                "squashfs_checksum_path": str(checksum), "squashfs_checksum_sha256": checksum_sha,
                "squashfs_package_receipt_path": str(package), "squashfs_package_receipt_sha256": package_sha,
                "mission_sha256": None, "status": "PASS_INDEPENDENT_VALIDATION",
                "runtime_report_path": str(receipt), "runtime_report_sha256": target_sha,
                "checks": {
                    "target_v1_8_runtime_acceptance_e01_e15_int8": {
                        "status": "PASS", "returncode": 0,
                        "receipt_path": str(receipt), "receipt_sha256": target_sha,
                    },
                    "rootfs": {"status": "PASS", "returncode": 0},
                    "jasp": {"status": "PASS", "returncode": 0},
                    "jasp_packaged_fixture_nonregression": {"status": "PASS", "returncode": 0},
                    "jasp_post_mutation_runtime_identity": {
                        "status": "PASS", "returncode": 0,
                        "jasp_binary_sha256": executable_sha,
                        "flatpak_runtime_commit": runtime_commit,
                    },
                    "jasp_process_tree_lifecycle": {
                        "status": "PASS", "returncode": 0,
                        "invocation_count": 5, "expected_invocation_count": 5,
                        "unique_invocation_id_count": 5,
                        "workflow_identity": {"run_id": run_id, "run_attempt": run_attempt},
                        "jasp_binary_sha256": executable_sha,
                        "flatpak_runtime_ostree_commit": runtime_commit,
                        "invocations": process_invocations,
                    },
                    "squashfs_image_and_package_binding": image_check,
                },
                "frozen_g06_mutated": False, "canonical_g08_bindings_mutated": False,
            }), encoding="utf-8")
            out = base / "outputs"
            out.mkdir()
            with mock.patch.dict(lane.os.environ, {"GITHUB_RUN_ID": run_id, "GITHUB_RUN_ATTEMPT": run_attempt}), \
                 mock.patch.object(lane, "CERTIFICATION_PROFILE", "V1_8_DIRECT"), \
                 mock.patch.object(lane, "CANDIDATE_MANIFEST", manifest), \
                 mock.patch.object(lane, "SQUASHFS_IMAGE", image), \
                 mock.patch.object(lane, "SQUASHFS_CHECKSUM", checksum), \
                 mock.patch.object(lane, "SQUASHFS_PACKAGE_RECEIPT", package), \
                 mock.patch.object(lane, "TARGET_RUNTIME_RECEIPT_DIR", receipts), \
                 mock.patch.object(lane, "INDEPENDENT_REPORT", independent), \
                 mock.patch.object(lane, "RUNTIME_REPORT", base / "missing-v17-runtime.json"), \
                 mock.patch.object(lane, "OUT", out):
                result = lane.stable_release_gate()
            self.assertEqual("WAITING_FOR_S32_BOUND_CERTIFICATION_RECEIPT", result["status"])
            self.assertEqual("NOT_GRANTED", result["certification"])



class JaspPostMutationRuntimeIdentityTests(unittest.TestCase):
    def test_missing_mutation_receipt_fails_closed(self):
        with (
            mock.patch.object(lane, "CERTIFICATION_PROFILE", "V1_8_DIRECT"),
            mock.patch.dict(lane.os.environ, {}, clear=True),
        ):
            result = lane.verify_jasp_runtime_mutation_receipt()
        self.assertEqual("BLOCKED", result["status"])
        self.assertEqual(1, result["returncode"])
        self.assertIn("LUNITA_JASP_MUTATION_RECEIPT is unset", result["details"])

    def test_embedded_formatter_patch_accepts_hash_bound_jasp_binary_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = pathlib.Path(tmp) / "files/bin/JASP"
            binary.parent.mkdir(parents=True)
            before = b"JASP before embedded formatter patch"
            after = b"JASP after embedded formatter patch"
            binary.write_bytes(after)
            before_sha = hashlib.sha256(before).hexdigest()
            after_sha = hashlib.sha256(after).hexdigest()
            path = str(binary.resolve())
            app = {
                "binary_before_sha256": before_sha,
                "binary_after": {"path": path, "sha256": after_sha},
                "binary_unchanged_by_formatter_patch": False,
                "binary_transition": {
                    "path": path, "before_sha256": before_sha,
                    "after_sha256": after_sha, "changed": True,
                    "scope": "EMBEDDED_FORMATTER_RESOURCE_IN_APPLICATION_BINARY",
                },
            }
            patch = {
                "changed_jasp_binary": True,
                "patched_resources": [{
                    "path": path, "before_sha256": before_sha,
                    "after_sha256": after_sha, "observed_after_sha256": after_sha,
                }],
            }
            lane.validate_jasp_binary_patch_binding(app, patch)

    def test_unchanged_executable_allows_patch_in_separate_qt_resource(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "files"
            (root / "bin").mkdir(parents=True)
            (root / "resources").mkdir()
            binary = root / "bin/JASP"
            resource = root / "resources/formatter.js"
            binary.write_bytes(b"unchanged executable")
            before = b"old Qt resource"
            after = b"new Qt resource"
            resource.write_bytes(after)
            binary_sha = hashlib.sha256(binary.read_bytes()).hexdigest()
            before_sha = hashlib.sha256(before).hexdigest()
            after_sha = hashlib.sha256(after).hexdigest()
            path = str(binary.resolve())
            app = {
                "binary_before_sha256": binary_sha,
                "binary_after": {"path": path, "sha256": binary_sha},
                "binary_unchanged_by_formatter_patch": True,
                "binary_transition": {
                    "path": path, "before_sha256": binary_sha,
                    "after_sha256": binary_sha, "changed": False,
                    "scope": "APPLICATION_BINARY_UNCHANGED",
                },
            }
            patch = {
                "changed_jasp_binary": False,
                "patched_resources": [{
                    "path": str(resource.resolve()), "before_sha256": before_sha,
                    "after_sha256": after_sha, "observed_after_sha256": after_sha,
                }],
            }
            lane.validate_jasp_binary_patch_binding(app, patch)

    def test_binary_change_without_matching_patch_row_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = pathlib.Path(tmp) / "files/bin/JASP"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"post-patch")
            before_sha = hashlib.sha256(b"pre-patch").hexdigest()
            after_sha = hashlib.sha256(b"post-patch").hexdigest()
            path = str(binary.resolve())
            app = {
                "binary_before_sha256": before_sha,
                "binary_after": {"path": path, "sha256": after_sha},
                "binary_unchanged_by_formatter_patch": False,
                "binary_transition": {
                    "path": path, "before_sha256": before_sha,
                    "after_sha256": after_sha, "changed": True,
                    "scope": "EMBEDDED_FORMATTER_RESOURCE_IN_APPLICATION_BINARY",
                },
            }
            patch = {"changed_jasp_binary": True, "patched_resources": []}
            with self.assertRaisesRegex(RuntimeError, "exactly one embedded formatter patch record"):
                lane.validate_jasp_binary_patch_binding(app, patch)


class JaspReferenceMismatchClassificationTests(unittest.TestCase):
    def test_replay_pass_is_never_labelled_as_strict_reference_pass(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out = base / "out"
            evidence = base / "evidence"
            out.mkdir()
            evidence.mkdir()
            rootfs = base / "rootfs"
            source = rootfs / (
                "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/"
                "Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp"
            )
            JaspDeterministicFixtureTests.write_fixture(
                source, [{"setSeed": False, "seed": 1}]
            )
            source_sha = lane.sha_file(source)
            banner = (
                "Starting JASP 0.98.8 from commit "
                "b6cd3b0310be4e18e1b673ac11f14e55615c8fa1\n"
            )
            rows = (
                "Row: | h: Model Comparison | \n"
                "Row: | h: Models | \n"
                "Row: | Model A | 0.500 | 1.000 | \n"
                "Footer:\n"
                "The results are different...\n"
            )
            responses = [
                SimpleNamespace(returncode=1, stdout=banner + rows, stderr=""),
                SimpleNamespace(returncode=1, stdout=banner + rows, stderr=""),
            ]
            response_iter = iter(responses)
            with (
                mock.patch.object(lane, "OUT", out),
                mock.patch.object(lane, "EVIDENCE", evidence),
                mock.patch.object(lane, "ROOTFS", rootfs),
                mock.patch.object(lane, "DEATH_PENALTY_SOURCE_SHA256", source_sha),
                mock.patch.object(lane, "run_bounded_process_tree", side_effect=lambda *a, **k: next(response_iter)),
                mock.patch.object(lane, "validate_process_tree_receipt", return_value=True),
                mock.patch.object(lane, "process_tree_receipt_identity_matches", return_value=True),
            ):
                result = lane.run_death_penalty_roundtrip(
                    "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7",
                    {"QT_QPA_PLATFORM": "offscreen"},
                    "REFERENCE_MISMATCH_TEST",
                )
                aggregate = lane.latest_jasp_evidence()

            self.assertEqual("PASS_DETERMINISTIC_REPLAY_REFERENCE_MISMATCH_RECORDED", result["status"])
            self.assertEqual("BLOCKED_STORED_REFERENCE_MISMATCH", result["reference_comparison_status"])
            self.assertEqual("PASS_DETERMINISTIC_REPLAY", result["deterministic_replay_status"])
            self.assertEqual(1, result["save_run"]["returncode"])
            self.assertEqual(1, result["strict_rerun_after_save"]["returncode"])
            self.assertTrue(result["original_sample_unchanged"])
            replay = aggregate["cases"]["death_penalty_roundtrip"]
            self.assertEqual("PASS_DETERMINISTIC_REPLAY", replay["status"])
            self.assertEqual("DETERMINISTIC_REPLAY_ONLY", replay["acceptance_scope"])
            self.assertEqual("BLOCKED_STORED_REFERENCE_MISMATCH", replay["reference_comparison_status"])
            self.assertFalse(aggregate["all_required_jasp_cases_pass"])


class WorkflowIdentityAndTerminalStateTests(unittest.TestCase):
    def test_positive_ascii_workflow_identity_is_accepted(self):
        self.assertTrue(lane.valid_workflow_identity("43408457985", "1"))
        self.assertTrue(lane.valid_workflow_identity("1", "12"))

    def test_malformed_or_non_positive_workflow_identity_is_rejected(self):
        for run_id, attempt in (
            ("", "1"), ("0", "1"), ("abc", "1"), ("43408457985", ""),
            ("43408457985", "0"), ("43408457985", "1.0"), ("４３４", "1"),
        ):
            with self.subTest(run_id=run_id, attempt=attempt):
                self.assertFalse(lane.valid_workflow_identity(run_id, attempt))

    def test_replay_only_jasp_case_is_terminal_but_not_strict_reference_pass(self):
        cases = {
            "flatpak_launch": {"status": "PASS", "returncode": 0},
            "reliability": {"status": "PASS", "returncode": 0},
            "weight_gain": {"status": "PASS", "returncode": 0},
            "death_penalty_roundtrip": {
                "status": "PASS_DETERMINISTIC_REPLAY",
                "returncode": 0,
                "acceptance_scope": "DETERMINISTIC_REPLAY_ONLY",
                "reference_comparison_status": "BLOCKED_STORED_REFERENCE_MISMATCH",
            },
        }
        self.assertTrue(lane.jasp_case_results_terminal(cases))
        self.assertEqual(
            "BLOCKED_STORED_REFERENCE_MISMATCH",
            cases["death_penalty_roundtrip"]["reference_comparison_status"],
        )
        self.assertNotEqual("PASS", cases["death_penalty_roundtrip"]["status"])

    def test_invalid_replay_classification_is_not_terminal(self):
        cases = {
            "flatpak_launch": {"status": "PASS", "returncode": 0},
            "reliability": {"status": "PASS", "returncode": 0},
            "weight_gain": {"status": "PASS", "returncode": 0},
            "death_penalty_roundtrip": {
                "status": "PASS_DETERMINISTIC_REPLAY",
                "returncode": 1,
                "acceptance_scope": "STRICT_REFERENCE_AND_REPLAY",
                "reference_comparison_status": "PASS",
            },
        }
        self.assertFalse(lane.jasp_case_results_terminal(cases))
        cases.pop("weight_gain")
        self.assertFalse(lane.jasp_case_results_terminal(cases))



class PostvalidationManifestClosureRegressionTests(unittest.TestCase):
    def _run_closure(self, observed_sha):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            repo_root = base / "repo"
            lane_root = repo_root / "recovery" / "lunita-custoszv9"
            packager_dir = repo_root / "scripts" / "lunita"
            lane_root.mkdir(parents=True)
            packager_dir.mkdir(parents=True)
            packager = packager_dir / "package_candidate_squashfs_v1.py"
            packager.write_text(
                "def tree_manifest(root):\n"
                f"    return {{'entries_sha256': '{observed_sha}', 'entry_count': 3}}\n",
                encoding="utf-8",
            )
            rootfs = base / "rootfs"
            rootfs.mkdir()
            evidence = base / "evidence"
            evidence.mkdir()
            package_path = base / "LUNITA_SQUASHFS_PACKAGE_RECEIPT.json"
            expected_sha = "a" * 64
            package_path.write_text(json.dumps({
                "schema": "LUNITA_SQUASHFS_PACKAGE_RECEIPT/1.0",
                "candidate_id": "G06_REBUILD_CANDIDATE_R1",
                "version": "1.8.0",
                "source_rootfs": str(rootfs),
                "roundtrip_manifest_match": True,
                "source_rootfs_unchanged": True,
                "source_rootfs_manifest_sha256": expected_sha,
                "source_rootfs_entry_count": 3,
            }), encoding="utf-8")
            inventory = {
                "report_sha256": "c" * 64,
                "manifest_sha256": "d" * 64,
            }
            jasp = {"worker_evidence": {"sha256": "b" * 64}}
            with mock.patch.object(lane, "ROOT", lane_root), \
                 mock.patch.object(lane, "ROOTFS", rootfs), \
                 mock.patch.object(lane, "SQUASHFS_PACKAGE_RECEIPT", package_path), \
                 mock.patch.object(lane, "EVIDENCE", evidence), \
                 mock.patch.object(lane, "CERTIFICATION_PROFILE", "V1_8_DIRECT"):
                result = lane.direct_candidate_rootfs_manifest_closure(jasp, inventory, True)
            receipt_path = result.get("manifest_closure_receipt_path")
            if isinstance(receipt_path, str):
                receipt_file = pathlib.Path(receipt_path)
                if receipt_file.is_file() and not receipt_file.is_symlink():
                    receipt_bytes = receipt_file.read_bytes()
                    result["manifest_closure_receipt_snapshot"] = json.loads(receipt_bytes)
                    result["manifest_closure_receipt_snapshot_sha256"] = hashlib.sha256(receipt_bytes).hexdigest()
            return result

    def test_postvalidation_closure_binds_verified_inventory_and_exact_tree(self):
        result = self._run_closure("a" * 64)
        self.assertEqual("PASS", result["status"])
        self.assertEqual(0, result["returncode"])
        receipt = result["manifest_closure_receipt_snapshot"]
        self.assertEqual(
            result["manifest_closure_receipt_sha256"],
            result["manifest_closure_receipt_snapshot_sha256"],
        )
        self.assertEqual("c" * 64, receipt["independent_inventory_report_sha256"])
        self.assertEqual("d" * 64, receipt["independent_inventory_manifest_sha256"])
        self.assertTrue(receipt["exact_manifest_equality"])

    def test_receipt_snapshot_is_hash_bound_before_tempdir_cleanup(self):
        result = self._run_closure("a" * 64)
        self.assertIn("manifest_closure_receipt_snapshot", result)
        self.assertEqual(
            result["manifest_closure_receipt_sha256"],
            result["manifest_closure_receipt_snapshot_sha256"],
        )
        self.assertEqual("PASS", result["manifest_closure_receipt_snapshot"]["status"])

    def test_postvalidation_closure_keeps_tree_mismatch_blocked(self):
        result = self._run_closure("e" * 64)
        self.assertEqual("BLOCKED", result["status"])
        self.assertEqual(1, result["returncode"])
        self.assertIn("does not equal the packaged source manifest", result["details"])

    def test_postvalidation_closure_fails_closed_when_inventory_or_worker_is_missing(self):
        with mock.patch.object(lane, "CERTIFICATION_PROFILE", "V1_8_DIRECT"):
            result = lane.direct_candidate_rootfs_manifest_closure({}, None, False)
        self.assertEqual("BLOCKED", result["status"])
        self.assertEqual(1, result["returncode"])
        self.assertIn("waits for completed JASP worker and valid independent inventory", result["details"])


class SeededFixturePostExecutionHashIntegrityTests(unittest.TestCase):
    def test_exact_original_clone_hash_must_survive_save_and_rerun(self):
        expected = "a" * 64
        receipt = {"clone_sha256": expected, "clone_path": "/tmp/DeathPenalty_seeded.jasp"}
        self.assertTrue(lane.seeded_fixture_post_execution_hashes_unchanged(
            receipt, receipt["clone_path"], expected, expected, expected,
            True, True, True,
        ))

    def test_identical_mutation_in_both_invocations_is_still_rejected(self):
        expected = "a" * 64
        mutated = "b" * 64
        receipt = {"clone_sha256": expected, "clone_path": "/tmp/DeathPenalty_seeded.jasp"}
        self.assertFalse(lane.seeded_fixture_post_execution_hashes_unchanged(
            receipt, receipt["clone_path"], expected, mutated, mutated,
            True, True, True,
        ))

    def test_mutation_after_either_save_or_rerun_is_rejected(self):
        expected = "a" * 64
        mutated = "b" * 64
        receipt = {"clone_sha256": expected, "clone_path": "/tmp/DeathPenalty_seeded.jasp"}
        self.assertFalse(lane.seeded_fixture_post_execution_hashes_unchanged(
            receipt, receipt["clone_path"], expected, mutated, expected,
            True, True, True,
        ))
        self.assertFalse(lane.seeded_fixture_post_execution_hashes_unchanged(
            receipt, receipt["clone_path"], expected, expected, mutated,
            True, True, True,
        ))

    def test_missing_hash_unsafe_file_or_missing_cleanup_fails_closed(self):
        expected = "a" * 64
        receipt = {"clone_sha256": expected, "clone_path": "/tmp/DeathPenalty_seeded.jasp"}
        self.assertFalse(lane.seeded_fixture_post_execution_hashes_unchanged(
            receipt, receipt["clone_path"], expected, None, expected,
            True, True, True,
        ))
        self.assertFalse(lane.seeded_fixture_post_execution_hashes_unchanged(
            receipt, receipt["clone_path"], expected, expected, expected,
            False, True, True,
        ))
        self.assertFalse(lane.seeded_fixture_post_execution_hashes_unchanged(
            receipt, receipt["clone_path"], expected, expected, expected,
            True, True, False,
        ))


class S32JaspRoundtripFailClosedRegressionTests(unittest.TestCase):
    def _checks(self):
        expected = "a" * 64
        row = {
            "status": "PASS",
            "returncode": 0,
            "acceptance_scope": "STRICT_REFERENCE_AND_REPLAY",
            "reference_comparison_status": "PASS",
            "deterministic_replay_status": "PASS_DETERMINISTIC_REPLAY",
            "deterministic_fixture_receipt_valid": True,
            "temporary_fixture_hash_invariant_passed": True,
            "temporary_fixture_regular_after_save": True,
            "temporary_fixture_regular_after_rerun": True,
            "temporary_fixture_changed": False,
            "temporary_fixture_removed_after_test": True,
            "temporary_fixture_stable_after_save_and_rerun": True,
            "save_fixture_unchanged_after_execution": True,
            "rerun_fixture_unchanged_after_execution": True,
            "original_sample_unchanged": True,
            "original_sample_identity_matches_pin": True,
            "original_sample_sha256_before": lane.DEATH_PENALTY_SOURCE_SHA256,
            "original_sample_sha256_after": lane.DEATH_PENALTY_SOURCE_SHA256,
            "temporary_fixture_sha256_expected": expected,
            "temporary_fixture_sha256_before": expected,
            "temporary_fixture_sha256_after_save": expected,
            "temporary_fixture_sha256_after_rerun": expected,
            "save_fixture_sha256_after_execution": expected,
            "rerun_fixture_sha256_after_execution": expected,
        }
        return {
            "jasp_packaged_fixture_nonregression": {
                "status": "PASS",
                "returncode": 0,
                "cases": {
                    "flatpak_launch": {"status": "PASS", "returncode": 0},
                    "reliability": {"status": "PASS", "returncode": 0},
                    "weight_gain": {"status": "PASS", "returncode": 0},
                    "death_penalty_roundtrip": row,
                },
                "evidence": {},
            }
        }, row

    def test_s32_gate_rejects_replay_only_historical_reference_mismatch(self):
        checks, row = self._checks()
        row["status"] = "PASS_DETERMINISTIC_REPLAY"
        row["acceptance_scope"] = "DETERMINISTIC_REPLAY_ONLY"
        row["reference_comparison_status"] = "BLOCKED_STORED_REFERENCE_MISMATCH"
        self.assertFalse(lane.jasp_roundtrip_functional_evidence_valid(checks))

    def test_s32_gate_rejects_identical_post_execution_mutation(self):
        checks, row = self._checks()
        row["temporary_fixture_sha256_after_save"] = "b" * 64
        row["temporary_fixture_sha256_after_rerun"] = "b" * 64
        row["save_fixture_sha256_after_execution"] = "b" * 64
        row["rerun_fixture_sha256_after_execution"] = "b" * 64
        self.assertFalse(lane.jasp_roundtrip_functional_evidence_valid(checks))

    def test_s32_gate_requires_all_jasp_cases_and_returncodes(self):
        checks, row = self._checks()
        checks["jasp_packaged_fixture_nonregression"]["cases"].pop("weight_gain")
        self.assertFalse(lane.jasp_roundtrip_functional_evidence_valid(checks))
        checks, row = self._checks()
        checks["jasp_packaged_fixture_nonregression"]["cases"]["reliability"]["returncode"] = 125
        self.assertFalse(lane.jasp_roundtrip_functional_evidence_valid(checks))
