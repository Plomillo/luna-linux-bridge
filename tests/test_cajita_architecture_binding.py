from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
RUNTIME = REPOSITORY / "cajita-luna-runtime"
sys.path.insert(0, str(REPOSITORY / "tools"))
sys.path.insert(0, str(RUNTIME))

import cajita_architecture_binding as binding
import cajita_tokenizer_materializer as tokenizer_materializer


class ArchitectureBindingLogicalTokenizerTreeTests(unittest.TestCase):
    def test_target_descriptor_uses_source_tokenizer_identity_when_only_gzip_is_packed(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            module = runtime / "1. Cerebro"
            module.mkdir()
            tokenizer_bytes = json.dumps(
                {"version": "test-1", "tokens": [f"token-{i:05d}" for i in range(12000)]},
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
            config_bytes = b'{"model_type":"test"}\n'
            (module / "tokenizer.json").write_bytes(tokenizer_bytes)
            (module / "config.json").write_bytes(config_bytes)
            tokenizer_rel = (module.relative_to(runtime) / "tokenizer.json").as_posix()
            manifest = tokenizer_materializer.prepare_compressed_tokenizers(runtime, (tokenizer_rel,))
            entry = manifest["entries"][0]
            self.assertTrue(entry["packed"])
            self.assertEqual(entry["source_bytes"], len(tokenizer_bytes))
            self.assertNotEqual(entry["source_bytes"], entry["compressed_bytes"])

            # Simulate the compact distribution: raw tokenizer JSON is absent,
            # while the deterministic gzip and source-bound manifest remain.
            (module / "tokenizer.json").unlink()
            rows = binding._rows(module, runtime)
            indexed = {row["path"]: row for row in rows}
            self.assertIn("tokenizer.json", indexed)
            self.assertNotIn("tokenizer.json.gz", indexed)
            self.assertEqual(indexed["tokenizer.json"]["bytes"], len(tokenizer_bytes))
            self.assertEqual(indexed["tokenizer.json"]["sha256"], hashlib.sha256(tokenizer_bytes).hexdigest())
            self.assertEqual(indexed["config.json"]["bytes"], len(config_bytes))
            self.assertEqual(sum(row["bytes"] for row in rows), len(tokenizer_bytes) + len(config_bytes))

    def test_target_descriptor_uses_logical_tree_when_source_and_gzip_coexist(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            module = runtime / "3. Transcripción"
            module.mkdir()
            tokenizer_bytes = b'{"version":"source","tokens":["hola","mundo"]}\n'
            (module / "tokenizer.json").write_bytes(tokenizer_bytes)
            tokenizer_rel = (module.relative_to(runtime) / "tokenizer.json").as_posix()
            tokenizer_materializer.prepare_compressed_tokenizers(runtime, (tokenizer_rel,))
            rows = binding._rows(module, runtime)
            indexed = {row["path"]: row for row in rows}
            self.assertIn("tokenizer.json", indexed)
            self.assertNotIn("tokenizer.json.gz", indexed)
            self.assertEqual(indexed["tokenizer.json"]["sha256"], hashlib.sha256(tokenizer_bytes).hexdigest())
            self.assertEqual(sum(row["bytes"] for row in rows), len(tokenizer_bytes))


class CanonicalConsumerAdapterRegistrationTests(unittest.TestCase):
    def test_registers_only_hash_pinned_synthetic_adapter_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            module = runtime / "1. Cerebro"
            module.mkdir()
            entry = module / "adapter_entry.py"
            entry.write_text("# exact entrypoint\n", encoding="utf-8")
            weight = module / "model.safetensors"
            weight_bytes = b"test-weight-payload"
            weight.write_bytes(weight_bytes)
            weight_manifest = {
                "schema": "CAJITA_SIX_DOMAIN_WEIGHT_MANIFEST/1.0",
                "candidate_id": "CAJITA_TEST_CANDIDATE",
                "artifacts": [{
                    "path": "1. Cerebro/model.safetensors",
                    "bytes": len(weight_bytes),
                    "sha256": hashlib.sha256(weight_bytes).hexdigest(),
                }],
            }
            weight_root = runtime / "CAJITA_RUNTIME_V1"
            weight_root.mkdir()
            encoded_weight_manifest = (json.dumps(weight_manifest, sort_keys=True) + "\n").encode("utf-8")
            (weight_root / "weights_manifest.json").write_bytes(encoded_weight_manifest)
            manifest_sha = hashlib.sha256(encoded_weight_manifest).hexdigest()
            adapter_source = (
                "MANIFEST_SHA = " + repr(manifest_sha) + "\n"
                "CANDIDATE_ID = 'CAJITA_TEST_CANDIDATE'\n"
                "ADAPTERS = {'D01_CEREBRO': {'target': 'D01_CEREBRO_ROOT', "
                "'id': 'CAJITA_TEST_TEXT/1.0', 'op': 'generate_text', "
                "'entry': '1. Cerebro/adapter_entry.py', 'module': '1. Cerebro', "
                "'weight': '1. Cerebro/model.safetensors', "
                "'sha': " + repr(hashlib.sha256(weight_bytes).hexdigest()) + ", "
                "'bytes': " + str(len(weight_bytes)) + "}}\n"
            )
            (runtime / "cajita_task_adapters.py").write_text(adapter_source, encoding="utf-8")
            target = {"id": "D01_CEREBRO_ROOT", "domain_id": "D01_CEREBRO", "path": "1. Cerebro"}

            registered = binding._registered_consumer_adapters(runtime, [target])
            row = registered["D01_CEREBRO_ROOT"]
            self.assertEqual(row["status"], "REGISTERED_SYNTHETIC_SCOPE_ONLY")
            self.assertEqual(row["adapter_id"], "CAJITA_TEST_TEXT/1.0")
            self.assertEqual(row["weight_sha256"], hashlib.sha256(weight_bytes).hexdigest())
            self.assertEqual(row["native_smoke"], "REQUIRED")
            self.assertEqual(row["reference_quality_equivalence"], "NOT_ESTABLISHED")
            self.assertEqual(row["certification"], "NOT_GRANTED")

    def test_adapter_registry_must_bind_to_a_canonical_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            module = runtime / "1. Cerebro"
            module.mkdir()
            (module / "adapter_entry.py").write_text("# entry\n", encoding="utf-8")
            weight_bytes = b"weight"
            (module / "model.safetensors").write_bytes(weight_bytes)
            weight_manifest = {
                "schema": "CAJITA_SIX_DOMAIN_WEIGHT_MANIFEST/1.0",
                "candidate_id": "CAJITA_TEST_CANDIDATE",
                "artifacts": [{
                    "path": "1. Cerebro/model.safetensors",
                    "bytes": len(weight_bytes),
                    "sha256": hashlib.sha256(weight_bytes).hexdigest(),
                }],
            }
            weight_root = runtime / "CAJITA_RUNTIME_V1"
            weight_root.mkdir()
            encoded = (json.dumps(weight_manifest, sort_keys=True) + "\n").encode("utf-8")
            (weight_root / "weights_manifest.json").write_bytes(encoded)
            adapter_source = (
                "MANIFEST_SHA = " + repr(hashlib.sha256(encoded).hexdigest()) + "\n"
                "CANDIDATE_ID = 'CAJITA_TEST_CANDIDATE'\n"
                "ADAPTERS = {'D01_CEREBRO': {'target': 'D99_UNKNOWN', 'id': 'A/1.0', "
                "'op': 'generate_text', 'entry': '1. Cerebro/adapter_entry.py', "
                "'module': '1. Cerebro', 'weight': '1. Cerebro/model.safetensors', "
                "'sha': " + repr(hashlib.sha256(weight_bytes).hexdigest()) + ", "
                "'bytes': " + str(len(weight_bytes)) + "}}\n"
            )
            (runtime / "cajita_task_adapters.py").write_text(adapter_source, encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "TASK_ADAPTER_CANONICAL_TARGET_MISMATCH"):
                binding._registered_consumer_adapters(
                    runtime, [{"id": "D01_CEREBRO_ROOT", "domain_id": "D01_CEREBRO", "path": "1. Cerebro"}]
                )


class CanonicalRuntimeEngineScopeRegistrationTests(unittest.TestCase):
    def test_registers_only_hash_bound_runtime_scope_without_promoting_task_adapter(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            module = runtime / "6. Sistema Inteligente" / "Consola"
            module.mkdir(parents=True)
            qjs = module / "qjs"
            qjs.write_bytes(b"fixture-quickjs-binary")
            adapter_source = (
                "TARGET_ADAPTERS = {"
                "'D06_CONSOLA': {"
                "'domain_id':'D06_SISTEMA_INTELIGENTE',"
                "'adapter_id':'CAJITA_QUICKJS_KNOWN_ANSWER/1.0',"
                "'operation':'evaluate_fixed_javascript_fixture',"
                "'module':'6. Sistema Inteligente/Consola',"
                "'entry':'qjs','required_files':['qjs'],"
                "'engine':'QUICKJS','scope':'FIXED_EXPRESSION_KNOWN_ANSWER_NO_USER_CODE'"
                ""}\n"
            )
            (runtime / "cajita_target_adapters.py").write_text(adapter_source, encoding="utf-8")
            targets = [{
                "id": "D06_CONSOLA",
                "domain_id": "D06_SISTEMA_INTELIGENTE",
                "path": "6. Sistema Inteligente/Consola",
            }]

            registered = binding._registered_runtime_engine_scopes(runtime, targets)
            row = registered["D06_CONSOLA"]
            self.assertEqual(row["status"], "REGISTERED_RUNTIME_SMOKE_SCOPE_ONLY")
            self.assertEqual(row["adapter_id"], "CAJITA_QUICKJS_KNOWN_ANSWER/1.0")
            self.assertEqual(row["consumer_task_adapter_completion"], "NOT_ESTABLISHED")
            self.assertEqual(row["reference_quality_equivalence"], "NOT_ESTABLISHED")
            self.assertEqual(row["certification"], "NOT_GRANTED")
            self.assertEqual(row["source_files"][0]["path"], "6. Sistema Inteligente/Consola/qjs")
            self.assertEqual(row["source_files"][0]["sha256"], hashlib.sha256(qjs.read_bytes()).hexdigest())

    def test_runtime_scope_rejects_undeclared_required_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            module = runtime / "6. Sistema Inteligente" / "Consola"
            module.mkdir(parents=True)
            (module / "qjs").write_bytes(b"fixture-quickjs-binary")
            adapter_source = (
                "TARGET_ADAPTERS = {"
                "'D06_CONSOLA': {"
                "'domain_id':'D06_SISTEMA_INTELIGENTE',"
                "'adapter_id':'CAJITA_QUICKJS_KNOWN_ANSWER/1.0',"
                "'operation':'evaluate_fixed_javascript_fixture',"
                "'module':'6. Sistema Inteligente/Consola',"
                "'entry':'qjs','required_files':['qjs','missing-file'],"
                "'engine':'QUICKJS','scope':'FIXED_EXPRESSION_KNOWN_ANSWER_NO_USER_CODE'"
                ""}\n"
            )
            (runtime / "cajita_target_adapters.py").write_text(adapter_source, encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "RUNTIME_TARGET_ADAPTER_REQUIRED_FILE_MISSING_OR_UNSAFE"):
                binding._registered_runtime_engine_scopes(runtime, [{
                    "id": "D06_CONSOLA",
                    "domain_id": "D06_SISTEMA_INTELIGENTE",
                    "path": "6. Sistema Inteligente/Consola",
                }])


if __name__ == "__main__":
    unittest.main(verbosity=2)
