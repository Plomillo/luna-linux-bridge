import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import louksnapg_six_obligation_audit as audit


class SixObligationAuditTests(unittest.TestCase):
    def test_missing_real_workers_repair_and_21_target_quality_stays_hold(self):
        with tempfile.TemporaryDirectory(prefix="louksnapg-six-obligation-") as tmp:
            bundle = Path(tmp) / "LOUKSNAPG.md"
            bundle.write_bytes(b"test-only bundle bytes")
            source_commit = "a" * 40
            contract_bytes = b'{"schema":"test"}'
            contract = {
                "target_ids": [f"T{i:02d}" for i in range(21)],
                "source_catalog": [],
                "prohibitions": {
                    "heavy_model_weights_download": False,
                    "remote_commander_use": False,
                    "canonical_identity_mutation": False,
                    "block_or_axiom_reassignment": False,
                    "engine_substitution_without_explicit_authorization": False,
                    "synthetic_evidence_as_product_proof": False,
                    "self_certification": False,
                    "automatic_g23_to_g24_propagation": False,
                    "merge_or_promotion_without_complete_chain": False,
                },
            }
            bundle_sha = audit.sha256_file(bundle)
            contract_sha = hashlib.sha256(contract_bytes).hexdigest()
            worker = {
                "worker_status": "PASS",
                "worker_run_id": "12345",
                "source_commit": source_commit,
                "contract_sha256": contract_sha,
                "bundle_sha256": bundle_sha,
                "artifact": {"sha256": bundle_sha},
                "authorized_scope": "BUILD_LOUKSNAPG_SINGLE_FILE_CANDIDATE",
            }
            task_rows = [
                {
                    "target_id": f"T{i:02d}",
                    "status": "PASS_FUNCTIONAL_EXECUTION",
                    "exit_code": 0,
                    "quality_acceptance": {
                        "status": "FAIL",
                        "reference_kind": "FIXED_SYNTHETIC_EXPECTATION",
                    },
                }
                for i in range(5)
            ]
            task_report = {
                "status": "FAIL",
                "inputs": "ESPEAK_NG_KNOWN_SPEECH_AND_SYNTHETIC_INVOICE_FIXTURES",
                "task_results": task_rows,
            }
            telemetry = {
                "source_commit": source_commit,
                "bundle_sha256": bundle_sha,
                "contract_sha256": contract_sha,
                "events": [],
                "safety": {
                    "heavy_model_download_count": 0,
                    "remote_commander_used": False,
                    "canonical_mutation": False,
                    "synthetic_evidence_used_as_product_proof": False,
                },
            }
            result = audit.evaluate(
                contract=contract,
                contract_sha256=contract_sha,
                source_commit=source_commit,
                bundle=bundle,
                worker=worker,
                task_report=task_report,
                functional_gate={"decision": "HOLD", "eligible_for_g24": False},
                g24_evidence={"decision": "NOT_GRANTED", "global_certification": "NOT_GRANTED"},
                telemetry=telemetry,
                kestra_receipt={"status": "NOT_CONFIGURED"},
            )
            obligations = result["obligations"]
            self.assertEqual(obligations["C1_COORDINATED_WORKERS"]["status"], "HOLD")
            self.assertEqual(obligations["C2_OFFICIAL_SOURCE_REPAIR"]["status"], "HOLD")
            self.assertEqual(obligations["C3_PRIMITIVE_FUNCTIONS"]["status"], "HOLD")
            self.assertEqual(obligations["C4_TELEMETRY_AND_AUDIT"]["status"], "HOLD")
            self.assertEqual(obligations["C5_GOVERNED_RELEASE_CHAIN"]["status"], "HOLD")
            self.assertEqual(obligations["C6_PROHIBITIONS_AND_RECOVERY"]["status"], "PASS_PROHIBITIONS_OBSERVED")
            self.assertFalse(result["summary"]["release_eligible"])
            self.assertEqual(result["summary"]["decision"], "HOLD_NOT_CERTIFIED")
            self.assertEqual(result["summary"]["global_certification"], "NOT_GRANTED")

    def test_global_distribution_cap_is_not_runtime_cap(self):
        self.assertEqual(audit.GLOBAL_LUNA_HARD_MAX_BYTES, 479_000_000)
        self.assertEqual(audit.CAJITA_RUNTIME_MAX_BYTES, 470_000_000)
        self.assertNotEqual(audit.GLOBAL_LUNA_HARD_MAX_BYTES, audit.CAJITA_RUNTIME_MAX_BYTES)


if __name__ == "__main__":
    unittest.main()
