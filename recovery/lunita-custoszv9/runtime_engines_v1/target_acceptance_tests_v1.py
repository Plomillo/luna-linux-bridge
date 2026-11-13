from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import tempfile
import unittest
from unittest import mock

import target_runtime_acceptance_v1 as target


REQUIRED_FILES = {
    "__init__.py", "engine_runtime_v1.py", "engine_acceptance_v1.py",
    "engine_gateway_v1.py", "gateway_acceptance_v1.py", "lunita_beta_v1_8.py",
    "launcher_acceptance_v1.py", "target_runtime_acceptance_v1.py",
    "apply_engine_overlay_v1.py", "checkpoint_v1.py", "overlay_acceptance_v1.py",
    "engine_assignments_v1.json", "requirements-engine-stack.txt",
    "DEPENDENCY_EVIDENCE_v1.json", "ENGINE_RUNTIME_V1_README.md",
}
REQUIRED_DIRECTORIES = {"vendor/python3.12/site-packages", "model-cache/fastembed"}
MODEL_RELATIVE = pathlib.Path(
    "models--Qdrant--paraphrase-multilingual-MiniLM-L12-v2-onnx-Q/"
    "snapshots/faf4aa4225822f3bc6376869cb1164e8e3feedd0/model_optimized.onnx"
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_receipt(root: pathlib.Path) -> dict:
    entries = []
    for item in sorted(root.rglob("*")):
        if item.is_file():
            entries.append({
                "path": item.relative_to(root).as_posix(),
                "sha256": digest(item),
                "bytes": item.stat().st_size,
            })
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "file_count": len(entries),
        "bytes": sum(row["bytes"] for row in entries),
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }


class TargetPivotRootCommandTests(unittest.TestCase):
    def test_pivot_root_user_command_uses_setpriv_and_no_chroot(self):
        with mock.patch.dict(target.os.environ, {"LUNITA_IN_PIVOT_ROOT": "1"}), \
             mock.patch.object(target.os, "geteuid", return_value=0):
            command = target.build_target_user_command(
                pathlib.Path("/"),
                ("HOME=/home/lunita", "PATH=/usr/bin:/bin"),
                ("/usr/bin/flatpak", "--system", "run", "org.jamovi.jamovi"),
            )
        self.assertEqual(
            ["/usr/bin/setpriv", "--reuid=1000", "--regid=1000", "--clear-groups", "/usr/bin/env"],
            command[:5],
        )
        self.assertNotIn("chroot", command)
        self.assertIn("/usr/bin/flatpak", command)

    def test_pivot_root_mode_rejects_non_candidate_root(self):
        with mock.patch.dict(target.os.environ, {"LUNITA_IN_PIVOT_ROOT": "1"}), \
             mock.patch.object(target.os, "geteuid", return_value=0):
            with self.assertRaisesRegex(target.TargetGateError, "candidate mount root"):
                target.build_target_user_command(
                    pathlib.Path("/tmp/not-the-rootfs"),
                    ("HOME=/home/lunita",), ("/usr/bin/true",),
                )

    def test_pivot_root_mode_rejects_non_root_supervisor(self):
        with mock.patch.dict(target.os.environ, {"LUNITA_IN_PIVOT_ROOT": "1"}), \
             mock.patch.object(target.os, "geteuid", return_value=1001):
            with self.assertRaisesRegex(target.TargetGateError, "candidate mount root"):
                target.build_target_user_command(
                    pathlib.Path("/"),
                    ("HOME=/home/lunita",), ("/usr/bin/true",),
                )

    def test_non_pivot_mode_keeps_existing_chroot_boundary(self):
        with tempfile.TemporaryDirectory(prefix="lunita-legacy-chroot-") as temporary:
            with mock.patch.dict(target.os.environ, {"LUNITA_IN_PIVOT_ROOT": ""}):
                command = target.build_target_user_command(
                    pathlib.Path(temporary),
                    ("HOME=/home/lunita",), ("/usr/bin/true",),
                )
        self.assertEqual(
            ["sudo", "-n", "chroot", "--userspec=1000:1000", temporary, "/usr/bin/env"],
            command[:6],
        )
        self.assertIn("/usr/bin/true", command)


