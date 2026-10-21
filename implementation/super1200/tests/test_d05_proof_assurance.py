"""D05 proof-assurance tests for capabilities 129-132."""
import importlib.util
from pathlib import Path
import sys
import unittest
MODULE_PATH=Path(__file__).resolve().parents[1]/"domains"/"D05_proof_assurance.py"
spec=importlib.util.spec_from_file_location("d05_proof_assurance",MODULE_PATH)
assurance=importlib.util.module_from_spec(spec);sys.modules[spec.name]=assurance;spec.loader.exec_module(assurance)

class D05ProofAssuranceTests(unittest.TestCase):
 def test_checker_binding_requires_independent_checker_and_untrusted_producer(self):
  b=assurance.validate_proof_checker_binding(checker_id="checker",version="1.0",toolchain_sha256="a"*64,proof_language="cubical",producer_is_trusted=False)
  self.assertTrue(b["independent_checker_required"]);self.assertFalse(b["producer_output_trusted"]);self.assertEqual(b["decision"],"BOUND_NOT_EXECUTED")
  with self.assertRaisesRegex(ValueError,"producer_output_must_not_be_trusted"):
   assurance.validate_proof_checker_binding(checker_id="c",version="1",toolchain_sha256="a"*64,proof_language="p",producer_is_trusted=True)

 def test_proof_artifact_descriptor_is_hash_bound_and_does_not_claim_persistence(self):
  d=assurance.build_proof_artifact_descriptor(artifact_id="proof-1",proof_term_sha256="a"*64,source_sha256="b"*64,
   environment_sha256="c"*64,toolchain_lock_sha256="d"*64,proof_language="cubical",
   dependencies=[{"dependency_id":"lemma-1","sha256":"e"*64}])
  self.assertEqual(d["storage_semantics"],"CONTENT_ADDRESSED_IMMUTABLE_DESCRIPTOR_ONLY")
  self.assertFalse(d["artifact_persisted"]);self.assertFalse(d["proof_replay_verified"]);self.assertFalse(d["theorem_claim"])
  with self.assertRaisesRegex(ValueError,"proof_artifact_dependency_duplicate"):
   assurance.build_proof_artifact_descriptor(artifact_id="p",proof_term_sha256="a"*64,source_sha256="b"*64,
    environment_sha256="c"*64,toolchain_lock_sha256="d"*64,proof_language="cubical",
    dependencies=[{"dependency_id":"x","sha256":"e"*64},{"dependency_id":"x","sha256":"f"*64}])

 def test_proof_dependency_graph_rejects_cycles_and_computes_reverse_invalidation(self):
  nodes=[{"node_id":"T","kind":"THEOREM","sha256":"a"*64},{"node_id":"L","kind":"LEMMA","sha256":"b"*64},{"node_id":"A","kind":"AXIOM","sha256":"c"*64}]
  edges=[{"depends_on":"T","dependency":"L"},{"depends_on":"L","dependency":"A"}]
  graph=assurance.validate_proof_dependency_graph(nodes,edges)
  self.assertEqual(graph["decision"],"ACYCLIC_TYPED_GRAPH_VALID")
  closure=assurance.reverse_invalidation_closure(graph,["A"])
  self.assertEqual(closure["invalidated_all"],["A","L","T"])
  with self.assertRaisesRegex(ValueError,"proof_graph_cycle"):
   assurance.validate_proof_dependency_graph(nodes,edges+[{"depends_on":"A","dependency":"T"}])

 def test_proof_replay_requires_trusted_exact_callback_and_never_grants_global_certification(self):
  receipt=assurance.replay_proof_artifact(proof_term_sha256="a"*64,source_sha256="b"*64,environment_sha256="c"*64,
   toolchain_lock_sha256="d"*64,checker_id="checker",checker_version="2.0",trusted_replay=lambda request:request["checker_id"]=="checker")
  self.assertEqual(receipt["decision"],"INDEPENDENT_REPLAY_VERIFIED");self.assertFalse(receipt["theorem_claim"])
  with self.assertRaisesRegex(ValueError,"independent_proof_replay_denied"):
   assurance.replay_proof_artifact(proof_term_sha256="a"*64,source_sha256="b"*64,environment_sha256="c"*64,
    toolchain_lock_sha256="d"*64,checker_id="checker",checker_version="2.0",trusted_replay=lambda _request:False)

if __name__=="__main__":unittest.main()
