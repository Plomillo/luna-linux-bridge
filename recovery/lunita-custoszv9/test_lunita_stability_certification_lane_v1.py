import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
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
            with mock.patch.object(lane, "ROOTFS", rootfs), mock.patch.object(lane, "EVIDENCE", evidence):
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
            (out / "JASP_UNITTEST_FLATPAK_20261020.log").write_text("JASP_UNITTEST_RC=1\n", encoding="utf-8")
            (out / "JASP_UNITTEST_RELIABILITY_20261020.log").write_text("JASP_RELIABILITY_UNITTEST_RC=1\n", encoding="utf-8")
            (out / "JASP_UNITTEST_WEIGHT_GAIN_20261020.log").write_text("JASP_WEIGHT_GAIN_UNITTEST_RC=1\n", encoding="utf-8")
            (out / "JASP_UNITTEST_ROUNDTRIP_DEATH_PENALTY_20261020.json").write_text(json.dumps({
                "strict_rerun_after_save": {"status": "FAIL", "returncode": 1},
                "original_sample_unchanged": True,
            }), encoding="utf-8")
            with mock.patch.object(lane, "OUT", out):
                result = lane.latest_jasp_evidence()
        self.assertEqual("BLOCKED_JASP_PACKAGED_FIXTURE_NONREGRESSION", result["status"])
        self.assertTrue(all(x["status"] == "BLOCKED" and x["returncode"] == 1 for x in result["cases"].values()))

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
                "certification": "NOT_GRANTED",
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
            "squashfs_image_and_package_binding",
        }
        checks = {name: {"status": "PASS", "returncode": 0} for name in required}
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
            "canonical_g08_binding_mutation": False,
        }
        return out, manifest, target, independent, target_acceptance, image, checksum, package

    def test_s32_issues_hash_bound_receipt_and_unlocks_candidate_stable_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out, manifest, target, independent, acceptance, image, checksum, package = self.prepare_valid_evidence(base)
            with mock.patch.object(lane, "CERTIFICATION_PROFILE", "V1_8_DIRECT"), \
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


