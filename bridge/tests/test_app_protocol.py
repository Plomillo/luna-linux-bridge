"""P02 LRB_APP/0.4 typed protocol verification."""
import copy
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import app_protocol as app
import lrb_core as base

NOW=dt.datetime(2026,10,7,18,0,0,tzinfo=dt.timezone.utc)
SOURCE="a"*64
EVIDENCE="b"*64

def envelope(kind,payload,nonce="0123456789abcdef0123456789abcdef"):
    h,size=app.payload_identity(payload)
    return {
      "schema":app.SCHEMA,"version":app.VERSION,"message_type":kind,
      "operation_id":"op-001","mission_id":"MIS-TEST","session_id":"session-001",
      "scope":"V04_TEST_ONLY","payload_sha256":h,"payload_size":size,
      "deadline_utc":"2026-10-07T18:10:00Z","replay_nonce":nonce,
      "provenance":{"source_sha256":SOURCE,"actor":"CUSTOSZ_V7","authority":"Louksna.md"},
      "evidence_ref":EVIDENCE,"payload":payload
    }

PAYLOADS={
 "CHAT":{"text":"hola","turn_id":"t1"},
 "ARTIFACT_TRANSFER":{"artifact_id":"a1","sha256":"c"*64,"size_bytes":9,"mime":"text/plain","action":"NEGOTIATE"},
 "VOICE_SESSION":{"action":"START","turn_id":"t1"},
 "TRANSCRIPT":{"text":"hola","language":"es","turn_id":"t1"},
 "TTS":{"text":"hola","voice":"SABELA","route":"CHATTERBOX_ES_ES_SELF_HOSTED_API","turn_id":"t1"},
 "REASONING_REQUEST":{"text":"razona","effort_profile":"Alto","turn_id":"t1"},
 "GITHUB_OPERATION":{"capability_id":"repo.read","action":"probe","target":"sandbox","mutation":False}
}

class TypedProtocolTests(unittest.TestCase):
    def test_all_seven_registered_types_validate_without_authority(self):
        for idx,(kind,payload) in enumerate(PAYLOADS.items()):
            with self.subTest(kind=kind):
                env=envelope(kind,payload,nonce=("%032x"%(idx+1)))
                r=app.validate(env,now=NOW)
                self.assertEqual(r["status"],"VALIDATED_NOT_AUTHORIZED")
                self.assertFalse(r["execution_authorized"])
                self.assertFalse(r["certified"])
                self.assertFalse(r["active"])

    def test_unknown_type_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["message_type"]="SUDO"
        with self.assertRaisesRegex(RuntimeError,"MESSAGE_TYPE_UNREGISTERED"): app.validate(e,now=NOW)

    def test_extra_field_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["surprise"]=1
        with self.assertRaisesRegex(RuntimeError,"ENVELOPE_FIELDS"): app.validate(e,now=NOW)

    def test_hash_mismatch_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["payload_sha256"]="0"*64
        with self.assertRaisesRegex(RuntimeError,"HASH_MISMATCH"): app.validate(e,now=NOW)

    def test_size_mismatch_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["payload_size"]+=1
        with self.assertRaisesRegex(RuntimeError,"SIZE_MISMATCH"): app.validate(e,now=NOW)

    def test_expired_deadline_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["deadline_utc"]="2026-10-07T17:00:00Z"
        with self.assertRaisesRegex(RuntimeError,"DEADLINE_EXPIRED"): app.validate(e,now=NOW)

    def test_far_deadline_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["deadline_utc"]="2026-10-08T18:00:00Z"
        with self.assertRaisesRegex(RuntimeError,"DEADLINE_OUT_OF_BOUNDS"): app.validate(e,now=NOW)

    def test_empty_scope_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["scope"]=""
        with self.assertRaisesRegex(RuntimeError,"SCOPE_REQUIRED"): app.validate(e,now=NOW)

    def test_authority_drift_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["provenance"]["authority"]="OTHER"
        with self.assertRaisesRegex(RuntimeError,"AUTHORITY_DRIFT"): app.validate(e,now=NOW)

    def test_replay_denied(self):
        with tempfile.TemporaryDirectory() as td:
            guard=app.ReplayGuard(Path(td)/"state")
            e=envelope("CHAT",PAYLOADS["CHAT"])
            app.validate(e,replay_guard=guard,now=NOW)
            with self.assertRaisesRegex(RuntimeError,"REPLAY_DETECTED"): app.validate(e,replay_guard=guard,now=NOW)

    def test_tts_voice_identity_drift_denied(self):
        p=copy.deepcopy(PAYLOADS["TTS"]); p["voice"]="OTHER"
        e=envelope("TTS",p)
        with self.assertRaisesRegex(RuntimeError,"VOICE_IDENTITY_DRIFT"): app.validate(e,now=NOW)

    def test_github_mutation_is_typed_not_authorized(self):
        p=copy.deepcopy(PAYLOADS["GITHUB_OPERATION"]); p["mutation"]=True
        r=app.validate(envelope("GITHUB_OPERATION",p),now=NOW)
        self.assertFalse(r["execution_authorized"])
        self.assertFalse(r["privileged_execution"])

    def test_ledger_binding_is_hash_chained(self):
        with tempfile.TemporaryDirectory() as td:
            state=base.secure_state(Path(td)/"state")
            ledger=base.EvidenceLedger(state)
            r=app.validate(envelope("CHAT",PAYLOADS["CHAT"]),ledger=ledger,now=NOW)
            self.assertEqual(r["ledger_entry_hash"],ledger.verify())

if __name__=="__main__":
    unittest.main()
