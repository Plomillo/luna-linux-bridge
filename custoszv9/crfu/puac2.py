"""PUAC2 contract validators for typed claims, causal events, authority, recovery and coverage.

These validators operationalize explicit clauses; they do not make PUAC2 canonically admitted
and do not replace G23/G24. Unknown or conflicting authority evidence is denied.
"""
from __future__ import annotations
from datetime import datetime,timezone
from typing import Any,Callable
from .model import is_sha256, canonical_json, sha256_bytes
import re

EVIDENCE_STATES={"SUPPORTED","REFUTED","UNKNOWN","CONFLICT"}
def _time(value:Any)->datetime|None:
 if not isinstance(value,str) or not value.strip():return None
 try:
  dt=datetime.fromisoformat(value.replace("Z","+00:00"))
  return dt if dt.tzinfo is not None else None
 except ValueError:return None
def _interval(value:Any,now:datetime|None=None)->list[str]:
 errors=[]
 if not isinstance(value,dict):return ["VALIDITY_INTERVAL_NOT_TYPED_OBJECT"]
 start=_time(value.get("not_before_utc"));end=_time(value.get("expires_at_utc"))
 if start is None:errors.append("VALIDITY_START_INVALID")
 if end is None:errors.append("VALIDITY_EXPIRY_INVALID")
 if start and end and start>=end:errors.append("VALIDITY_INTERVAL_EMPTY_OR_REVERSED")
 now=now or datetime.now(timezone.utc)
 if start and now<start:errors.append("AUTHORITY_NOT_YET_VALID")
 if end and now>=end:errors.append("AUTHORITY_EXPIRED")
 return errors

def validate_claim_v2(claim:Any)->dict[str,Any]:
 if not isinstance(claim,dict):return {"status":"DENY","reasons":["CLAIM_NOT_OBJECT"]}
 required=("claim_id","subject_id","property_id","scope_id","context_id","version","validity_interval","unit_of_measure")
 missing=[k for k in required if k not in claim or claim[k] is None or claim[k]==""]
 if missing:return {"status":"HOLD","reasons":["CLAIM_FIELDS_MISSING:"+",".join(missing)]}
 key=tuple(claim[k] for k in ("subject_id","property_id","scope_id","context_id","version","validity_interval","unit_of_measure"))
 unit=claim["unit_of_measure"];unit_errors=[]
 if isinstance(unit,dict):
  if not unit.get("unit_id") or not unit.get("dimension") or not unit.get("version"):unit_errors.append("UNIT_ID_DIMENSION_VERSION_REQUIRED")
  if unit.get("dimension")=="dimensionless" and not unit.get("dimensionless_declared",False):unit_errors.append("DIMENSIONLESS_MUST_BE_EXPLICIT")
 elif unit=="dimensionless":
  pass
 else:unit_errors.append("UNIT_OF_MEASURE_NOT_TYPED")
 interval_errors=_interval(claim["validity_interval"])
 if interval_errors:return {"status":"HOLD","reasons":interval_errors,"semantic_key":key}
 if unit_errors:return {"status":"HOLD","reasons":unit_errors,"semantic_key":key}
 if claim.get("evidence_state") not in EVIDENCE_STATES:
  return {"status":"HOLD","reasons":["CLAIM_EVIDENCE_STATE_INVALID_OR_MISSING"],"semantic_key":key}
 if claim.get("not_applicable") is True and not str(claim.get("not_applicable_basis","")).strip():
  return {"status":"HOLD","reasons":["NOT_APPLICABLE_REQUIRES_BASIS"],"semantic_key":key}
 conversion=claim.get("conversion")
 if conversion is not None:
  needed=("rule_id","source_unit","target_unit","evidence_reference","original_value","converted_value")
  absent=[k for k in needed if k not in conversion or conversion[k] is None]
  if absent:return {"status":"HOLD","reasons":["CONVERSION_EVIDENCE_MISSING:"+",".join(absent)],"semantic_key":key}
  if "original_value" in claim and conversion.get("original_value")!=claim.get("original_value"):
   return {"status":"DENY","reasons":["CONVERSION_DID_NOT_PRESERVE_ORIGINAL_VALUE"],"semantic_key":key}
 return {"status":"PASS_SCHEMA_ONLY","reasons":[],"claim_id":claim["claim_id"],"semantic_key":key,
         "evidence_state":claim["evidence_state"],"claim_truth_asserted":False,
         "claim_id_is_record_identity_not_semantic_key":True,"unit_of_measure":unit}
