from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cajita-luna-runtime" / "LOUKSNAPG2_RUNTIME"))
import louksnapg2_engine as engine


class FakeCajitaAdapter:
    def __init__(self):
        self.requests = []
        self.routes = {
            "D01_CEREBRO": {"weight_path": "1. Cerebro/model.safetensors", "weight_sha256": "gpt-oss"},
            "D03_TRANSCRIPCION": {"weight_path": "3. Transcripción/model.safetensors", "weight_sha256": "whisper"},
            "D04_TRADUCTOR_INTELIGENTE": {"weight_path": "4. Traductor Inteligente/Traducción general/model.safetensors", "weight_sha256": "seamless"},
            "D05_INTELIGENCIA_DOCUMENTAL": {"weight_path": "5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_weights.bin", "weight_sha256": "docling"},
            "D06_SISTEMA_INTELIGENTE": {"weight_path": "6. Sistema Inteligente/Análisis Avanzado/model.safetensors", "weight_sha256": "qwen"},
        }

    def verify_integrity(self, root, domain):
        return {"domain_id": domain, **self.routes[domain], "module_tree_sha256": "a" * 64}

    def execute_task(self, request, root, timeout_cap=600):
        self.requests.append(request)
        domain = request["domain_id"]
        operation = request["operation"]
        payload = request["input"]
        text = payload.get("prompt") or payload.get("text") or "fixture transcript"
        if domain == "D01_CEREBRO":
            if "SOURCE TEXT:" in text:
                text = "The die is cast." if "Alea iacta est" in text else "Everything flows."
            else:
                text = "42"
        elif domain == "D06_SISTEMA_INTELIGENTE":
            text = "55" if "books" in text.lower() else "No"
        elif domain == "D04_TRADUCTOR_INTELIGENTE":
            text = "La reunión empieza al mediodía." if payload.get("tgt_lang") == "spa" else "The meeting starts at noon."
        elif domain == "D05_INTELIGENCIA_DOCUMENTAL":
            text = "INVOICE 4821 TOTAL 37.50"
        elif domain == "D03_TRANSCRIPCION":
            text = "The meeting starts at noon."
        return ({
            "schema": "CAJITA_TASK_RESULT/1.0",
            "status": "PASS_FUNCTIONAL_EXECUTION",
            "execution_authorized": True,
            "domain_id": domain,
            "operation": operation,
            "target_id": "native-target",
            "adapter_id": "native-adapter",
            "output_text": text,
            "generated_token_count": max(1, len(text.split())),
            "model_runtime_status": "PASS_FIXTURE_ONLY",
            "integrity": self.routes[domain],
            "entrypoint_sha256": hashlib.sha256(b"fixture entry").hexdigest(),
        }, 0)


