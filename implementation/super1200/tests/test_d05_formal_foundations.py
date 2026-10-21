"""D05 formal-foundations tests for capabilities 125-128."""
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH=Path(__file__).resolve().parents[1]/"domains"/"D05_formal_foundations.py"
spec=importlib.util.spec_from_file_location("d05_formal_foundations",MODULE_PATH)
foundations=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=foundations
spec.loader.exec_module(foundations)

class D05FormalFoundationsTests(unittest.TestCase):
    def test_univalence_profile_pins_explicit_assumptions_without_claiming_univalence(self):
        assumption=foundations.explicit_assumption(
            assumption_id="UA-1",statement="Univalence is assumed in this model.",
            source_sha256="a"*64,justification="Declared axiom; no derivation is claimed.")
        profile=foundations.validate_univalence_profile(
            foundation_version="UF-1.0",source_sha256="b"*64,assumptions=[assumption])
        self.assertEqual(profile["decision"],"DECLARED_ASSUMPTIONS_ONLY")
        self.assertFalse(profile["univalence_proved"])
        self.assertFalse(profile["theorem_claim"])
        bad=dict(assumption,statement="changed")
        with self.assertRaisesRegex(ValueError,"univalence_assumption_hash_mismatch"):
            foundations.validate_univalence_profile(foundation_version="UF-1.0",source_sha256="b"*64,assumptions=[bad])

    def test_cubical_provider_binding_pins_provider_version_library_and_no_authority(self):
        binding=foundations.bind_cubical_provider(
            provider_id="cubical-adapter",version="1.2.3",library_set_sha256="c"*64,
            adapter_schema_version="CUBE-1",authority="NONE")
        self.assertEqual(binding["authority"],"NONE")
        self.assertFalse(binding["provider_executed"])
        self.assertEqual(binding["external_verification"],"NOT_PERFORMED")
        with self.assertRaisesRegex(ValueError,"cubical_provider_authority_must_be_NONE"):
            foundations.bind_cubical_provider(provider_id="p",version="1",library_set_sha256="c"*64,
                adapter_schema_version="CUBE-1",authority="CANONICAL")

    def test_higher_inductive_spec_validates_constructor_and_computation_rule_references(self):
        spec={"type_name":"Circle","source_sha256":"d"*64,
              "point_constructors":[{"name":"base","type":"Circle"}],
              "path_constructors":[{"name":"loop","from":"base","to":"base","type":"Id(base,base)"}],
              "computation_rules":[{"rule_id":"comp-1","constructor":"loop","result":"base"}]}
        result=foundations.validate_higher_inductive_spec(spec)
        self.assertEqual(result["decision"],"STRUCTURE_AND_REFERENCES_VALID")
        self.assertFalse(result["full_cubical_derivation_verified"])
        self.assertFalse(result["theorem_claim"])
        broken={**spec,"path_constructors":[{"name":"loop","from":"missing","to":"base","type":"Id"}]}
        with self.assertRaisesRegex(ValueError,"hit_path_endpoint_unknown"):
            foundations.validate_higher_inductive_spec(broken)

    def test_proof_term_registry_binds_hashes_assumptions_prover_and_dependencies(self):
        assumption=foundations.explicit_assumption(
            assumption_id="AX-REG-1",statement="Declared local axiom.",
            source_sha256="e"*64,justification="Not proved in this registry.")
        record=foundations.register_proof_term(
            proof_term_id="PT-001",theorem_id="THM-001",proof_term_sha256="f"*64,
            source_sha256="1"*64,assumptions=[assumption],prover_id="cubical-adapter",
            prover_version="1.2.3",dependencies=[{"dependency_id":"lib-core","sha256":"2"*64}])
        self.assertEqual(record["status"],"REGISTERED_UNVERIFIED_PROOF_TERM")
        self.assertFalse(record["proof_replay_verified"])
        self.assertFalse(record["theorem_claim"])
        with self.assertRaisesRegex(ValueError,"proof_term_dependency_duplicate"):
            foundations.register_proof_term(
                proof_term_id="PT-002",theorem_id="THM-002",proof_term_sha256="f"*64,
                source_sha256="1"*64,assumptions=[],prover_id="p",prover_version="1",
                dependencies=[{"dependency_id":"x","sha256":"2"*64},{"dependency_id":"x","sha256":"3"*64}])

if __name__=="__main__":
    unittest.main()
