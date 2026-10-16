"""Scoped equivalence; no transport of authority, rights, signatures or certification."""
from typing import Any
from .model import is_sha256
FORBIDDEN={"binary_identity","authorization","signature","certification","canonical_authority","operational_activation","model_quality"}
def validate_equivalence(record:Any)->dict[str,Any]:
 if not isinstance(record,dict):return {"status":"UNPROVEN","issues":["EQUIVALENCE_RECORD_NOT_OBJECT"],"property_transport":"DENIED"}
 issues=[]
 if not is_sha256(record.get("source_sha256")) or not is_sha256(record.get("target_sha256")):issues.append("SOURCE_OR_TARGET_IDENTITY_INVALID")
 if not record.get("equivalence_specification_id") or not is_sha256(record.get("specification_sha256")):issues.append("EQUIVALENCE_SPECIFICATION_UNBOUND")
 if record.get("proof_status")!="VERIFIED" or record.get("proof_verified_by") in (None,"",record.get("producer_identity")):issues.append("INDEPENDENT_EQUIVALENCE_PROOF_MISSING")
 props=record.get("transportable_properties")
 if not isinstance(props,list) or not props:issues.append("TRANSPORTABLE_PROPERTIES_NOT_ENUMERATED");props=[]
 forbidden=sorted(set(props)&FORBIDDEN)
 if forbidden:issues.append("FORBIDDEN_PROPERTY_TRANSPORT:"+",".join(forbidden))
 if issues:return {"status":"UNPROVEN","issues":issues,"property_transport":"DENIED"}
 return {"status":"ADMISSIBLE_FOR_DECLARED_SCOPE","issues":[],"property_transport":sorted(set(props)),"authority_transfer":False,"certification_transfer":False}