def classify_claim_conflicts(claims:list[dict[str,Any]])->dict[str,Any]:
 by_key={};by_id=set();errors=[];conflicts=[]
 for claim in claims:
  result=validate_claim_v2(claim)
  if result["status"]!="PASS_SCHEMA_ONLY":errors.extend(result["reasons"]);continue
  if claim["claim_id"] in by_id:errors.append("DUPLICATE_CLAIM_RECORD_ID:"+str(claim["claim_id"]))
  by_id.add(claim["claim_id"]);key=repr(result["semantic_key"])
  previous=by_key.get(key)
  if previous is not None and (previous.get("value")!=claim.get("value") or previous.get("evidence_state")!=claim.get("evidence_state")):
   conflicts.append({"semantic_key":key,"claim_ids":[previous.get("claim_id"),claim.get("claim_id")],"status":"CONFLICT"})
  else:by_key[key]=claim
 return {"status":"HOLD" if errors else ("CONFLICT" if conflicts else "VALID_SCHEMA_NO_KEY_CONFLICTS"),"errors":errors,"conflicts":conflicts,
         "claims_checked":len(claims),"claim_truth_asserted":False,"direct_contradiction_requires_same_semantic_key":True}

def validate_event_records(events:Any)->dict[str,Any]:
 if not isinstance(events,list) or not events:return {"status":"HOLD","reasons":["EVENT_RECORD_SET_EMPTY_OR_INVALID"]}
 required=("event_id","event_time_utc","observed_at_utc","recorded_at_utc","sequence_number","causal_parents")
 index={};seqs=set();errors=[];holds=[]
 for e in events:
  if not isinstance(e,dict):errors.append("EVENT_NOT_OBJECT");continue
  missing=[k for k in required if k not in e]
  if missing:holds.append("EVENT_FIELDS_MISSING:"+",".join(missing));continue
  eid=e.get("event_id")
  if not isinstance(eid,str) or not eid.strip():errors.append("EVENT_ID_INVALID");continue
  if eid in index:errors.append("DUPLICATE_EVENT_ID:"+eid);continue
  index[eid]=e
  for k in ("event_time_utc","observed_at_utc","recorded_at_utc"):
   if _time(e.get(k)) is None:errors.append("EVENT_TIMESTAMP_INVALID:"+eid+":"+k)
  n=e.get("sequence_number")
  if isinstance(n,bool) or not isinstance(n,int) or n<1:errors.append("EVENT_SEQUENCE_INVALID:"+eid)
  elif n in seqs:errors.append("DUPLICATE_SEQUENCE_NUMBER:"+str(n))
  else:seqs.add(n)
  if not isinstance(e.get("causal_parents"),list):errors.append("CAUSAL_PARENTS_NOT_LIST:"+eid)
  elif any(not isinstance(p,str) or not p.strip() for p in e["causal_parents"]):errors.append("CAUSAL_PARENT_ID_INVALID:"+eid)
 if holds or errors:return {"status":"HOLD" if holds and not errors else "FAIL","reasons":holds+errors,"event_count":len(index)}
 for eid,e in index.items():
  for parent in e["causal_parents"]:
   if parent not in index:holds.append("CAUSAL_PARENT_UNRESOLVED:"+eid+":"+str(parent))
   if parent==eid:errors.append("EVENT_SELF_CAUSAL_CYCLE:"+eid)
 graph={eid:list(e["causal_parents"]) for eid,e in index.items()};visiting=set();visited=set()
 def visit(eid:str)->bool:
  if eid in visiting:return False
  if eid in visited:return True
  visiting.add(eid)
  for parent in graph[eid]:
   if parent in graph and not visit(parent):return False
  visiting.remove(eid);visited.add(eid);return True
 for eid in graph:
  if not visit(eid):errors.append("CAUSAL_CYCLE_DETECTED");break
 if errors:return {"status":"FAIL","reasons":sorted(set(errors)),"event_count":len(index)}
 if holds:return {"status":"HOLD","reasons":sorted(set(holds)),"event_count":len(index)}
 return {"status":"PASS","reasons":[],"event_count":len(index),"causal_graph_acyclic":True,
         "event_time_observed_time_recorded_time_distinguished":True,
         "time_order_alone_not_used_as_causality":True}