class TargetUserRequestFileTests(unittest.TestCase):
    def setUp(self):
        self.environment = (
            "HOME=/home/lunita",
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "TMPDIR=/tmp/lunita-xdg",
        )

    def test_e01_request_is_created_exclusively_by_target_uid_1000(self):
        request_path = pathlib.Path("/tmp/lunita-xdg/lunita-e01-qwen-test.json")
        result = mock.Mock(returncode=0, stdout="PASS_TARGET_USER_REQUEST_CREATED", stderr="")
        with (
            mock.patch.dict(target.os.environ, {"LUNITA_IN_PIVOT_ROOT": "1"}),
            mock.patch.object(target.os, "geteuid", return_value=0),
            mock.patch.object(target.subprocess, "run", return_value=result) as run,
        ):
            receipt = target.write_target_user_json(
                pathlib.Path("/"), request_path, {"engine_id": "E01", "payload": {"prompt": "OK"}},
                self.environment,
            )
        self.assertEqual("PASS_TARGET_USER_REQUEST_CREATED", receipt["status"])
        self.assertEqual("1000:1000", receipt["owner"])
        self.assertEqual("0600", receipt["mode"])
        command = run.call_args.args[0]
        self.assertEqual(
            ["/usr/bin/setpriv", "--reuid=1000", "--regid=1000", "--clear-groups", "/usr/bin/env"],
            command[:5],
        )
        self.assertNotIn("chroot", command)
        code = command[command.index("-c") + 1]
        self.assertIn("O_EXCL", code)
        self.assertIn("O_NOFOLLOW", code)
        self.assertIn("0o600", code)
        compile(code, "<e01-request-writer>", "exec")
        self.assertIn("TMPDIR=/tmp/lunita-xdg", command)
        self.assertEqual(str(request_path), command[-2])

    def test_e01_request_writer_rejects_direct_tmp_without_mutation(self):
        with (
            mock.patch.dict(target.os.environ, {"LUNITA_IN_PIVOT_ROOT": "1"}),
            mock.patch.object(target.os, "geteuid", return_value=0),
            mock.patch.object(target.subprocess, "run") as run,
        ):
            with self.assertRaisesRegex(target.TargetGateError, "private target XDG directory"):
                target.write_target_user_json(
                    pathlib.Path("/"), pathlib.Path("/tmp/lunita-e01-qwen-test.json"),
                    {"engine_id": "E01"}, self.environment,
                )
        run.assert_not_called()

    def test_e01_request_cleanup_runs_as_owning_target_uid(self):
        request_path = pathlib.Path("/tmp/lunita-xdg/lunita-e01-qwen-test.json")
        result = mock.Mock(returncode=0, stdout="PASS_TARGET_USER_REQUEST_REMOVED", stderr="")
        with (
            mock.patch.dict(target.os.environ, {"LUNITA_IN_PIVOT_ROOT": "1"}),
            mock.patch.object(target.os, "geteuid", return_value=0),
            mock.patch.object(target.subprocess, "run", return_value=result) as run,
        ):
            target.unlink_target_user_request(pathlib.Path("/"), request_path, self.environment)
        command = run.call_args.args[0]
        self.assertEqual(
            ["/usr/bin/setpriv", "--reuid=1000", "--regid=1000", "--clear-groups", "/usr/bin/env"],
            command[:5],
        )
        self.assertNotIn("chroot", command)
        code = command[command.index("-c") + 1]
        self.assertIn("path.unlink()", code)
        compile(code, "<e01-request-cleanup>", "exec")
        self.assertIn("1000", code)

class TargetSystemPythonAliasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lunita-system-python-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.bin = self.root / "usr/bin"
        self.bin.mkdir(parents=True)
        self.python312 = self.bin / "python3.12"
        self.python312.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.python312.chmod(0o755)
        self.python3 = self.bin / "python3"

    def test_ubuntu_python3_alias_resolves_to_python312(self):
        self.python3.symlink_to("python3.12")
        result = target.verify_system_python_alias(self.root)
        self.assertEqual("PASS_SYSTEM_PYTHON_ALIAS", result["status"])
        self.assertEqual("python3.12", result["symlink_target"])
        self.assertEqual(str(self.python312.resolve()), result["resolved_executable"])

    def test_missing_python3_alias_is_denied(self):
        with self.assertRaisesRegex(
            target.TargetGateError, "compatibility symlink is missing"
        ):
            target.verify_system_python_alias(self.root)

    def test_wrong_python3_alias_target_is_denied(self):
        python311 = self.bin / "python3.11"
        python311.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        python311.chmod(0o755)
        self.python3.symlink_to("python3.11")
        with self.assertRaisesRegex(
            target.TargetGateError, "must resolve to /usr/bin/python3.12"
        ):
            target.verify_system_python_alias(self.root)


