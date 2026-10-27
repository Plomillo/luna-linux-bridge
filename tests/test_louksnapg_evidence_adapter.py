import hashlib
import tempfile
import unittest
from pathlib import Path
import sys

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "tools"))
import louksnapg_integral_gate as gate
import louksnapg_evidence_adapter as adapter


class FunctionalEvidenceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        (self.runtime / "cajita_task_adapters.py").write_text("adapter-runtime\n", encoding="utf-8")
        (self.runtime / "cajita_target_adapters.py").write_text("target-runtime\n", encoding="utf-8")
        (self.runtime / "CAJITA_RUNTIME_V1").mkdir()
        (self.runtime / "CAJITA_RUNTIME_V1" / "weights_manifest.json").write_text("{}\n", encoding="utf-8")
        self.commit = "a" * 40
        self.bundle = self.root / "LOUKSNAPG.md"
        self.bundle.write_bytes(b"candidate")
        self.bundle_sha = hashlib.sha256(self.bundle.read_bytes()).hexdigest()
        self.task = {
            "schema": "LOUKSNA1_TASK_ADAPTER_EVIDENCE/1.0",
            "inputs": "REAL_RUNTIME_EXECUTION_WITH_SYNTHETIC_AUDIO_AND_INVOICE_FIXTURES",
            "adapter_runtime_sha256": adapter.sha256_file(self.runtime / "cajita_task_adapters.py"),
            "target_engine_adapter_runtime_sha256": adapter.sha256_file(self.runtime / "cajita_target_adapters.py"),
            "weight_manifest_sha256": adapter.sha256_file(self.runtime / "CAJITA_RUNTIME_V1" / "weights_manifest.json"),
            "task_results": [],
            "target_engine_results": [],
        }
        for domain, target in adapter.MODEL_DOMAIN_TO_TARGET.items():
            self.task["task_results"].append({
                "domain_id": domain, "target_id": target, "status": "PASS_FUNCTIONAL_EXECUTION", "exit_code": 0,
                "input_sha256": "1" * 64, "output_sha256": "2" * 64, "entrypoint_sha256": "3" * 64,
                "weight_sha256": "4" * 64, "module_tree_sha256": "5" * 64, "generated_token_count": 4,
                "output_char_count": 8, "peak_rss_bytes": 1000,
                "quality_acceptance": {"status": "FAIL", "check_id": "known-answer",
                    "reference_kind": "FIXED_SYNTHETIC_EXPECTATION", "output_char_count": 8,
                    "output_text_sha256": "6" * 64},
            })
        engine_ids = [
            "D02_ORQUESTADOR", "D02_CONFESION_ECLESIAL_REFORMADA", "D02_MULTI_INTERDISCIPLINAR",
            "D06_CONSOLA", "D06_MEMORIA_GOBERNADA", "D06_MOTOR_PROTOCOLAR",
        ]
        for target in engine_ids:
            self.task["target_engine_results"].append({
                "target_id": target, "status": "PASS_TARGET_ENGINE_EXECUTION", "exit_code": 0,
                "execution_scope": "SOURCE_BOUND_ENGINE_SMOKE_ONLY",
                "consumer_task_adapter_completion": "NOT_ESTABLISHED",
                "task_coverage": "PARTIAL_TARGET_ENGINE_SMOKE_ONLY",
                "required_file_identities": [{"path": "module.py", "sha256": "7" * 64, "bytes": 10}],
                "result": {"status": "PASS"},
            })
        self.extended = {
            "schema": "CAJITA_EXTENDED_TARGET_E2E/1.0", "source_commit": self.commit,
            "bundle_sha256": self.bundle_sha, "targets": [],
        }
        statuses = {
            "D04_HERMENEUTICA_HG": ("FAIL", None),
            "D04_TRADUCCION_LENGUAS_ANTIGUAS": ("FAIL", None),
            "D05_CALIBRE": ("PASS_PRIMITIVE_SMOKE", "PASS_FOR_TXT_TO_EPUB_PRIMITIVE_ONLY"),
            "D06_ANTI_ALUCINACIONES": ("BLOCKED", None),
            "D06_ARCHIVADO_DETECCION": ("PASS_PRIMITIVE_SMOKE", "PASS_FOR_ZIP_FILE_IDENTIFICATION_ONLY"),
            "D06_COGNITIVE_CI_CD": ("BLOCKED", None),
            "D06_MIGRACION_PERSISTENCIA": ("PASS_PRIMITIVE_SMOKE", "PASS_FOR_DATABASE_MIGRATION_AND_LOCAL_PERSISTENCE_PRIMITIVES"),
            "D06_PORTABILIDAD_BASE": ("BLOCKED", None),
            "D06_RUNTIME_ANDROID_WINDOWS": ("BLOCKED", None),
            "D06_TESTING": ("PASS_PRIMITIVE_SMOKE", "PASS_FOR_TEST_RUNNER_PRIMITIVE_ONLY"),
        }
        for target, (status, scope) in statuses.items():
            self.extended["targets"].append({
                "target_id": target, "status": status, "purpose": "bounded primitive test",
                "evidence_sha256": "8" * 64, "details": {"result": {"consumer_task_equivalence": scope} if scope else {}},
            })

    def test_normalizer_emits_all_21_targets_and_preserves_quality_failures(self):
        evidence = adapter.build_evidence(self.task, self.extended, self.bundle_sha, self.commit, self.runtime)
        rows = evidence["target_results"]
        self.assertEqual(len(rows), 21)
        self.assertEqual({row["target_id"] for row in rows}, set(gate.EXPECTED_TARGET_IDS))
        self.assertEqual(evidence["functional_status"], "HOLD_NOT_CERTIFIED")
        self.assertEqual(evidence["semantic_quality_status"], "FAIL")
        self.assertTrue(evidence["synthetic_only"])
        brain = next(row for row in rows if row["target_id"] == "D01_CEREBRO_ROOT")
        self.assertEqual(brain["status"], "PASS_FUNCTIONAL_EXECUTION")
        self.assertEqual(brain["test_cases_passed"], 0)
        self.assertEqual(brain["quality_status"], "FAIL")
        calibre = next(row for row in rows if row["target_id"] == "D05_CALIBRE")
        self.assertTrue(calibre["scope_complete"])
        hermeneutics = next(row for row in rows if row["target_id"] == "D04_HERMENEUTICA_HG")
        self.assertFalse(hermeneutics["scope_complete"])
        self.assertNotIn("g23", evidence)

    def test_bundle_or_source_commit_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "EXTENDED_REPORT_BUNDLE_SHA256_MISMATCH"):
            adapter.build_evidence(self.task, {**self.extended, "bundle_sha256": "0" * 64}, self.bundle_sha, self.commit, self.runtime)
        with self.assertRaisesRegex(ValueError, "EXTENDED_REPORT_SOURCE_COMMIT_MISMATCH"):
            adapter.build_evidence(self.task, {**self.extended, "source_commit": "b" * 40}, self.bundle_sha, self.commit, self.runtime)

    def test_runtime_hash_mismatch_is_recorded_and_never_promoted(self):
        task = dict(self.task)
        task["adapter_runtime_sha256"] = "0" * 64
        evidence = adapter.build_evidence(task, self.extended, self.bundle_sha, self.commit, self.runtime)
        self.assertIn("TASK_REPORT_RUNTIME_HASH_MISMATCH:adapter_runtime_sha256", evidence["binding_failures"])
        self.assertEqual(evidence["functional_status"], "HOLD_NOT_CERTIFIED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