AUTHORITY_FIELDS=("binding_id","actor_id","actor_identity_proof","role_id","issuer_id","issuer_authority_proof",
 "action","object_id","scope_id","validity_interval","delegation_chain","revocation_state","provenance_id")
def validate_authority_binding(binding:Any,*,action:str,object_id:str,scope_id:str,
                             trust_verifier:Callable[[dict[str,Any]],dict[str,Any]]|None,
                             now:datetime|None=None)->dict[str,Any]:
 if not isinstance(binding,dict):return {"status":"DENY","reason":"AUTHORITY_BINDING_NOT_OBJECT"}
 missing=[k for k in AUTHORITY_FIELDS if k not in binding or binding[k] is None or binding[k]==""]
 if missing:return {"status":"DENY","reason":"AUTHORITY_BINDING_FIELDS_MISSING","fields":missing}
 if binding.get("action")!=action or binding.get("object_id")!=object_id or binding.get("scope_id")!=scope_id:
  return {"status":"DENY","reason":"ACTION_OBJECT_OR_SCOPE_MISMATCH"}
 if not isinstance(binding.get("delegation_chain"),list):return {"status":"DENY","reason":"DELEGATION_CHAIN_INVALID"}
 if binding.get("revocation_state")!="NOT_REVOKED":return {"status":"DENY","reason":"AUTHORITY_REVOKED_OR_UNKNOWN"}
 interval=_interval(binding.get("validity_interval"),now)
 if interval:return {"status":"DENY","reason":"AUTHORITY_VALIDITY_NOT_PROVEN","details":interval}
 if binding.get("signature_required") is True and not binding.get("signature_if_required"):
  return {"status":"DENY","reason":"REQUIRED_SIGNATURE_MISSING"}
 if trust_verifier is None:return {"status":"DENY","reason":"TRUSTED_IDENTITY_AND_DELEGATION_VERIFIER_UNAVAILABLE"}
 verified=trust_verifier(dict(binding))
 if not isinstance(verified,dict) or verified.get("status")!="PASS" or verified.get("binding_id")!=binding["binding_id"]:
  return {"status":"DENY","reason":"IDENTITY_DELEGATION_OR_ISSUER_PROOF_NOT_VERIFIED"}
 if verified.get("least_privilege_verified") is not True:return {"status":"DENY","reason":"LEAST_PRIVILEGE_NOT_VERIFIED"}
 return {"status":"PASS","binding_id":binding["binding_id"],"action":action,"object_id":object_id,"scope_id":scope_id,
         "actor_id":binding["actor_id"],"authorization_grant":True,"provenance_id":binding["provenance_id"]}

RECOVERY_FIELDS=("incident_id","authorized_actor","checkpoint_id","checkpoint_hash","target_environment","dependency_hashes",
 "restoration_oracles","nonregression_plan","rollback_scope","irreversible_side_effects","authority_ref")
def validate_recovery_plan(plan:Any)->dict[str,Any]:
 if not isinstance(plan,dict):return {"status":"HOLD","reasons":["RECOVERY_PLAN_NOT_OBJECT"]}
 missing=[k for k in RECOVERY_FIELDS if k not in plan]
 errors=[]
 if not is_sha256(plan.get("checkpoint_hash")):errors.append("CHECKPOINT_HASH_INVALID")
 for k in ("dependency_hashes","restoration_oracles","irreversible_side_effects"):
  if not isinstance(plan.get(k),list):errors.append("RECOVERY_LIST_INVALID:"+k)
  elif k=="dependency_hashes" and any(not is_sha256(h) for h in plan[k]):errors.append("DEPENDENCY_HASH_INVALID")
 for k in ("incident_id","authorized_actor","checkpoint_id","target_environment","nonregression_plan","rollback_scope","authority_ref"):
  if not isinstance(plan.get(k),str) or not plan[k].strip():errors.append("RECOVERY_FIELD_INVALID:"+k)
 return {"status":"HOLD" if missing else ("FAIL" if errors else "PASS"),
         "reasons":(["RECOVERY_FIELDS_MISSING:"+",".join(missing)] if missing else [])+errors,
         "reversibility_proven":False,"execution_or_restoration_not_inferred_from_plan":True}
