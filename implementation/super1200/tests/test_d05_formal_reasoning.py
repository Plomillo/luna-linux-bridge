"""D05 formal reasoning tests, scoped to capabilities 121-124."""
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH=Path(__file__).resolve().parents[1]/"domains"/"D05_formal_reasoning.py"
spec=importlib.util.spec_from_file_location("d05_formal_reasoning",MODULE_PATH)
formal=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=formal
spec.loader.exec_module(formal)


def sig():
    sort0={"kind":"Sort","level":0}
    nat={"kind":"Const","name":"Nat"}
    boolean={"kind":"Const","name":"Bool"}
    return {
        "Nat":sort0,
        "zero":nat,
        "Bool":sort0,
        "true":boolean,
        "Vec":{"kind":"Pi","binder":"n","domain":nat,"codomain":{"kind":"Sort","level":1}},
        "succ":{"kind":"Pi","binder":"n","domain":nat,"codomain":nat},
    }


class D05FormalReasoningTests(unittest.TestCase):
    def test_formal_reasoning_fabric_requires_explicit_assumptions_and_trusted_replay(self):
        source="a"*64
        env="b"*64
        assumption=formal.explicit_assumption(
            assumption_id="AX-EXPLICIT-1",
            statement="For every natural number n, succ(n) is a natural number.",
            source_sha256=source,
            justification="Declared axiom for this local formalization; not derived here.")
        obligation=formal.build_proof_obligation(
            theorem_id="THM-SUCC-CLOSED",goal="succ(zero) has type Nat",
            assumptions=[assumption],source_sha256=source,prover_id="dtt-kernel",
            prover_version="0.1",environment_sha256=env,proof_term_sha256="c"*64)
        self.assertEqual(obligation["status"],"OPEN_NOT_PROVED")
        self.assertFalse(obligation["proof_claim"])
        receipt={"checker_id":"trusted-dtt-checker","checker_version":"1.2",
            "proof_sha256":"c"*64,"obligation_sha256":obligation["obligation_sha256"],
            "source_sha256":source,"environment_sha256":env,"replayed":True,
            "result":"PASS","checker_signature_verified":True}
        accepted=formal.validate_replay_receipt(obligation,receipt,
            trusted_checker=lambda o,r:o["obligation_sha256"]==r["obligation_sha256"] and r["checker_id"]=="trusted-dtt-checker")
        self.assertEqual(accepted["decision"],"ALLOW_REPLAY_VERIFIED")
        untrusted=formal.validate_replay_receipt(obligation,receipt,trusted_checker=lambda *_:False)
        self.assertEqual(untrusted["decision"],"DENY")
        wrong= dict(receipt,source_sha256="d"*64)
        self.assertEqual(formal.validate_replay_receipt(obligation,wrong,trusted_checker=lambda *_:True)["reason"],"source_digest_mismatch")
        with self.assertRaisesRegex(ValueError,"assumption_hash_mismatch"):
            bad=dict(assumption,statement="silently changed")
            formal.build_proof_obligation(theorem_id="x",goal="g",assumptions=[bad],source_sha256=source,
                prover_id="p",prover_version="1",environment_sha256=env)

    def test_dependent_type_theory_checks_pi_lambda_application_and_dependent_codomain(self):
        signature=sig()
        nat={"kind":"Const","name":"Nat"}
        identity_function={"kind":"Lam","binder":"x","domain":nat,"body":{"kind":"Var","name":"x"}}
        inferred=formal.infer_type(identity_function,signature=signature)
        expected={"kind":"Pi","binder":"x","domain":nat,"codomain":nat}
        self.assertTrue(formal.definitionally_equal(inferred,expected))
        app={"kind":"App","function":identity_function,"argument":{"kind":"Const","name":"zero"}}
        self.assertEqual(formal.infer_type(app,signature=signature),nat)
        dependent={"kind":"Pi","binder":"n","domain":nat,
                   "codomain":{"kind":"Pi","binder":"v","domain":{"kind":"App","function":{"kind":"Const","name":"Vec"},"argument":{"kind":"Var","name":"n"}},
                               "codomain":{"kind":"App","function":{"kind":"Const","name":"Vec"},"argument":{"kind":"Var","name":"n"}}}}
        self.assertEqual(formal.infer_type(dependent,signature=signature),{"kind":"Sort","level":1})
        with self.assertRaisesRegex(ValueError,"application_argument_type_mismatch"):
            formal.infer_type({"kind":"App","function":identity_function,"argument":{"kind":"Const","name":"true"}},signature=signature)
        with self.assertRaisesRegex(ValueError,"variable_unbound"):
            formal.infer_type({"kind":"Var","name":"missing"},signature=signature)

    def test_higher_order_type_theory_validates_quantification_over_function_space(self):
        signature=sig()
        nat={"kind":"Const","name":"Nat"}
        boolean={"kind":"Const","name":"Bool"}
        predicate_type={"kind":"Pi","binder":"n","domain":nat,"codomain":boolean}
        higher_order={"kind":"Pi","binder":"P","domain":predicate_type,
                      "codomain":{"kind":"Pi","binder":"n","domain":nat,
                                  "codomain":{"kind":"App","function":{"kind":"Var","name":"P"},"argument":{"kind":"Var","name":"n"}}}}
        result=formal.validate_higher_order_type(higher_order,signature=signature)
        self.assertEqual(result["decision"],"WELL_FORMED_TYPE")
        self.assertTrue(result["higher_order_domain_present"])
        self.assertFalse(result["theorem_claim"])
        with self.assertRaisesRegex(ValueError,"higher_order_function_domain_required"):
            formal.validate_higher_order_type({"kind":"Pi","binder":"n","domain":nat,"codomain":boolean},signature=signature)

    def test_hott_identity_typechecks_refl_but_keeps_axioms_and_proof_claims_explicit(self):
        signature=sig()
        nat={"kind":"Const","name":"Nat"}
        zero={"kind":"Const","name":"zero"}
        identity={"kind":"Identity","type":nat,"left":zero,"right":zero}
        refl={"kind":"Refl","type":nat,"value":zero}
        axiom=formal.explicit_assumption(assumption_id="UNIVERSE-0",statement="Universe level 0 is available",
            source_sha256="e"*64,justification="Environment assumption; not proved by this kernel.")
        valid=formal.validate_hott_identity(identity,refl,signature=signature,universe_assumptions=[axiom])
        self.assertEqual(valid["decision"],"TYPE_CHECKED_ONLY")
        self.assertFalse(valid["proof_replay_verified"])
        self.assertFalse(valid["theorem_claim"])
        bad_identity={"kind":"Identity","type":nat,"left":zero,"right":{"kind":"App",
                       "function":{"kind":"Const","name":"succ"},"argument":zero}}
        with self.assertRaisesRegex(ValueError,"hott_proof_type_mismatch"):
            formal.validate_hott_identity(bad_identity,refl,signature=signature,universe_assumptions=[axiom])
        corrupted=dict(axiom,assumption_id="changed")
        with self.assertRaisesRegex(ValueError,"universe_assumption_hash_mismatch"):
            formal.validate_hott_identity(identity,refl,signature=signature,universe_assumptions=[corrupted])


if __name__=="__main__":
    unittest.main()
