import tempfile
import unittest
from pathlib import Path

from scripts.missions.louksna_infrastructure_readiness_audit import audit


class InfrastructureReadinessTests(unittest.TestCase):
    def test_external_gates_are_never_inferred_as_passed(self):
        report = audit(Path(__file__).resolve().parents[1])
        self.assertEqual(report["overall_status"], "HOLD")
        self.assertEqual(report["certification"], "NOT_GRANTED")
        self.assertEqual(report["activation"], "FALSE")
        by_code = {item["code"]: item for item in report["findings"]}
        for code in (
            "CP09_LIVE_RUNNER",
            "VOICE_REAL_E2E",
            "CP10_DIGEST_FREEZE",
            "G23_INDEPENDENT_VALIDATION",
            "G24_CERTIFICATION",
        ):
            self.assertIn(code, by_code)
            self.assertIn(by_code[code]["status"], {"BLOCKED", "UNVERIFIED"})
        self.assertNotEqual(by_code["G23_INDEPENDENT_VALIDATION"]["status"], "PASS")
        self.assertNotEqual(by_code["G24_CERTIFICATION"]["status"], "PASS")

    def test_missing_contract_is_a_structural_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/louksna-zd-v03-governance.yml").write_text("name: test\n")
            report = audit(root)
            self.assertEqual(report["overall_status"], "FAIL")
            self.assertGreater(report["counts"]["fail"], 0)

    def test_main_mutation_and_activation_remain_prohibited_in_report(self):
        report = audit(Path(__file__).resolve().parents[1])
        self.assertEqual(report["main_mutation"], "NOT_PERFORMED")
        self.assertEqual(report["activation"], "FALSE")
        self.assertTrue(any("not G23" in x.lower() or "g23" in x.lower()
                            for x in report["limitations"]))


if __name__ == "__main__":
    unittest.main()
