import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "louksnapg_bundle.py"
SPEC = importlib.util.spec_from_file_location("louksnapg_bundle", MODULE_PATH)
bundle = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(bundle)

VALIDATOR_PATH = Path(__file__).resolve().parents[1] / "tools" / "louksnapg_independent_validator.py"
VALIDATOR_SPEC = importlib.util.spec_from_file_location("louksnapg_independent_validator", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(VALIDATOR_SPEC)
assert VALIDATOR_SPEC and VALIDATOR_SPEC.loader
VALIDATOR_SPEC.loader.exec_module(validator)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class LouksnapgBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "LOUKSNAMEJORADA.md"
        self.cajita = self.root / "CajitadeLuna.md"
        self.doc = self.root / "Louksna1.md"
        self.runtime = self.root / "CAJITA_LUNA_RUNTIME_V10.macrodown"
        self.output = self.root / "LOUKSNAPG.md"

        self.source_bytes = b"# protected architecture\nIMMUTABLE=TRUE\n"
        self.cajita_bytes = b"# Cajita Runtime V10\nROUTE=READY\n"
        self.source.write_bytes(self.source_bytes)
        self.cajita.write_bytes(self.cajita_bytes)
        self.doc.write_bytes(
            self.source_bytes
            + b"\n---\n# Unification marker\n\n# Documento central del runtime Cajita de Luna (copia literal)\n\n"
            + self.cajita_bytes
        )
        engine_bindings = [
            {"id": "E01", "name": "LLM"}, {"id": "E02", "name": "NLP"}, {"id": "E03", "name": "RAG"},
            {"id": "E04", "name": "EMBEDDINGS"}, {"id": "E05", "name": "VECTOR_SEARCH"}, {"id": "E06", "name": "KNOWLEDGE_GRAPH"},
            {"id": "E07", "name": "RDF"}, {"id": "E08", "name": "OWL"}, {"id": "E09", "name": "SEMANTIC_INFERENCE"},
            {"id": "E10", "name": "RULE_ENGINE"}, {"id": "E11", "name": "HERMENEUTIC"}, {"id": "E12", "name": "FORMALIZATION"},
            {"id": "E13", "name": "VALIDATION"}, {"id": "E14", "name": "PROVENANCE"}, {"id": "E15", "name": "CONSENSUS"},
        ]
        target_ids = [
            "D01_CEREBRO_ROOT", "D02_CONFESION_ECLESIAL_REFORMADA", "D02_MULTI_INTERDISCIPLINAR", "D02_ORQUESTADOR",
            "D03_TRANSCRIPCION_ROOT", "D04_HERMENEUTICA_HG", "D04_TRADUCCION_LENGUAS_ANTIGUAS", "D04_TRADUCCION_GENERAL",
            "D05_CALIBRE", "D05_DOCLING", "D06_ANTI_ALUCINACIONES", "D06_ANALISIS_AVANZADO", "D06_ARCHIVADO_DETECCION",
            "D06_COGNITIVE_CI_CD", "D06_CONSOLA", "D06_MEMORIA_GOBERNADA", "D06_MIGRACION_PERSISTENCIA", "D06_MOTOR_PROTOCOLAR",
            "D06_PORTABILIDAD_BASE", "D06_RUNTIME_ANDROID_WINDOWS", "D06_TESTING",
        ]
        command_ids = ["HELP", "PT", "PA", "DCI", "DCIL", "TRAD", "E", "EMA", "P", "C", "CP", "MA", "H", "AE"]
        routing = {
            "domain_order": [
                "D01_CEREBRO", "D02_ORQUESTACION", "D03_TRANSCRIPCION",
                "D04_TRADUCTOR_INTELIGENTE", "D05_INTELIGENCIA_DOCUMENTAL",
                "D06_SISTEMA_INTELIGENTE",
            ],
            "engine_registry": engine_bindings,
            "targets": [{"id": target_id} for target_id in target_ids],
            "route_profiles": [{"id": command_id} for command_id in command_ids],
            "state": {"engine_count": 15},
        }
        registry = {
            "schema": "CAJITA_MODULE_REGISTRY/1.0",
            "canonical_engine_count": 15,
            "canonical_command_count": 14,
        }
        model_metadata = [
            ("1. Cerebro/compression_metadata.json", {"model_id": "OPENAI_GPT_OSS_CEREBRO_MXFP4"}),
            ("3. Transcripción/compression_metadata.json", {"model_id": "CAJITA_TRANSCRIPCION_WHISPER_TURBO"}),
            ("4. Traductor Inteligente/Traducción general/compression_metadata.json", {"model_id": "CAJITA_TRADUCCION_SEAMLESSM4T_V2_LARGE"}),
            ("5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_manifest.json", {"model_id": "ibm-granite/granite-docling-258M"}),
            ("6. Sistema Inteligente/Análisis Avanzado/compression_metadata.json", {"model_id": "CAJITA_SISTEMA_INTELIGENTE_ANALISIS_AVANZADO_QWEN3"}),
        ]
        self.runtime_rows = [
            ("cajita_runtime.py", b"def main():\n    return 0\n", "DEFLATED"),
            ("cajita_router.py", b"ROUTE_TABLE = 21\n", "DEFLATED"),
            ("model.bin", b"\x00\x01\x02runtime-bytes", "STORED"),
            ("command_subdomain_routing.json", json.dumps(routing).encode(), "DEFLATED"),
            ("CAJITA_DISTRIBUTION_MODULE_REGISTRY.json", json.dumps(registry).encode(), "DEFLATED"),
            *[(path, json.dumps(data).encode(), "DEFLATED") for path, data in model_metadata],
        ]
        files = [
            {"path": name, "size_bytes": len(data), "sha256": sha(data), "zip_method": method}
            for name, data, method in self.runtime_rows
        ]
        manifest = {
            "schema": "CAJITA_RUNTIME_MACRODOWN/1.0",
            "candidate_id": "CAJITA_TEST_CANDIDATE",
            "files": files,
        }
        with zipfile.ZipFile(self.runtime, "w", allowZip64=True) as zf:
            for name, data, method in self.runtime_rows:
                compression = zipfile.ZIP_STORED if method == "STORED" else zipfile.ZIP_DEFLATED
                zf.writestr(name, data, compress_type=compression)
            zf.writestr(
                "MACRODOWN_MANIFEST.json",
                json.dumps(manifest, sort_keys=True).encode(),
                compress_type=zipfile.ZIP_DEFLATED,
            )

    def tearDown(self):
        self.temp.cleanup()

    def build(self, cap=bundle.DEFAULT_MAX_BYTES):
        return bundle.build_bundle(
            self.doc,
            self.runtime,
            self.output,
            self.source,
            self.cajita,
            max_bytes=cap,
        )

    def test_builds_one_zip_container_with_document_and_runtime_members(self):
        report = self.build()
        self.assertEqual(report["integrity_status"], "PASS")
        self.assertLessEqual(report["bundle_bytes"], bundle.DEFAULT_MAX_BYTES)
        self.assertEqual(report["global_certification"], "NOT_GRANTED")
        self.assertTrue(zipfile.is_zipfile(self.output))
        with zipfile.ZipFile(self.output) as zf:
            names = set(zf.namelist())
            self.assertIn("Louksna1.md", names)
            self.assertIn("cajita_runtime.py", names)
            self.assertIn("cajita_router.py", names)
            self.assertIn("model.bin", names)
            self.assertIn("MACRODOWN_MANIFEST.json", names)
            self.assertIn("LOUKSNAPG_MANIFEST.json", names)
            self.assertNotIn("CAJITA_LUNA_RUNTIME_V10.macrodown", names)
            self.assertEqual(zf.read("Louksna1.md"), self.doc.read_bytes())

    def test_independent_reverification_detects_member_hash_change(self):
        self.build()
        tampered = self.root / "tampered.md"
        with zipfile.ZipFile(self.output) as zin, zipfile.ZipFile(tampered, "w") as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == "cajita_router.py":
                    data += b"# tamper"
                zout.writestr(info.filename, data)
        with self.assertRaisesRegex(ValueError, "CRC_FAILURE|HASH_OR_SIZE_MISMATCH|MEMBER_SET"):
            bundle.verify_bundle(tampered)

    def test_independent_validator_checks_source_binding_and_member_table(self):
        self.build()
        report = validator.verify(self.output, max_bytes=bundle.DEFAULT_MAX_BYTES)
        self.assertEqual(report["budget_status"], "PASS")
        self.assertEqual(report["container_integrity"], "PASS")
        self.assertEqual(report["protected_prefix_integrity"], "PASS")
        self.assertEqual(report["cajita_document_copy_integrity"], "PASS")
        self.assertEqual(report["runtime_member_integrity"], "PASS")
        self.assertEqual(report["single_distribution_container"], "PASS")
        self.assertEqual(report["identity_preservation_status"], "PASS_SOURCE_IDENTITY_PRESERVED")
        self.assertEqual(report["engine_replacement"], "FORBIDDEN")
        self.assertEqual(report["runtime_routing_registry"], "PASS_DECLARATION_ONLY")
        self.assertEqual(report["module_registry"], "PASS_DECLARATION_ONLY")
        self.assertEqual(report["global_certification"], "NOT_GRANTED")

    def test_independent_validator_rejects_wrong_commit_binding(self):
        self.build()
        with self.assertRaisesRegex(ValueError, "SOURCE_COMMIT_MISMATCH"):
            validator.verify(self.output, expected_source_commit="a" * 40)


    def test_independent_validator_rejects_engine_replacement_claim(self):
        self.build()
        tampered = self.root / "identity-tampered.md"
        with zipfile.ZipFile(self.output, "r") as zin, zipfile.ZipFile(tampered, "w") as zout:
            for info in zin.infolist():
                payload = zin.read(info.filename)
                if info.filename == "LOUKSNAPG_MANIFEST.json":
                    manifest = json.loads(payload.decode("utf-8"))
                    manifest["identity_preservation"]["engine_bindings"][0]["name"] = "REPLACEMENT_ENGINE"
                    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
                zout.writestr(info, payload)
        with self.assertRaisesRegex(ValueError, "ENGINE_BINDING_IDENTITY_MISMATCH"):
            validator.verify(tampered)

    def test_hard_byte_cap_is_enforced_and_candidate_removed(self):
        with self.assertRaisesRegex(ValueError, "LOUKSNAPG_OVER_CAP"):
            self.build(cap=1)
        self.assertFalse(self.output.exists())

    def test_runtime_archive_is_capped_at_470mb_even_when_product_ceiling_is_490mb(self):
        self.assertEqual(bundle.DEFAULT_MAX_BYTES, 479_000_000)
        self.assertEqual(bundle.MAX_RUNTIME_BYTES, 470_000_000)
        self.assertEqual(validator.CAP_BYTES, 479_000_000)
        with self.runtime.open("wb") as stream:
            stream.truncate(bundle.MAX_RUNTIME_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "CAJITA_RUNTIME_OVER_CAP"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_protected_prefix_cannot_drift(self):
        wrong = self.root / "wrong-source.md"
        wrong.write_bytes(b"# changed architecture\n")
        with self.assertRaisesRegex(ValueError, "PREFIX_NOT_BYTE_EXACT"):
            bundle.build_bundle(self.doc, self.runtime, self.output, wrong, self.cajita)
        self.assertFalse(self.output.exists())

    def test_runtime_member_hash_is_checked_before_release(self):
        broken = self.root / "broken.macrodown"
        with zipfile.ZipFile(self.runtime) as zin, zipfile.ZipFile(broken, "w") as zout:
            for info in zin.infolist():
                payload = zin.read(info.filename)
                if info.filename == "cajita_runtime.py":
                    payload += b"# altered without manifest update"
                zout.writestr(info.filename, payload)
        with self.assertRaisesRegex(ValueError, "CRC_FAILURE|HASH_OR_SIZE_MISMATCH"):
            bundle.build_bundle(self.doc, broken, self.output, self.source, self.cajita)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
