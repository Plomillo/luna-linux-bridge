from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, module_name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("SCRIPT_IMPORT_FAILED:" + name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ledger = load_script("louksna_global_gate_ledger.py", "louksna_global_gate_ledger_test")
certifier = load_script("louksna_g24_terminal_certifier.py", "louksna_g24_terminal_certifier_test")


class LouksnaGlobalCertificationFailClosedTests(unittest.TestCase):
    def test_global_matrix_has_all_24_canonical_slots_in_order(self):
        policy = json.loads((ROOT / "scripts/louksna_global_scope_policy.json").read_text(encoding="utf-8"))
        matrix = json.loads((ROOT / "scripts/louksna_global_gate_matrix.json").read_text(encoding="utf-8"))
        expected = [f"G{i:02d}" for i in range(1, 25)]
        self.assertEqual(policy["canonical_gate_ids"], expected)
        self.assertEqual([row["gate_id"] for row in matrix["gates"]], expected)
        self.assertEqual(len(matrix["gates"]), 24)

    def test_missing_v25_baseline_cannot_pass_global_g23(self):
        report = ledger.validate(
            ROOT,
            ROOT,
            ROOT / "scripts/louksna_global_scope_policy.json",
            ROOT / "scripts/louksna_global_gate_matrix.json",
            "a" * 40,
        )
        self.assertEqual(report["decision"], "HOLD")
        self.assertFalse(report["certification_issued"])
        self.assertIn("PROTECTED_V25_BASELINE_ABSENT", report["reason_codes"])
        self.assertIn("PROTECTED_V25_BASELINE_SHA256_NOT_PINNED", report["reason_codes"])

    def test_g24_never_issues_from_hold_or_unverified_incomplete_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            g23 = {
                "schema": "LOUKSNA_GLOBAL_G23_RESULT/1.0",
                "candidate_sha": "a" * 40,
                "decision": "HOLD",
                "reason_codes": ["PROTECTED_V25_BASELINE_ABSENT"],
                "trusted_policy_sha256": "b" * 64,
                "trusted_matrix_sha256": "c" * 64,
                "protected_baseline_sha256": None,
                "authority_sha256": "d" * 64,
                "gate_count": 24,
                "required_gate_ids": [f"G{i:02d}" for i in range(1, 25)],
                "checked_evidence": [],
            }
            g23["report_sha256"] = ledger.sha256_bytes(ledger.canonical_bytes(g23))
            recheck = dict(g23)
            recheck["report_sha256"] = ledger.sha256_bytes(ledger.canonical_bytes(recheck))
            g23_path = root / "g23.json"
            recheck_path = root / "recheck.json"
            attestation_path = root / "attestation.json"
            g23_path.write_text(json.dumps(g23), encoding="utf-8")
            recheck_path.write_text(json.dumps(recheck), encoding="utf-8")
            attestation_path.write_text("{}", encoding="utf-8")
            result = certifier.decide(g23, recheck, attestation_path)
            self.assertEqual(result["decision"], "HOLD")
            self.assertFalse(result["certification_issued"])
            self.assertEqual(result["certification"], "NOT_ISSUED")


if __name__ == "__main__":
    unittest.main()