def evaluate_incident_closure(evidence:Any)->dict[str,Any]:
 required=("diagnosis_verified","correction_authorized","correction_executed","restoration_verified",
           "nonregression_verified","traceability_complete","g23_g24_required","g23_g24_pass",
           "new_operational_authorization")
 if not isinstance(evidence,dict):return {"status":"HOLD","reasons":["INCIDENT_EVIDENCE_NOT_OBJECT"]}
 missing=[k for k in required if k not in evidence]
 if missing:return {"status":"HOLD","reasons":["INCIDENT_CLOSURE_EVIDENCE_MISSING:"+",".join(missing)]}
 failed=[]
 for key in ("diagnosis_verified","correction_authorized","correction_executed","restoration_verified","nonregression_verified","traceability_complete"):
  if evidence.get(key) is not True:failed.append(key.upper()+"_NOT_PROVEN")
 if evidence.get("g23_g24_required") is True and evidence.get("g23_g24_pass") is not True:failed.append("G23_G24_REQUIRED_BUT_NOT_PASS")
 if evidence.get("new_operational_authorization") is not True:failed.append("NEW_OPERATIONAL_AUTHORIZATION_MISSING")
 return {"status":"PASS" if not failed else "BLOCKED","reasons":failed,"incident_closed":not failed,
         "activation_authorized":False,"reactivation_requires_separate_authorization_controller":True,"certification_propagation":False}

def coverage_report(requirements:Any,documented_requirement_ids:Any,operational_evidence:Any,
                    *,required_test_classes:int=28,required_invariants:int=16,target_sha256:str|None=None)->dict[str,Any]:
 if not isinstance(requirements,list) or not requirements:
  return {"status":"HOLD","reason":"CRITICAL_REQUIREMENT_SET_EMPTY_OR_UNKNOWN","documentation_coverage":None,"operational_coverage":None}
 required_ids={r.get("requirement_id") for r in requirements if isinstance(r,dict) and r.get("requirement_id")}
 if not required_ids:return {"status":"HOLD","reason":"REQUIREMENTS_NOT_IDENTIFIED","documentation_coverage":None,"operational_coverage":None}
 documented=set(documented_requirement_ids) if isinstance(documented_requirement_ids,(list,set,tuple)) else set()
 operational=set()
 if isinstance(operational_evidence,list):
  for e in operational_evidence:
   if not isinstance(e,dict) or e.get("status")!="PASS" or e.get("reference_only") is True:continue
   if target_sha256 is not None and e.get("target_sha256")!=target_sha256:continue
   rid=e.get("requirement_id")
   if rid in required_ids:operational.add(rid)
 doc_count=len(required_ids&documented);op_count=len(required_ids&operational)
 test_ids=set();invariant_ids=set()
 if isinstance(operational_evidence,list):
  for e in operational_evidence:
   if not isinstance(e,dict) or e.get("status")!="PASS" or e.get("reference_only") is True:continue
   if target_sha256 is not None and e.get("target_sha256")!=target_sha256:continue
   ident=e.get("test_class_id")
   if e.get("record_type")=="TEST_CLASS" and isinstance(ident,str) and ident.strip():test_ids.add(ident)
   ident=e.get("invariant_id")
   if e.get("record_type")=="INVARIANT" and isinstance(ident,str) and ident.strip():invariant_ids.add(ident)
 return {"status":"MEASURED","requirements_total":len(required_ids),
  "documentation":{"covered":doc_count,"total":len(required_ids),"ratio":doc_count/len(required_ids)},
  "operational":{"covered":op_count,"total":len(required_ids),"ratio":op_count/len(required_ids)},
  "T_operational":{"passed":len(test_ids),"total":required_test_classes,"ratio":len(test_ids)/required_test_classes if required_test_classes else None},
  "I_operational":{"proven":len(invariant_ids),"total":required_invariants,"ratio":len(invariant_ids)/required_invariants if required_invariants else None},
  "target_artifact_binding_required":target_sha256 is not None,
  "reference_only_evidence_excluded":True,"g23_g24_not_replaced_by_coverage":True}

