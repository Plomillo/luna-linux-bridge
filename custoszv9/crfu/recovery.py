"""Checkpoint integrity is not evidence of successful restoration."""
import hashlib
from typing import Any
from .model import is_sha256
def checkpoint_record(payload:bytes,*,checkpoint_id:str,state_identity:str,dependency_fingerprint:str)->dict[str,Any]:
 if not checkpoint_id or not state_identity or not is_sha256(dependency_fingerprint):raise ValueError("CHECKPOINT_IDENTITY_INVALID")
 return {"checkpoint_id":checkpoint_id,"state_identity":state_identity,"dependency_fingerprint":dependency_fingerprint,"payload_sha256":hashlib.sha256(payload).hexdigest(),"payload_size_bytes":len(payload),"restoration_proven":False,"status":"CHECKPOINT_CAPTURED_NOT_RESTORED"}
def verify_restoration(record:dict[str,Any],restored_payload:bytes,*,expected_state_identity:str,expected_dependency_fingerprint:str,invariants_pass:bool,journal_valid:bool)->dict[str,Any]:
 fail=[]
 if hashlib.sha256(restored_payload).hexdigest()!=record.get("payload_sha256") or len(restored_payload)!=record.get("payload_size_bytes"):fail.append("RESTORED_BYTES_MISMATCH")
 if expected_state_identity!=record.get("state_identity"):fail.append("RESTORED_STATE_IDENTITY_MISMATCH")
 if expected_dependency_fingerprint!=record.get("dependency_fingerprint"):fail.append("RESTORED_DEPENDENCY_MISMATCH")
 if invariants_pass is not True:fail.append("RESTORED_INVARIANTS_NOT_PROVEN")
 if journal_valid is not True:fail.append("EVIDENCE_JOURNAL_INVALID")
 return {"status":"PASS" if not fail else "BLOCKED","failures":fail,"restoration_proven":not fail,"certification_propagation":False}
