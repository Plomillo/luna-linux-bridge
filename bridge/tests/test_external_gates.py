"""Cryptographic negative tests use disposable TEST keys, never production G23/G24.

Successful unit tests do NOT issue real certificates or confer root authority.
"""
from datetime import datetime,timezone,timedelta
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import external_gates as gates


@unittest.skipUnless(shutil.which("openssl"),"OpenSSL absent; release must HOLD")
class SignatureVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.base=Path(cls.tmp.name)
        cls.trust=cls.base/"trust"
        cls.trust.mkdir(mode=0o700)
        cls.privates={}
        signers={}
        for role in gates.ROLES:
            key=cls.base/(role.lower()+".key")
            pem=cls.trust/(role.lower()+".pem")
            subprocess.run(["openssl","genrsa","-out",str(key),"2048"],check=True,
                           capture_output=True,timeout=10)
            subprocess.run(["openssl","rsa","-in",str(key),"-pubout","-out",str(pem)],
                           check=True,capture_output=True,timeout=10)
            cls.privates[role]=key
            signers[role]={"issuer_id":"TEST_ISSUER_"+role,
                           "key_filename":pem.name,
                           "sha256":hashlib.sha256(pem.read_bytes()).hexdigest()}
        (cls.trust/"trust.json").write_text(json.dumps({
            "schema":"LRB_TRUST_ROOTS/0.3","signers":signers}))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.testtmp=tempfile.TemporaryDirectory()
        self.path=Path(self.testtmp.name)
        self.now=datetime(2030,1,1,tzinfo=timezone.utc)
        self.subject="c"*64
        self.verifier=gates.ExternalGateVerifier(self.trust,
                                enforce_root_owned=False,clock=lambda:self.now)
        req={"schema":"LRB_SCOPED_REQUEST/0.3",
             "mission_id":"TEST-ONLY","scope_id":"STORAGE_READONLY",
             "host":"TEST_HOST","boot_id":"TEST_BOOT",
             "source_sha256":self.subject,"capability":"CAP_STORAGE_INSPECT",
             "risk":"ROOT_READONLY","owner_objective_sha256":"b"*64,
             "deadline_utc":(self.now+timedelta(minutes=5)).isoformat()}
        self.request=self.path/"request.json"
        self.request.write_text(json.dumps(req,sort_keys=True))
        self.request_sig=self.sign("OWNER",self.request)
        self.request_hash=gates.sha256_bytes(self.request.read_bytes())
        self.docs={}

    def tearDown(self):
        self.testtmp.cleanup()

    def sign(self,role,doc):
        dest=Path(str(doc)+".sig")
        subprocess.run(["openssl","dgst","-sha256","-sign",str(self.privates[role]),
                        "-out",str(dest),str(doc)],check=True,capture_output=True,timeout=6)
        return dest

    def make_receipt(self,role,prior=None,issued=None,secondary=None):
        issued=issued or self.now
        obj={"schema":"LRB_SIGNED_GATE/0.3","role":role,"issuer_id":"TEST_ISSUER_"+role,
             "decision":"PASS","request_sha256":self.request_hash,
             "host":"TEST_HOST","boot_id":"TEST_BOOT","source_sha256":self.subject,
             "issued_utc":issued.isoformat(),
             "expires_utc":(issued+timedelta(minutes=5)).isoformat()}
        if prior:obj["depends_on_sha256"]=prior
        if secondary:obj["depends_on_secondary_sha256"]=secondary
        path=self.path/(role+".json")
        path.write_text(json.dumps(obj,sort_keys=True))
        self.docs[role]={"document":str(path),"signature":str(self.sign(role,path))}
        return gates.sha256_bytes(path.read_bytes())

    def valid_chain(self,strong=False):
        h23=self.make_receipt("G23")
        h24=self.make_receipt("G24",prior=h23)
        if strong:
            h232=self.make_receipt("G23_2",prior=h23)
            self.make_receipt("G24_2",prior=h24,secondary=h232)

    def verify(self,strong=False):
        return self.verifier.preflight(
            str(self.request),str(self.request_sig),self.docs,strong=strong,
            expected_host="TEST_HOST",expected_boot="TEST_BOOT")

    def test_signed_g23_g24_positive_but_cannot_execute(self):
        self.valid_chain()
        out=self.verify()
        self.assertEqual(out["status"],"SIGNED_RECEIPTS_CRYPTOGRAPHICALLY_VERIFIED")
        self.assertFalse(out["certified"])
        self.assertFalse(out["execution_authorized_by_this_verifier"])
        self.assertFalse(out["strong_second_order_receipts_verified"])

    def test_full_second_order_chain_positive_but_not_certified(self):
        self.valid_chain(strong=True)
        out=self.verify(strong=True)
        self.assertTrue(out["strong_second_order_receipts_verified"])
        self.assertFalse(out["issuer_independence_externally_audited"])
        self.assertFalse(out["certified"])

    def test_strong_gate_missing_second_order_fails(self):
        self.valid_chain()
        with self.assertRaisesRegex(RuntimeError,"INDEPENDENT_RECEIPTS_MISSING"):
            self.verify(strong=True)

    def test_owner_signature_tampering_fails(self):
        self.valid_chain()
        self.request.write_text(self.request.read_text()+" ")
        with self.assertRaisesRegex(RuntimeError,"INVALID_SIGNATURE_OWNER"):
            self.verify()

    def test_g23_signed_data_tampering_fails(self):
        self.valid_chain()
        file=Path(self.docs["G23"]["document"])
        file.write_text(file.read_text()+" ")
        with self.assertRaisesRegex(RuntimeError,"INVALID_SIGNATURE_G23"):
            self.verify()

    def test_g24_hash_dependency_fails(self):
        self.valid_chain()
        path=Path(self.docs["G24"]["document"])
        data=json.loads(path.read_text())
        data["depends_on_sha256"]="0"*64
        path.write_text(json.dumps(data,sort_keys=True))
        self.docs["G24"]["signature"]=str(self.sign("G24",path))
        with self.assertRaisesRegex(RuntimeError,"INDEPENDENT_GATE_CHAIN_MISMATCH_G24"):
            self.verify()

    def test_second_order_requires_both_gates(self):
        self.valid_chain(strong=True)
        path=Path(self.docs["G24_2"]["document"])
        data=json.loads(path.read_text())
        data["depends_on_secondary_sha256"]="0"*64
        path.write_text(json.dumps(data,sort_keys=True))
        self.docs["G24_2"]["signature"]=str(self.sign("G24_2",path))
        with self.assertRaisesRegex(RuntimeError,"SECOND_ORDER_SECONDARY_CHAIN_MISMATCH"):
            self.verify(strong=True)

    def test_wrong_machine_boot_fails(self):
        self.valid_chain()
        with self.assertRaisesRegex(RuntimeError,"OWNER_REQUEST_SCOPE_INVALID"):
            self.verifier.preflight(str(self.request),str(self.request_sig),self.docs,
                                    expected_host="TEST_HOST",expected_boot="DIFFERENT")

    def test_expired_signed_g23_fails(self):
        self.valid_chain()
        path=Path(self.docs["G23"]["document"])
        payload=json.loads(path.read_text())
        payload["issued_utc"]=(self.now-timedelta(hours=1)).isoformat()
        payload["expires_utc"]=(self.now-timedelta(minutes=30)).isoformat()
        path.write_text(json.dumps(payload,sort_keys=True))
        self.docs["G23"]["signature"]=str(self.sign("G23",path))
        with self.assertRaisesRegex(RuntimeError,"GATE_STALE_OR_INVALID_TIME"):
            self.verify()

    def test_scope_semantics_risk_cannot_change(self):
        data=json.loads(self.request.read_text())
        data["risk"]="ROOT_MUTATION"
        self.request.write_text(json.dumps(data,sort_keys=True))
        self.request_sig=self.sign("OWNER",self.request)
        with self.assertRaisesRegex(RuntimeError,"CAPABILITY_RISK_MISMATCH"):
            self.verify()

    def test_uncontrolled_trust_dir_rejected_in_production(self):
        with self.assertRaisesRegex(RuntimeError,"TRUST_PATH_WRITABLE_OR_SYMLINK|TRUST_PATH_NOT_ROOT_OWNED"):
            gates.ExternalGateVerifier(self.trust,enforce_root_owned=True,clock=lambda:self.now)

    def test_role_signatures_not_substitutable(self):
        self.valid_chain()
        self.docs["G24"]["signature"]=self.docs["G23"]["signature"]
        with self.assertRaisesRegex(RuntimeError,"INVALID_SIGNATURE_G24"):
            self.verify()


if __name__=="__main__":
    unittest.main()
