"""PUAC2 contract validators for typed claims, causal events, authority, recovery and coverage.

These validators operationalize explicit clauses; they do not make PUAC2 canonically admitted
and do not replace G23/G24. Unknown or conflicting authority evidence is denied.
"""
from __future__ import annotations
from datetime import datetime,timezone
from typing import Any,Callable
from .model import is_sha256

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
 if claim.get("not_applicable") is True and not str(claim.get("not_applicable_basis","")).strip():
  return {"status":"HOLD","reasons":["NOT_APPLICABLE_REQUIRES_BASIS"],"semantic_key":key}
 conversion=claim.get("conversion")
 if conversion is not None:
  needed=("rule_id","source_unit","target_unit","evidence_reference","original_value","converted_value")
  absent=[k for k in needed if k not in conversion or conversion[k] is None]
  if absent:return {"status":"HOLD","reasons":["CONVERSION_EVIDENCE_MISSING:"+",".join(absent)],"semantic_key":key}
  if "original_value" in claim and conversion.get("original_value")!=claim.get("original_value"):
   return {"status":"DENY","reasons":["CONVERSION_DID_NOT_PRESERVE_ORIGINAL_VALUE"],"semantic_key":key}
 return {"status":"PASS","reasons":[],"claim_id":claim["claim_id"],"semantic_key":key,
         "claim_id_is_record_identity_not_semantic_key":True,"unit_of_measure":unit}
def classify_claim_conflicts(claims:list[dict[str,Any]])->dict[str,Any]:
 by_key={};by_id=set();errors=[];conflicts=[]
 for claim in claims:
  result=validate_claim_v2(claim)
  if result["status"]!="PASS":errors.extend(result["reasons"]);continue
  if claim["claim_id"] in by_id:errors.append("DUPLICATE_CLAIM_RECORD_ID:"+str(claim["claim_id"]))
  by_id.add(claim["claim_id"]);key=repr(result["semantic_key"])
  previous=by_key.get(key)
  if previous is not None and (previous.get("value")!=claim.get("value") or previous.get("evidence_state")!=claim.get("evidence_state")):
   conflicts.append({"semantic_key":key,"claim_ids":[previous.get("claim_id"),claim.get("claim_id")],"status":"CONFLICT"})
  else:by_key[key]=claim
 return {"status":"HOLD" if errors else ("CONFLICT" if conflicts else "PASS"),"errors":errors,"conflicts":conflicts,
         "claims_checked":len(claims),"direct_contradiction_requires_same_semantic_key":True}

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
def verify_authority_binding(binding:Any,*,action:str,object_id:str,scope_id:str,
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
         "activation_authorized":False if failed else True,"certification_propagation":False}

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
 return {"status":"MEASURED","requirements_total":len(required_ids),
  "documentation":{"covered":doc_count,"total":len(required_ids),"ratio":doc_count/len(required_ids)},
  "operational":{"covered":op_count,"total":len(required_ids),"ratio":op_count/len(required_ids)},
  "test_class_total_required":required_test_classes,"invariant_total_required":required_invariants,
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
def validate_puac_control(control_id:str,payload:Any,*,producer_identity:str|None=None,evaluator_identity:str|None=None)->dict[str,Any]:
 if control_id not in PUAC_CONTROL_OUTPUTS:return {"status":"HOLD","reasons":["CONTROL_ID_NOT_REGISTERED_LOCALLY"]}
 if not isinstance(payload,dict):return {"status":"HOLD","reasons":["CONTROL_EVIDENCE_PAYLOAD_MISSING"]}
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
 if control_id=="PUAC.C29":
  reproduction=payload.get("reproduction_report")
  if not isinstance(reproduction,dict) or reproduction.get("status")!="PASS":errors.append("REPRODUCTION_REPORT_NOT_PASS")
 if control_id=="PUAC.C31" and payload.get("restoration_evidence",{}).get("restoration_proven") is not True:
  errors.append("RESTORATION_EVIDENCE_NOT_PROVEN")
 if missing:return {"status":"HOLD","reasons":sorted(set(errors+["CONTROL_EVIDENCE_FIELDS_MISSING:"+",".join(sorted(set(missing)))])),"control_id":control_id,"canonical_admission":"NOT_GRANTED"}
 if errors:return {"status":"FAIL","reasons":sorted(set(errors)),"control_id":control_id,"canonical_admission":"NOT_GRANTED"}
 return {"status":"PASS_FOR_LOCAL_CONTROL_SCOPE","reasons":[],"control_id":control_id,"canonical_admission":"NOT_GRANTED",
         "does_not_replace_G23_G24":True}
