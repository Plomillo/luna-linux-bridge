"""Global root registry adversarial tests: no sudo, no root deployment.

Root ownership is bypassed ONLY via mocked helper functions in test fixtures.
The production GlobalScopeRegister always checks true UID and root paths.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import global_scope_register as registry


class SyntheticStrongVerifier:
    def __init__(self,bad=False):
        self.calls=0
        self.bad=bad
    def preflight(self,path,sig,receipts,*,strong,expected_host,expected_boot):
        self.calls+=1
        assert strong is True and len(receipts)==4
        req=json.loads(Path(path).read_text())
        return {"status":"SIGNED_RECEIPTS_CRYPTOGRAPHICALLY_VERIFIED",
            "scope_id":req["scope_id"], "capability":req["capability"],
            "host":expected_host, "boot_id":expected_boot,
            "strong_second_order_receipts_verified":True,
            "execution_authorized_by_this_verifier":False,
            "certified":bool(self.bad),
            "hashes":{"request_sha256":hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                "g23_sha256":"1"*64,"g24_sha256":"2"*64,
                "g23_2_sha256":"3"*64,"g24_2_sha256":"4"*64}}


class GlobalScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.db=self.root/"root-global"
        self.db.mkdir(mode=0o700)
        self.source=self.root/"known.py"
        self.source.write_bytes(b"TEST_FIXTURE_PINNED")
        self.request=self.root/"request.json"
        self.operation="8"*64
        self.ref={role:{"document":"TEST_"+role,"signature":"TEST_"+role}
                  for role in registry.ROLES}
        self.v= SyntheticStrongVerifier()
        self.instance=registry.GlobalScopeRegister(self.db)
        self.payload={
            "schema":"LRB_SCOPED_REQUEST/0.3",
            "scope_id":"GLOBAL-ONE", "mission_id":"mission-one",
            "mission_sha256":"9"*64,"owner_objective_sha256":"a"*64,
            "host":"TEST_HOST","boot_id":"TEST_BOOT",
            "source_sha256":hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "capability":"CAP_STORAGE_INSPECT","risk":"ROOT_READONLY",
            "operation_sha256":self.operation,
            "deadline_utc":(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()
        }
        self.write()
        # Patch only filesystem UID checks in this unprivileged test; production
        # methods contain no testing switch and cannot authorize a root action.
        self.guard=patch.object(registry,"_protected_root",lambda root:None)
        self.file=patch.object(registry,"_pinned_file",lambda root:root/"GLOBAL_SCOPE.db")
        self.guard.start()
        self.file.start()
        self.addCleanup(self.guard.stop)
        self.addCleanup(self.file.stop)

    def write(self):
        self.request.write_text(json.dumps(self.payload,sort_keys=True))

    def attempt(self, instance=None, verifier=None):
        return (instance or self.instance).consume(
            request_path=self.request,owner_signature=self.root/"owner.sig",
            receipts=self.ref,verifier=verifier or self.v,
            expected_host="TEST_HOST",expected_boot="TEST_BOOT",
            source_path=self.source,operation_sha256=self.operation)

    def test_proof_is_no_root_authorization(self):
        r=self.attempt()
        self.assertEqual(r["status"],"CONSUMED_NO_DISPATCH")
        self.assertFalse(r["privileged_dispatch_performed"])
        self.assertFalse(r["execution_authorized_by_registry"])
        self.assertFalse(r["certified"])

    def test_duplicate_across_distinct_instances_rejected(self):
        self.attempt()
        other=registry.GlobalScopeRegister(self.db)
        with self.assertRaisesRegex(RuntimeError,"GLOBAL_SCOPE_REPLAY"):
            self.attempt(instance=other)

    def test_changed_scope_same_mission_rejected(self):
        self.attempt()
        self.payload["scope_id"]="GLOBAL-TWO"
        self.write()
        with self.assertRaisesRegex(RuntimeError,"GLOBAL_SCOPE_REPLAY"):
            self.attempt()

    def test_changed_mission_same_scope_rejected(self):
        self.attempt()
        self.payload["mission_sha256"]="7"*64
        self.write()
        with self.assertRaisesRegex(RuntimeError,"GLOBAL_SCOPE_REPLAY"):
            self.attempt()

    def test_explicit_operation_digest_mismatch_rejected(self):
        self.payload["operation_sha256"]="6"*64
        self.write()
        with self.assertRaisesRegex(RuntimeError,"SIGNED_OPERATION_IDENTITY_MISMATCH"):
            self.attempt()
        self.assertEqual(self.v.calls,0)

    def test_live_source_drift_rejected(self):
        self.source.write_text("UNEXPECTED_SOURCE")
        with self.assertRaisesRegex(RuntimeError,"SIGNED_EXECUTION_SCOPE_DRIFT"):
            self.attempt()

    def test_second_order_missing_rejected(self):
        del self.ref["G24_2"]
        with self.assertRaisesRegex(RuntimeError,"ALL_INDEPENDENT"):
            self.attempt()

    def test_self_certifying_result_denied_without_db_insert(self):
        with self.assertRaisesRegex(RuntimeError,"REPORT_UNTRUSTED"):
            self.attempt(verifier=SyntheticStrongVerifier(bad=True))
        self.assertEqual(self.attempt()["status"],"CONSUMED_NO_DISPATCH")


    def test_failed_verification_rolls_back_atomic_transaction(self):
        class Invalid:
            def preflight(self,*args,**kwargs):
                raise RuntimeError("INDEPENDENT_GATE_REJECTED")
        with self.assertRaisesRegex(RuntimeError,"INDEPENDENT_GATE_REJECTED"):
            self.attempt(verifier=Invalid())
        self.assertEqual(self.attempt()["status"],"CONSUMED_NO_DISPATCH")

    def test_simultaneous_cross_instance_only_one_wins(self):
        first=registry.GlobalScopeRegister(self.db)
        second=registry.GlobalScopeRegister(self.db)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(self.attempt,obj,SyntheticStrongVerifier())
                     for obj in (first,second)]
            outcomes=[]
            for future in futures:
                try:
                    outcomes.append(future.result()["status"])
                except RuntimeError as exc:
                    outcomes.append(str(exc))
        self.assertEqual(outcomes.count("CONSUMED_NO_DISPATCH"),1)
        self.assertEqual(outcomes.count("GLOBAL_SCOPE_REPLAY_OR_MISSION_DUPLICATION"),1)

    def test_production_root_guard_is_hard_requirement(self):
        self.guard.stop()
        try:
            if registry.os.geteuid()!=0:
                with self.assertRaisesRegex(RuntimeError,"ROOT_BROKER_ONLY"):
                    registry._protected_root(self.db)
        finally:
            self.guard.start()


if __name__=="__main__":
    unittest.main()