class TargetXdgRuntimeDirectoryTests(unittest.TestCase):
    HOST_BIND_NAME = "lunita-host-43332281299-1"
    RUN_ID = "43332281299"
    RUN_ATTEMPT = "1"
    RUNTIME_DIR = f"/run/{HOST_BIND_NAME}-runtime-1000"

    def test_private_uid1000_runtime_directory_passes(self):
        metadata = mock.Mock(st_mode=0o40700, st_uid=1000, st_gid=1000)
        environment = {"GITHUB_RUN_ID": self.RUN_ID, "GITHUB_RUN_ATTEMPT": self.RUN_ATTEMPT, "HOST_BIND_NAME": self.HOST_BIND_NAME, "XDG_RUNTIME_DIR": self.RUNTIME_DIR}
        with mock.patch.dict(target.os.environ, environment), mock.patch.object(target.os, "lstat", return_value=metadata):
            result = target.verify_xdg_runtime_dir()
        self.assertEqual("PASS_XDG_RUNTIME_DIR_UID1000_PRIVATE", result["status"])
        self.assertEqual(self.RUNTIME_DIR, result["path"])
        self.assertEqual("0o700", result["mode_octal"])

    def test_different_workflow_attempts_get_distinct_runtime_paths(self):
        with mock.patch.dict(target.os.environ, {"GITHUB_RUN_ID": "1001", "GITHUB_RUN_ATTEMPT": "1", "HOST_BIND_NAME": "lunita-host-1001-1"}):
            first_path = target.expected_xdg_runtime_dir()
        with mock.patch.dict(target.os.environ, {"GITHUB_RUN_ID": "1001", "GITHUB_RUN_ATTEMPT": "2", "HOST_BIND_NAME": "lunita-host-1001-2"}):
            second_path = target.expected_xdg_runtime_dir()
        self.assertNotEqual(first_path, second_path)

    def test_github_run_identity_is_mandatory(self):
        with mock.patch.dict(target.os.environ, {"HOST_BIND_NAME": self.HOST_BIND_NAME}, clear=True):
            with self.assertRaisesRegex(target.TargetGateError, "GITHUB_RUN_ID and GITHUB_RUN_ATTEMPT"):
                target.expected_xdg_runtime_dir()

    def test_host_bind_name_must_match_run_and_attempt(self):
        environment = {
            "GITHUB_RUN_ID": self.RUN_ID,
            "GITHUB_RUN_ATTEMPT": "2",
            "HOST_BIND_NAME": self.HOST_BIND_NAME,
        }
        with mock.patch.dict(target.os.environ, environment):
            with self.assertRaisesRegex(target.TargetGateError, "does not match"):
                target.expected_xdg_runtime_dir()

    def test_runtime_directory_path_must_match_run_scoped_contract(self):
        environment = {"GITHUB_RUN_ID": self.RUN_ID, "GITHUB_RUN_ATTEMPT": self.RUN_ATTEMPT, "HOST_BIND_NAME": self.HOST_BIND_NAME, "XDG_RUNTIME_DIR": "/tmp/runtime"}
        with mock.patch.dict(target.os.environ, environment):
            with self.assertRaisesRegex(target.TargetGateError, "must be exactly"):
                target.verify_xdg_runtime_dir()

    def test_unsafe_run_identity_is_denied(self):
        environment = {"GITHUB_RUN_ID": "1001", "GITHUB_RUN_ATTEMPT": "1", "HOST_BIND_NAME": "../shared", "XDG_RUNTIME_DIR": "/run/../shared-runtime-1000"}
        with mock.patch.dict(target.os.environ, environment):
            with self.assertRaisesRegex(target.TargetGateError, "does not match"):
                target.verify_xdg_runtime_dir()

    def test_runtime_directory_must_exist_as_a_real_directory(self):
        metadata = mock.Mock(st_mode=0o120700, st_uid=1000, st_gid=1000)
        environment = {"GITHUB_RUN_ID": self.RUN_ID, "GITHUB_RUN_ATTEMPT": self.RUN_ATTEMPT, "HOST_BIND_NAME": self.HOST_BIND_NAME, "XDG_RUNTIME_DIR": self.RUNTIME_DIR}
        with mock.patch.dict(target.os.environ, environment), mock.patch.object(target.os, "lstat", return_value=metadata):
            with self.assertRaisesRegex(target.TargetGateError, "real directory"):
                target.verify_xdg_runtime_dir()

    def test_runtime_directory_rejects_wrong_owner_group_or_mode(self):
        invalid_metadata = (
            mock.Mock(st_mode=0o40700, st_uid=0, st_gid=1000),
            mock.Mock(st_mode=0o40700, st_uid=1000, st_gid=0),
            mock.Mock(st_mode=0o40755, st_uid=1000, st_gid=1000),
        )
        environment = {"GITHUB_RUN_ID": self.RUN_ID, "GITHUB_RUN_ATTEMPT": self.RUN_ATTEMPT, "HOST_BIND_NAME": self.HOST_BIND_NAME, "XDG_RUNTIME_DIR": self.RUNTIME_DIR}
        for metadata in invalid_metadata:
            with self.subTest(uid=metadata.st_uid, gid=metadata.st_gid, mode=oct(metadata.st_mode)):
                with mock.patch.dict(target.os.environ, environment), mock.patch.object(target.os, "lstat", return_value=metadata):
                    with self.assertRaisesRegex(target.TargetGateError, "owned by UID/GID 1000"):
                        target.verify_xdg_runtime_dir()


