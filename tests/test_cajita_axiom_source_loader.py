from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from cajita_axiom_source_loader import verify_binding

ENGINES = ["E03", "E04", "E05", "E06", "E07", "E08", "E09", "E12", "E13", "E14", "E15"]
BLOCK_IDS = [f"B{i}" for i in range(1, 135)]
MULTI_PATH = "2. Orquestación/Multi + Interdisciplinar"

def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _write_fixture(tmp: str, *, source_doc: bytes = b"protected architecture\nruntime appendix\n") -> tuple[Path, Path]:
    root = Path(tmp) / "install"
    multi = root / "cajita-luna-runtime" / MULTI_PATH
    multi.mkdir(parents=True)
    runtime = root / "cajita-luna-runtime"
    doc = root / "Louksna1.md"
    doc.write_bytes(source_doc)
    (runtime / "command_subdomain_routing.json").write_text(json.dumps({
        "schema": "CAJITA_COMMAND_SUBDOMAIN_ROUTING/1.0",
        "targets": [{
            "id": "D02_MULTI_INTERDISCIPLINAR",
            "domain_id": "D02_ORQUESTACION",
            "path": MULTI_PATH,
            "engine_ids": ENGINES,
            "support_assets": ["APACHE_JENA_6_2_0"]
        }]
    }, indent=2) + "\n", encoding="utf-8")
    protected = b"protected architecture\n"
    graph = {
        "schema": "LOUKSNA_BLOCK_ENGINE_BINDING/1.0",
        "status": "DECLARED_STRUCTURAL_ROUTING_ONLY",
        "scope": "CANONICAL_IDENTIFIER_ROUTING_NOT_SEMANTIC_PROOF",
        "source": {
            "document_path": "Louksna1.md", "document_sha256": _sha(source_doc),
            "protected_architecture_path": "LOUKSNAMEJORADA.md",
            "protected_architecture_sha256": _sha(protected), "protected_architecture_bytes": len(protected),
            "provenance_mode": "EXACT_DOCUMENT_AND_PROTECTED_PREFIX_HASHES"
        },
        "block_inventory": {"range": "B1-B134", "count": 134, "ids": BLOCK_IDS, "mutation_allowed": False},
        "target": {"id": "D02_MULTI_INTERDISCIPLINAR", "domain_id": "D02_ORQUESTACION",
                   "path": MULTI_PATH, "engine_ids": ENGINES},
        "block_routes": [
            {"from_block_id": bid, "relation": "routes_to_interdisciplinary_target",
             "to_target_id": "D02_MULTI_INTERDISCIPLINAR",
             "source_scope": "CANONICAL_BLOCK_RANGE_DECLARATION_ONLY",
             "provenance_sha256": _sha(source_doc)} for bid in BLOCK_IDS
        ],
        "engine_routes": [
            {"from_target_id": "D02_MULTI_INTERDISCIPLINAR", "relation": "uses_canonical_engine", "to_engine_id": eid}
            for eid in ENGINES
        ],
        "invariants": {"canonical_block_identity_mutation": False, "canonical_engine_reassignment": False,
                       "synthetic_block_ids": False, "semantic_content_reconstructed": False},
        "certification": "NOT_GRANTED"
    }
    graph_bytes = (json.dumps(graph, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    (multi / "block_engine_binding.json").write_bytes(graph_bytes)
    binding = {
        "schema": "LOUKSNA_AXIOM_MULTI_INTERDISCIPLINAR_BINDING/1.0",
        "status": "SOURCE_BOUND_BLOCK_ENGINE_GRAPH_BOUND",
        "companion_artifact": {"path_from_runtime_root": "../Louksna1.md", "bytes": len(source_doc), "sha256": _sha(source_doc)},
        "protected_architecture_prefix": {"source_path": "LOUKSNAMEJORADA.md", "bytes": len(protected),
                                          "sha256": _sha(protected), "mutation_allowed": False},
        "axiom_inventory": {"range": "AX0001-AX12414", "declared_materialized_count": 11757,
                            "declared_historical_gap_count": 657, "gap_range": "AX0001-AX2414",
                            "contiguous_range": "AX2415-AX12414",
                            "state": "PRESERVED_DECLARATION_NOT_INDEPENDENTLY_REPARSED", "mutation_allowed": False},
        "block_inventory": {"range": "B1-B134", "count": 134, "state": "PRESERVED_CANONICAL_RANGE", "mutation_allowed": False},
        "block_engine_graph": {"path_from_runtime_root": MULTI_PATH + "/block_engine_binding.json",
                               "sha256": _sha(graph_bytes), "block_count": 134,
                               "state": "DECLARED_STRUCTURAL_ROUTING_ONLY"},
        "framework_count": 18,
        "target": {"id": "D02_MULTI_INTERDISCIPLINAR", "domain_id": "D02_ORQUESTACION",
                   "path": MULTI_PATH, "engine_ids": ENGINES},
        "reader": {"relative_path": MULTI_PATH + "/cajita_axiom_source_loader.py",
                   "operation": "VERIFY_DOCUMENT_SHA256_PREFIX_AND_B1_B134_BLOCK_ENGINE_ROUTES"},
        "graph_execution": "STRUCTURAL_BLOCK_ROUTING_DECLARED_RUNTIME_VERIFICATION_REQUIRED",
        "certification": "NOT_GRANTED"
    }
    (multi / "axiom_interdisciplinary_binding.json").write_text(json.dumps(binding, indent=2) + "\n", encoding="utf-8")
    return runtime, doc

class AxiomBindingTests(unittest.TestCase):
    def test_source_prefix_and_all_134_block_routes_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, doc = _write_fixture(tmp)
            result = verify_binding(runtime, doc)
            self.assertEqual(result["status"], "PASS_SOURCE_PREFIX_VERIFIED")
            self.assertEqual(result["target"]["id"], "D02_MULTI_INTERDISCIPLINAR")
            self.assertEqual(result["semantic_graph_execution"], "PASS_STRUCTURAL_BLOCK_ROUTING_ONLY")
            graph = result["block_engine_graph"]
            self.assertEqual(graph["status"], "PASS_CANONICAL_B1_B134_ROUTING")
            self.assertEqual(graph["block_count"], 134)
            self.assertEqual(graph["first_block_id"], "B1")
            self.assertEqual(graph["last_block_id"], "B134")
            self.assertEqual(graph["route_edge_count"], 134)
            self.assertEqual(graph["engine_route_count"], 11)
            self.assertEqual(graph["engine_ids"], ENGINES)
            self.assertEqual(result["axiom_inventory"]["declared_historical_gap_count"], 657)

    def test_missing_canonical_block_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, doc = _write_fixture(tmp)
            graph_path = runtime / MULTI_PATH / "block_engine_binding.json"
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            graph["block_inventory"]["ids"] = graph["block_inventory"]["ids"][:-1]
            graph["block_routes"] = graph["block_routes"][:-1]
            raw = (json.dumps(graph, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
            graph_path.write_bytes(raw)
            binding_path = runtime / MULTI_PATH / "axiom_interdisciplinary_binding.json"
            binding = json.loads(binding_path.read_text(encoding="utf-8"))
            binding["block_engine_graph"]["sha256"] = _sha(raw)
            binding_path.write_text(json.dumps(binding, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "BLOCK_ENGINE_GRAPH_CANONICAL_RANGE_MISMATCH"):
                verify_binding(runtime, doc)

    def test_modified_graph_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, doc = _write_fixture(tmp)
            graph_path = runtime / MULTI_PATH / "block_engine_binding.json"
            graph_path.write_bytes(graph_path.read_bytes() + b" ")
            with self.assertRaisesRegex(RuntimeError, "BLOCK_ENGINE_GRAPH_SHA256_MISMATCH"):
                verify_binding(runtime, doc)

    def test_tampered_companion_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, doc = _write_fixture(tmp)
            doc.write_bytes(b"altered")
            with self.assertRaisesRegex(RuntimeError, "LOUKSNA1_COMPANION_HASH_MISMATCH"):
                verify_binding(runtime, doc)

if __name__ == "__main__":
    unittest.main()
