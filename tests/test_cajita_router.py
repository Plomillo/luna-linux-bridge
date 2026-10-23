import json
import tempfile
import unittest
import subprocess
import sys
from pathlib import Path

from cajita_router import (
    CAPABILITY_ADAPTERS, DOMAINS, ROUTES, append_trace, build_plan,
    normalize_command, route_table_selftest,
)

class CajitaRouterTests(unittest.TestCase):
    def test_catalog_contains_fourteen_routes_and_six_domains(self):
        result = route_table_selftest()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["route_count"], 14)
        self.assertEqual(len({route["command"] for route in ROUTES}), 14)
        self.assertEqual(len(DOMAINS), 6)

    def test_command_case_normalization(self):
        self.assertEqual(normalize_command("/PLAY EMA"), "/play ema")
        self.assertEqual(normalize_command("/play PT"), "/play PT")
        self.assertEqual(normalize_command("/play traductor"), "/play traductor")

    def test_unknown_command_fails_closed(self):
        result = build_plan("/play UNKNOWN haz algo")
        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["reason"], "UNKNOWN_CANONICAL_COMMAND")

    def test_translation_route_preserves_canonical_profile(self):
        result = build_plan("/play traductor traduce este párrafo al inglés")
        route = next(route for route in ROUTES if route["command"] == "/play traductor")
        self.assertIn("D04_TRADUCTOR_INTELIGENTE", result["domain_sequence"])
        self.assertEqual(result["route_command"], "/play traductor")
        self.assertEqual(result["engines"], route["engines"])
        self.assertEqual(result["agents"], route["agents"])
        self.assertEqual(result["domain_sequence"][:2], ["D01_CEREBRO", "D02_ORQUESTACION"])

    def test_transcription_intent_selects_transcription_domain(self):
        result = build_plan("Transcribe este audio de voz a texto")
        self.assertIn("D03_TRANSCRIPCION", result["domain_sequence"])
        self.assertIn("audio_transcription", result["required_capabilities"])

    def test_pdf_generation_is_not_claimed_as_available(self):
        result = build_plan("Crea un PDF con este informe")
        self.assertIn("pdf_generation", result["required_capabilities"])
        self.assertIn("D05_INTELIGENCIA_DOCUMENTAL", result["domain_sequence"])
        self.assertNotIn("PDF_GENERATION_ADAPTER_NOT_REGISTERED", result["blockers"])
        self.assertTrue(any("D05_INTELIGENCIA_DOCUMENTAL" in item for item in result["unmeasured_peak_rss_domains"]))
        self.assertFalse(result["execution_authorized"])

    def test_document_extraction_then_translation_is_sequential(self):
        result = build_plan("Extrae el texto del PDF y tradúcelo al inglés")
        sequence = result["domain_sequence"]
        self.assertLess(sequence.index("D05_INTELIGENCIA_DOCUMENTAL"),
                        sequence.index("D04_TRADUCTOR_INTELIGENTE"))
        self.assertLess(sequence.index("D01_CEREBRO"), sequence.index("D02_ORQUESTACION"))

    def test_complex_route_preserves_canonical_engines(self):
        route = next(route for route in ROUTES if route["command"] == "/play DCIL")
        result = build_plan("/play DCIL analiza este documento")
        self.assertEqual(result["engines"], route["engines"])
        self.assertEqual(result["agents"], route["agents"])

    def test_execution_is_blocked_without_adapter_and_peak_rss_evidence(self):
        result = build_plan("Responde a esta pregunta general")
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["orchestration_mode"], "PLAN_ONLY; DOMAIN_TASK_DISPATCH_NOT_IMPLEMENTED")
        self.assertIn("D01_CEREBRO", result["unmeasured_peak_rss_domains"])

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
        self.assertEqual(CAPABILITY_ADAPTERS["pdf_generation"], "CAJITA_MODEL_ADAPTERS/1.0_STANDARD_LIBRARY")
        self.assertEqual(CAPABILITY_ADAPTERS["audio_transcription"], "CAJITA_MODEL_ADAPTERS/1.0")
        self.assertEqual(CAPABILITY_ADAPTERS["job_orchestration"], "CAJITA_MODEL_ADAPTERS/1.0_DIAGNOSTIC_ONLY")

    def test_primary_runtime_exposes_routes_command(self):
        runtime = Path(__file__).resolve().parents[1] / "cajita-luna-runtime" / "cajita_runtime.py"
        result = subprocess.run([sys.executable, "-B", str(runtime), "routes"],
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["routes"]), 14)
        self.assertEqual(len(payload["domains"]), 6)

    def test_primary_runtime_fails_closed_for_unregistered_pdf_generator(self):
        runtime = Path(__file__).resolve().parents[1] / "cajita-luna-runtime" / "cajita_runtime.py"
        result = subprocess.run([sys.executable, "-B", str(runtime), "plan", "--request", "Crea un PDF con este informe"],
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["execution_authorized"])
        self.assertNotIn("PDF_GENERATION_ADAPTER_NOT_REGISTERED", payload["blockers"])
        self.assertTrue(any(item.startswith("PEAK_RSS_UNMEASURED:") for item in payload["blockers"]))

if __name__ == "__main__":
    unittest.main()
