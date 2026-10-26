import hashlib
import json
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
            self.assertEqual(result["summary"]["global_certification"], "NOT_GRANTED_BY_THIS_AUDIT")

    def test_telemetry_payload_and_envelope_hashes_are_recomputed(self):
        with tempfile.TemporaryDirectory(prefix="louksnapg-telemetry-binding-") as tmp:
            bundle = Path(tmp) / "LOUKSNAPG.md"
            bundle.write_bytes(b"test-only bundle bytes")
            source_commit = "c" * 40
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
            event_types = [
                "SOURCE", "INPUT", "OPERATION", "OUTPUT", "TEST", "VALIDATION",
                "INDEPENDENT_VALIDATION_G23", "KESTRA_AUDIT", "CERTIFICATION_DECISION_G24",
                "NON_REGRESSION", "ROLLBACK",
            ]
            events = []
            for sequence, event_type in enumerate(event_types, 1):
                event = {
                    "operation_id": "audit-test",
                    "sequence_id": sequence,
                    "timestamp_utc": "2026-10-26T10:00:00Z",
                    "actor": "unit-test",
                    "tool_name": "six-obligation-audit-test",
                    "tool_version": "1",
                    "source": "unit-test-source",
                    "source_commit": source_commit,
                    "bundle_sha256": bundle_sha,
                    "contract_sha256": contract_sha,
                    "input_sha256": contract_sha,
                    "input_bytes": len(contract_bytes),
                    "validation_status": "HOLD_TEST_ONLY",
                    "rollback_reference": "unit-test-checkpoint",
                    "status": "HOLD",
                    "event_type": event_type,
                    "count": 1,
                    "details": "synthetic telemetry test; not product evidence",
                }
                payload = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                digest = hashlib.sha256(payload).hexdigest()
                event["output_bytes"] = len(payload)
                event["output_sha256"] = digest
                event["evidence_sha256"] = digest
                events.append(event)
            receipt_sha = "d" * 64
            receipt = {
                "status": "NOT_CONFIGURED",
                "source_commit": source_commit,
                "bundle_sha256": bundle_sha,
                "_evidence_file_sha256": receipt_sha,
            }
            receipt_event = {
                "operation_id": "audit-test",
                "sequence_id": len(events) + 1,
                "timestamp_utc": "2026-10-26T10:00:01Z",
                "actor": "unit-test",
                "tool_name": "Kestra audit receipt materializer",
                "tool_version": "1",
                "source": "unit-test-source",
                "source_commit": source_commit,
                "bundle_sha256": bundle_sha,
                "contract_sha256": contract_sha,
                "input_sha256": receipt_sha,
                "input_bytes": 1,
                "validation_status": "HOLD_KESTRA_EXECUTION_NOT_ESTABLISHED",
                "rollback_reference": "unit-test-checkpoint",
                "status": "HOLD_KESTRA_EXECUTION_NOT_ESTABLISHED",
                "event_type": "KESTRA_AUDIT_RESULT",
                "count": 1,
                "details": {
                    "receipt_sha256": receipt_sha,
                    "receipt_status": "NOT_CONFIGURED",
                    "execution_id_present": False,
                    "terminal_state": None,
                },
            }
            receipt_payload = json.dumps(receipt_event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            receipt_digest = hashlib.sha256(receipt_payload).hexdigest()
            receipt_event["output_bytes"] = len(receipt_payload)
            receipt_event["output_sha256"] = receipt_digest
            receipt_event["evidence_sha256"] = receipt_digest
            events.append(receipt_event)

            telemetry = {
                "schema": "LOUKSNAPG_PERSISTENT_TELEMETRY_SNAPSHOT/1.0",
                "source_commit": source_commit,
                "bundle_sha256": bundle_sha,
                "contract_sha256": contract_sha,
                "generated_at_utc": "2026-10-26T10:00:00Z",
                "trace_integrity": "PASS_TEST_FIXTURE_ONLY",
                "status": "INCOMPLETE_HOLD",
                "release_telemetry_status": "INCOMPLETE_HOLD",
                "events": events,
                "safety": {
                    "heavy_model_download_count": 0,
                    "remote_commander_used": False,
                    "canonical_mutation": False,
                    "synthetic_evidence_used_as_product_proof": False,
                },
                "global_certification": "NOT_GRANTED",
            }
            telemetry["evidence_sha256"] = hashlib.sha256(
                json.dumps(telemetry, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest()
            worker = {
                "worker_status": "PASS", "worker_run_id": "12345",
                "source_commit": source_commit, "contract_sha256": contract_sha,
                "bundle_sha256": bundle_sha, "artifact": {"sha256": bundle_sha},
            }
            base_args = {
                "contract": contract, "contract_sha256": contract_sha,
                "source_commit": source_commit, "bundle": bundle, "worker": worker,
                "task_report": {},
                "functional_gate": {"decision": "HOLD", "eligible_for_g24": False},
                "g24_evidence": {"decision": "NOT_GRANTED", "global_certification": "NOT_GRANTED"},
                "kestra_receipt": receipt,
            }
            good = audit.evaluate(**base_args, telemetry=telemetry)
            self.assertEqual(good["obligations"]["C4_TELEMETRY_AND_AUDIT"]["status"], "PASS_TRACEABILITY_WITH_RELEASE_HOLD")
            self.assertEqual(good["obligations"]["C4_TELEMETRY_AND_AUDIT"]["details"]["event_count"], 12)
            self.assertTrue(good["obligations"]["C4_TELEMETRY_AND_AUDIT"]["details"]["kestra_receipt_event_bound"])
            self.assertFalse(good["summary"]["release_eligible"])

            missing_post_dispatch = json.loads(json.dumps(telemetry))
            missing_post_dispatch.pop("evidence_sha256", None)
            missing_post_dispatch["events"] = missing_post_dispatch["events"][:-1]
            missing_post_dispatch["evidence_sha256"] = hashlib.sha256(
                json.dumps(missing_post_dispatch, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest()
            missing_result = audit.evaluate(**base_args, telemetry=missing_post_dispatch)
            self.assertEqual(missing_result["obligations"]["C4_TELEMETRY_AND_AUDIT"]["status"], "HOLD")
            self.assertIn(
                "KESTRA_RECEIPT_MISSING_OR_NOT_BOUND_TO_FINAL_TELEMETRY",
                missing_result["obligations"]["C4_TELEMETRY_AND_AUDIT"]["reason_codes"],
            )

            tampered = json.loads(json.dumps(telemetry))
            tampered["events"][0]["details"] = "changed after hashing"
            bad = audit.evaluate(**base_args, telemetry=tampered)
            self.assertEqual(bad["obligations"]["C4_TELEMETRY_AND_AUDIT"]["status"], "HOLD")
            self.assertIn("PERSISTENT_TELEMETRY_MISSING_INCOMPLETE_OR_UNBOUND",
                          bad["obligations"]["C4_TELEMETRY_AND_AUDIT"]["reason_codes"])

    def test_qwen_candidate_config_must_match_the_pinned_variant(self):
        with tempfile.TemporaryDirectory(prefix="louksnapg-qwen-identity-") as tmp:
            root = Path(tmp)
            candidate = root / "candidate.zip"
            with __import__("zipfile").ZipFile(candidate, "w") as archive:
                archive.writestr(audit.QWEN_CONFIG_PATH, json.dumps({
                    "hidden_size": 5120,
                    "intermediate_size": 17408,
                    "num_hidden_layers": 40,
                    "num_attention_heads": 40,
                    "num_key_value_heads": 8,
                    "tie_word_embeddings": False,
                    "vocab_size": 151936,
                }))
            mismatch = audit.inspect_qwen_model_identity(candidate, "Qwen/Qwen3-0.6B")
            self.assertEqual(mismatch["status"], "HOLD_QWEN_CONFIG_VARIANT_MISMATCH")
            self.assertEqual(mismatch["mismatches"]["hidden_size"], {"expected": 1024, "observed": 5120})
            self.assertEqual(mismatch["mismatches"]["num_hidden_layers"], {"expected": 28, "observed": 40})

            match_candidate = root / "candidate-0.6b.zip"
            with __import__("zipfile").ZipFile(match_candidate, "w") as archive:
                archive.writestr(audit.QWEN_CONFIG_PATH, json.dumps({
                    "hidden_size": 1024,
                    "intermediate_size": 3072,
                    "num_hidden_layers": 28,
                    "num_attention_heads": 16,
                    "num_key_value_heads": 8,
                    "tie_word_embeddings": True,
                    "vocab_size": 151936,
                }))
            match = audit.inspect_qwen_model_identity(match_candidate, "Qwen/Qwen3-0.6B")
            self.assertEqual(match["status"], "PASS_CONFIG_MATCHES_PINNED_VARIANT")

    def test_worker_scope_matches_the_governed_contract_not_a_stale_literal(self):
        contract = {"worker_mission":{"authorized_scope":"VERIFY_REPAIR_PRIMITIVES_AND_BUILD_LOUKSNAPG_CANDIDATE"}}
        worker = {"authorized_scope":"VERIFY_REPAIR_PRIMITIVES_AND_BUILD_LOUKSNAPG_CANDIDATE"}
        self.assertTrue(audit.worker_scope_matches_contract(contract, worker))
        worker["authorized_scope"] = "BUILD_LOUKSNAPG_SINGLE_FILE_CANDIDATE"
        self.assertFalse(audit.worker_scope_matches_contract(contract, worker))
        self.assertFalse(audit.worker_scope_matches_contract({}, worker))

    def test_global_distribution_cap_is_not_runtime_cap(self):
        self.assertEqual(audit.GLOBAL_LUNA_HARD_MAX_BYTES, 479_000_000)
        self.assertEqual(audit.CAJITA_RUNTIME_MAX_BYTES, 470_000_000)
        self.assertNotEqual(audit.GLOBAL_LUNA_HARD_MAX_BYTES, audit.CAJITA_RUNTIME_MAX_BYTES)


if __name__ == "__main__":
    unittest.main()
