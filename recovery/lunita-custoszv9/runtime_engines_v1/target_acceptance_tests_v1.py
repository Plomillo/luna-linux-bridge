from __future__ import annotations

import hashlib
import json
import pathlib
import tempfile
import unittest
from unittest import mock

import target_runtime_acceptance_v1 as target


REQUIRED_FILES = {
    "__init__.py", "engine_runtime_v1.py", "engine_acceptance_v1.py",
    "engine_gateway_v1.py", "gateway_acceptance_v1.py", "lunita_beta_v1_8.py",
    "launcher_acceptance_v1.py", "target_runtime_acceptance_v1.py",
    "apply_engine_overlay_v1.py", "checkpoint_v1.py", "overlay_acceptance_v1.py",
    "engine_assignments_v1.json", "requirements-engine-stack.txt",
    "DEPENDENCY_EVIDENCE_v1.json", "ENGINE_RUNTIME_V1_README.md",
}
REQUIRED_DIRECTORIES = {"vendor/python3.12/site-packages", "model-cache/fastembed"}
MODEL_RELATIVE = pathlib.Path(
    "models--Qdrant--paraphrase-multilingual-MiniLM-L12-v2-onnx-Q/"
    "snapshots/faf4aa4225822f3bc6376869cb1164e8e3feedd0/model_optimized.onnx"
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_receipt(root: pathlib.Path) -> dict:
    entries = []
    for item in sorted(root.rglob("*")):
        if item.is_file():
            entries.append({
                "path": item.relative_to(root).as_posix(),
                "sha256": digest(item),
                "bytes": item.stat().st_size,
            })
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "file_count": len(entries),
        "bytes": sum(row["bytes"] for row in entries),
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }


class TargetOverlayAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lunita-target-gate-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.overlay = self.root / "runtime_engines_v1"
        self.overlay.mkdir()
        self.legacy = self.root / "lunita.py"
        self.legacy.write_bytes(b"hash-pinned legacy launcher fixture")
        self.legacy_hash = digest(self.legacy)
        self.receipt_path = self.overlay / "OVERLAY_APPLY_RECEIPT.json"

        files = {}
        for name in REQUIRED_FILES:
            payload = f"fixture:{name}\n".encode("utf-8")
            path = self.overlay / name
            path.write_bytes(payload)
            files[name] = digest(path)

        directories = {}
        for relative in REQUIRED_DIRECTORIES:
            directory = self.overlay / relative
            directory.mkdir(parents=True)
            fixture = directory / ("vendor-fixture.bin" if relative.startswith("vendor") else "model-fixture.bin")
            fixture.write_bytes(("fixture:" + relative).encode())
            directories[relative] = tree_receipt(directory)

        receipt = {
            "schema": "LUNITA_ADDITIVE_ENGINE_OVERLAY_RECEIPT/1.0",
            "status": "APPLIED_ADDITIVELY_NOT_CERTIFIED",
            "candidate_id": "G06_REBUILD_CANDIDATE_R1",
            "certification": "NOT_GRANTED",
            "launcher_sha256": self.legacy_hash,
            "files": files,
            "directories": directories,
            "canonical_identity_mutation": False,
            "engine_reassignment": False,
            "command_reassignment": False,
            "agent_reassignment": False,
            "frozen_g06_mutated": False,
            "canonical_g08_mutated": False,
            "launcher_mutated": False,
            "model_weights_mutated": False,
        }
        self.write_json(self.receipt_path, receipt)
        self.patches = [
            mock.patch.object(target, "OVERLAY", self.overlay),
            mock.patch.object(target, "OVERLAY_RECEIPT", self.receipt_path),
            mock.patch.object(target, "LEGACY_LAUNCHER", self.legacy),
            mock.patch.object(target, "EXPECTED_LEGACY_SHA256", self.legacy_hash),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def write_json(path: pathlib.Path, value: dict) -> None:
        path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    def load_receipt(self):
        return json.loads(self.receipt_path.read_text(encoding="utf-8"))

    def test_complete_overlay_file_and_directory_hashes_pass(self):
        result = target.verify_overlay()
        self.assertEqual("PASS_OVERLAY_INTEGRITY", result["status"])
        self.assertEqual(digest(self.receipt_path), result["receipt_sha256"])
        self.assertEqual(self.legacy_hash, result["legacy_launcher_sha256"])

    def test_modified_top_level_runtime_file_is_denied(self):
        (self.overlay / "engine_runtime_v1.py").write_text("tampered", encoding="utf-8")
        with self.assertRaises(target.TargetGateError):
            target.verify_overlay()

    def test_modified_vendored_dependency_is_denied(self):
        vendor = self.overlay / "vendor/python3.12/site-packages/vendor-fixture.bin"
        vendor.write_bytes(b"tampered")
        with self.assertRaises(target.TargetGateError):
            target.verify_overlay()

    def test_missing_manifest_entry_is_denied(self):
        receipt = self.load_receipt()
        del receipt["files"]["engine_gateway_v1.py"]
        self.write_json(self.receipt_path, receipt)
        with self.assertRaises(target.TargetGateError):
            target.verify_overlay()

    def test_mutated_frozen_identity_flag_is_denied(self):
        receipt = self.load_receipt()
        receipt["frozen_g06_mutated"] = True
        self.write_json(self.receipt_path, receipt)
        with self.assertRaises(target.TargetGateError):
            target.verify_overlay()

    def test_modified_legacy_launcher_is_denied(self):
        self.legacy.write_bytes(b"modified launcher")
        with self.assertRaises(target.TargetGateError):
            target.verify_overlay()


class TargetE04QuantizationAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lunita-e04-target-gate-")
        self.addCleanup(self.temp.cleanup)
        self.overlay = pathlib.Path(self.temp.name)
        self.cache = self.overlay / "model-cache/fastembed"
        self.model = self.cache / MODEL_RELATIVE
        self.model.parent.mkdir(parents=True)
        self.model.write_bytes(b"measured INT8 ONNX model fixture")
        self.receipt_path = self.cache / "LUNITA_E04_ONNX_QUANTIZATION_RECEIPT.json"
        self.receipt = {
            "schema": "LUNITA_E04_ONNX_QUANTIZATION/1.0",
            "status": "PASS_INT8_QUANTIZATION_MEASURED",
            "model_id": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "model_cache_relative_path": MODEL_RELATIVE.as_posix(),
            "quantization": "ONNX_RUNTIME_DYNAMIC_QINT8_PER_CHANNEL",
            "quantized_sha256": digest(self.model),
            "original_bytes": 1000,
            "quantized_bytes": self.model.stat().st_size,
            "size_ratio": self.model.stat().st_size / 1000,
            "embedding_dimension": 384,
            "mean_vector_cosine": 0.998,
            "minimum_vector_cosine": 0.990,
            "retrieval_top1_agreement": 1.0,
            "corpus_document_count": 10,
            "query_count": 10,
            "thresholds": {
                "minimum_mean_vector_cosine": 0.995,
                "minimum_vector_cosine": 0.985,
                "required_retrieval_top1_agreement": 1.0,
                "maximum_model_size_ratio": 0.60,
            },
            "retrieval_decisions": [{"query_index": i, "top1_match": True} for i in range(10)],
            "onnx_validation": {
                "checker_status": "KNOWN_ONNX_SCHEMA_REGISTRY_GAP_LAYER_NORMALIZATION_OPSET11",
                "onnxruntime_load_status": "PASS",
                "int8_initializer_count": 24,
                "quantized_operator_counts": {"MatMulInteger": 24},
            },
        }
        self.write_receipt()
        self.patches = [
            mock.patch.object(target, "OVERLAY", self.overlay),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    def test_measured_int8_receipt_passes_all_quality_and_size_gates(self):
        result = target.verify_e04_quantization_receipt()
        self.assertEqual("PASS_E04_INT8_QUALITY_GATE", result["status"])
        self.assertEqual(digest(self.model), result["model_sha256"])

    def test_missing_retrieval_decision_is_denied(self):
        self.receipt["retrieval_decisions"] = self.receipt["retrieval_decisions"][:-1]
        self.write_receipt()
        with self.assertRaises(target.TargetGateError):
            target.verify_e04_quantization_receipt()

    def test_size_ratio_regression_is_denied(self):
        self.receipt["size_ratio"] = 0.80
        self.receipt["quantized_bytes"] = 800
        self.receipt["original_bytes"] = 1000
        self.write_receipt()
        with self.assertRaises(target.TargetGateError):
            target.verify_e04_quantization_receipt()

    def test_unknown_checker_status_is_denied(self):
        self.receipt["onnx_validation"]["checker_status"] = "SKIPPED"
        self.write_receipt()
        with self.assertRaises(target.TargetGateError):
            target.verify_e04_quantization_receipt()

    def test_quantized_model_digest_mismatch_is_denied(self):
        self.model.write_bytes(b"tampered INT8 model")
        with self.assertRaises(target.TargetGateError):
            target.verify_e04_quantization_receipt()


if __name__ == "__main__":
    unittest.main(verbosity=2)
