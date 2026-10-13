import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "domains" / "D04_runtime.py"
spec = importlib.util.spec_from_file_location("d04_runtime", MODULE_PATH)
d04 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = d04
spec.loader.exec_module(d04)


def node(node_id, parents=(), output="out"):
    return d04.ProvenanceNode(
        node_id=node_id, kind="operation", subject="unit-test",
        input_hashes=tuple(parents), output_hash=output,
        actor="test-runner", tool="python-unittest",
        tool_version="stdlib", policy_version="policy-v1",
    )


class D04RuntimeTests(unittest.TestCase):
    def test_content_address_is_deterministic_and_key_order_independent(self):
        self.assertEqual(d04.content_id({"a": 1, "b": 2}),
                         d04.content_id({"b": 2, "a": 1}))
        self.assertNotEqual(d04.content_id({"a": 1}), d04.content_id({"a": 2}))

    def test_universal_object_id_is_stable_scoped_and_does_not_embed_value(self):
        first = d04.universal_object_id("D04 / object", {"a": 1})
        second = d04.universal_object_id("D04 / object", {"a": 1})
        other = d04.universal_object_id("D05", {"a": 1})
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertIn("D04%20%2F%20object", first)
        self.assertNotIn('"a"', first)
        with self.assertRaisesRegex(ValueError, "namespace_required"):
            d04.universal_object_id(" ", {"a": 1})

    def test_graph_accepts_known_parent_and_exports_stable_hash(self):
        graph = d04.ProvenanceGraph()
        graph.add(node("root", output="a" * 64))
        graph.add(node("child", ("root",), output="b" * 64))
        exported = graph.export()
        self.assertEqual(exported["schema"], "SUPER1200_D04_PROVENANCE_GRAPH/1")
        self.assertEqual(exported["edges"], [["root", "child"]])
        self.assertEqual(exported["graph_sha256"], graph.export()["graph_sha256"])
        self.assertFalse(graph.has_cycle())

    def test_graph_rejects_unknown_parent_and_conflicting_rewrite(self):
        graph = d04.ProvenanceGraph()
        with self.assertRaisesRegex(ValueError, "unknown_provenance_parent"):
            graph.add(node("orphan", ("missing",)))
        graph.add(node("root"))
        with self.assertRaisesRegex(ValueError, "immutable_node_conflict"):
            graph.add(node("root", output="changed"))

    def test_w3c_prov_adapter_preserves_generation_and_usage_edges(self):
        graph = d04.ProvenanceGraph()
        graph.add(node("source", output="a" * 64))
        graph.add(node("transform", ("source",), output="b" * 64))
        exported = d04.to_w3c_prov(graph)
        self.assertEqual(exported["prefix"]["prov"], "http://www.w3.org/ns/prov#")
        self.assertEqual(len(exported["wasGeneratedBy"]), 2)
        self.assertEqual(len(exported["used"]), 1)
        self.assertTrue(any(x["louksna:outputHash"] == "b" * 64
                            for x in exported["entity"].values()))

    def test_intoto_statement_has_required_identity_and_rejects_bad_digest(self):
        digest = "a" * 64
        statement = d04.to_intoto_statement(
            "artifact.tar", digest, "https://example.org/predicate/v1", {"test": "PASS"})
        self.assertEqual(statement["_type"], "https://in-toto.io/Statement/v1")
        self.assertEqual(statement["subject"][0]["digest"]["sha256"], digest)
        self.assertEqual(statement["predicate"], {"test": "PASS"})
        with self.assertRaisesRegex(ValueError, "subject_sha256"):
            d04.to_intoto_statement("artifact.tar", "not-a-hash",
                                    "https://example.org/predicate/v1", {})

    def test_slsa_provenance_binds_source_builder_and_invocation(self):
        digest = "c" * 64
        predicate = d04.to_slsa_provenance(
            builder_id="https://ci.example.org/builder",
            build_type="https://ci.example.org/buildtypes/python/v1",
            invocation_id="run-123",
            source_uri="git+https://github.com/example/project",
            source_sha256=digest,
            started_on="2026-10-13T10:00:00Z",
            finished_on="2026-10-13T10:01:00Z",
            external_parameters={"ref": "candidate"},
        )
        self.assertEqual(predicate["runDetails"]["builder"]["id"],
                         "https://ci.example.org/builder")
        self.assertEqual(predicate["runDetails"]["metadata"]["invocationId"], "run-123")
        self.assertEqual(predicate["buildDefinition"]["resolvedDependencies"][0]
                         ["digest"]["sha256"], digest)
        with self.assertRaisesRegex(ValueError, "source_sha256"):
            d04.to_slsa_provenance(
                builder_id="https://ci.example.org/builder",
                build_type="https://ci.example.org/buildtypes/python/v1",
                invocation_id="run-123",
                source_uri="git+https://github.com/example/project",
                source_sha256="bad",
                started_on="2026-10-13T10:00:00Z",
                finished_on="2026-10-13T10:01:00Z",
            )

    def test_evidence_reuse_requires_exact_key_and_validated_record(self):
        index = d04.EvidenceReuseIndex()
        key = d04.EvidenceKey(81, "input-a", "source-a", "tool-v1", "policy-v1")
        record = d04.EvidenceRecord(key, "output-a", "evidence-a", validated=True)
        index.put(record)
        self.assertEqual(index.get_reusable(key), record)
        changed_policy = d04.EvidenceKey(81, "input-a", "source-a", "tool-v1", "policy-v2")
        self.assertIsNone(index.get_reusable(changed_policy))
        index.invalidate(key)
        self.assertIsNone(index.get_reusable(key))

    def test_evidence_conflict_fails_closed(self):
        index = d04.EvidenceReuseIndex()
        key = d04.EvidenceKey(82, "i", "s", "t", "p")
        index.put(d04.EvidenceRecord(key, "o1", "e1", True))
        with self.assertRaisesRegex(ValueError, "evidence_key_conflict"):
            index.put(d04.EvidenceRecord(key, "o2", "e2", True))

    def test_policy_envelope_validation(self):
        good = {"schema": "SUPER1200_POLICY/1", "policy_id": "test",
                "version": "1", "rules": [{"id": "allow"}]}
        self.assertEqual(d04.validate_policy_document(good), ())
        self.assertIn("policy_schema_invalid",
                      d04.validate_policy_document({"schema": "wrong"}))


if __name__ == "__main__":
    unittest.main()