class TargetRuntimeMountIsolationContractTests(unittest.TestCase):
    def test_runtime_mount_target_is_scoped_to_workflow_attempt(self):
        repository = pathlib.Path(__file__).resolve().parents[3]
        wrapper = repository / "scripts/lunita/run_target_runtime_acceptance_in_container_v1.sh"
        content = wrapper.read_text(encoding="utf-8")
        self.assertIn('RUNTIME_BIND_TARGET="/run/${HOST_BIND_NAME}-runtime-1000"', content)
        self.assertIn('export XDG_RUNTIME_DIR="$RUNTIME_BIND_TARGET"', content)
        self.assertIn(r"^lunita-host-[A-Za-z0-9-]+$", content)
        self.assertIn('RUN_ID="${GITHUB_RUN_ID:-}"', content)
        self.assertIn('RUN_ATTEMPT="${GITHUB_RUN_ATTEMPT:-}"', content)
        self.assertIn('if [[ ! "$RUN_ID" =~ ^[0-9]+$ || ! "$RUN_ATTEMPT" =~ ^[0-9]+$ ]]; then', content)
        self.assertIn('export GITHUB_RUN_ID="$RUN_ID"', content)
        self.assertIn('export GITHUB_RUN_ATTEMPT="$RUN_ATTEMPT"', content)
        self.assertIn("LUNITA_WORKFLOW_IDENTITY", content)
        self.assertNotIn("GITHUB_RUN_ID:-local", content)
        self.assertNotIn("RUNTIME_BIND_TARGET=/run/lunita-runtime-1000", content)
        identity_validation = content.index('RUN_ID="${GITHUB_RUN_ID:-}"')
        evidence_creation = content.index('mkdir -p "$path"')
        runtime_source_creation = content.index('install -d -o 1000 -g 1000 -m 0700 "$RUNTIME_SOURCE"')
        self.assertLess(identity_validation, evidence_creation)
        self.assertLess(identity_validation, runtime_source_creation)

        workflow = repository / ".github/workflows/lunita-v18-direct-functional-validation.yml"
        workflow_content = workflow.read_text(encoding="utf-8")
        start = workflow_content.index("      - name: Execute actual E01 inference and E02-E15 plus legacy application smoke tests")
        end = workflow_content.index("      - name: Verify target virtual filesystems were unmounted before image materialization", start)
        target_step = workflow_content[start:end]
        self.assertIn('GITHUB_RUN_ID="$GITHUB_RUN_ID"', target_step)
        self.assertIn('GITHUB_RUN_ATTEMPT="$GITHUB_RUN_ATTEMPT"', target_step)
        self.assertIn("github.event.pull_request.base.ref == 'fix/lunita-v18-rootfs-bound-checkpoint-20261109'", workflow_content)
        runtime_source = (repository / "recovery/lunita-custoszv9/runtime_engines_v1/target_runtime_acceptance_v1.py").read_text(encoding="utf-8")
        self.assertIn('"workflow_identity": workflow_identity_receipt()', runtime_source)
        self.assertIn('"run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT")', runtime_source)


class TargetHostFlatpakInstallWorkflowTests(unittest.TestCase):
    def test_host_flatpak_install_retries_network_and_still_requires_cli(self):
        repository = pathlib.Path(__file__).resolve().parents[3]
        workflow = repository / ".github/workflows/lunita-v18-direct-functional-validation.yml"
        content = workflow.read_text(encoding="utf-8")
        start = content.index("      - name: Ensure host Flatpak client is available for independent JASP validation")
        end = content.index("      - name: Verify the actual candidate rootfs and target prerequisites", start)
        step = content[start:end]
        self.assertIn("for attempt in 1 2 3 4", step)
        self.assertIn("Acquire::Retries=3", step)
        self.assertIn("apt-get", step)
        self.assertIn("install -y --no-install-recommends flatpak", step)
        self.assertIn("BLOCKED: host Flatpak installation failed", step)
        self.assertIn("flatpak --version", step)

