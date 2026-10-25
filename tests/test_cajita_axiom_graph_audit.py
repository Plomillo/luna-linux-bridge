from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cajita_externalized_packaging import materialize_registered_asset, prepare_source_materializations
from cajita_axiom_graph_audit import (
    END_HEADING,
    HEADING,
    legacy_census,
    expected_block,
    parse_legacy,
    parse_materialized,
    validate_materialized,
    canonical_target_adapter_summary,
)


def row(axiom_id: str, class_name: str, first_text: str, block: int, trace_id: str | None = None) -> str:
    trace = trace_id or f"TRACE-V11-B{block:03d}::{axiom_id}"
    return "  " + axiom_id.ljust(18) + class_name.ljust(18) + first_text.ljust(21) + trace


class AxiomGraphAuditTests(unittest.TestCase):
    def test_materialized_rows_preserve_content_trace_and_line_provenance(self):
        text = "\n".join([
            HEADING,
            row("AX02415", "IDENTITY", "The canonical", 15),
            " " * 38 + "subject of".ljust(21),
            " " * 38 + "Criminology SHALL".ljust(21),
            " " * 38 + "remain bounded.".ljust(21),
            "",
            row("AX02416", "IDENTITY", "Claims attributed", 15),
            " " * 38 + "to Criminology".ljust(21),
            END_HEADING,
        ])
        records = parse_materialized(text)
        self.assertEqual([r["id"] for r in records], ["AX02415", "AX02416"])
        self.assertEqual(records[0]["block"], "B015")
        self.assertEqual(records[0]["trace"], "TRACE-V11-B015::AX02415")
        self.assertIn("Criminology SHALL", records[0]["text"])
        self.assertGreater(records[0]["line"], 1)

    def test_mismatched_trace_fails_closed(self):
        text = "\n".join([
            HEADING,
            row("AX02415", "IDENTITY", "The canonical", 15, "TRACE-V11-B015::AX02416"),
            END_HEADING,
        ])
        with self.assertRaisesRegex(ValueError, "AXIOM_ROW_TRACE_MISMATCH"):
            parse_materialized(text)

    def test_legacy_census_reports_duplicates_without_rewriting_source(self):
        rows = parse_legacy("id: AX0001\nid: AX0003\nid: AX0003\n")
        result = legacy_census(rows)
        self.assertEqual(result["definition_records"], 3)
        self.assertEqual(result["distinct_numeric_ids"], 2)
        self.assertEqual(result["repeated_definition_records"], 1)
        self.assertEqual(result["numeric_gaps_1_2414"], 2412)

    def test_block_allocation_boundaries_are_deterministic(self):
        self.assertEqual(expected_block(2415), 15)
        self.assertEqual(expected_block(5774), 54)
        self.assertEqual(expected_block(5775), 55)
        self.assertEqual(expected_block(12414), 134)
        with self.assertRaisesRegex(ValueError, "AXIOM_OUTSIDE_MATERIALIZED_RANGE"):
            expected_block(2414)

    def test_full_materialized_range_has_10000_unique_ids_and_120_blocks(self):
        records = []
        for n in range(2415, 12415):
            block = expected_block(n)
            aid = f"AX{n:05d}"
            records.append({"id": aid, "numeric": n, "class": "IDENTITY",
                            "text": f"proposition {n}", "trace": f"TRACE-V11-B{block:03d}::{aid}",
                            "block": f"B{block:03d}", "line": n})
        result = validate_materialized(records)
        self.assertEqual(result["record_count"], 10000)
        self.assertEqual(result["block_count"], 120)
        self.assertTrue(result["contiguous"])
        self.assertEqual(result["block_counts"]["B015"], 84)
        self.assertEqual(result["block_counts"]["B134"], 83)


