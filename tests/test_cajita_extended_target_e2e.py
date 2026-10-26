from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "tools"))
spec = importlib.util.spec_from_file_location(
    "cajita_extended_target_e2e",
    REPOSITORY / "tools" / "cajita_extended_target_e2e.py",
)
assert spec and spec.loader
coverage = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = coverage
spec.loader.exec_module(coverage)


class ExtendedTargetCoverageTests(unittest.TestCase):
    def _bind_native_engine_receipts(self, root: Path, build_specs: list[dict]) -> None:
        """Create hash-bound test fixture binaries in the same layout as factory outputs."""
        artifact_root = root / ".native-engine-bin"
        receipt_builds = []
        for spec in build_specs:
            engine_root = artifact_root / spec["label"]
            engine_root.mkdir(parents=True, exist_ok=True)
            binary_artifacts = []
            for name, source_binary in spec["binaries"]:
                destination = engine_root / name
                destination.write_bytes(source_binary.read_bytes())
                destination.chmod(0o755)
                binary_artifacts.append({
                    "name": name,
                    "path": destination.relative_to(root).as_posix(),
                    "bytes": destination.stat().st_size,
                    "sha256": coverage.sha256_file(destination),
                })
            source_tree_sha = self._fixture_tree_sha256(spec["source"])
            receipt_builds.append({
                "target_id": spec["target_id"],
                "source_path": spec["source"].relative_to(root).as_posix(),
                "source_commit": "a" * 40,
                "source_tree_sha256_before_build": source_tree_sha,
                "source_tree_sha256_after_build": source_tree_sha,
                "source_tree_preserved": True,
                "build_commands": [{"command": ["fixture-only"], "return_code": 0}],
                "native_artifact_root": engine_root.relative_to(root).as_posix(),
                "binary_artifacts": binary_artifacts,
                "shared_libraries": [],
                "build_status": "PASS",
                "runtime_compile_required": False,
                "certification": "NOT_GRANTED",
                "fixture_only": True,
            })
        receipt = {
            "schema": "CAJITA_NATIVE_ENGINE_BUILD_RECEIPTS/1.0",
            "source_commit": "a" * 40,
            "build_environment": {"fixture": "unit-test-only"},
            "builds": receipt_builds,
            "runtime_compile_required": False,
            "model_weight_downloads": 0,
            "remote_commander_used": False,
            "certification": "NOT_GRANTED",
            "fixture_only": True,
        }
        receipt_path = root / "NATIVE_ENGINE_BUILD_RECEIPTS.json"
        receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        routing_path = root / "command_subdomain_routing.json"
        routing = json.loads(routing_path.read_text(encoding="utf-8"))
        materialization = routing.setdefault("materialization", {})
        materialization["native_engine_build_receipt"] = receipt_path.name
        materialization["native_engine_build_receipt_sha256"] = coverage.sha256_file(receipt_path)
        materialization["native_engine_artifact_root"] = ".native-engine-bin"
        materialization["native_engine_build_status"] = "PASS_TEST_FIXTURE_ONLY"
        routing_path.write_text(json.dumps(routing, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _fixture_tree_sha256(source_root: Path) -> str:
        rows = []
        for path in sorted(source_root.rglob("*"), key=lambda item: item.relative_to(source_root).as_posix()):
            if path.is_symlink():
                raise AssertionError("fixture source tree must not contain symlinks")
            if path.is_file():
                rows.append({
                    "path": path.relative_to(source_root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": coverage.sha256_file(path),
                })
        payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
    def test_exactly_ten_uncovered_non_model_targets_are_registered(self):
        expected = {
            "D04_HERMENEUTICA_HG",
            "D04_TRADUCCION_LENGUAS_ANTIGUAS",
            "D05_CALIBRE",
            "D06_ANTI_ALUCINACIONES",
            "D06_ARCHIVADO_DETECCION",
            "D06_COGNITIVE_CI_CD",
            "D06_MIGRACION_PERSISTENCIA",
            "D06_PORTABILIDAD_BASE",
            "D06_RUNTIME_ANDROID_WINDOWS",
            "D06_TESTING",
        }
        self.assertEqual(set(coverage.TARGETS), expected)
        self.assertEqual(set(coverage.PROBES), expected)
        self.assertEqual(len(coverage.TARGETS), 10)

    def test_selected_target_runner_can_limit_to_explicit_repair_scope(self):
        selected = coverage.select_target_specs([
            "D04_HERMENEUTICA_HG",
            "D04_TRADUCCION_LENGUAS_ANTIGUAS",
            "D06_MIGRACION_PERSISTENCIA",
        ])
        self.assertEqual(set(selected), {
            "D04_HERMENEUTICA_HG",
            "D04_TRADUCCION_LENGUAS_ANTIGUAS",
            "D06_MIGRACION_PERSISTENCIA",
        })
        self.assertEqual(len(selected), 3)
        self.assertEqual(set(coverage.select_target_specs(None)), set(coverage.TARGETS))

    def test_selected_target_runner_rejects_duplicate_or_unknown_target(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_PRIMITIVE_TARGET_SELECTION"):
            coverage.select_target_specs(["D04_HERMENEUTICA_HG", "D04_HERMENEUTICA_HG"])
        with self.assertRaisesRegex(ValueError, "UNKNOWN_PRIMITIVE_TARGET_SELECTION"):
            coverage.select_target_specs(["D04_NOT_REGISTERED"])

    def test_regular_files_without_filter_returns_nested_regular_files(self):
        with tempfile.TemporaryDirectory(prefix="extended-target-list-files-") as temp:
            root = Path(temp)
            (root / "root.txt").write_text("root", encoding="utf-8")
            (root / "nested").mkdir()
            (root / "nested" / "opa_linux_amd64_static").write_bytes(b"pinned-opa")
            actual = {path.relative_to(root).as_posix() for path in coverage.regular_files(root)}
            self.assertEqual(actual, {"root.txt", "nested/opa_linux_amd64_static"})

    def test_sqlite_probe_builds_from_canonical_source_when_amalgamation_files_are_absent(self):
        with tempfile.TemporaryDirectory(prefix="extended-target-sqlite-canonical-build-") as temp:
            root = Path(temp)
            source_root = root / "SQLITE_SOURCE_3_53_4"
            source_tree = source_root / "sqlite-src-3530400"
            source_tree.mkdir(parents=True)
            configure = source_tree / "configure"
            configure.write_text(
                "#!/bin/sh\n"
                "cat > Makefile <<'MAKEFILE'\n"
                "sqlite3:\n"
                "\tprintf '%s\\n' '#!/usr/bin/env python3' 'import pathlib,sys' "
                "'if len(sys.argv) == 2 and sys.argv[1] == \"--version\": print(\"3.53.4 fixture\"); raise SystemExit(0)' "
                "'pathlib.Path(sys.argv[-1]).write_bytes(b\"fixture database\")' "
                "'sys.stdin.read()' 'print(\"preserve-me|migrated\")' 'print(\"ok\")' > sqlite3\n"
                "\tchmod +x sqlite3\n"
                "MAKEFILE\n",
                encoding="utf-8",
            )
            build_temp = root / "tmp"
            build_temp.mkdir()
            result = coverage.sqlite_migration_probe(source_root, build_temp)
            self.assertEqual(result["migration"]["return_code"], 0)
            self.assertIn("preserve-me|migrated", result["migration"]["stdout_excerpt"])
            self.assertEqual(result["sqlite_version"]["return_code"], 0)
            self.assertEqual(len(result["source_tree_sha256_before_build"]), 64)
            self.assertTrue((source_tree / "configure").is_file())
            self.assertFalse((source_tree / "sqlite3").exists())

    def test_materialized_asset_root_uses_registered_path_and_descriptor_hash(self):
        with tempfile.TemporaryDirectory(prefix="extended-target-asset-root-") as temp:
            root = Path(temp)
            asset_root = root / "native" / "OPA_STATIC"
            asset_root.mkdir(parents=True)
            descriptor = {
                "canonical_asset_id": "OPA_STATIC",
                "module_key": "native/OPA_STATIC",
                "target_id": "D06_COGNITIVE_CI_CD",
            }
            descriptor_bytes = (json.dumps(descriptor, sort_keys=True, indent=2) + "\n").encode()
            (asset_root / "CAJITA_MODULE.json").write_bytes(descriptor_bytes)
            (asset_root / "opa_linux_amd64_static").write_bytes(b"pinned-test-fixture")
            placement = {
                "schema": "CAJITA_EXTERNALIZED_ASSET_PLACEMENT/1.0",
                "assets": [{
                    "id": "OPA_STATIC",
                    "expanded_path": "cajita-luna-runtime/native/OPA_STATIC",
                    "factory_reconciliation": {
                        "module_manifest_sha256": hashlib.sha256(descriptor_bytes).hexdigest()
                    }
                }]
            }
            (root / "EXTERNALIZED_ASSET_PLACEMENT.json").write_text(json.dumps(placement), encoding="utf-8")
            resolved = coverage.materialized_asset_root(root, "OPA_STATIC")
            self.assertEqual(resolved, asset_root)
            self.assertEqual(coverage.regular_files(resolved)[0].name, "CAJITA_MODULE.json")

    def test_runner_invokes_processes_without_shell(self):
        import subprocess
        result = coverage.run_process([sys.executable, "-c", "print('primitive-ok')"], timeout=10)
        self.assertEqual(result["return_code"], 0)
        self.assertIn("primitive-ok", result["stdout_excerpt"])
        self.assertEqual(len(result["stdout_sha256"]), 64)

    def test_executable_copy_preserves_bytes_and_sets_mode_only_on_copy(self):
        with tempfile.TemporaryDirectory(prefix="extended-target-copy-test-") as temp:
            root = Path(temp)
            source = root / "source"
            source.write_bytes(b"fixture executable bytes")
            source.chmod(0o644)
            original_mode = source.stat().st_mode
            copy = coverage.copy_executable(source, root / "probe")
            self.assertEqual(hashlib.sha256(copy.read_bytes()).hexdigest(), hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(source.stat().st_mode, original_mode)
            self.assertTrue(os.access(copy, os.X_OK))

    def test_antihallucination_lfs_pointer_is_not_misreported_as_a_model(self):
        with tempfile.TemporaryDirectory(prefix="extended-target-lfs-test-") as temp:
            root = Path(temp)
            module = root / "6. Sistema Inteligente" / "Anti-Alucinaciones"
            module.mkdir(parents=True)
            pointer = (
                "version https://git-lfs.github.com/spec/v1\n"
                "oid sha256:" + "a" * 64 + "\n"
                "size 11051600\n"
            ).encode("utf-8")
            (module / "model.onnx").write_bytes(pointer)
            (module / "CAJITA_MODULE.json").write_text(json.dumps({
                "schema": "CAJITA_CANONICAL_TARGET_MODULE/1.0",
                "target_id": "D06_ANTI_ALUCINACIONES",
                "relative_path": "6. Sistema Inteligente/Anti-Alucinaciones",
                "tree_integrity": {"sha256": "b" * 64},
            }), encoding="utf-8")
            (root / "command_subdomain_routing.json").write_text(json.dumps({
                "schema": "CAJITA_COMMAND_SUBDOMAIN_ROUTING/1.0",
                "targets": [{
                    "id": "D06_ANTI_ALUCINACIONES",
                    "path": "6. Sistema Inteligente/Anti-Alucinaciones",
                }],
            }), encoding="utf-8")
            result = coverage.probe_antihallucination(root)
            self.assertEqual(result["status"], coverage.BLOCKED)
            self.assertEqual(result["reason"], "ONNX_PAYLOAD_IS_GIT_LFS_POINTER_NOT_EXECUTABLE_MODEL")
            self.assertEqual(result["lfs_declared_bytes"], 11051600)
            self.assertFalse(result["large_model_payload_downloaded"])
            self.assertEqual(result["certification"], "NOT_GRANTED")

    def _make_calibre_test_root(self, root: Path) -> tuple[Path, Path]:
        relative = "5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/calibre"
        module = root / relative
        module.mkdir(parents=True)
        (module / "CAJITA_MODULE.json").write_text(json.dumps({
            "schema": "CAJITA_CANONICAL_TARGET_MODULE/1.0",
            "target_id": "D05_CALIBRE",
            "relative_path": relative,
            "tree_integrity": {"sha256": "b" * 64},
        }), encoding="utf-8")
        (module / "CALIBRE_BINARY_EXTERNALIZATION.json").write_text(json.dumps({
            "bundled_binary": False, "equivalence": "NOT_ESTABLISHED", "functional_tests": "NOT_RUN",
        }), encoding="utf-8")
        (module / "CALIBRE_SOURCE_PROVENANCE.json").write_text(json.dumps({
            "bundled_source_archive": False, "equivalence": "NOT_ESTABLISHED", "functional_tests": "NOT_RUN",
        }), encoding="utf-8")
        (root / "command_subdomain_routing.json").write_text(json.dumps({
            "schema": "CAJITA_COMMAND_SUBDOMAIN_ROUTING/1.0",
            "targets": [{"id": "D05_CALIBRE", "path": relative}],
        }), encoding="utf-8")
        wrapper_source = REPOSITORY / "cajita-luna-runtime" / "5. Inteligencia documental" / "Conversión documental" / "Calibre Slim"
        wrapper_dest = root / "5. Inteligencia documental" / "Conversión documental" / "Calibre Slim"
        wrapper_dest.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copytree(wrapper_source, wrapper_dest)
        return module, wrapper_dest

    def _write_fake_calibre_converter(self, path: Path) -> None:
        lines = [
            "#!/usr/bin/env python3",
            "import pathlib,sys,zipfile",
            "if len(sys.argv) > 1 and sys.argv[1] == \"--version\":",
            "    print(\"ebook-convert (calibre 9.17.0)\")",
            "    raise SystemExit(0)",
            "source = pathlib.Path(sys.argv[-2])",
            "destination = pathlib.Path(sys.argv[-1])",
            "with zipfile.ZipFile(destination, \"w\") as archive:",
            "    archive.writestr(\"mimetype\", \"application/epub+zip\", compress_type=zipfile.ZIP_STORED)",
            "    archive.writestr(\"META-INF/container.xml\", \"<container version=\\\"1.0\\\"><rootfiles><rootfile full-path=\\\"OEBPS/content.opf\\\" media-type=\\\"application/oebps-package+xml\\\"/></rootfiles></container>\")",
            "    archive.writestr(\"OEBPS/content.opf\", \"<package version=\\\"2.0\\\"><metadata/><manifest/><spine/></package>\")",
            "    archive.writestr(\"OEBPS/chapter.xhtml\", \"<html><body>fixture</body></html>\")",
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        path.chmod(0o755)

    def test_calibre_is_held_if_no_external_executable_is_available(self):
        with tempfile.TemporaryDirectory(prefix="extended-target-calibre-missing-") as temp:
            root = Path(temp)
            module, wrapper = self._make_calibre_test_root(root)
            with patch.object(coverage.shutil, "which", return_value=None), patch.dict(coverage.os.environ, {"CALIBRE_EBOOK_CONVERT": ""}):
                with self.assertRaisesRegex(coverage.ProbeBlocked, "CALIBRE_FUNCTIONAL_ENGINE_ABSENT"):
                    coverage.probe_calibre(root)

    def test_calibre_runs_the_pinned_wrapper_and_validates_real_epub_contract(self):
        with tempfile.TemporaryDirectory(prefix="extended-target-calibre-convert-") as temp:
            root = Path(temp)
            module, wrapper = self._make_calibre_test_root(root)
            fake_converter = root / "ebook-convert-fixture"
            self._write_fake_calibre_converter(fake_converter)
            environment = {
                "CALIBRE_EBOOK_CONVERT": str(fake_converter),
                "CALIBRE_RUNTIME_ROOT": str(root),
                "CALIBRE_OFFICIAL_ASSET_ID": "CALIBRE_V9_17_0_LINUX_X86_64_BINARY",
                "CALIBRE_OFFICIAL_ASSET_SHA256": "953e4512a6482848cd803c88b6d942e6afca65dc3b67c7d1353ae048d616de53",
                "CALIBRE_OFFICIAL_ASSET_SIZE_BYTES": "201590724",
            }
            with patch.object(coverage.shutil, "which", return_value=str(fake_converter)), patch.dict(coverage.os.environ, environment):
                result = coverage.probe_calibre(root)
            self.assertEqual(result["status"], coverage.PASS)
            self.assertEqual(result["primitive"], "REAL_TXT_TO_EPUB_CONVERSION_THROUGH_PRODUCT_WRAPPER")
            self.assertEqual(result["runtime_identity"]["expected_version"], "9.17.0")
            self.assertEqual(result["epub_output"]["container_integrity"], "PASS")
            self.assertEqual(result["epub_output"]["mimetype"], "PASS")
            self.assertEqual(result["epub_output"]["container_xml"], "PASS")
            self.assertEqual(result["epub_output"]["package_document"], "PASS")
            self.assertEqual(len(result["epub_output"]["sha256"]), 64)

    def test_calibre_runtime_asset_without_exact_hash_receipt_is_blocked(self):
        with tempfile.TemporaryDirectory(prefix="extended-target-calibre-provenance-") as temp:
            root = Path(temp)
            module, wrapper = self._make_calibre_test_root(root)
            fake_converter = root / "ebook-convert-fixture"
            self._write_fake_calibre_converter(fake_converter)
            environment = {"CALIBRE_EBOOK_CONVERT": str(fake_converter), "CALIBRE_OFFICIAL_ASSET_ID": "", "CALIBRE_OFFICIAL_ASSET_SHA256": "", "CALIBRE_OFFICIAL_ASSET_SIZE_BYTES": "0"}
            with patch.object(coverage.shutil, "which", return_value=str(fake_converter)), patch.dict(coverage.os.environ, environment):
                with self.assertRaisesRegex(coverage.ProbeBlocked, "CALIBRE_OFFICIAL_RUNTIME_ASSET_NOT_PROVEN"):
                    coverage.probe_calibre(root)

    def test_archive_detection_hashes_fixture_before_temp_cleanup(self):
        with tempfile.TemporaryDirectory(prefix="extended-target-archive-detection-") as temp:
            root = Path(temp)
            relative = "6. Sistema Inteligente/Archivado/Detección de archivos"
            module = root / relative / "siegfried_1-11-6_linux-x86_64_static"
            module.mkdir(parents=True)
            binary = module / "sf"
            binary.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib,sys,os\n"
                "assert pathlib.Path(sys.argv[-1]).is_file()\n"
                "print('ZIP matches')\n",
                encoding="utf-8",
            )
            binary.chmod(0o755)
            (root / relative / "CAJITA_MODULE.json").write_text(json.dumps({
                "schema": "CAJITA_CANONICAL_TARGET_MODULE/1.0",
                "target_id": "D06_ARCHIVADO_DETECCION",
                "relative_path": relative,
                "tree_integrity": {"sha256": "b" * 64},
            }), encoding="utf-8")
            (root / "command_subdomain_routing.json").write_text(json.dumps({
                "schema": "CAJITA_COMMAND_SUBDOMAIN_ROUTING/1.0",
                "targets": [{"id": "D06_ARCHIVADO_DETECCION", "path": relative}],
            }), encoding="utf-8")
            result = coverage.probe_archive_detection(root)
            self.assertEqual(result["status"], coverage.PASS)
            self.assertEqual(len(result["fixture_sha256"]), 64)
            self.assertEqual(len(result["binary_sha256"]), 64)

    def test_trealla_probe_executes_packaged_binary_without_source_build(self):
        with tempfile.TemporaryDirectory(prefix="extended-target-trealla-packaged-") as temp:
            root = Path(temp)
            relative = "4. Traductor Inteligente/Hermenéutica H-G"
            module = root / relative
            source = module / "trealla-2.100.24" / "trealla-2.100.24"
            (source / "samples").mkdir(parents=True)
            (source / "library").mkdir()
            grammar = source / "samples" / "grammar.pl"
            grammar.write_text(
                ":- use_module(library(dcgs)).\n"
                "sentence --> [the,man,shoots].\n",
                encoding="utf-8",
            )
            binary = source / "tpl"
            binary.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib,sys,os\n"
                "assert pathlib.Path('samples/grammar.pl').is_file()\n"
                "assert os.environ.get('TPL_LIBRARY_PATH') == str(pathlib.Path('library').resolve())\n"
                "assert '-l' in sys.argv\n"
                "driver = pathlib.Path(sys.argv[sys.argv.index('-l')+1])\n"
                "text = driver.read_text(encoding='utf-8')\n"
                "assert text.count(chr(10)) >= 2 and chr(92)+'n' not in text\n"
                "assert 'use_module(library(dcgs))' in text\n"
                "assert 'include(' in text\n"
                "assert 'phrase(sentence,[the,man,shoots]),write(true),halt' in text\n"
                "print('true')\n",
                encoding="utf-8",
            )
            binary.chmod(0o755)
            module.mkdir(parents=True, exist_ok=True)
            (module / "CAJITA_MODULE.json").write_text(json.dumps({
                "schema": "CAJITA_CANONICAL_TARGET_MODULE/1.0",
                "target_id": "D04_HERMENEUTICA_HG",
                "relative_path": relative,
                "tree_integrity": {"sha256": "c" * 64, "file_count_excluding_module_descriptors": 2, "bytes_excluding_module_descriptors": 100},
            }), encoding="utf-8")
            (root / "command_subdomain_routing.json").write_text(json.dumps({
                "schema": "CAJITA_COMMAND_SUBDOMAIN_ROUTING/1.0",
                "targets": [{"id": "D04_HERMENEUTICA_HG", "path": relative}],
            }), encoding="utf-8")
            self._bind_native_engine_receipts(root, [{
                "target_id": "D04_HERMENEUTICA_HG",
                "label": "trealla",
                "source": source,
                "binaries": [("tpl", binary)],
            }])
            # Reproduce archives where verified binary bytes survive but POSIX mode
            # bits do not; the probe must execute an identity-checked copy only.
            packaged = root / ".native-engine-bin" / "trealla" / "tpl"
            packaged.chmod(0o644)
            packaged_sha256 = coverage.sha256_file(packaged)
            result = coverage.probe_trealla(root)
            self.assertEqual(packaged.stat().st_mode & 0o111, 0)
            self.assertEqual(coverage.sha256_file(packaged), packaged_sha256)
            self.assertEqual(result["status"], coverage.PASS)
            self.assertTrue(result["packaged_binary_execution"])
            self.assertEqual(result["task_coverage"], "PROLOG_GRAMMAR_PRIMITIVE_ONLY_NOT_FULL_HISTORICAL_HERMENEUTICS")
            self.assertEqual(len(result["binary_sha256"]), 64)

    def test_foma_probe_executes_packaged_foma_and_flookup(self):
        with tempfile.TemporaryDirectory(prefix="extended-target-foma-packaged-") as temp:
            root = Path(temp)
            relative = "4. Traductor Inteligente/Traducción de lenguas antiguas"
            module = root / relative
            source = module / "foma-master" / "foma-master" / "foma"
            (source / "tests").mkdir(parents=True)
            (source / "Makefile").write_text("check:\n\t@./foma -v\n", encoding="utf-8")
            (source / "tests" / "run.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            foma = source / "foma"
            foma.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib,sys\n"
                "if '-v' in sys.argv: print('foma test version'); raise SystemExit(0)\n"
                "if '-f' in sys.argv:\n"
                " script=pathlib.Path(sys.argv[sys.argv.index('-f')+1]).read_text()\n"
                " assert script.count(chr(10)) >= 2 and chr(92)+'n' not in script\n"
                " assert 'regex [c a t]:[g a t o];' in script\n"
                " p=pathlib.Path('primitive.fst'); p.write_text('fixture'); print('compiled'); raise SystemExit(0)\n",
                encoding="utf-8",
            )
            foma.chmod(0o755)
            flookup = source / "flookup"
            flookup.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "if '-v' in sys.argv: print('flookup test version'); raise SystemExit(0)\n"
                "assert '-i' in sys.argv, 'forward translation requires -i'\n"
                "value=sys.stdin.read()\n"
                "assert value == 'cat'+chr(10)\n"
                "print('cat'+chr(9)+'gato')\n",
                encoding="utf-8",
            )
            flookup.chmod(0o755)
            (module / "CAJITA_MODULE.json").write_text(json.dumps({
                "schema": "CAJITA_CANONICAL_TARGET_MODULE/1.0",
                "target_id": "D04_TRADUCCION_LENGUAS_ANTIGUAS",
                "relative_path": relative,
                "tree_integrity": {"sha256": "d" * 64, "file_count_excluding_module_descriptors": 3, "bytes_excluding_module_descriptors": 100},
            }), encoding="utf-8")
            (root / "command_subdomain_routing.json").write_text(json.dumps({
                "schema": "CAJITA_COMMAND_SUBDOMAIN_ROUTING/1.0",
                "targets": [{"id": "D04_TRADUCCION_LENGUAS_ANTIGUAS", "path": relative}],
            }), encoding="utf-8")
            self._bind_native_engine_receipts(root, [{
                "target_id": "D04_TRADUCCION_LENGUAS_ANTIGUAS",
                "label": "foma",
                "source": source,
                "binaries": [("foma", foma), ("flookup", flookup)],
            }])
            packaged_foma = root / ".native-engine-bin" / "foma" / "foma"
            packaged_flookup = root / ".native-engine-bin" / "foma" / "flookup"
            packaged_foma.chmod(0o644)
            packaged_flookup.chmod(0o644)
            foma_sha256, flookup_sha256 = coverage.sha256_file(packaged_foma), coverage.sha256_file(packaged_flookup)
            result = coverage.probe_foma(root)
            self.assertEqual(packaged_foma.stat().st_mode & 0o111, 0)
            self.assertEqual(packaged_flookup.stat().st_mode & 0o111, 0)
            self.assertEqual(coverage.sha256_file(packaged_foma), foma_sha256)
            self.assertEqual(coverage.sha256_file(packaged_flookup), flookup_sha256)
            self.assertEqual(result["status"], coverage.PASS)
            self.assertTrue(result["packaged_binary_execution"])
            self.assertEqual(result["consumer_task_equivalence"], "NOT_ESTABLISHED_ANCIENT_LANGUAGE_LEXICON_MISSING")
            self.assertEqual(len(result["flookup_sha256"]), 64)

    def test_foma_probe_requires_forward_lookup_mode(self):
        import inspect
        source = inspect.getsource(coverage.probe_foma)
        self.assertIn('run_process([str(flookup_binary),"-i",str(fst)]', source)
        self.assertIn("assert '-i' in sys.argv", Path(__file__).read_text(encoding="utf-8"))

    def test_opa_policy_uses_rego_v1_rule_syntax(self):
        policy = coverage.rego_release_policy()
        self.assertIn("default allow := false", policy)
        self.assertIn("allow if {", policy)
        self.assertNotIn("allow {", policy)

    def test_rqlite_readiness_requires_elected_leader_and_store(self):
        self.assertFalse(coverage.rqlite_ready_body_is_complete(503, "[+]node ok\\n[-]leader not found"))
        self.assertFalse(coverage.rqlite_ready_body_is_complete(200, "[+]node ok\\n[-]leader not found"))
        self.assertFalse(coverage.rqlite_ready_body_is_complete(200, "[+]node ok\\n[+]leader ok"))
        self.assertTrue(coverage.rqlite_ready_body_is_complete(200, "[+]node ok\\n[+]leader ok\\n[+]store ok"))

    def test_rqlite_readiness_polls_readyz_not_status(self):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b"[+]node ok\\n[+]leader ok\\n[+]store ok\\n"
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        process = MagicMock()
        process.poll.return_value = None
        with patch("urllib.request.urlopen", return_value=response) as open_url:
            receipt = coverage.wait_for_rqlite_ready("http://127.0.0.1:4001", process, timeout_seconds=1)
        self.assertEqual(receipt["endpoint"], "/readyz")
        self.assertEqual(receipt["ready_state"], "NODE_LEADER_STORE_READY")
        self.assertTrue(open_url.call_args.args[0].endswith("/readyz"))

    def test_rqlite_statement_body_is_the_documented_json_array(self):
        self.assertEqual(
            coverage.rqlite_statement_batch("CREATE TABLE x(id INTEGER)", "SELECT 1"),
            ["CREATE TABLE x(id INTEGER)", "SELECT 1"],
        )
        with self.assertRaisesRegex(ValueError, "RQLITE_SQL_STATEMENT_BATCH_INVALID"):
            coverage.rqlite_statement_batch("")

    def test_runtime_image_declares_native_build_and_offline_test_dependencies(self):
        workflow = (REPOSITORY / ".github" / "workflows" / "cajita-louksna1-factory.yml").read_text(encoding="utf-8")
        for package in ("git", "zlib1g-dev", "p7zip-full", "build-essential"):
            self.assertIn(package, workflow)
        for package in ("iniconfig==2.3.0", "pluggy==1.6.0", "packaging==25.0", "pygments==2.21.0", "py==1.11.0"):
            self.assertIn(package, workflow)
        self.assertIn("build-essential tcl git", workflow)
        source = (REPOSITORY / "tools" / "cajita_extended_target_e2e.py").read_text(encoding="utf-8")
        self.assertIn('"--no-index", "--no-deps"', source)

    def test_status_contract_never_promotes_diagnostic_coverage(self):
        source = (REPOSITORY / "tools" / "cajita_extended_target_e2e.py").read_text(encoding="utf-8")
        self.assertIn('"product_certification": "NOT_GRANTED"', source)
        self.assertIn('"release_eligibility": False', source)
        self.assertIn('"COMPLETE_DIAGNOSTIC_ONLY"', source)
        self.assertIn('"HOLD_NOT_CERTIFIED"', source)
        self.assertIn('"heavy_model_weight_download_count": 0', source)
        self.assertIn('"synthetic_evidence_used_as_product_proof": False', source)
        workflow = (REPOSITORY / ".github" / "workflows" / "cajita-louksna1-factory.yml").read_text(encoding="utf-8")
        self.assertIn("calibre-9.17.0-x86_64.txz", workflow)
        self.assertIn("953e4512a6482848cd803c88b6d942e6afca65dc3b67c7d1353ae048d616de53", workflow)
        self.assertIn("CALIBRE_OFFICIAL_ASSET_SHA256", workflow)
        self.assertIn('"remote_commander_used": False', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
