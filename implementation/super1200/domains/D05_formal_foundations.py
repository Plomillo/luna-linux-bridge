"""D05 formal-foundations primitives for capabilities 125-128.
These validators pin assumptions and artifacts; they do not prove univalence or theorems.
"""
from __future__ import annotations
import hashlib
import json
import re
from typing import Any

_SHA256=re.compile(r"^[0-9a-f]{64}$")

def canonical_json(value: Any) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")

def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()

def require_sha256(value: Any, field: str) -> str:
    if not isinstance(value,str) or not _SHA256.fullmatch(value):
        raise ValueError(field+"_must_be_lowercase_sha256")
    return value

def _name(value: Any, field: str) -> str:
    if not isinstance(value,str) or not value.strip():
        raise ValueError(field+"_required")
    return value.strip()

def _object(value: Any, field: str) -> dict[str,Any]:
    if not isinstance(value,dict):
        raise ValueError(field+"_must_be_object")
    return value

def explicit_assumption(*, assumption_id: str, statement: str, source_sha256: str, justification: str) -> dict[str,Any]:
    record={"schema":"SUPER1200_FORMAL_ASSUMPTION/1","assumption_id":_name(assumption_id,"assumption_id"),
      "statement":_name(statement,"assumption_statement"),"source_sha256":require_sha256(source_sha256,"source_sha256"),
      "justification":_name(justification,"assumption_justification"),
      "epistemic_status":"DECLARED_EXPLICIT_ASSUMPTION_NOT_PROVED","theorem_claim":False}
    record["assumption_sha256"]=digest(record)
    return record

def validate_univalence_profile(*, foundation_version: str, source_sha256: str,
                                assumptions: list[dict[str,Any]]) -> dict[str,Any]:
    foundation_version=_name(foundation_version,"foundation_version")
    require_sha256(source_sha256,"univalence_source_sha256")
    if not isinstance(assumptions,list) or not assumptions:
        raise ValueError("univalence_assumptions_required")
    normalized=[]; seen=set()
    for item in assumptions:
        _object(item,"univalence_assumption")
        aid=_name(item.get("assumption_id"),"univalence_assumption_id")
        unsigned=dict(item); recorded=unsigned.pop("assumption_sha256",None)
        if recorded!=digest(unsigned): raise ValueError("univalence_assumption_hash_mismatch:"+aid)
        if item.get("epistemic_status")!="DECLARED_EXPLICIT_ASSUMPTION_NOT_PROVED":
            raise ValueError("univalence_assumption_not_explicit:"+aid)
        if item.get("theorem_claim") is not False: raise ValueError("univalence_assumption_overclaims_theorem:"+aid)
        if aid in seen: raise ValueError("univalence_assumption_duplicate:"+aid)
        seen.add(aid); normalized.append(dict(item))
    normalized.sort(key=lambda x:x["assumption_id"])
    result={"schema":"SUPER1200_UNIVALENCE_PROFILE/1","foundation_version":foundation_version,
      "source_sha256":source_sha256,"assumptions":normalized,"decision":"DECLARED_ASSUMPTIONS_ONLY",
      "univalence_proved":False,"theorem_claim":False}
    result["profile_sha256"]=digest(result)
    return result

def bind_cubical_provider(*, provider_id: str, version: str, library_set_sha256: str,
                          adapter_schema_version: str, authority: str="NONE") -> dict[str,Any]:
    provider_id=_name(provider_id,"cubical_provider_id"); version=_name(version,"cubical_provider_version")
    adapter_schema_version=_name(adapter_schema_version,"adapter_schema_version")
    require_sha256(library_set_sha256,"cubical_library_set_sha256")
    if authority!="NONE": raise ValueError("cubical_provider_authority_must_be_NONE")
    result={"schema":"SUPER1200_CUBICAL_PROVIDER_BINDING/1","provider_id":provider_id,"version":version,
      "library_set_sha256":library_set_sha256,"adapter_schema_version":adapter_schema_version,"authority":"NONE",
      "provider_executed":False,"external_verification":"NOT_PERFORMED","theorem_claim":False}
    result["binding_sha256"]=digest(result)
    return result