class CanonicalTargetAdapterSummaryTests(unittest.TestCase):
    def _write_registry(self, runtime: Path):
        registry = {
            "schema": "CAJITA_MODULE_REGISTRY/1.0",
            "canonical_target_module_count": 2,
            "target_modules": [
                {
                    "target_id": "D01_CEREBRO_ROOT",
                    "domain_id": "D01_CEREBRO",
                    "consumer_adapter": "CAJITA_CEREBRO_TEXT_GENERATION/1.0",
                    "consumer_adapter_registration": {
                        "status": "REGISTERED_SYNTHETIC_SCOPE_ONLY",
                        "certification": "NOT_GRANTED",
                        "reference_quality_equivalence": "NOT_ESTABLISHED",
                    },
                },
                {
                    "target_id": "D02_ORQUESTADOR",
                    "domain_id": "D02_ORQUESTACION",
                    "consumer_adapter": "NOT_REGISTERED_FOR_ALL_TASKS",
                    "consumer_adapter_registration": {"status": "NOT_REGISTERED", "certification": "NOT_GRANTED"},
                    "runtime_engine_scope_registration": {
                        "status": "REGISTERED_RUNTIME_SMOKE_SCOPE_ONLY",
                        "target_id": "D02_ORQUESTADOR",
                        "adapter_id": "CAJITA_CLI_REGISTRY_SELFTEST/1.0",
                        "operation": "audit_cli_registry",
                        "certification": "NOT_GRANTED",
                        "reference_quality_equivalence": "NOT_ESTABLISHED",
                        "consumer_task_adapter_completion": "NOT_ESTABLISHED",
                        "source_files": [{"path": "2. Orquestación/Orquestador/CLIs/cli_registry.py",
                                          "bytes": 1, "sha256": "a" * 64}],
                    },
                },
            ],
        }
        (runtime / "module_registry.json").write_text(json.dumps(registry), encoding="utf-8")

    def test_reports_five_style_partial_registration_without_promoting_certification(self):
        with tempfile.TemporaryDirectory() as temp_name:
            runtime = Path(temp_name) / "runtime"
            runtime.mkdir()
            self._write_registry(runtime)
            task = {
                "task_results": [{
                    "domain_id": "D01_CEREBRO",
                    "target_id": "D01_CEREBRO_ROOT",
                    "status": "PASS_FUNCTIONAL_EXECUTION",
                    "exit_code": 0,
                }],
                "target_engine_results": [{
                    "domain_id": "D02_ORQUESTACION",
                    "target_id": "D02_ORQUESTADOR",
                    "status": "PASS_TARGET_ENGINE_EXECUTION",
                    "exit_code": 0,
                }]
            }
            summary = canonical_target_adapter_summary(runtime, task)
            self.assertEqual(summary["canonical_target_count"], 2)
            self.assertEqual(summary["synthetic_scope_registered_target_count"], 1)
            self.assertEqual(summary["unregistered_target_count"], 1)
            self.assertEqual(summary["registered_target_ids"], ["D01_CEREBRO_ROOT"])
            self.assertEqual(summary["unregistered_target_ids"], ["D02_ORQUESTADOR"])
            self.assertEqual(summary["runtime_engine_smoke_scope_registered_target_count"], 1)
            self.assertEqual(summary["runtime_engine_smoke_scope_passed_target_count"], 1)
            self.assertEqual(summary["runtime_engine_smoke_scope_target_ids"], ["D02_ORQUESTADOR"])
            self.assertEqual(summary["unregistered_task_adapter_requirement_count"], 1)
            self.assertEqual(summary["all_21_target_task_adapters"], "NOT_ESTABLISHED")
            self.assertEqual(summary["reference_quality_equivalence"], "NOT_ESTABLISHED")
            self.assertEqual(summary["certification"], "NOT_GRANTED")

    def test_g23_reports_g24_runtime_engine_evidence_as_pending_without_promoting_task_adapter(self):
        with tempfile.TemporaryDirectory() as temp_name:
            runtime = Path(temp_name) / "runtime"
            runtime.mkdir()
            self._write_registry(runtime)
            task = {"task_results": [{
                "domain_id": "D01_CEREBRO",
                "target_id": "D01_CEREBRO_ROOT",
                "status": "PASS_FUNCTIONAL_EXECUTION",
                "exit_code": 0,
            }], "target_engine_results": []}
            summary = canonical_target_adapter_summary(runtime, task)
            self.assertEqual(summary["runtime_engine_smoke_scope_validation_status"], "PENDING_G24_TARGET_ENGINE_EVIDENCE")
            self.assertEqual(summary["runtime_engine_smoke_scope_missing_target_ids"], ["D02_ORQUESTADOR"])
            self.assertEqual(summary["unregistered_target_count"], 1)
            self.assertEqual(summary["all_21_target_task_adapters"], "NOT_ESTABLISHED")
            self.assertEqual(summary["certification"], "NOT_GRANTED")

    def test_registered_adapter_requires_source_bound_passing_task_evidence(self):
        with tempfile.TemporaryDirectory() as temp_name:
            runtime = Path(temp_name) / "runtime"
            runtime.mkdir()
            self._write_registry(runtime)
            with self.assertRaisesRegex(ValueError, "REGISTERED_SYNTHETIC_ADAPTER_WITHOUT_CURRENT_E2E_EVIDENCE"):
                canonical_target_adapter_summary(runtime, {"task_results": []})


