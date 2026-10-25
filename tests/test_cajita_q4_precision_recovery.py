from __future__ import annotations

import json
import unittest

from cajita_q4_precision_recovery import (
    Q4_SCHEMA,
    RESTORE_IDS,
    UNCHANGED_IDS,
    parse_lfs_pointer,
    resolve_historical_weight_blob,
    validate_manifest_transition,
    validate_q4_sidecar,
)


def _manifest():
    rows = [
        {"id": "W01", "path": "1. Cerebro/model.safetensors", "domain_id": "1_CEREBRO", "label": "GPT-OSS compactado", "bytes": 40, "sha256": "a" * 64},
        {"id": "W02", "path": "3. Transcripción/model.safetensors", "domain_id": "3_TRANSCRIPCION", "label": "Whisper compactado", "bytes": 10, "sha256": "b" * 64},
        {"id": "W03", "path": "4. Traductor Inteligente/Traducción general/model.safetensors", "domain_id": "4_TRADUCTOR_INTELIGENTE", "label": "SeamlessM4T v2 compactado", "bytes": 11, "sha256": "c" * 64},
        {"id": "W04", "path": "5. Inteligencia documental/weights.bin", "domain_id": "5_INTELIGENCIA_DOCUMENTAL", "label": "Granite Docling cuantizado", "bytes": 13, "sha256": "d" * 64},
        {"id": "W05", "path": "6. Sistema Inteligente/Análisis Avanzado/model.safetensors", "domain_id": "6_SISTEMA_INTELIGENTE", "label": "Qwen3 compactado", "bytes": 15, "sha256": "e" * 64},
        {"id": "W06", "path": "6. Sistema Inteligente/Anti-Alucinaciones/model.onnx", "domain_id": "6_SISTEMA_INTELIGENTE", "label": "Anti-Alucinaciones ONNX", "bytes": 110, "sha256": "f" * 64},
    ]
    return {"schema": "CAJITA_SIX_DOMAIN_WEIGHT_MANIFEST/1.0",
            "candidate_id": "CAJITA_LUNA_RUNTIME_V9_20261023",
            "artifact_count": 6, "artifacts": rows}


class Q4PrecisionRecoveryTests(unittest.TestCase):
    def test_lfs_pointer_parser_accepts_only_sha256_pointer(self):
        data = b"version https://git-lfs.github.com/spec/v1\n" + b"oid sha256:" + b"a" * 64 + b"\nsize 12345\n"
        self.assertEqual(parse_lfs_pointer(data), {"sha256": "a" * 64, "bytes": 12345})
        with self.assertRaisesRegex(ValueError, "NOT_A_GIT_LFS_POINTER"):
            parse_lfs_pointer(b"arbitrary model bytes")

    def test_historical_blob_accepts_exact_raw_payload_and_rejects_tampering(self):
        import hashlib
        import tempfile
        from pathlib import Path
        payload = b"same-candidate-pinned-model-bytes"
        sha = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            resolved = resolve_historical_weight_blob(payload, sha, len(payload), tmp)
        self.assertEqual(resolved["source_kind"], "RAW_GIT_SHOW_PAYLOAD_SHA256_VERIFIED")
        self.assertEqual(resolved["source_bytes"], payload)
        self.assertIsNone(resolved["source_object"])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "NOT_POINTER_OR_PINNED_PAYLOAD"):
                resolve_historical_weight_blob(payload + b"tampered", sha, len(payload), tmp)

    def test_manifest_transition_preserves_candidate_paths_and_unrelated_weights(self):
        current = _manifest()
        historical = json.loads(json.dumps(current))
        for row in historical["artifacts"]:
            if row["id"] in RESTORE_IDS:
                row["bytes"] += 100
                row["sha256"] = row["sha256"][0] * 64
        rows = validate_manifest_transition(current, historical)
        self.assertEqual(set(rows), set(RESTORE_IDS) | set(UNCHANGED_IDS))
        self.assertEqual(rows["W04"]["sha256"], current["artifacts"][3]["sha256"])
        self.assertEqual(rows["W06"]["sha256"], current["artifacts"][5]["sha256"])

    def test_manifest_transition_rejects_model_identity_or_path_changes(self):
        current = _manifest()
        historical = json.loads(json.dumps(current))
        historical["artifacts"][0]["id"] = "W99"
        with self.assertRaisesRegex(RuntimeError, "CANONICAL_WEIGHT_ARTIFACT_ID_SET_MISMATCH"):
            validate_manifest_transition(current, historical)
        historical = json.loads(json.dumps(current))
        historical["artifacts"][0]["path"] = "1. Cerebro/other_model.safetensors"
        with self.assertRaisesRegex(RuntimeError, "CANONICAL_WEIGHT_BINDING_DRIFT"):
            validate_manifest_transition(current, historical)

    def test_manifest_transition_rejects_change_to_w04_or_w06(self):
        current = _manifest()
        historical = json.loads(json.dumps(current))
        for row in historical["artifacts"]:
            if row["id"] in RESTORE_IDS:
                row["bytes"] += 100
        historical["artifacts"][3]["bytes"] += 1
        with self.assertRaisesRegex(RuntimeError, "UNRELATED_MODEL_WEIGHT_MUTATION"):
            validate_manifest_transition(current, historical)

    def test_q4_sidecar_rejects_q2_encoding_or_wrong_weight_hash(self):
        sidecar = {"schema": Q4_SCHEMA, "candidate_sha256": "a" * 64,
                   "tensors": [{"name": "weight_u", "shape": [10, 2], "numel": 20}]}
        self.assertEqual(len(validate_q4_sidecar(json.dumps(sidecar).encode(), "a" * 64)["tensors"]), 1)
        sidecar["tensors"][0]["encoding"] = "UNSIGNED_INT2_ASYMMETRIC"
        with self.assertRaisesRegex(RuntimeError, "Q2_OR_UNKNOWN_ENCODING_IN_Q4_SIDECAR"):
            validate_q4_sidecar(json.dumps(sidecar).encode(), "a" * 64)
        sidecar["tensors"][0].pop("encoding")
        with self.assertRaisesRegex(RuntimeError, "IDENTITY_MISMATCH"):
            validate_q4_sidecar(json.dumps(sidecar).encode(), "b" * 64)


if __name__ == "__main__":
    unittest.main()
