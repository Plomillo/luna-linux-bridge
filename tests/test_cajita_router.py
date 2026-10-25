import json
import tempfile
import unittest
import subprocess
import sys
from pathlib import Path

from cajita_router import (
    CAPABILITY_ADAPTERS, DOMAINS, ROUTES, ROUTING_REGISTRY, TARGETS_BY_ID,
    SUPPORT_ASSETS_BY_ID, append_trace, build_plan, matched_intent_targets,
    normalize_command, route_table_selftest,
)


class CajitaRouterTests(unittest.TestCase):
    def test_catalog_contains_fourteen_routes_six_domains_and_all_subdomains(self):
        result = route_table_selftest()
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["route_count"], 14)
        self.assertEqual(len({route["command"] for route in ROUTES}), 14)
        self.assertEqual(len(DOMAINS), 6)
        self.assertEqual(result["target_count"], 21)
        self.assertEqual(result["subdomain_count"], 19)
        self.assertEqual(result["subdomain_counts_by_domain"]["D02_ORQUESTACION"], 3)
        self.assertEqual(result["subdomain_counts_by_domain"]["D04_TRADUCTOR_INTELIGENTE"], 3)
        self.assertEqual(result["subdomain_counts_by_domain"]["D05_INTELIGENCIA_DOCUMENTAL"], 2)
        self.assertEqual(result["subdomain_counts_by_domain"]["D06_SISTEMA_INTELIGENTE"], 11)
        self.assertEqual(result["support_asset_count"], 10)
        self.assertEqual(result["engine_count"], 15)
        self.assertEqual(result["target_engine_binding_count"], 21)

    def test_canonical_spellings_and_only_explicit_aliases(self):
        self.assertEqual(normalize_command("/play PT"), "/play PT")
        self.assertEqual(normalize_command("/play traductor"), "/play traductor")
        self.assertEqual(normalize_command("/play E"), "/play e")
        self.assertEqual(normalize_command("/play EMA"), "/play ema")
        self.assertEqual(normalize_command("/play P"), "/play p")
        self.assertEqual(normalize_command("/play C"), "/play c")
        self.assertEqual(normalize_command("/play CP"), "/play cp")
        self.assertIsNone(normalize_command("/PLAY EMA"))
        self.assertIsNone(normalize_command("/HELP"))
        self.assertIsNone(normalize_command("/play UNKNOWN"))
        self.assertIsNone(normalize_command("/play  PT"))

    def test_unknown_command_fails_closed(self):
        result = build_plan("/play UNKNOWN haz algo")
        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["reason"], "UNKNOWN_CANONICAL_COMMAND")

    def test_undeclared_case_variants_fail_closed(self):
        result = build_plan("/PLAY EMA reflexiona sobre este texto")
        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertFalse(result["execution_authorized"])

    def test_translation_route_preserves_canonical_profile_and_targets_general_translation(self):
        result = build_plan("/play traductor Traduce este párrafo al inglés")
        route = next(route for route in ROUTES if route["command"] == "/play traductor")
        self.assertIn("D04_TRADUCTOR_INTELIGENTE", result["domain_sequence"])
        self.assertEqual(result["route_command"], "/play traductor")
        self.assertEqual(result["engines"], route["engines"])
        self.assertEqual(result["agents"], route["agents"])
        self.assertTrue(result["canonical_rationale"])
        self.assertTrue(result["extension_families"])
        self.assertIn("D04_TRADUCCION_GENERAL", [target["id"] for target in result["selected_targets"]])
        self.assertEqual(result["domain_sequence"][:2], ["D01_CEREBRO", "D02_ORQUESTACION"])

    def test_ancient_languages_route_avoids_general_translation_target(self):
        result = build_plan("/play traductor Traduce del griego koiné al español")
        target_ids = {target["id"] for target in result["selected_targets"]}
        self.assertIn("D04_HERMENEUTICA_HG", target_ids)
        self.assertIn("D04_TRADUCCION_LENGUAS_ANTIGUAS", target_ids)
        self.assertNotIn("D04_TRADUCCION_GENERAL", target_ids)
        self.assertIn("INTENT_ANCIENT_LANGUAGES", result["matched_intent_rules"])

    def test_transcription_intent_selects_transcription_target(self):
        result = build_plan("Transcribe este audio de voz a texto")
        self.assertIn("D03_TRANSCRIPCION", result["domain_sequence"])
        self.assertIn("D03_TRANSCRIPCION_ROOT", [target["id"] for target in result["selected_targets"]])
        self.assertIn("audio_transcription", result["required_capabilities"])

    def test_pdf_extraction_targets_docling_and_pdf_generation_stays_blocked(self):
        result = build_plan("Crea un PDF con este informe y extrae texto del documento")
        self.assertIn("pdf_generation", result["required_capabilities"])
        self.assertIn("D05_INTELIGENCIA_DOCUMENTAL", result["domain_sequence"])
        self.assertIn("D05_DOCLING", [target["id"] for target in result["selected_targets"]])
        self.assertIn("PDF_GENERATION_ADAPTER_NOT_REGISTERED", result["blockers"])
        self.assertFalse(result["execution_authorized"])

    def test_document_extraction_then_translation_is_sequential(self):
        result = build_plan("Extrae el texto del PDF y tradúcelo al inglés")
        sequence = result["domain_sequence"]
        self.assertLess(sequence.index("D05_INTELIGENCIA_DOCUMENTAL"),
                        sequence.index("D04_TRADUCTOR_INTELIGENTE"))
        self.assertLess(sequence.index("D01_CEREBRO"), sequence.index("D02_ORQUESTACION"))

    def test_memory_and_persistence_targets_map_to_sqlite_and_rqlite(self):
        result = build_plan("Consulta la memoria gobernada y valida la base SQLite")
        target_ids = {target["id"] for target in result["selected_targets"]}
        self.assertIn("D06_MEMORIA_GOBERNADA", target_ids)
        self.assertIn("D06_MIGRACION_PERSISTENCIA", target_ids)
        asset_ids = {asset["id"] for asset in result["selected_support_assets"]}
        self.assertIn("RQLITE_10_2_7_LINUX_AMD64", asset_ids)
        self.assertIn("SQLITE_SOURCE_3_53_4", asset_ids)

    def test_cicd_and_protocol_targets_map_dagger_and_opa(self):
        result = build_plan("Audita el pipeline CI/CD y la política OPA del workflow")
        target_ids = {target["id"] for target in result["selected_targets"]}
        self.assertIn("D06_COGNITIVE_CI_CD", target_ids)
        self.assertIn("D06_MOTOR_PROTOCOLAR", target_ids)
        asset_ids = {asset["id"] for asset in result["selected_support_assets"]}
        self.assertIn("DAGGER_0_21_8_LINUX_AMD64", asset_ids)
        self.assertIn("OPA_STATIC_LINUX_AMD64_CANDIDATE", asset_ids)

    def test_orchestrator_and_testing_targets_map_playwright(self):
        result = build_plan("Automatiza el navegador con Playwright y ejecuta pruebas")
        target_ids = {target["id"] for target in result["selected_targets"]}
        self.assertIn("D02_ORQUESTADOR", target_ids)
        self.assertIn("D06_TESTING", target_ids)
        self.assertIn("PLAYWRIGHT_1_63_0_SOURCE",
                      {asset["id"] for asset in result["selected_support_assets"]})

    def test_every_selected_asset_has_activation_gates_and_no_direct_execution(self):
        result = build_plan("/play AE integra el runtime y valida la arquitectura")
        self.assertTrue(result["selected_support_assets"])
        for asset in result["selected_support_assets"]:
            if asset.get("container_retained_in_distribution"):
                # In a compact distribution the verified .7z is present, while
                # its expanded tree is absent until an explicit materialization.
                self.assertFalse(asset.get("materialized_path"))
                self.assertEqual(asset["activation_status"], "MAPPED_CONTAINER_NOT_ACTIVATED")
                self.assertFalse(asset["archive_removed_from_runtime"])
                self.assertEqual(asset["path"], asset["container_path"])
                self.assertEqual(asset["bytes"], asset["container_bytes"])
                self.assertEqual(asset["sha256"], asset["container_sha256"])
                self.assertIn("verify-container-sha256", asset["activation_requirements"])
                self.assertIn("verify-expanded-tree-sha256-before-materialization", asset["activation_requirements"])
                self.assertEqual(len(asset["container_sha256"]), 64)
                self.assertEqual(len(asset["expanded_tree_sha256"]), 64)
            elif asset.get("materialized_path"):
                self.assertEqual(asset["activation_status"], "MATERIALIZED_NOT_FUNCTIONALLY_VALIDATED")
                self.assertTrue(asset["archive_removed_from_runtime"])
            else:
                self.assertEqual(asset["activation_status"], "MAPPED_CONTAINER_NOT_ACTIVATED")
            self.assertIn("verify-sha256", asset["activation_requirements"])
            self.assertIn("verify-module-manifest", asset["activation_requirements"])
            self.assertIn("register-real-consumer-adapter", asset["activation_requirements"])
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["orchestration_mode"], "PLAN_ONLY; REGISTERED_DOMAIN_ADAPTERS_REQUIRE_MEASURED_RESOURCE_AND_TARGET_EVIDENCE")
        self.assertTrue(any(x.startswith("SUBDOMAIN_TASK_ADAPTER_NOT_REGISTERED:")
                            for x in result["blockers"]))

    def test_all_ten_support_assets_reference_existing_targets(self):
        self.assertEqual(len(SUPPORT_ASSETS_BY_ID), 10)
        for asset in SUPPORT_ASSETS_BY_ID.values():
            self.assertTrue(asset["sha256"])
            self.assertGreater(asset["bytes"], 0)
            self.assertTrue(asset["relative_path"].endswith(".7z"))
            self.assertTrue(asset["subdomain_ids"])
            for target_id in asset["subdomain_ids"]:
                self.assertIn(target_id, TARGETS_BY_ID)
        for target in TARGETS_BY_ID.values():
            self.assertTrue(target["engine_ids"])
            self.assertTrue(set(target["engine_ids"]).issubset({f"E{i:02d}" for i in range(1, 16)}))

    def test_complex_route_preserves_canonical_engines(self):
        route = next(route for route in ROUTES if route["command"] == "/play DCIL")
        result = build_plan("/play DCIL analiza este documento")
        self.assertEqual(result["engines"], route["engines"])
        self.assertEqual(result["agents"], route["agents"])

    def test_execution_is_blocked_without_adapter_and_peak_rss_evidence(self):
        result = build_plan("Responde a esta pregunta general")
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["orchestration_mode"], "PLAN_ONLY; REGISTERED_DOMAIN_ADAPTERS_REQUIRE_MEASURED_RESOURCE_AND_TARGET_EVIDENCE")
        self.assertIn("D01_CEREBRO", result["unmeasured_peak_rss_domains"])
        self.assertTrue(any(blocker.startswith("PEAK_RSS_UNMEASURED:D01_CEREBRO") for blocker in result["blockers"]))

    def test_trace_records_hash_but_not_request_body(self):
        request = "Mi texto privado que no debe persistirse"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "audit.jsonl"
            plan = build_plan(request)
            append_trace(str(path), plan)
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(request, content)
            self.assertIn(plan["request_sha256"], content)
            self.assertFalse(json.loads(content).get("execution_authorized", True))

    def test_domain_stages_are_sequential_and_unloaded(self):
        result = build_plan("transcribe este audio y traduce la transcripción")
        self.assertEqual(result["parallel_domain_processes"], 1)
        self.assertEqual(result["load_policy"], "ON_DEMAND_SEQUENTIAL")
        self.assertEqual(result["unload_policy"], "UNLOAD_AFTER_EACH_DOMAIN_STAGE")

    def test_canonical_authority_and_route_catalog_are_not_mutated(self):
        result = build_plan("/play AE analiza este sistema")
        self.assertFalse(result["canonical_routes_mutated"])
        self.assertFalse(result["authority_transfer"])
        self.assertEqual(len(ROUTES), 14)

    def test_task_adapter_registry_reflects_current_evidence_boundary(self):
        self.assertEqual(CAPABILITY_ADAPTERS["pdf_generation"], "NOT_REGISTERED")
        self.assertEqual(CAPABILITY_ADAPTERS["audio_transcription"], "CAJITA_WHISPER_TRANSCRIPTION/1.0")
        self.assertEqual(CAPABILITY_ADAPTERS["text_translation"], "CAJITA_SEAMLESS_TRANSLATION/1.0")
        self.assertEqual(CAPABILITY_ADAPTERS["advanced_reasoning"], "CAJITA_QWEN3_REASONING/1.0")
        self.assertEqual(CAPABILITY_ADAPTERS["job_orchestration"], "REGISTRY_AND_PLAN_ONLY_NOT_EXECUTOR")
        self.assertEqual(CAPABILITY_ADAPTERS["pdf_generation"], "NOT_REGISTERED")

    def test_primary_runtime_exposes_routes_and_subdomain_registry(self):
        runtime = Path(__file__).resolve().parents[1] / "cajita-luna-runtime" / "cajita_runtime.py"
        result = subprocess.run([sys.executable, "-B", str(runtime), "routes"],
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["routes"]), 14)
        self.assertEqual(len(payload["domains"]), 6)
        self.assertEqual(payload["subdomain_routing"]["schema"], "CAJITA_COMMAND_SUBDOMAIN_ROUTING/1.0")
        self.assertEqual(len(payload["subdomain_routing"]["targets"]), 21)

    def test_primary_runtime_fails_closed_for_unregistered_pdf_generator(self):
        runtime = Path(__file__).resolve().parents[1] / "cajita-luna-runtime" / "cajita_runtime.py"
        result = subprocess.run([sys.executable, "-B", str(runtime), "plan", "--request", "Crea un PDF con este informe"],
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["execution_authorized"])
        self.assertIn("PDF_GENERATION_ADAPTER_NOT_REGISTERED", payload["blockers"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