class TargetRuntimeWorkflowIdentityReceiptTests(unittest.TestCase):
    def test_receipt_captures_exact_run_attempt_and_runtime_path(self):
        environment = {
            "GITHUB_RUN_ID": "43337415331",
            "GITHUB_RUN_ATTEMPT": "2",
            "HOST_BIND_NAME": "lunita-host-43337415331-2",
            "XDG_RUNTIME_DIR": "/run/lunita-host-43337415331-2-runtime-1000",
        }
        with mock.patch.dict(target.os.environ, environment, clear=True):
            receipt = target.workflow_identity_receipt()
        self.assertEqual({
            "run_id": "43337415331",
            "run_attempt": "2",
            "host_bind_name": "lunita-host-43337415331-2",
            "xdg_runtime_dir": "/run/lunita-host-43337415331-2-runtime-1000",
        }, receipt)


class TargetLegacyFlatpakDiagnosticTests(unittest.TestCase):
    def test_flatpak_diagnostic_compares_inherited_and_clean_guest_environments(self):
        calls = [
            mock.Mock(returncode=3, stdout="", stderr="inherited dbus failure"),
            mock.Mock(returncode=0, stdout="", stderr=""),
        ]
        host_bind_name = "lunita-host-43337415331-1"
        with mock.patch.dict(target.os.environ, {"GITHUB_RUN_ID": "43337415331", "GITHUB_RUN_ATTEMPT": "1", "HOST_BIND_NAME": host_bind_name}), \
             mock.patch.object(target.subprocess, "run", side_effect=calls) as run:
            result = target.diagnose_flatpak_smoke("org.jamovi.jamovi")
        self.assertTrue(result["diagnostic_only"])
        self.assertEqual(1000, int(result["execution_user"].split(":")[0]))
        self.assertEqual(3, result["runs"]["inherited"]["returncode"])
        self.assertEqual("inherited dbus failure", result["runs"]["inherited"]["stderr"])
        self.assertEqual(0, result["runs"]["clean"]["returncode"])
        inherited_command = run.call_args_list[0].args[0]
        clean_command = run.call_args_list[1].args[0]
        self.assertNotIn("-i", inherited_command)
        self.assertIn("-i", clean_command)
        self.assertIn("/usr/bin/flatpak", clean_command)
        self.assertIn("--system", clean_command)
        expected_runtime = f"XDG_RUNTIME_DIR=/run/{host_bind_name}-runtime-1000"
        self.assertIn(expected_runtime, inherited_command)
        self.assertIn(expected_runtime, clean_command)

    def test_flatpak_diagnostic_requires_workflow_attempt_identity(self):
        with mock.patch.dict(target.os.environ, {}, clear=True):
            with self.assertRaisesRegex(target.TargetGateError, "GITHUB_RUN_ID and GITHUB_RUN_ATTEMPT"):
                target.diagnose_flatpak_smoke("org.jamovi.jamovi")

    def test_flatpak_diagnostic_rejects_unregistered_application(self):
        with mock.patch.object(target.subprocess, "run") as run:
            with self.assertRaisesRegex(target.TargetGateError, "Unsupported Flatpak"):
                target.diagnose_flatpak_smoke("org.example.unregistered")
        run.assert_not_called()