class LouksnapG2NativeRoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "cajita_task_adapters.py").write_text("# patched native adapter module\n", encoding="utf-8")
        manifest_dir = self.root / "CAJITA_RUNTIME_V1"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        (manifest_dir / "weights_manifest.json").write_text("{}", encoding="utf-8")
        self.fake = FakeCajitaAdapter()
        self.loader_patch = mock.patch.object(engine, "_load_native_adapter", return_value=self.fake)
        self.loader_patch.start()
        self.runtime = engine.LouksnapG2Runtime(self.root, threads=1)

    def tearDown(self):
        self.loader_patch.stop()
        self.temp.cleanup()

    def test_cerebro_uses_existing_gpt_oss_source_adapter(self):
        result = self.runtime.route("D01_CEREBRO", "generate_text", {"prompt": "Compute 6*7.", "max_new_tokens": 16}, task_id="brain-01")
        self.assertEqual(self.fake.requests[-1]["domain_id"], "D01_CEREBRO")
        self.assertEqual(self.fake.requests[-1]["operation"], "generate_text")
        self.assertEqual(result["source_model_id"], "GPT-OSS compactado — rank-1 INT8 factors")
        self.assertEqual(result["output_text"], "42")
        self.assertTrue(result["execution_authorized"])

    def test_advanced_analysis_uses_existing_qwen3_source_adapter(self):
        result = self.runtime.route("D06_SISTEMA_INTELIGENTE", "analyze_reasoning", {"prompt": "How many books remain?", "max_new_tokens": 16}, task_id="analysis-01")
        self.assertEqual(self.fake.requests[-1]["domain_id"], "D06_SISTEMA_INTELIGENTE")
        self.assertEqual(result["source_model_id"], "Qwen3 compactado — low-rank INT8 factors")
        self.assertEqual(result["adapter_id"], "CAJITA_QWEN3_REASONING/1.0")

    def test_general_translation_uses_existing_seamless_adapter(self):
        result = self.runtime.route("D04_TRADUCTOR_INTELIGENTE", "translate_text", {"text": "The meeting starts at noon.", "src_lang": "eng", "tgt_lang": "spa", "max_new_tokens": 32}, task_id="translation-01")
        self.assertEqual(self.fake.requests[-1]["domain_id"], "D04_TRADUCTOR_INTELIGENTE")
        self.assertEqual(result["source_model_id"], "SeamlessM4T v2 compactado — low-rank INT8 factors")
        self.assertEqual(result["output_text"], "La reunión empieza al mediodía.")

    def test_docling_uses_existing_native_document_adapter(self):
        image = self.root / "invoice.png"
        image.write_bytes(b"fixture image")
        result = self.runtime.route(
            "D05_INTELIGENCIA_DOCUMENTAL", "extract_document_image",
            {"image_path": str(image), "prompt": "Extract invoice fields.", "max_new_tokens": 48},
            task_id="docling-01",
        )
        self.assertEqual(self.fake.requests[-1]["domain_id"], "D05_INTELIGENCIA_DOCUMENTAL")
        self.assertEqual(self.fake.requests[-1]["operation"], "extract_document_image")
        self.assertEqual(result["target_id"], "D05_DOCLING")
        self.assertEqual(result["adapter_id"], "CAJITA_DOCLING_IMAGE_EXTRACTION/1.0")
        self.assertEqual(result["output_text"], "INVOICE 4821 TOTAL 37.50")

    def test_transcription_uses_existing_whisper_source_adapter(self):
        audio = self.root / "sample.wav"
        audio.write_bytes(b"fixture audio")
        result = self.runtime.route("D03_TRANSCRIPCION", "transcribe_audio", {"audio_path": str(audio), "max_new_tokens": 32}, task_id="transcribe-01")
        self.assertEqual(self.fake.requests[-1]["domain_id"], "D03_TRANSCRIPCION")
        self.assertEqual(result["source_model_id"], "Whisper compactado — low-rank INT8 factors")
        self.assertEqual(result["operation"], "transcribe_audio")

    def test_ancient_translation_uses_dedicated_gpt_oss_prompt_and_never_general_route(self):
        result = self.runtime.route("D04_TRADUCCION_LENGUAS_ANTIGUAS", "translate_ancient_text", {"text": "Alea iacta est", "src_lang": "lat", "tgt_lang": "eng", "max_new_tokens": 48}, task_id="ancient-01")
        request = self.fake.requests[-1]
        self.assertEqual(request["domain_id"], "D01_CEREBRO")
        self.assertIn("ANCIENT-LANGUAGE TRANSLATION SPECIALIST", request["input"]["prompt"])
        self.assertIn("Alea iacta est", request["input"]["prompt"])
        self.assertEqual(result["domain_id"], "D04_TRADUCCION_LENGUAS_ANTIGUAS")
        self.assertEqual(result["translation_strategy"], "DEDICATED_DOMAIN_PROMPT_OVER_EXISTING_GPT_OSS")
        self.assertFalse(result["general_translation_fallback_selected"])
        self.assertEqual(result["output_text"], "The die is cast.")

    def test_unknown_ancient_language_fails_closed(self):
        with self.assertRaisesRegex(engine.EngineRuntimeError, "ANCIENT_SOURCE_LANGUAGE_NOT_REGISTERED"):
            self.runtime.route("D04_TRADUCCION_LENGUAS_ANTIGUAS", "translate_ancient_text", {"text": "bonjour", "src_lang": "fra"}, task_id="ancient-invalid")

    def test_wrong_domain_operation_pair_fails_closed(self):
        with self.assertRaisesRegex(engine.EngineRuntimeError, "DOMAIN_OPERATION_PAIR_NOT_REGISTERED"):
            self.runtime.route("D04_TRADUCCION_LENGUAS_ANTIGUAS", "translate_text", {"text": "Alea iacta est", "src_lang": "lat"}, task_id="ancient-misroute")

    def test_native_weight_identity_preflight_uses_original_manifests(self):
        with mock.patch.object(engine, "verify_model_files", return_value={"D01_CEREBRO": {"weight_sha256": "gpt-oss"}}):
            result = self.runtime.preflight()
        self.assertEqual(result["status"], "PASS_MODEL_SOURCE_IDENTITIES")
        self.assertFalse(result["new_external_model_fetch_performed"])

    def test_one_thread_budget_is_enforced(self):
        with self.assertRaisesRegex(engine.EngineRuntimeError, "CPU_THREAD_BUDGET_MUST_BE_ONE"):
            engine.LouksnapG2Runtime(self.root, threads=2)


if __name__ == "__main__":
    unittest.main()
