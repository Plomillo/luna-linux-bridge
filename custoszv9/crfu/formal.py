"""Exact-artifact proof bridge; absent independent proof evidence returns HOLD."""
from typing import Any
from .model import is_sha256
def validate_proof_bundle(bundle:Any,target_sha256:str,required_scope:str)->dict[str,Any]:
 if not isinstance(bundle,dict):return {"status":"HOLD","reasons":["PROOF_BUNDLE_NOT_OBJECT"],"proof_transport":"DENIED"}
 issues=[]
 if not is_sha256(target_sha256):issues.append("TARGET_SHA256_INVALID")
 if bundle.get("target_sha256")!=target_sha256:issues.append("PROOF_TARGET_IDENTITY_MISMATCH")
 if bundle.get("scope")!=required_scope:issues.append("PROOF_SCOPE_MISMATCH")
 if not is_sha256(bundle.get("specification_sha256")):issues.append("SPECIFICATION_IDENTITY_MISSING")
 tool=bundle.get("toolchain")
 if not isinstance(tool,dict) or not tool.get("name") or not tool.get("version"):issues.append("FORMAL_TOOLCHAIN_UNBOUND")
 if not isinstance(bundle.get("assumptions"),list) or not isinstance(bundle.get("limitations"),list):issues.append("ASSUMPTIONS_OR_LIMITATIONS_MISSING")
 if bundle.get("status") not in {"PASS","PASS_WITH_LIMITATIONS"}:issues.append("FORMAL_RESULT_NOT_PASS")
 if bundle.get("evidence_verified") is not True:issues.append("FORMAL_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED")
 if issues:return {"status":"HOLD","reasons":issues,"proof_transport":"DENIED","claim":"NO_FORMAL_CORRECTNESS_CLAIM"}
 return {"status":"PASS_FOR_DECLARED_SCOPE","reasons":[],"proof_transport":"ONLY_EXPLICITLY_LISTED_PROPERTIES","transportable_properties":bundle.get("transportable_properties",[]),"not_transported":["binary_identity","authorization","signatures","certification","canonical_authority","empirical_model_quality"]}
