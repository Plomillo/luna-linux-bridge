"""Adversarial proof of one-shot externally signed scope reservation (no sudo)."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import elastic_automation as elastic
import lrb_core as base
import one_time_scope

CONTRACT = json.loads((ROOT / "CONTRACT.v0.json").read_text())
KEYS = ("G23", "G24", "G23_2", "G24_2")


class SyntheticVerifier:
    """Only verifies reservation wiring. Crypto gets separate real OpenSSL tests."""
    def __init__(self, invalid=None):
        self.invalid = invalid
        self.calls = 0

    def preflight(self, path, owner_sig, refs, strong, expected_host, expected_boot):
        self.calls += 1
        if not strong or set(refs) != set(KEYS):
            raise AssertionError("Strong gate input was altered")
        obj = json.loads(Path(path).read_text())
        proof = {
            "status": "SIGNED_RECEIPTS_CRYPTOGRAPHICALLY_VERIFIED",
            "scope_id": obj["scope_id"], "capability": obj["capability"],
            "host": expected_host, "boot_id": expected_boot,
            "strong_second_order_receipts_verified": True,
            "execution_authorized_by_this_verifier": False, "certified": False,
            "hashes": {
                "request_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                "g23_sha256": "a"*64, "g24_sha256": "b"*64,
                "g23_2_sha256": "c"*64, "g24_2_sha256": "d"*64
            }
        }
        if self.invalid:
            name, value = self.invalid
            proof[name] = value
        return proof


class SingleUseScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root/"private"
        self.source = self.root/"live_link.py"
        self.source.write_bytes(b"PINNED_LIVE_SOURCE_TEST")
        self.agent = elastic.Automation(self.state, CONTRACT)
        self.verifier = SyntheticVerifier()
        self.broker = one_time_scope.SingleUseScope(
            self.state, CONTRACT, verifier=self.verifier,
            source_file=self.source, host="SYNTHETIC_HOST", boot="SYNTHETIC_BOOT")
        self.sig = self.root/"owner.sig"
        self.sig.write_bytes(b"TEST_ONLY_SIGNATURE_NOT_VALID")
        self.refs = {role: {"document": f"/test/{role}.json", "signature": f"/test/{role}.sig"}
                     for role in KEYS}
        self.request = self.admit("probe")

    def tearDown(self):
        self.temp.cleanup()

    def admit(self, name):
        mission = {"mission_id": name, "user_objective": "Owner-defined exact scope",
            "model_proposal": "Do not use sudo, wait for independent external gates",
            "model": {"declared_name": "SYNTHETIC", "declared_version": "TEST"},
            "deadline_utc": (datetime.now(timezone.utc)+timedelta(minutes=9)).isoformat(),
            "max_auto_steps": 1,
            "steps": [{"kind":"GATED_OPERATION", "requested_capability":"CAP_STORAGE_INSPECT"}]}
        self.agent.admit(mission)
        self.assertEqual(self.agent.run_once(name)["status"], "WAITING_FRESH_G23_G24")
        request = {
            "schema": "LRB_SCOPED_REQUEST/0.3", "mission_id": name,
            "scope_id": "SCOPE-" + name,
            "host": "SYNTHETIC_HOST", "boot_id": "SYNTHETIC_BOOT",
            "capability": "CAP_STORAGE_INSPECT", "risk": "ROOT_READONLY",
            "source_sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "reservation_module_sha256": hashlib.sha256(Path(one_time_scope.__file__).read_bytes()).hexdigest(),
            "mission_sha256": base.digest(mission),
            "owner_objective_sha256": base.digest(mission["user_objective"]),
            "deadline_utc": mission["deadline_utc"]
        }
        p = self.root/(name + ".json")
        p.write_text(json.dumps(request, sort_keys=True))
        return p

    def reserve(self, p=None):
        p = p or self.request
        return self.broker.reserve(json.loads(p.read_text())["mission_id"],
                                   p, self.sig, self.refs)

    def test_valid_synthetic_wiring_reserves_once_never_executes(self):
        r = self.reserve()
        self.assertEqual(r["status"], "RESERVED_ONCE_AWAITING_INDEPENDENT_EXECUTOR")
        self.assertTrue(r["cryptographic_receipts_checked"])
        self.assertFalse(r["authorization_consumed_for_root"])
        self.assertFalse(r["issuer_operator_independence_certified"])
        self.assertFalse(r["root_operation_executed"])
        self.assertFalse(r["certified"])
        self.assertEqual(self.verifier.calls, 1)
        self.assertEqual(self.broker.ledger.verify(), r["reservation_evidence_hash"])

    def test_exact_replay_denied_on_restart(self):
        self.reserve()
        second = one_time_scope.SingleUseScope(
            self.state, CONTRACT, verifier=SyntheticVerifier(),
            source_file=self.source, host="SYNTHETIC_HOST", boot="SYNTHETIC_BOOT")
        with self.assertRaisesRegex(RuntimeError, "NO_REPLAY"):
            second.reserve("probe", self.request, self.sig, self.refs)

    def test_same_mission_reissued_new_scope_denied(self):
        self.reserve()
        data=json.loads(self.request.read_text())
        data["scope_id"]="SCOPE-REISSUED"
        self.request.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, "NO_REPLAY"):
            self.reserve()

    def test_different_mission_same_scope_denied(self):
        self.reserve()
        other = self.admit("second")
        data=json.loads(other.read_text())
        data["scope_id"]="SCOPE-probe"
        other.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, "NO_REPLAY"):
            self.reserve(other)

    def test_wrong_scope_or_host_denied_before_verifier(self):
        for field, value in (("mission_sha256","0"*64),
                             ("owner_objective_sha256","1"*64),
                             ("host","OTHER_HOST"), ("source_sha256","2"*64),
                             ("reservation_module_sha256","3"*64)):
            with self.subTest(field=field):
                data=json.loads(self.request.read_text())
                saved=dict(data)
                data[field]=value
                self.request.write_text(json.dumps(data))
                try:
                    with self.assertRaisesRegex(RuntimeError, "SCOPE_MISSION_HOST_OR_SOURCE"):
                        self.reserve()
                    self.assertEqual(self.verifier.calls,0)
                finally:
                    self.request.write_text(json.dumps(saved))

    def test_missing_second_order_denied(self):
        del self.refs["G24_2"]
        with self.assertRaisesRegex(RuntimeError, "ALL_FOUR"):
            self.reserve()

    def test_fake_report_with_execution_authority_denied(self):
        self.broker.verifier = SyntheticVerifier(("execution_authorized_by_this_verifier", True))
        with self.assertRaisesRegex(RuntimeError, "REPORT_UNTRUSTED"):
            self.reserve()
        self.assertFalse(any(x["kind"]=="STRONG_SCOPE_RESERVED"
                             for x in self.broker.ledger._records()))

    def test_fake_report_without_strong_second_order_denied(self):
        self.broker.verifier = SyntheticVerifier(("strong_second_order_receipts_verified", False))
        with self.assertRaisesRegex(RuntimeError, "REPORT_UNTRUSTED"):
            self.reserve()

    def test_changed_live_source_after_signing_denied(self):
        self.source.write_bytes(b"UNREVIEWED_CODE_DRIFT")
        with self.assertRaisesRegex(RuntimeError,"SOURCE_MISMATCH"):
            self.reserve()

    def test_corrupted_evidence_ledger_fail_closed(self):
        self.reserve()
        p=self.broker.ledger.path
        p.write_text(p.read_text().replace("STRONG_SCOPE_RESERVED", "FORGED_SCOPE_RESERVED"))
        with self.assertRaisesRegex(RuntimeError,"EVIDENCE_HASH_BROKEN"):
            self.reserve()

    def test_unknown_mission_and_unapproved_step_denied(self):
        with self.assertRaisesRegex(RuntimeError,"SIGNED_MISSION_NOT_AT_GATE"):
            self.broker.reserve("different",self.request,self.sig,self.refs)


if __name__=="__main__":
    unittest.main()
