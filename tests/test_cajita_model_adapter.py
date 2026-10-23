import json
import tempfile
import unittest
from pathlib import Path

import cajita_model_adapter as adapter

class ModelAdapterControlTests(unittest.TestCase):
    def test_registry_has_six_domains_with_unique_capabilities(self):
        self.assertEqual(len(adapter.DOMAINS), 6)
        self.assertEqual(len({v["capability"] for v in adapter.DOMAINS.values()}), 6)
        self.assertTrue(all(Path(v["module"]).is_file() for v in adapter.DOMAINS.values()))

    def test_onnx_guard_does_not_claim_inference(self):
        self.assertEqual(
            adapter.TASK_ADAPTER_STATUS["anti_hallucination_onnx"],
            "BLOCKED_RUNTIME_AND_ARCHITECTURE_UNVERIFIED",
        )

    def test_pdf_adapter_creates_valid_minimal_pdf_and_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "sample.pdf"
            result = adapter.make_pdf("Informe de prueba\nResumen: acción, economía y traducción.", output)
            data = output.read_bytes()
            self.assertEqual(result["status"], "PASS_PDF_CREATED")
            self.assertTrue(data.startswith(b"%PDF-1.4"))
            self.assertIn(b"xref\n", data)
            self.assertTrue(data.rstrip().endswith(b"%%EOF"))
            self.assertEqual(result["output_sha256"], adapter.sha256_file(output))
            self.assertGreaterEqual(result["page_count"], 1)

    def test_pdf_adapter_handles_multiple_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "long.pdf"
            result = adapter.make_pdf("\n".join(f"line {i}" for i in range(125)), output)
            data = output.read_bytes()
            self.assertEqual(result["page_count"], 3)
            self.assertIn(b"/Count 3", data)


    def test_document_processor_uses_bounded_512px_non_tiled_profile(self):
        from types import SimpleNamespace
        processor = SimpleNamespace(image_processor=SimpleNamespace(
            size={"longest_edge": 2048},
            max_image_size={"longest_edge": 512},
            do_image_splitting=True,
        ))
        profile = adapter.apply_low_memory_document_profile(processor)
        self.assertEqual(processor.image_processor.size, {"longest_edge": 512})
        self.assertEqual(processor.image_processor.max_image_size, {"longest_edge": 512})
        self.assertFalse(processor.image_processor.do_image_splitting)
        self.assertEqual(profile["profile_id"], "LOW_MEMORY_512_NO_SPLITS")
        self.assertEqual(profile["quality_equivalence"], "NOT_ESTABLISHED")

    def test_pdf_generation_domain_adapter_does_not_claim_model_load(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "domain.pdf"
            result = adapter.run_model_task("D05_INTELIGENCIA_DOCUMENTAL", {
                "action": "generate_pdf", "text": "Contenido de prueba", "output_file": str(output)
            })
            self.assertEqual(result["status"], "PASS_PDF_CREATED")
            self.assertFalse(result["model_loaded"])
            self.assertTrue(output.is_file())

    def test_trace_hashes_request_without_recording_request_body(self):
        secretish = "el texto privado que no se debe guardar"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "audit.jsonl"
            report = {
                "domain_id": "D01_CEREBRO", "status": "PASS", "operation_status": "PASS_TEXT_GENERATION",
                "model_asset": {"sha256": "abc123"}, "peak_rss_mib": 321.25, "worker_rss_limit_mib": 800,
                "worker_pid_reaped": True, "output_sha256": "def456",
            }
            adapter.append_audit_trace(str(path), report, secretish)
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(secretish, content)
            item = json.loads(content)
            self.assertEqual(item["request_sha256"], adapter.sha256_text(secretish))
            self.assertFalse(item["request_body_stored"])

    def test_rss_limits_keep_system_headroom(self):
        self.assertEqual(adapter.MAX_GLOBAL_RAM_MIB, 1024)
        self.assertEqual(adapter.DEFAULT_WORKER_RSS_LIMIT_MIB, 850)
        self.assertEqual(adapter.MAX_PARENT_PLUS_WORKER_RSS_MIB, 900)
        self.assertGreaterEqual(adapter.MAX_GLOBAL_RAM_MIB - adapter.MAX_PARENT_PLUS_WORKER_RSS_MIB, 124)

    def test_synthetic_fixtures_have_valid_container_signatures(self):
        with tempfile.TemporaryDirectory() as temp:
            wav = Path(temp) / "test.wav"
            ppm = Path(temp) / "test.ppm"
            adapter.make_synthetic_audio(wav)
            adapter.make_synthetic_image(ppm)
            self.assertTrue(wav.read_bytes().startswith(b"RIFF"))
            self.assertTrue(ppm.read_bytes().startswith(b"P6\n64 64\n255\n"))

if __name__ == "__main__":
    unittest.main()