class ExternalizedJenaInputTests(unittest.TestCase):
    def _fixture(self, root: Path, declared_sha: str | None = None):
        root.mkdir(parents=True, exist_ok=True)
        payload = b"test-container-bytes-not-a-real-archive"
        digest = hashlib.sha256(payload).hexdigest()
        (root / "test-jena.7z").write_bytes(payload)
        expected_sha = declared_sha or digest
        placement = {
            "assets": [{
                "id": "APACHE_JENA_6_2_0",
                "expanded_path": "cajita-luna-runtime/APACHE_JENA_6_2_0",
                "expanded_bytes": 123,
                "expanded_file_count": 7,
                "expanded_tree_sha256": "a" * 64,
                "container_sha256": expected_sha,
                "container_size_bytes": len(payload),
                "compact_runtime_container": {
                    "path": "cajita-luna-runtime/test-jena.7z",
                    "sha256": expected_sha,
                    "size_bytes": len(payload),
                },
            }]
        }
        (root / "EXTERNALIZED_ASSET_PLACEMENT.json").write_text(
            json.dumps(placement), encoding="utf-8"
        )
        return {"bytes": 123, "file_count": 7, "tree_sha256": "a" * 64}, digest

    def test_registered_jena_container_is_hash_bound_before_extraction(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "runtime"
            expected_tree, digest = self._fixture(root)
            destination = Path(temp_name) / "extracted" / "jena"
            with patch("cajita_externalized_packaging._extract_raw_tree", return_value=expected_tree) as extract:
                result = materialize_registered_asset(root, "APACHE_JENA_6_2_0", destination)
            self.assertEqual(result["status"], "PASS_REGISTERED_CONTAINER_RECONSTRUCTION")
            self.assertEqual(result["container_sha256"], digest)
            self.assertEqual(result["expanded_tree_sha256"], expected_tree["tree_sha256"])
            self.assertEqual(extract.call_count, 1)

    def test_tampered_registered_jena_container_fails_before_extraction(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "runtime"
            self._fixture(root, declared_sha="0" * 64)
            destination = Path(temp_name) / "extracted" / "jena"
            with patch("cajita_externalized_packaging._extract_raw_tree") as extract:
                with self.assertRaisesRegex(RuntimeError, "EXTERNALIZED_CONTAINER_IDENTITY_MISMATCH"):
                    materialize_registered_asset(root, "APACHE_JENA_6_2_0", destination)
            extract.assert_not_called()


class SourceMaterializationPreparationTests(unittest.TestCase):
    def test_compact_checkout_reconstructs_only_registered_trees_and_restores_descriptors(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "runtime"
            root.mkdir()
            source_rows = []
            placement_assets = []
            distribution_rows = []
            expected = {}
            for index in range(10):
                asset_id = f"ASSET_{index:02d}"
                expanded_rel = f"domain/{asset_id}"
                expanded_path = "cajita-luna-runtime/" + expanded_rel
                container_path = "cajita-luna-runtime/containers/" + asset_id + ".7z"
                tree = {"bytes": index + 10, "file_count": 1, "tree_sha256": f"{index + 1:064x}"}
                descriptor = {
                    "schema": "CAJITA_MATERIALIZED_MODULE/1.0",
                    "canonical_asset_id": asset_id,
                    "module_key": expanded_rel,
                    "materialization": {"status": "PASS", **tree},
                    "source_archives": [{"path": container_path, "sha256": f"{index + 101:064x}", "bytes": index + 1000}],
                    "certification": "NOT_GRANTED",
                }
                raw = json.dumps(descriptor, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
                descriptor_sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                container_sha = descriptor["source_archives"][0]["sha256"]
                container_bytes = descriptor["source_archives"][0]["bytes"]
                placement_assets.append({
                    "id": asset_id,
                    "expanded_path": expanded_path,
                    "expanded_bytes": tree["bytes"],
                    "expanded_file_count": tree["file_count"],
                    "expanded_tree_sha256": tree["tree_sha256"],
                    "placed_path": container_path,
                    "container_sha256": container_sha,
                    "container_size_bytes": container_bytes,
                    "compact_runtime_container": {
                        "path": container_path,
                        "sha256": container_sha,
                        "size_bytes": container_bytes,
                    },
                    "factory_reconciliation": {"module_manifest_sha256": descriptor_sha},
                })
                source_rows.append({
                    "module_key": expanded_rel,
                    "path": expanded_rel,
                    "bytes": tree["bytes"],
                    "file_count": tree["file_count"],
                    "tree_sha256": tree["tree_sha256"],
                    "manifest_sha256": descriptor_sha,
                })
                distribution_rows.append({
                    "canonical_asset_id": asset_id,
                    "module_key": expanded_rel,
                    "path": expanded_rel,
                    "container_path": container_path.removeprefix("cajita-luna-runtime/"),
                    "container_sha256": container_sha,
                    "container_bytes": container_bytes,
                    **tree,
                    "materialization": {"status": "PACKED_NOT_EXPANDED", **tree},
                    "manifest_sha256": descriptor_sha,
                    "module_descriptor_raw": raw,
                    "module_descriptor_sha256": descriptor_sha,
                    "nested_modules": [],
                })
                expected[asset_id] = (expanded_rel, tree, raw)

            (root / "module_registry.json").write_text(json.dumps({
                "schema": "CAJITA_MODULE_REGISTRY/1.0",
                "materialized_module_count": 10,
                "modules": source_rows,
            }), encoding="utf-8")
            (root / "EXTERNALIZED_ASSET_PLACEMENT.json").write_text(json.dumps({
                "assets": placement_assets,
            }), encoding="utf-8")
            (root / "CAJITA_DISTRIBUTION_MODULE_REGISTRY.json").write_text(json.dumps({
                "schema": "CAJITA_MODULE_REGISTRY/1.0",
                "externalized_modules": distribution_rows,
            }), encoding="utf-8")

            def reconstruct(_root, asset_id, destination):
                rel, tree, _raw = expected[asset_id]
                Path(destination).mkdir(parents=True, exist_ok=True)
                return {
                    "id": asset_id,
                    "status": "PASS_REGISTERED_CONTAINER_RECONSTRUCTION",
                    "expanded_bytes": tree["bytes"],
                    "expanded_file_count": tree["file_count"],
                    "expanded_tree_sha256": tree["tree_sha256"],
                }

            with patch("cajita_externalized_packaging.materialize_registered_asset", side_effect=reconstruct) as extract:
                result = prepare_source_materializations(root)

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["asset_count"], 10)
            self.assertEqual(result["reconstructed_count"], 10)
            self.assertEqual(extract.call_count, 10)
            for asset_id, (rel, _tree, raw) in expected.items():
                self.assertEqual((root / rel / "CAJITA_MODULE.json").read_text(encoding="utf-8"), raw)

    def test_source_materialization_refuses_distribution_descriptor_hash_drift(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name) / "runtime"
            root.mkdir()
            payload = b"{}"
            (root / "module_registry.json").write_text(json.dumps({
                "schema": "CAJITA_MODULE_REGISTRY/1.0",
                "modules": [],
            }), encoding="utf-8")
            (root / "EXTERNALIZED_ASSET_PLACEMENT.json").write_text(json.dumps({
                "assets": [{"id": f"ASSET_{i:02d}"} for i in range(10)],
            }), encoding="utf-8")
            (root / "CAJITA_DISTRIBUTION_MODULE_REGISTRY.json").write_text(json.dumps({
                "schema": "CAJITA_MODULE_REGISTRY/1.0",
                "externalized_modules": [],
            }), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "DISTRIBUTION_EXTERNALIZED_MODULE_SET_INVALID"):
                prepare_source_materializations(root)




if __name__ == "__main__":
    unittest.main()