def validate_higher_inductive_spec(spec: Any) -> dict[str,Any]:
    _object(spec,"higher_inductive_spec")
    type_name=_name(spec.get("type_name"),"hit_type_name")
    source_sha256=require_sha256(spec.get("source_sha256"),"hit_source_sha256")
    points=spec.get("point_constructors"); paths=spec.get("path_constructors"); rules=spec.get("computation_rules")
    if not isinstance(points,list) or not points: raise ValueError("hit_point_constructors_required")
    if not isinstance(paths,list): raise ValueError("hit_path_constructors_must_be_list")
    if not isinstance(rules,list): raise ValueError("hit_computation_rules_must_be_list")
    point_names=[]
    for point in points:
        _object(point,"hit_point_constructor"); point_names.append(_name(point.get("name"),"hit_point_constructor_name"))
        _name(point.get("type"),"hit_point_constructor_type")
    if len(set(point_names))!=len(point_names): raise ValueError("hit_constructor_name_duplicate")
    path_names=[]
    for path in paths:
        _object(path,"hit_path_constructor"); path_names.append(_name(path.get("name"),"hit_path_constructor_name"))
        if path.get("from") not in point_names or path.get("to") not in point_names:
            raise ValueError("hit_path_endpoint_unknown")
        _name(path.get("type"),"hit_path_constructor_type")
    if len(set(path_names))!=len(path_names) or set(path_names)&set(point_names):
        raise ValueError("hit_constructor_name_duplicate")
    known=set(point_names)|set(path_names); rule_ids=set(); normalized_rules=[]
    for rule in rules:
        _object(rule,"hit_computation_rule"); rid=_name(rule.get("rule_id"),"hit_rule_id")
        if rid in rule_ids: raise ValueError("hit_computation_rule_duplicate")
        rule_ids.add(rid)
        if rule.get("constructor") not in known or rule.get("result") not in known:
            raise ValueError("hit_computation_rule_unknown_constructor")
        normalized_rules.append(dict(rule))
    normalized_rules.sort(key=lambda x:x["rule_id"])
    result={"schema":"SUPER1200_HIT_SPEC_VALIDATION/1","type_name":type_name,"source_sha256":source_sha256,
      "point_constructors":sorted(points,key=lambda x:x["name"]),"path_constructors":sorted(paths,key=lambda x:x["name"]),
      "computation_rules":normalized_rules,"decision":"STRUCTURE_AND_REFERENCES_VALID",
      "full_cubical_derivation_verified":False,"theorem_claim":False}
    result["spec_sha256"]=digest(result)
    return result

def register_proof_term(*, proof_term_id: str, theorem_id: str, proof_term_sha256: str,
                        source_sha256: str, assumptions: list[dict[str,Any]], prover_id: str,
                        prover_version: str, dependencies: list[dict[str,Any]]) -> dict[str,Any]:
    proof_term_id=_name(proof_term_id,"proof_term_id"); theorem_id=_name(theorem_id,"proof_term_theorem_id")
    prover_id=_name(prover_id,"proof_term_prover_id"); prover_version=_name(prover_version,"proof_term_prover_version")
    require_sha256(proof_term_sha256,"proof_term_sha256"); require_sha256(source_sha256,"proof_term_source_sha256")
    if not isinstance(assumptions,list) or not isinstance(dependencies,list):
        raise ValueError("proof_term_assumptions_and_dependencies_must_be_lists")
    assumption_ids=set()
    for assumption in assumptions:
        _object(assumption,"proof_term_assumption"); aid=_name(assumption.get("assumption_id"),"proof_term_assumption_id")
        unsigned=dict(assumption); recorded=unsigned.pop("assumption_sha256",None)
        if recorded!=digest(unsigned) or assumption.get("theorem_claim") is not False:
            raise ValueError("proof_term_assumption_integrity_failure:"+aid)
        if aid in assumption_ids: raise ValueError("proof_term_assumption_duplicate:"+aid)
        assumption_ids.add(aid)
    dep_ids=set(); normalized_dependencies=[]
    for dep in dependencies:
        _object(dep,"proof_term_dependency"); dep_id=_name(dep.get("dependency_id"),"proof_term_dependency_id")
        require_sha256(dep.get("sha256"),"proof_term_dependency_sha256")
        if dep_id in dep_ids: raise ValueError("proof_term_dependency_duplicate:"+dep_id)
        dep_ids.add(dep_id); normalized_dependencies.append(dict(dep))
    normalized_dependencies.sort(key=lambda x:x["dependency_id"])
    result={"schema":"SUPER1200_PROOF_TERM_REGISTRY_RECORD/1","proof_term_id":proof_term_id,"theorem_id":theorem_id,
      "proof_term_sha256":proof_term_sha256,"source_sha256":source_sha256,
      "assumptions":sorted((dict(x) for x in assumptions),key=lambda x:x["assumption_id"]),
      "prover_id":prover_id,"prover_version":prover_version,"dependencies":normalized_dependencies,
      "status":"REGISTERED_UNVERIFIED_PROOF_TERM","proof_replay_verified":False,"theorem_claim":False}
    result["record_sha256"]=digest(result)
    return result
