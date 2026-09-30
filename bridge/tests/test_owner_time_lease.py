"""Genuine synthetic OpenSSL owner signatures prove hot nonroot time-contract behavior."""
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import owner_time_lease as timelease
import lrb_core as base
CONTRACT_PATH=ROOT/"CONTRACT.v0.json"
CONTRACT=json.loads(CONTRACT_PATH.read_text())


class StubOwnerSignature:
    """Uses real OpenSSL with a TEMP test owner identity, not real authorization."""
    def __init__(self,pub):
        self.pub=pub
    def sig(self,role,doc,signature):
        if role!="OWNER":
            raise RuntimeError("ONLY_OWNER_PERMITTED")
        p=subprocess.run(["openssl","dgst","-sha256","-verify",str(self.pub),
                          "-signature",str(signature),str(doc)],
                         capture_output=True,timeout=5)
        if p.returncode!=0 or b"Verified OK" not in p.stdout:
            raise RuntimeError("INVALID_SIGNATURE_OWNER")


@unittest.skipUnless(shutil.which("openssl"),"release requires OpenSSL")
class OwnerTimeLeaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=tempfile.TemporaryDirectory()
        cls.parent=Path(cls.root.name)
        cls.key=cls.parent/"test-only.key"
        cls.pub=cls.parent/"test-only.pem"
        subprocess.run(["openssl","genrsa","-out",str(cls.key),"2048"],
                       check=True,capture_output=True,timeout=12)
        subprocess.run(["openssl","rsa","-in",str(cls.key),"-pubout","-out",str(cls.pub)],
                       check=True,capture_output=True,timeout=12)

    @classmethod
    def tearDownClass(cls):
        cls.root.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root_state=Path(self.temp.name)
        self.state=base.secure_state(self.root_state/"state")
        self.now=datetime(2030,1,1,tzinfo=timezone.utc)
        self.verifier=StubOwnerSignature(self.pub)
        self.lease=self.root_state/"lease.json"
        self.sig=self.root_state/"lease.sig"
        self.identity=self.valid()
        self.sign(self.identity)

    def tearDown(self):
        self.temp.cleanup()

    def valid(self):
        return {
           "schema":timelease.SCHEMA,
           "lease_id":"SIGNED_OWNER_TEST_0001",
           "owner_intent":"EXPLICIT_NONPRIVILEGED_BUDGET_CHANGE",
           "host":base.os.uname().nodename,
           "boot_id":base.boot_id(),
           "contract_sha256":hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),
           "controller_sha256":hashlib.sha256(Path(timelease.__file__).read_bytes()).hexdigest(),
           "expected_revision":0,
           "heartbeat_sec":25,
           "max_work_seconds":1400,
           "issued_utc":self.now.isoformat(),
           "expires_utc":(self.now+timedelta(minutes=10)).isoformat()
        }

    def sign(self,content):
        self.lease.write_text(json.dumps(content,sort_keys=True))
        subprocess.run(["openssl","dgst","-sha256","-sign",str(self.key),
                        "-out",str(self.sig),str(self.lease)],
                       check=True,capture_output=True,timeout=5)

    def apply(self):
        return timelease.apply_lease(self.state,CONTRACT,CONTRACT_PATH,
                   self.lease,self.sig,verifier=self.verifier,clock=lambda:self.now)

    def test_authorized_hot_extension_revisioned_without_root(self):
        before=base.load_time_policy(self.state,CONTRACT)
        assert before["max_work_seconds"]==1200
        report=self.apply()
        after=base.load_time_policy(self.state,CONTRACT)
        self.assertEqual(report["status"],"SIGNED_NONPRIVILEGED_TIME_POLICY_UPDATED")
        self.assertEqual(after["max_work_seconds"],1400)
        self.assertEqual(after["heartbeat_sec"],25)
        self.assertEqual(after["revision"],1)
        self.assertFalse(report["root_privilege_extended"])
        self.assertFalse(report["existing_g23_g24_extended"])
        self.assertFalse(report["certified"])
        self.assertTrue(base.EvidenceLedger(self.state).verify())

    def test_same_signed_lease_does_not_replay(self):
        self.apply()
        with self.assertRaisesRegex(RuntimeError,"REVISION_COLLISION|REPLAY"):
            self.apply()

    def test_signed_lease_cannot_exceed_hard_contract(self):
        payload=dict(self.identity)
        payload["max_work_seconds"]=CONTRACT["resource_defaults"]["hard_deadline_sec"]+1
        self.sign(payload)
        with self.assertRaisesRegex(RuntimeError,"HARD_LIMIT"):
            self.apply()
        self.assertEqual(base.load_time_policy(self.state,CONTRACT)["revision"],0)

    def test_tampered_signature_denied_and_state_unchanged(self):
        self.lease.write_text(self.lease.read_text()+" ")
        with self.assertRaisesRegex(RuntimeError,"INVALID_SIGNATURE_OWNER"):
            self.apply()
        self.assertEqual(base.load_time_policy(self.state,CONTRACT)["revision"],0)

    def test_wrong_host_or_boot_denied_after_real_signature(self):
        payload=dict(self.identity)
        payload["host"]="WRONG_HOST"
        self.sign(payload)
        with self.assertRaisesRegex(RuntimeError,"HOST_OR_BOOT_DRIFT"):
            self.apply()
        self.assertEqual(base.load_time_policy(self.state,CONTRACT)["revision"],0)

    def test_old_or_expired_signed_lease_denied(self):
        payload=dict(self.identity)
        payload["issued_utc"]=(self.now-timedelta(minutes=21)).isoformat()
        payload["expires_utc"]=(self.now-timedelta(minutes=1)).isoformat()
        self.sign(payload)
        with self.assertRaisesRegex(RuntimeError,"STALE"):
            self.apply()

    def test_unknown_fields_fails_closed_even_with_signature(self):
        payload=dict(self.identity)
        payload["sudo_bash"]="unrestricted"
        self.sign(payload)
        with self.assertRaisesRegex(RuntimeError,"FIELDS_UNREVIEWED"):
            self.apply()

    def test_existing_reduction_may_not_use_signed_lease_for_extra_privilege(self):
        base.update_time_policy(self.state,CONTRACT,0,20,600)
        payload=dict(self.identity)
        payload["expected_revision"]=1
        payload["max_work_seconds"]=750
        self.sign(payload)
        self.apply()
        current=base.load_time_policy(self.state,CONTRACT)
        self.assertEqual(current["max_work_seconds"],750)
        self.assertEqual(current["revision"],2)
        with self.assertRaisesRegex(RuntimeError,"EXTENDED_BUDGET_REQUIRES_NEW_AUTHORITY"):
            base.update_time_policy(self.state,CONTRACT,2,20,800)

    def test_incomplete_signed_owner_transaction_holds_all_policy_consumers(self):
        ledger=base.EvidenceLedger(self.state)
        ledger.append("OWNER_LEASE_INTENT",{"lease_id":"TEST_MIDCRASH"})
        with self.assertRaisesRegex(RuntimeError,"INCOMPLETE_SIGNED_TIME_LEASE"):
            base.load_time_policy(self.state,CONTRACT)
        with self.assertRaisesRegex(RuntimeError,"INCOMPLETE_SIGNED_TIME_LEASE"):
            base.update_time_policy(self.state,CONTRACT,0,25,800)

    def test_policy_file_rollback_denied_after_signing(self):
        self.apply()
        file=self.state/"TIME_POLICY.json"
        obj=json.loads(file.read_text())
        obj["revision"]=0
        file.write_text(json.dumps(obj))
        with self.assertRaisesRegex(RuntimeError,"SIGNED_TIME_POLICY_ROLLBACK_DENIED"):
            base.load_time_policy(self.state,CONTRACT)


if __name__=="__main__":
    unittest.main()
