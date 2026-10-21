import hashlib
import json
import pathlib
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
            independent = candidate / "independent.json"
            independent.write_text(json.dumps({
                "schema": "CUSTOSZ_LUNITA_BETA_INDEPENDENT_VALIDATION/1.0",
                "candidate_id": "G06_REBUILD_CANDIDATE_R1", "mission_sha256": lane.MISSION_SHA,
                "status": "PASS_INDEPENDENT_VALIDATION",
                "runtime_report_sha256": lane.sha_file(runtime),
                "checks": {"rootfs": {"status": "PASS", "returncode": 0},
                           "jasp": {"status": "PASS", "returncode": 0}},
                "frozen_g06_mutated": False, "canonical_g08_bindings_mutated": False,
            }), encoding="utf-8")
            with mock.patch.object(lane, "OUT", out), mock.patch.object(lane, "RUNTIME_REPORT", runtime), \
                 mock.patch.object(lane, "INDEPENDENT_REPORT", independent):
                result = lane.stable_release_gate()
        self.assertEqual("WAITING_FOR_S32_BOUND_CERTIFICATION_RECEIPT", result["status"])
        self.assertEqual("NOT_GRANTED", result["certification"])


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
            self.assertEqual("PASS", result["tests"]["flatpak_launch"]["status"])
            self.assertEqual(1, result["tests"]["reliability"]["returncode"])
            self.assertEqual("BLOCKED", result["tests"]["reliability"]["status"])
            self.assertIn("JASP_RELIABILITY_UNITTEST_RC=1", pathlib.Path(result["tests"]["reliability"]["log_path"]).read_text())
            self.assertEqual("BLOCKED_JASP_STRICT_ROUNDTRIP", result["roundtrip_gate"]["status"])
            self.assertFalse(result["roundtrip_gate"]["original_sample_unchanged"])
            self.assertTrue(result["roundtrip_gate"]["temporary_fixture_removed_after_test"])
            self.assertTrue(report.is_file())


class StableReleaseReceiptTests(unittest.TestCase):
    def test_release_receipt_is_immutable_and_current_pointer_requires_revalidation(self):
        with tempfile.TemporaryDirectory() as tmp:
            st = pathlib.Path(tmp) / "state"
            gate = {
                "status": "STABLE_RELEASE_ELIGIBLE", "version": "1.7.0", "release_name": "LUNITA_STABLE_1_7",
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
            self.assertEqual("REVALIDATION_REQUIRED", second["status"])
            self.assertEqual(original_bytes, receipt.read_bytes())
            self.assertEqual("REVALIDATION_REQUIRED", pointer["status"])
            self.assertEqual("CERTIFIED_STABLE_RELEASE", json.loads(original_bytes)["status"])
