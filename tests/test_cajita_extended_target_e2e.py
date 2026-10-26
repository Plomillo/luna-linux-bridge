from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

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

    def test_calibre_is_held_when_only_externalization_metadata_exists(self):
        with tempfile.TemporaryDirectory(prefix="extended-target-calibre-test-") as temp:
            root = Path(temp)
            module = root / "5. Inteligencia documental" / "calibre"
            module.mkdir(parents=True)
            (module / "CAJITA_MODULE.json").write_text(json.dumps({
                "schema": "CAJITA_CANONICAL_TARGET_MODULE/1.0",
                "target_id": "D05_CALIBRE",
                "relative_path": "5. Inteligencia documental/calibre",
            }), encoding="utf-8")
            (module / "CALIBRE_BINARY_EXTERNALIZATION.json").write_text(json.dumps({
                "bundled_binary": False,
                "equivalence": "NOT_ESTABLISHED",
                "functional_tests": "NOT_RUN",
            }), encoding="utf-8")
            (module / "CALIBRE_SOURCE_PROVENANCE.json").write_text(json.dumps({
                "bundled_source_archive": False,
                "equivalence": "NOT_ESTABLISHED",
                "functional_tests": "NOT_RUN",
            }), encoding="utf-8")
            (root / "command_subdomain_routing.json").write_text(json.dumps({
                "schema": "CAJITA_COMMAND_SUBDOMAIN_ROUTING/1.0",
                "targets": [{
                    "id": "D05_CALIBRE",
                    "path": "5. Inteligencia documental/calibre",
                }],
            }), encoding="utf-8")
            with self.assertRaisesRegex(coverage.ProbeBlocked, "CALIBRE_FUNCTIONAL_ENGINE_ABSENT"):
                coverage.probe_calibre(root)

    def test_status_contract_never_promotes_diagnostic_coverage(self):
        source = (REPOSITORY / "tools" / "cajita_extended_target_e2e.py").read_text(encoding="utf-8")
        self.assertIn('"product_certification": "NOT_GRANTED"', source)
        self.assertIn('"release_eligibility": False', source)
        self.assertIn('"COMPLETE_DIAGNOSTIC_ONLY"', source)
        self.assertIn('"HOLD_NOT_CERTIFIED"', source)
        self.assertIn('"heavy_model_weight_download_count": 0', source)
        self.assertIn('"synthetic_evidence_used_as_product_proof": False', source)
        self.assertIn('"remote_commander_used": False', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