class JaspRunnerTests(unittest.TestCase):
    def test_runner_pins_commit_and_records_each_real_return_code(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out = base / "out"
            out.mkdir()
            report = base / "evidence" / "jasp-suite.json"
            rootfs = base / "rootfs"
            source_fixture = rootfs / "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp"
            source_fixture.parent.mkdir(parents=True)
            source_fixture.write_bytes(b"fake jasp fixture - immutable source")
            responses = [
                SimpleNamespace(returncode=0, stdout="83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7\n", stderr=""),
                SimpleNamespace(returncode=0, stdout="flatpak test pass\\n", stderr=""),
                SimpleNamespace(returncode=1, stdout="numeric delta\\n", stderr=""),
                SimpleNamespace(returncode=0, stdout="flatpak test pass\\n", stderr=""),
                SimpleNamespace(returncode=0, stdout="roundtrip save passed\\n", stderr=""),
                SimpleNamespace(returncode=0, stdout="roundtrip strict rerun passed\\n", stderr=""),
            ]
            with mock.patch.object(lane, "OUT", out), mock.patch.object(lane, "ROOTFS", rootfs), mock.patch.object(lane.subprocess, "run", side_effect=responses) as runner:
                result = lane.run_jasp_regression_suite(report)
            self.assertEqual("BLOCKED_JASP_REGRESSION", result["status"])
            self.assertEqual(6, runner.call_count)
            # Unknown JASP CLI arguments print help and return RC=1.
            # Qt's offscreen backend is selected through the environment.
            for call in runner.call_args_list:
                self.assertEqual("offscreen", call.kwargs["env"].get("QT_QPA_PLATFORM"))
                self.assertNotIn("-platform", call.args[0])
                self.assertNotIn("--timeOut=2", call.args[0])
            jasp_calls = [call.args[0] for call in runner.call_args_list
                          if "--unitTest" in call.args[0]]
            self.assertEqual(5, len(jasp_calls))
            self.assertTrue(all(command[command.index("org.jaspstats.JASP") + 1] == "--unitTest"
                                for command in jasp_calls))
            self.assertTrue(all(command.count("--hide") == 1 for command in jasp_calls))
            self.assertEqual("PASS", result["tests"]["flatpak_launch"]["status"])
            self.assertEqual(1, result["tests"]["reliability"]["returncode"])
            self.assertEqual("BLOCKED", result["tests"]["reliability"]["status"])
            self.assertIn("JASP_RELIABILITY_UNITTEST_RC=1", pathlib.Path(result["tests"]["reliability"]["log_path"]).read_text())
            self.assertEqual("BLOCKED_JASP_STRICT_ROUNDTRIP", result["roundtrip_gate"]["status"])
            self.assertFalse(result["roundtrip_gate"]["original_sample_unchanged"])
            self.assertTrue(result["roundtrip_gate"]["temporary_fixture_removed_after_test"])
            self.assertTrue(report.is_file())


class JaspStrictRoundtripPositiveTests(unittest.TestCase):
    def test_roundtrip_passes_when_save_reopen_and_sample_pins_match(self):
        from types import SimpleNamespace
        expected = "fc8b6f8faf0e4437c8e4ab4bd922b3e959a0d4549c813b229bc5708050851895"
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            out = base / "out"
            out.mkdir()
            rootfs = base / "rootfs"
            source = rootfs / (
                "var/lib/flatpak/app/org.jaspstats.JASP/x86_64/stable/active/files/"
                "Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp"
            )
            source.parent.mkdir(parents=True)
            source.write_bytes(b"fixture bytes for positive mocked roundtrip")
            responses = [
                SimpleNamespace(returncode=0, stdout="save successful\\n", stderr=""),
                SimpleNamespace(returncode=0, stdout="strict reopen successful\\n", stderr=""),
            ]
            with mock.patch.object(lane, "OUT", out):
                with mock.patch.object(lane, "ROOTFS", rootfs):
                    with mock.patch.object(lane, "sha_file", return_value=expected):
                        with mock.patch.object(lane.subprocess, "run", side_effect=responses) as runner:
                            result = lane.run_death_penalty_roundtrip(
                                "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7",
                                {"QT_QPA_PLATFORM": "offscreen"},
                                "POSITIVE_TEST",
                            )
            self.assertEqual(2, runner.call_count)
            self.assertEqual("PASS_JASP_STRICT_ROUNDTRIP", result["status"])
            self.assertEqual("PASS", result["save_run"]["status"])
            self.assertEqual("PASS", result["strict_rerun_after_save"]["status"])
            self.assertTrue(result["original_sample_unchanged"])
            self.assertTrue(result["temporary_fixture_removed_after_test"])


class TargetRuntimeEvidenceGateTests(unittest.TestCase):
    @staticmethod
    def valid_target_receipt():
        return {
            "schema": "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0",
            "status": "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED",
            "candidate_id": "G06_REBUILD_CANDIDATE_R1",
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
            self.assertEqual(25, result["engine_acceptance_tests"]["tests_run"])
            self.assertEqual("PASS_E01_QWEN_INFERENCE", result["qwen_e01"]["status"])
            self.assertEqual("PASS_E04_INT8_QUALITY_GATE", result["e04_quantization"]["status"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), result["receipt_sha256"])

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
            receipt = receipts / "LUNITA_TARGET_RUNTIME_ACCEPTANCE_test.json"
            receipt.write_text(json.dumps(TargetRuntimeEvidenceGateTests.valid_target_receipt()), encoding="utf-8")
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
                    "squashfs_image_and_package_binding": image_check,
                },
                "frozen_g06_mutated": False, "canonical_g08_bindings_mutated": False,
            }), encoding="utf-8")
            out = base / "outputs"
            out.mkdir()
            with mock.patch.object(lane, "CERTIFICATION_PROFILE", "V1_8_DIRECT"), \
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

