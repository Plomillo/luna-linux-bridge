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

    def test_graph_accepts_known_parent_and_exports_stable_hash(self):
        graph = d04.ProvenanceGraph()
        graph.add(node("root"))
        graph.add(node("child", ("root",)))
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