PUAC_CONTROL_OUTPUTS={
 "PUAC.C25":("approved_scope","claim_registry","acceptance_criteria","exclusions","scope_evidence"),
 "PUAC.C26":("assurance_case","evidence_coverage","unresolved_claims","argumentation_record"),
 "PUAC.C27":("independence_assessment","allowed_evaluators","separation_evidence","actor_registry","role_assignments","evaluation_plan","conflict_of_interest_records"),
 "PUAC.C28":("risk_register","threat_assessment","treatment_plan","residual_risk_record","threat_model","dependency_graph","risk_criteria"),
 "PUAC.C29":("integrity_report","reproduction_report","provenance_attestation","supply_chain_evidence","artifact_bytes_identity","manifest","dependency_lock","build_recipe","execution_environment"),
 "PUAC.C30":("impact_graph","regression_results","preserved_claims","invalidated_claims","revalidation_plan","previous_baseline","candidate_build","change_set","dependency_graph","previous_evidence"),
 "PUAC.C31":("rollback_test","restoration_evidence","recovery_limitations","operation_plan","checkpoint","restoration_procedure","expected_state"),
 "PUAC.C32":("assurance_status","impact_assessment","suspension_recommendation","revalidation_request","recertification_request","monitoring_profile","observations","change_events")
}
PUAC_CONTROL_TRUE_FLAGS={
 "PUAC.C25":("scope_unambiguous","critical_properties_accounted_for"),
 "PUAC.C26":("all_claims_have_argumentation","evidence_provenance_complete","premises_declared","limitations_visible","no_circular_argumentation","claims_within_evidence_strength"),
 "PUAC.C27":("identities_verified","permissions_verified","conflicts_declared","separation_verified"),
 "PUAC.C28":("risks_classified","treatments_traceable","residual_risks_explicit","residual_risks_authorized"),
 "PUAC.C29":("artifact_digest_verified","dependencies_pinned","provenance_verified","reproduction_verified"),
 "PUAC.C30":("direct_and_transitive_dependencies_examined","affected_tests_identified","invariants_preserved_or_blocked","invalidated_evidence_not_reused"),
 "PUAC.C31":("checkpoint_verified","restoration_tested","post_restore_integrity_verified"),
 "PUAC.C32":("monitoring_strategy_defined","observable_properties_identified","frequency_and_events_defined","incident_procedure_tested","monitoring_integrity_verified","authorization_current")
}
PUAC_CONTROL_FALSE_FLAGS={
 "PUAC.C25":("scope_open_or_contradictory","unsupported_claims_present","critical_property_omitted_without_authorization"),
 "PUAC.C26":("argumentation_circular","sources_unidentified","unsupported_claims_present"),
 "PUAC.C27":("self_evaluation_as_independent","conflicting_roles"),
 "PUAC.C28":("critical_prohibited_risk_present","essential_dependency_unknown","unauthorized_residual_risk"),
 "PUAC.C29":("hash_mismatch","unidentified_dependency","artifact_differs_from_evaluated_artifact"),
 "PUAC.C30":("unexplained_indirect_change","critical_regression","stale_evidence_reused"),
 "PUAC.C31":("checkpoint_invalid","restoration_unproven","recovered_state_unverified","hidden_dependency_prevents_recovery"),
 "PUAC.C32":("monitoring_stale","authorization_expired","incident_unmanaged")
}
def _validate_control_evidence_binding(control_id:str,payload:dict[str,Any],*,producer_identity:str|None,
                                             evaluator_identity:str|None,candidate_sha256:str|None)->dict[str,Any]:
 binding=payload.get("evidence_binding")
 if not isinstance(binding,dict):return {"status":"HOLD","reasons":["CONTROL_EVIDENCE_BINDING_MISSING"]}
 required=("schema","control_id","candidate_sha256","candidate_commit_sha","payload_sha256",
           "producer_identity","evaluator_identity","generated_at_utc","scope","source_evidence_refs")
 missing=[key for key in required if key not in binding or binding[key] is None or binding[key]==""]
 if missing:return {"status":"HOLD","reasons":["CONTROL_EVIDENCE_BINDING_FIELDS_MISSING:"+",".join(missing)]}
 errors=[]
 if binding.get("schema")!="PUAC2_CONTROL_EVIDENCE_BINDING/1.0":errors.append("CONTROL_EVIDENCE_BINDING_SCHEMA_INVALID")
 if binding.get("control_id")!=control_id:errors.append("CONTROL_EVIDENCE_CONTROL_ID_MISMATCH")
 if not is_sha256(binding.get("candidate_sha256")):errors.append("CONTROL_EVIDENCE_CANDIDATE_DIGEST_INVALID")
 elif candidate_sha256 and binding.get("candidate_sha256")!=candidate_sha256:errors.append("CONTROL_EVIDENCE_CANDIDATE_DIGEST_MISMATCH")
 if not isinstance(binding.get("candidate_commit_sha"),str) or re.fullmatch(r"[0-9a-f]{40}",binding["candidate_commit_sha"]) is None:
  errors.append("CONTROL_EVIDENCE_COMMIT_ID_INVALID")
 if not is_sha256(binding.get("payload_sha256")):errors.append("CONTROL_EVIDENCE_PAYLOAD_DIGEST_INVALID")
 else:
  unsigned={key:value for key,value in payload.items() if key!="evidence_binding"}
  observed=sha256_bytes(canonical_json(unsigned).encode("utf-8"))
  if observed!=binding.get("payload_sha256"):errors.append("CONTROL_EVIDENCE_PAYLOAD_DIGEST_MISMATCH")
 if not isinstance(binding.get("producer_identity"),str) or not binding["producer_identity"].strip():
  errors.append("CONTROL_EVIDENCE_PRODUCER_IDENTITY_MISSING")
 elif producer_identity is not None and binding["producer_identity"]!=producer_identity:
  errors.append("CONTROL_EVIDENCE_PRODUCER_IDENTITY_MISMATCH")
 if not isinstance(binding.get("evaluator_identity"),str) or not binding["evaluator_identity"].strip():
  errors.append("CONTROL_EVIDENCE_EVALUATOR_IDENTITY_MISSING")
 elif binding["evaluator_identity"]==binding.get("producer_identity"):
  errors.append("CONTROL_EVIDENCE_EXECUTOR_EVALUATOR_COLLISION")
 elif evaluator_identity is not None and binding["evaluator_identity"]!=evaluator_identity:
  errors.append("CONTROL_EVIDENCE_EVALUATOR_IDENTITY_MISMATCH")
 if _time(binding.get("generated_at_utc")) is None:errors.append("CONTROL_EVIDENCE_TIMESTAMP_INVALID")
 if not isinstance(binding.get("scope"),str) or not binding["scope"].strip():errors.append("CONTROL_EVIDENCE_SCOPE_MISSING")
 refs=binding.get("source_evidence_refs")
 if not isinstance(refs,list) or not refs:errors.append("CONTROL_EVIDENCE_SOURCE_REFERENCES_MISSING")
 elif any(not isinstance(item,dict) or not isinstance(item.get("sha256"),str) or not is_sha256(item.get("sha256")) or not item.get("uri") for item in refs):
  errors.append("CONTROL_EVIDENCE_SOURCE_REFERENCE_INVALID")
 return {"status":"FAIL" if errors else "PASS","reasons":sorted(set(errors)),
         "candidate_sha256":binding.get("candidate_sha256"),"candidate_commit_sha":binding.get("candidate_commit_sha"),
         "payload_sha256":binding.get("payload_sha256")}

