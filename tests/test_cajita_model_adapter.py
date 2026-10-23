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


    def test_document_processor_preserves_compatible_512px_tile_geometry(self):
        from types import SimpleNamespace
        processor = SimpleNamespace(image_processor=SimpleNamespace(
            size={"longest_edge": 2048},
            max_image_size={"longest_edge": 512},
            do_image_splitting=False,
        ))
        profile = adapter.apply_compatible_document_profile(processor)
        self.assertEqual(processor.image_processor.size, {"longest_edge": 2048})
        self.assertEqual(processor.image_processor.max_image_size, {"longest_edge": 512})
        self.assertTrue(processor.image_processor.do_image_splitting)
        self.assertEqual(profile["profile_id"], "PACKAGED_IDEFICS3_GEOMETRY_SPLIT_512")
        self.assertEqual(profile["quality_equivalence"], "NOT_ESTABLISHED")

    def test_document_processor_rejects_unbounded_tile_configuration(self):
        from types import SimpleNamespace
        processor = SimpleNamespace(image_processor=SimpleNamespace(
            size={"longest_edge": 4096},
            max_image_size={"longest_edge": 2048},
            do_image_splitting=True,
        ))
        with self.assertRaisesRegex(RuntimeError, "DOCUMENT_IMAGE_SIZE_PROFILE_OUT_OF_BOUNDS"):
            adapter.apply_compatible_document_profile(processor)


    def test_docling_releases_each_tensor_mapping_and_ties_embeddings_before_allocation(self):
        source = Path(adapter.DOMAINS["D05_INTELIGENCIA_DOCUMENTAL"]["module"]).read_text(encoding="utf-8")
        tie_pos = source.index('model.tie_weights()')
        allocate_pos = source.index('model.to_empty(device="cpu")')
        self.assertLess(tie_pos, allocate_pos, "tied embedding storage must be shared before CPU allocation")
        self.assertIn('output_parent._modules.pop(output_name)', source)
        self.assertIn('output_parent._modules[output_name] = output_head', source)
        self.assertIn('TIED_EMBEDDING_ALIAS_NOT_PRESERVED_AFTER_CPU_MATERIALIZATION', source)
        tensor_loop_start = source.index('for name,r in meta["tensors"].items():')
        tensor_loop_end = source.index('    finally:', tensor_loop_start)
        tensor_loop = source[tensor_loop_start:tensor_loop_end]
        self.assertIn('mapped.madvise(mmap.MADV_DONTNEED)', tensor_loop)
        self.assertLess(tensor_loop.index('loaded.add(name)'), tensor_loop.index('mapped.madvise(mmap.MADV_DONTNEED)'))


    def test_docling_bivlm_chunk_decoder_matches_full_reference(self):
        import importlib.util
        if importlib.util.find_spec("numpy") is None or importlib.util.find_spec("torch") is None:
            self.skipTest("numpy/torch are installed only in the model-resource workflow")
        import numpy as np
        import torch
        module_path = adapter.DOMAINS["D05_INTELIGENCIA_DOCUMENTAL"]["module"]
        spec = importlib.util.spec_from_file_location("docling_chunk_test_runtime", module_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        rows, cols = 13, 17
        sign_count = rows * cols
        signs = ((np.arange(sign_count) % 3) == 0).astype(np.uint8)
        packed = np.packbits(signs, bitorder="little").tobytes()
        scales = np.linspace(0.5, 1.5, rows, dtype=np.float32).astype("<f2").tobytes()
        outlier_ids = np.array([1, sign_count // 2, sign_count - 2], dtype="<u4")
        outlier_values = np.array([0.25, -0.5, 0.75], dtype="<f2")
        indices = outlier_ids.tobytes()
        values = outlier_values.tobytes()
        scale_offset = len(packed)
        index_offset = scale_offset + len(scales)
        value_offset = index_offset + len(indices)
        blob = packed + scales + indices + values
        record = {
            "name": "synthetic-vision-projection",
            "kind": "bivlm_binary_outliers",
            "shape": [rows, cols],
            "matrix_shape": [rows, cols],
            "sign_offset": 0,
            "sign_nbytes": len(packed),
            "scale_offset": scale_offset,
            "scale_nbytes": len(scales),
            "outlier_count": len(outlier_ids),
            "outlier_index_offset": index_offset,
            "outlier_value_offset": value_offset,
        }
        expected = module.decode_tensor(blob, record)
        target = torch.empty((rows, cols), dtype=torch.float16)
        module.decode_tensor_chunked_into(memoryview(blob), record, target, chunk_rows=8)
        np.testing.assert_array_equal(target.numpy(), expected)



    def test_docling_bivlm_chunk_decoder_restores_four_dimensional_conv_shape(self):
        import importlib.util
        if importlib.util.find_spec("numpy") is None or importlib.util.find_spec("torch") is None:
            self.skipTest("numpy/torch are installed only in the model-resource workflow")
        import numpy as np
        import torch
        module_path = adapter.DOMAINS["D05_INTELIGENCIA_DOCUMENTAL"]["module"]
        spec = importlib.util.spec_from_file_location("docling_conv_shape_test_runtime", module_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        rows, channels, height, width = 13, 3, 4, 4
        cols = channels * height * width
        sign_count = rows * cols
        signs = ((np.arange(sign_count) % 5) < 2).astype(np.uint8)
        packed = np.packbits(signs, bitorder="little").tobytes()
        scales = np.linspace(0.25, 1.25, rows, dtype=np.float32).astype("<f2").tobytes()
        outlier_ids = np.array([1, sign_count // 2, sign_count - 2], dtype="<u4")
        outlier_values = np.array([0.125, -0.25, 0.5], dtype="<f2")
        indices = outlier_ids.tobytes()
        values = outlier_values.tobytes()
        scale_offset = len(packed)
        index_offset = scale_offset + len(scales)
        value_offset = index_offset + len(indices)
        blob = packed + scales + indices + values
        record = {
            "name": "synthetic-patch-embedding-weight",
            "kind": "bivlm_binary_outliers",
            "shape": [rows, channels, height, width],
            "matrix_shape": [rows, cols],
            "sign_offset": 0,
            "sign_nbytes": len(packed),
            "scale_offset": scale_offset,
            "scale_nbytes": len(scales),
            "outlier_count": len(outlier_ids),
            "outlier_index_offset": index_offset,
            "outlier_value_offset": value_offset,
        }
        expected = module.decode_tensor(blob, record)
        target = torch.empty((rows, channels, height, width), dtype=torch.float16)
        module.decode_tensor_chunked_into(memoryview(blob), record, target, chunk_rows=8)
        self.assertEqual(tuple(target.shape), tuple(record["shape"]))
        np.testing.assert_array_equal(target.numpy(), expected)

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
        self.assertEqual(adapter.DEFAULT_WORKER_RSS_LIMIT_MIB, 875)
        self.assertEqual(adapter.MAX_PARENT_PLUS_WORKER_RSS_MIB, 900)
        self.assertGreaterEqual(adapter.MAX_GLOBAL_RAM_MIB - adapter.MAX_PARENT_PLUS_WORKER_RSS_MIB, 124)

    def test_synthetic_fixtures_have_valid_container_signatures(self):
        with tempfile.TemporaryDirectory() as temp:
            wav = Path(temp) / "test.wav"
            ppm = Path(temp) / "test.ppm"
            adapter.make_synthetic_audio(wav)
            adapter.make_synthetic_image(ppm)
            self.assertTrue(wav.read_bytes().startswith(b"RIFF"))
            self.assertTrue(ppm.read_bytes().startswith(b"P6\n512 512\n255\n"))
            self.assertGreater(len(ppm.read_bytes()), 750_000)

if __name__ == "__main__":
    unittest.main()
