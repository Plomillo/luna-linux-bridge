from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
                "import pathlib,sys\n"
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
            grammar = source / "samples" / "grammar.pl"
            grammar.write_text("sentence --> [fixture].\n", encoding="utf-8")
            binary = source / "tpl"
            binary.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib,sys\n"
                "assert pathlib.Path('samples/grammar.pl').is_file()\n"
                "assert '-g' in sys.argv and '-l' in sys.argv\n"
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
            result = coverage.probe_trealla(root)
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
                " p=pathlib.Path('primitive.fst'); p.write_text('fixture'); print('compiled'); raise SystemExit(0)\n",
                encoding="utf-8",
            )
            foma.chmod(0o755)
            flookup = source / "flookup"
            flookup.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "if '-v' in sys.argv: print('flookup test version'); raise SystemExit(0)\n"
                "sys.stdin.read(); print('cat\\tgato')\n",
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
            result = coverage.probe_foma(root)
            self.assertEqual(result["status"], coverage.PASS)
            self.assertTrue(result["packaged_binary_execution"])
            self.assertEqual(result["consumer_task_equivalence"], "NOT_ESTABLISHED_ANCIENT_LANGUAGE_LEXICON_MISSING")
            self.assertEqual(len(result["flookup_sha256"]), 64)

    def test_runtime_image_declares_native_build_and_offline_test_dependencies(self):
        workflow = (REPOSITORY / ".github" / "workflows" / "cajita-louksna1-factory.yml").read_text(encoding="utf-8")
        for package in ("git", "zlib1g-dev", "p7zip-full", "build-essential"):
            self.assertIn(package, workflow)
        for package in ("iniconfig==2.3.0", "pluggy==1.6.0", "packaging==25.0"):
            self.assertIn(package, workflow)
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