def validate_puac_control(control_id:str,payload:Any,*,producer_identity:str|None=None,evaluator_identity:str|None=None,candidate_sha256:str|None=None,candidate_commit_sha:str|None=None)->dict[str,Any]:
 if control_id not in PUAC_CONTROL_OUTPUTS:return {"status":"HOLD","reasons":["CONTROL_ID_NOT_REGISTERED_LOCALLY"]}
 if not isinstance(payload,dict):return {"status":"HOLD","reasons":["CONTROL_EVIDENCE_PAYLOAD_MISSING"]}
 if candidate_sha256 is not None:
  bound=_validate_control_evidence_binding(control_id,payload,producer_identity=producer_identity,
      evaluator_identity=evaluator_identity,candidate_sha256=candidate_sha256)
  if bound["status"]=="HOLD":return {"status":"HOLD","reasons":bound["reasons"],"control_id":control_id,"canonical_admission":"NOT_GRANTED"}
  if bound["status"]!="PASS":return {"status":"FAIL","reasons":bound["reasons"],"control_id":control_id,"canonical_admission":"NOT_GRANTED"}
 missing=[k for k in PUAC_CONTROL_OUTPUTS[control_id] if k not in payload]
 errors=["CONTROL_OUTPUTS_MISSING:"+",".join(missing)] if missing else []
 for flag in PUAC_CONTROL_TRUE_FLAGS[control_id]:
  if flag not in payload:missing.append(flag)
  elif payload[flag] is not True:errors.append("REQUIRED_TRUE_FLAG_NOT_PROVEN:"+flag)
 for flag in PUAC_CONTROL_FALSE_FLAGS[control_id]:
  if flag not in payload:missing.append(flag)
  elif payload[flag] is not False:errors.append("PROHIBITED_CONDITION_PRESENT_OR_UNKNOWN:"+flag)
 if control_id=="PUAC.C26" and isinstance(payload.get("unresolved_claims"),list) and payload["unresolved_claims"]:
  errors.append("IN_SCOPE_CLAIMS_UNRESOLVED")
 if control_id=="PUAC.C27":
  evaluator=payload.get("evaluator_identity",evaluator_identity);producer=payload.get("producer_identity",producer_identity)
  if not evaluator or not producer or evaluator==producer:errors.append("EXECUTOR_EVALUATOR_NOT_DISTINCT")
 if control_id=="PUAC.C25":
  if not isinstance(payload.get("claim_registry"),(list,dict)):errors.append("CLAIM_REGISTRY_INVALID")
  if not isinstance(payload.get("acceptance_criteria"),(list,dict)):errors.append("ACCEPTANCE_CRITERIA_INVALID")
  scope_evidence=payload.get("scope_evidence")
  if not isinstance(scope_evidence,dict):errors.append("SCOPE_EVIDENCE_NOT_OBJECT")
  elif candidate_sha256 and scope_evidence.get("package_sha256")!=candidate_sha256:errors.append("SCOPE_NOT_BOUND_TO_CANDIDATE_DIGEST")
 if control_id=="PUAC.C26":
  if not isinstance(payload.get("unresolved_claims"),list):errors.append("UNRESOLVED_CLAIMS_NOT_LIST")
  elif payload["unresolved_claims"]:errors.append("IN_SCOPE_CLAIMS_UNRESOLVED")
  if not payload.get("assurance_case"):errors.append("ASSURANCE_CASE_EMPTY")
  if not payload.get("argumentation_record"):errors.append("ARGUMENTATION_RECORD_EMPTY")
 if control_id=="PUAC.C27":
  if not isinstance(payload.get("allowed_evaluators"),list) or not payload["allowed_evaluators"]:errors.append("ALLOWED_EVALUATORS_EMPTY")
  if not payload.get("separation_evidence"):errors.append("SEPARATION_EVIDENCE_EMPTY")
  evaluator=payload.get("evaluator_identity",evaluator_identity);producer=payload.get("producer_identity",producer_identity)
  if not evaluator or not producer or evaluator==producer:errors.append("EXECUTOR_EVALUATOR_NOT_DISTINCT")
 if control_id=="PUAC.C28":
  if not payload.get("threat_model") or not payload.get("risk_criteria"):errors.append("THREAT_MODEL_OR_RISK_CRITERIA_MISSING")
  if not payload.get("residual_risk_record"):errors.append("RESIDUAL_RISK_RECORD_EMPTY")
 if control_id=="PUAC.C29":
  reproduction=payload.get("reproduction_report")
  if not isinstance(reproduction,dict) or reproduction.get("status")!="PASS":errors.append("REPRODUCTION_REPORT_NOT_PASS")
  identity=payload.get("artifact_bytes_identity")
  if not isinstance(identity,dict) or not is_sha256(identity.get("sha256")):errors.append("ARTIFACT_BYTE_IDENTITY_INVALID")
  elif candidate_sha256 and identity.get("sha256")!=candidate_sha256:errors.append("ARTIFACT_BYTE_IDENTITY_MISMATCH")
  if not payload.get("dependency_lock") or not payload.get("build_recipe") or not payload.get("execution_environment"):errors.append("BUILD_PROVENANCE_CONTEXT_INCOMPLETE")
  if not payload.get("provenance_attestation") or not payload.get("supply_chain_evidence"):errors.append("PROVENANCE_OR_SUPPLY_CHAIN_EVIDENCE_MISSING")
 if control_id=="PUAC.C30":
  if not isinstance(payload.get("dependency_graph"),dict) or not isinstance(payload.get("impact_graph"),dict):errors.append("DEPENDENCY_OR_IMPACT_GRAPH_INVALID")
  build=payload.get("candidate_build")
  if not isinstance(build,dict):errors.append("CANDIDATE_BUILD_NOT_OBJECT")
  elif candidate_sha256 and build.get("package_sha256")!=candidate_sha256:errors.append("CANDIDATE_BUILD_DIGEST_MISMATCH")
  if not isinstance(payload.get("revalidation_plan"),(dict,list)):errors.append("REVALIDATION_PLAN_INVALID")
 if control_id=="PUAC.C31":
  restoration=payload.get("restoration_evidence")
  if not isinstance(restoration,dict) or restoration.get("restoration_proven") is not True:errors.append("RESTORATION_EVIDENCE_NOT_PROVEN")
  checkpoint=payload.get("checkpoint")
  if not isinstance(checkpoint,dict) or not is_sha256(checkpoint.get("sha256")):errors.append("CHECKPOINT_HASH_NOT_VERIFIED")
  elif isinstance(restoration,dict) and restoration.get("checkpoint_sha256")!=checkpoint.get("sha256"):errors.append("RESTORATION_CHECKPOINT_IDENTITY_MISMATCH")
  rollback=payload.get("rollback_test")
  if not isinstance(rollback,dict) or rollback.get("status")!="PASS":errors.append("ROLLBACK_TEST_NOT_PASS")
 if control_id=="PUAC.C32":
  profile=payload.get("monitoring_profile")
  if not isinstance(profile,dict) or not profile:errors.append("MONITORING_PROFILE_NOT_DEFINED")
  elif not profile.get("responsible_roles"):errors.append("MONITORING_RESPONSIBLE_ROLES_MISSING")
  if not isinstance(payload.get("observations"),list) or not isinstance(payload.get("change_events"),list):errors.append("MONITORING_OBSERVATIONS_OR_CHANGE_EVENTS_INVALID")
 if missing:return {"status":"HOLD","reasons":sorted(set(errors+["CONTROL_EVIDENCE_FIELDS_MISSING:"+",".join(sorted(set(missing)))])),"control_id":control_id,"canonical_admission":"NOT_GRANTED"}
 if errors:return {"status":"FAIL","reasons":sorted(set(errors)),"control_id":control_id,"canonical_admission":"NOT_GRANTED"}
 return {"status":"PASS_FOR_LOCAL_CONTROL_SCOPE","reasons":[],"control_id":control_id,"canonical_admission":"NOT_GRANTED",
         "does_not_replace_G23_G24":True}