class TargetJaspReleaseIdentityContractTests(unittest.TestCase):
    def test_jasp_release_pins_are_coherent_across_all_certification_layers(self):
        repository = pathlib.Path(__file__).resolve().parents[3]
        builder = (repository / "scripts/lunita/build_rootfs_candidate_v1.sh").read_text(encoding="utf-8")
        source_verifier = (repository / "scripts/lunita/verify_jasp_release_identity_v1.py").read_text(encoding="utf-8")
        independent_lane = (repository / "recovery/lunita-custoszv9/lunita_stability_certification_lane_v1.py").read_text(encoding="utf-8")
        workflow = (repository / ".github/workflows/lunita-v18-direct-functional-validation.yml").read_text(encoding="utf-8")
        target_source = (repository / "recovery/lunita-custoszv9/runtime_engines_v1/target_runtime_acceptance_v1.py").read_text(encoding="utf-8")

        self.assertEqual("0.98.8", target.EXPECTED_JASP_VERSION)
        self.assertIn('JASP_VERSION="0.98.8"', builder)
        self.assertIn('JASP_COMMIT="83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"', builder)
        self.assertIn('JASP_SOURCE_COMMIT="b6cd3b0310be4e18e1b673ac11f14e55615c8fa1"', builder)
        self.assertIn('EXPECTED_VERSION = "0.98.8"', source_verifier)
        self.assertIn('EXPECTED_JASP_RUNTIME_VERSION = "0.98.8"', independent_lane)
        self.assertIn("JASP 0.98.8", workflow)
        self.assertIn("JASP 0.98.8", target.EXPECTED_LABEL_HIERARCHY_TEXT)
        self.assertNotIn("0.98.1", target_source)
        self.assertEqual(
            (
                "org.jaspstats.JASP", "lupa", "0.98.8",
                "PINNED_FLATHUB_MANIFEST_AND_JASP_CMAKE_SOURCE_VERIFIED",
                "flatpak_deployment_commit",
                "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7",
            ),
            target.EXPECTED_FLATPAK_RELEASES[1],
        )

    def test_git_blob_sha1_uses_git_object_header(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "blob"
            path.write_bytes(b"hello\n")
            self.assertEqual("ce013625030ba8dba906f756967f9e9ca394464a", target.git_blob_sha1(path))

    def test_jasp_source_release_provenance_binds_exact_manifest_source_and_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            metadata = root / "metadata"
            metadata.mkdir()
            source_commit = "a" * 40
            manifest_commit = "b" * 40
            manifest_bytes = json.dumps({
                "app-id": "org.jaspstats.JASP",
                "modules": [{
                    "name": "jasp",
                    "sources": [{
                        "type": "git",
                        "url": "https://github.com/jasp-stats/jasp-desktop.git",
                        "commit": source_commit,
                    }],
                }],
            }, sort_keys=True, separators=(",", ":")).encode("utf-8")
            cmake_bytes = b"project(JASP VERSION 0.98.8.0 LANGUAGES CXX C)\n"
            manifest_path = metadata / "JASP_FLATHUB_MANIFEST.json"
            cmake_path = metadata / "JASP_SOURCE_CMAKE_LISTS.txt"
            identity_path = metadata / "JASP_SOURCE_RELEASE_IDENTITY.json"
            manifest_path.write_bytes(manifest_bytes)
            cmake_path.write_bytes(cmake_bytes)

            manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
            cmake_sha = hashlib.sha256(cmake_bytes).hexdigest()
            manifest_blob = target.git_blob_sha1(manifest_path)
            cmake_blob = target.git_blob_sha1(cmake_path)
            identity = {
                "schema": "LUNITA_JASP_SOURCE_RELEASE_IDENTITY/1.0",
                "status": "PASS_JASP_SOURCE_RELEASE_IDENTITY",
                "application_id": "org.jaspstats.JASP",
                "version": "0.98.8",
                "cmake_project_version": "0.98.8.0",
                "version_source": "PINNED_JASP_CMAKE_PROJECT_VERSION",
                "flathub_manifest_commit": manifest_commit,
                "flathub_manifest_git_blob_sha1": manifest_blob,
                "flathub_manifest_sha256": manifest_sha,
                "jasp_source_commit": source_commit,
                "jasp_source_cmake_git_blob_sha1": cmake_blob,
                "jasp_source_cmake_sha256": cmake_sha,
                "manifest_jasp_source_commit_matches_pin": True,
                "source_cmake_version_matches_pin": True,
                "appstream_version_metadata_used": False,
            }
            identity_path.write_text(json.dumps(identity), encoding="utf-8")
            record = {
                "application_id": "org.jaspstats.JASP",
                "version": "0.98.8",
                "version_source": "PINNED_FLATHUB_MANIFEST_AND_JASP_CMAKE_SOURCE_VERIFIED",
                "flatpak_deployment_commit": target.EXPECTED_JASP_FLATPAK_COMMIT,
                "flathub_manifest_commit": manifest_commit,
                "flathub_manifest_git_blob_sha1": manifest_blob,
                "flathub_manifest_sha256": manifest_sha,
                "jasp_source_commit": source_commit,
                "jasp_source_cmake_git_blob_sha1": cmake_blob,
                "jasp_source_cmake_sha256": cmake_sha,
                "source_release_identity_receipt_sha256": hashlib.sha256(identity_path.read_bytes()).hexdigest(),
            }
            patches = {
                "EXPECTED_JASP_VERSION": "0.98.8",
                "EXPECTED_JASP_CMAKE_PROJECT_VERSION": "0.98.8.0",
                "EXPECTED_JASP_FLATHUB_MANIFEST_COMMIT": manifest_commit,
                "EXPECTED_JASP_FLATHUB_MANIFEST_BLOB_SHA1": manifest_blob,
                "EXPECTED_JASP_SOURCE_COMMIT": source_commit,
                "EXPECTED_JASP_SOURCE_CMAKE_BLOB_SHA1": cmake_blob,
            }
            with mock.patch.multiple(target, **patches):
                result = target.verify_jasp_source_release_provenance(root, record)
            self.assertEqual("0.98.8", result["version"])
            self.assertEqual(source_commit, result["jasp_source_commit"])

            identity["appstream_version_metadata_used"] = True
            identity_path.write_text(json.dumps(identity), encoding="utf-8")
            record["source_release_identity_receipt_sha256"] = hashlib.sha256(identity_path.read_bytes()).hexdigest()
            with mock.patch.multiple(target, **patches):
                with self.assertRaisesRegex(target.TargetGateError, "does not bind exact pinned source metadata"):
                    target.verify_jasp_source_release_provenance(root, record)


class TargetLabelHierarchyAcceptanceTests(unittest.TestCase):
    def _document(self):
        return {
            "schema": "LUNITA_LABEL_HIERARCHY/1.0",
            "candidate_id": "G06_REBUILD_CANDIDATE_R1",
            "version": "1.8.0",
            "preservation_policy": "APPEND_ONLY;DO_NOT_REWRITE_EXISTING_LABELS",
            "hierarchy": copy.deepcopy(target.EXPECTED_LABEL_HIERARCHY),
            "rendered_tree": target.EXPECTED_LABEL_HIERARCHY_TEXT,
        }

    def test_exact_requested_hierarchy_passes(self):
        result = target.validate_label_hierarchy_document(self._document())
        self.assertEqual("PASS_EXACT_LABEL_HIERARCHY", result["status"])
        self.assertIn("LUNITA LA INVESTIGADORA", result["labels"])
        self.assertIn("SACAPUNTAS", result["labels"])
        self.assertIn("LUPA", result["labels"])

    def test_missing_sacapuntas_label_is_rejected(self):
        document = self._document()
        del document["hierarchy"]["children"][0]["children"][0]["children"][0]["children"][3]
        with self.assertRaisesRegex(target.TargetGateError, "exact requested labels"):
            target.validate_label_hierarchy_document(document)

    def test_label_case_rewrite_is_rejected(self):
        document = self._document()
        document["hierarchy"]["children"][0]["children"][0]["children"][0]["children"][4]["label"] = "Lupa"
        with self.assertRaisesRegex(target.TargetGateError, "exact requested labels"):
            target.validate_label_hierarchy_document(document)


class TargetOverlayAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lunita-target-gate-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.overlay = self.root / "runtime_engines_v1"
        self.overlay.mkdir()
        self.legacy = self.root / "lunita.py"
        self.legacy.write_bytes(b"hash-pinned legacy launcher fixture")
        self.legacy_hash = digest(self.legacy)
        self.receipt_path = self.overlay / "OVERLAY_APPLY_RECEIPT.json"

        files = {}
        for name in REQUIRED_FILES:
            payload = f"fixture:{name}\n".encode("utf-8")
            path = self.overlay / name
            path.write_bytes(payload)
            files[name] = digest(path)

        directories = {}
        for relative in REQUIRED_DIRECTORIES:
            directory = self.overlay / relative
            directory.mkdir(parents=True)
            fixture = directory / ("vendor-fixture.bin" if relative.startswith("vendor") else "model-fixture.bin")
            fixture.write_bytes(("fixture:" + relative).encode())
            directories[relative] = tree_receipt(directory)

        receipt = {
            "schema": "LUNITA_ADDITIVE_ENGINE_OVERLAY_RECEIPT/1.0",
            "status": "APPLIED_ADDITIVELY_NOT_CERTIFIED",
            "candidate_id": "G06_REBUILD_CANDIDATE_R1",
            "certification": "NOT_GRANTED",
            "launcher_sha256": self.legacy_hash,
            "files": files,
            "directories": directories,
            "canonical_identity_mutation": False,
            "engine_reassignment": False,
            "command_reassignment": False,
            "agent_reassignment": False,
            "frozen_g06_mutated": False,
            "canonical_g08_mutated": False,
            "launcher_mutated": False,
            "model_weights_mutated": False,
        }
        self.write_json(self.receipt_path, receipt)
        self.patches = [
            mock.patch.object(target, "OVERLAY", self.overlay),
            mock.patch.object(target, "OVERLAY_RECEIPT", self.receipt_path),
            mock.patch.object(target, "LEGACY_LAUNCHER", self.legacy),
            mock.patch.object(target, "EXPECTED_LEGACY_SHA256", self.legacy_hash),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def write_json(path: pathlib.Path, value: dict) -> None:
        path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    def load_receipt(self):
        return json.loads(self.receipt_path.read_text(encoding="utf-8"))

    def test_complete_overlay_file_and_directory_hashes_pass(self):
        result = target.verify_overlay()
        self.assertEqual("PASS_OVERLAY_INTEGRITY", result["status"])
        self.assertEqual(digest(self.receipt_path), result["receipt_sha256"])
        self.assertEqual(self.legacy_hash, result["legacy_launcher_sha256"])

    def test_modified_top_level_runtime_file_is_denied(self):
        (self.overlay / "engine_runtime_v1.py").write_text("tampered", encoding="utf-8")
        with self.assertRaises(target.TargetGateError):
            target.verify_overlay()

    def test_modified_vendored_dependency_is_denied(self):
        vendor = self.overlay / "vendor/python3.12/site-packages/vendor-fixture.bin"
        vendor.write_bytes(b"tampered")
        with self.assertRaises(target.TargetGateError):
            target.verify_overlay()

    def test_missing_manifest_entry_is_denied(self):
        receipt = self.load_receipt()
        del receipt["files"]["engine_gateway_v1.py"]
        self.write_json(self.receipt_path, receipt)
        with self.assertRaises(target.TargetGateError):
            target.verify_overlay()

    def test_mutated_frozen_identity_flag_is_denied(self):
        receipt = self.load_receipt()
        receipt["frozen_g06_mutated"] = True
        self.write_json(self.receipt_path, receipt)
        with self.assertRaises(target.TargetGateError):
            target.verify_overlay()

    def test_modified_legacy_launcher_is_denied(self):
        self.legacy.write_bytes(b"modified launcher")
        with self.assertRaises(target.TargetGateError):
            target.verify_overlay()


class TargetE04QuantizationAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lunita-e04-target-gate-")
        self.addCleanup(self.temp.cleanup)
        self.overlay = pathlib.Path(self.temp.name)
        self.cache = self.overlay / "model-cache/fastembed"
        self.model = self.cache / MODEL_RELATIVE
        self.model.parent.mkdir(parents=True)
        self.model.write_bytes(b"measured INT8 ONNX model fixture")
        self.receipt_path = self.cache / "LUNITA_E04_ONNX_QUANTIZATION_RECEIPT.json"
        self.receipt = {
            "schema": "LUNITA_E04_ONNX_QUANTIZATION/1.0",
            "status": "PASS_INT8_QUANTIZATION_MEASURED",
            "model_id": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "model_cache_relative_path": MODEL_RELATIVE.as_posix(),
            "quantization": "ONNX_RUNTIME_DYNAMIC_QINT8_PER_CHANNEL",
            "quantized_sha256": digest(self.model),
            "original_bytes": 1000,
            "quantized_bytes": self.model.stat().st_size,
            "size_ratio": self.model.stat().st_size / 1000,
            "embedding_dimension": 384,
            "mean_vector_cosine": 0.998,
            "minimum_vector_cosine": 0.990,
            "retrieval_top1_agreement": 1.0,
            "corpus_document_count": 10,
            "query_count": 10,
            "thresholds": {
                "minimum_mean_vector_cosine": 0.995,
                "minimum_vector_cosine": 0.985,
                "required_retrieval_top1_agreement": 1.0,
                "maximum_model_size_ratio": 0.60,
            },
            "retrieval_decisions": [{"query_index": i, "top1_match": True} for i in range(10)],
            "onnx_validation": {
                "checker_status": "KNOWN_ONNX_SCHEMA_REGISTRY_GAP_LAYER_NORMALIZATION_OPSET11",
                "onnxruntime_load_status": "PASS",
                "int8_initializer_count": 24,
                "quantized_operator_counts": {"MatMulInteger": 24},
            },
        }
        self.write_receipt()
        self.patches = [
            mock.patch.object(target, "OVERLAY", self.overlay),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    def test_measured_int8_receipt_passes_all_quality_and_size_gates(self):
        result = target.verify_e04_quantization_receipt()
        self.assertEqual("PASS_E04_INT8_QUALITY_GATE", result["status"])
        self.assertEqual(digest(self.model), result["model_sha256"])

    def test_missing_retrieval_decision_is_denied(self):
        self.receipt["retrieval_decisions"] = self.receipt["retrieval_decisions"][:-1]
        self.write_receipt()
        with self.assertRaises(target.TargetGateError):
            target.verify_e04_quantization_receipt()

    def test_size_ratio_regression_is_denied(self):
        self.receipt["size_ratio"] = 0.80
        self.receipt["quantized_bytes"] = 800
        self.receipt["original_bytes"] = 1000
        self.write_receipt()
        with self.assertRaises(target.TargetGateError):
            target.verify_e04_quantization_receipt()

    def test_unknown_checker_status_is_denied(self):
        self.receipt["onnx_validation"]["checker_status"] = "SKIPPED"
        self.write_receipt()
        with self.assertRaises(target.TargetGateError):
            target.verify_e04_quantization_receipt()

    def test_quantized_model_digest_mismatch_is_denied(self):
        self.model.write_bytes(b"tampered INT8 model")
        with self.assertRaises(target.TargetGateError):
            target.verify_e04_quantization_receipt()


if __name__ == "__main__":
    unittest.main(verbosity=2)