def transitive_dependency_impact(dependency_graph:Any,changed_nodes:Any)->dict[str,Any]:
 """Compute reverse transitive dependents; unknown nodes and cycles are never silently ignored."""
 if not isinstance(dependency_graph,dict) or not isinstance(changed_nodes,(list,set,tuple)) or not changed_nodes:
  return {"status":"HOLD","reason":"DEPENDENCY_GRAPH_OR_CHANGED_SET_INVALID","impacted_nodes":[]}
 graph={}
 for node,deps in dependency_graph.items():
  if not isinstance(node,str) or not node.strip() or not isinstance(deps,list) or any(not isinstance(d,str) or not d.strip() for d in deps):
   return {"status":"HOLD","reason":"DEPENDENCY_EDGE_INVALID","node":str(node),"impacted_nodes":[]}
  graph[node]=set(deps)
 unknown=sorted({d for deps in graph.values() for d in deps if d not in graph})
 changed=set(changed_nodes)
 if not changed.issubset(set(graph)):
  return {"status":"HOLD","reason":"CHANGED_NODE_UNREGISTERED","unknown_changed_nodes":sorted(changed-set(graph)),"impacted_nodes":[]}
 if unknown:return {"status":"HOLD","reason":"DEPENDENCY_NODE_UNRESOLVED","unknown_dependencies":unknown,"impacted_nodes":[]}
 visiting=set();visited=set();cycle=[]
 def visit(node:str)->bool:
  if node in visiting:cycle.append(node);return False
  if node in visited:return True
  visiting.add(node)
  for dep in graph[node]:
   if not visit(dep):return False
  visiting.remove(node);visited.add(node);return True
 for node in graph:
  if not visit(node):return {"status":"FAIL","reason":"DEPENDENCY_CYCLE","cycle_nodes":sorted(set(cycle)),"impacted_nodes":[]}
 reverse={node:set() for node in graph}
 for node,deps in graph.items():
  for dep in deps:reverse[dep].add(node)
 impacted=set();frontier=list(changed)
 while frontier:
  current=frontier.pop()
  for dependent in reverse[current]:
   if dependent not in changed and dependent not in impacted:
    impacted.add(dependent);frontier.append(dependent)
 return {"status":"PASS","changed_nodes":sorted(changed),"impacted_nodes":sorted(impacted),
         "dependency_graph_complete":True,"transitive_closure":True}
