"""D05 proof-assurance primitives for capabilities 129-132.
These are fail-closed adapters and descriptors; no untrusted producer output is accepted as proof.
"""
from __future__ import annotations
import hashlib,json,re
from typing import Any,Callable

_SHA256=re.compile(r"^[0-9a-f]{64}$")
def canonical_json(v:Any)->bytes:
 return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
def digest(v:Any)->str:return hashlib.sha256(canonical_json(v)).hexdigest()
def _name(v:Any,f:str)->str:
 if not isinstance(v,str) or not v.strip():raise ValueError(f+"_required")
 return v.strip()
def _sha(v:Any,f:str)->str:
 if not isinstance(v,str) or not _SHA256.fullmatch(v):raise ValueError(f+"_must_be_lowercase_sha256")
 return v
def _obj(v:Any,f:str)->dict[str,Any]:
 if not isinstance(v,dict):raise ValueError(f+"_must_be_object")
 return v

def validate_proof_checker_binding(*,checker_id:str,version:str,toolchain_sha256:str,
                                   proof_language:str,producer_is_trusted:bool=False)->dict[str,Any]:
 checker_id=_name(checker_id,"checker_id");version=_name(version,"checker_version")
 proof_language=_name(proof_language,"proof_language");_sha(toolchain_sha256,"checker_toolchain_sha256")
 if producer_is_trusted is not False:raise ValueError("producer_output_must_not_be_trusted")
 out={"schema":"SUPER1200_PROOF_CHECKER_BINDING/1","checker_id":checker_id,"version":version,
  "toolchain_sha256":toolchain_sha256,"proof_language":proof_language,
  "producer_output_trusted":False,"independent_checker_required":True,"checker_executed":False,
  "decision":"BOUND_NOT_EXECUTED","theorem_claim":False}
 out["binding_sha256"]=digest(out);return out

def build_proof_artifact_descriptor(*,artifact_id:str,proof_term_sha256:str,source_sha256:str,
                                    environment_sha256:str,toolchain_lock_sha256:str,
                                    proof_language:str,dependencies:list[dict[str,Any]])->dict[str,Any]:
 artifact_id=_name(artifact_id,"proof_artifact_id");proof_language=_name(proof_language,"proof_language")
 for v,f in [(proof_term_sha256,"proof_term_sha256"),(source_sha256,"proof_source_sha256"),
             (environment_sha256,"proof_environment_sha256"),(toolchain_lock_sha256,"toolchain_lock_sha256")]:_sha(v,f)
 if not isinstance(dependencies,list):raise ValueError("proof_artifact_dependencies_must_be_list")
 normalized=[];seen=set()
 for dep in dependencies:
  _obj(dep,"proof_artifact_dependency");did=_name(dep.get("dependency_id"),"dependency_id")
  _sha(dep.get("sha256"),"dependency_sha256")
  if did in seen:raise ValueError("proof_artifact_dependency_duplicate")
  seen.add(did);normalized.append(dict(dep))
 normalized.sort(key=lambda x:x["dependency_id"])
 out={"schema":"SUPER1200_PROOF_ARTIFACT_DESCRIPTOR/1","artifact_id":artifact_id,
  "proof_term_sha256":proof_term_sha256,"source_sha256":source_sha256,"environment_sha256":environment_sha256,
  "toolchain_lock_sha256":toolchain_lock_sha256,"proof_language":proof_language,"dependencies":normalized,
  "storage_semantics":"CONTENT_ADDRESSED_IMMUTABLE_DESCRIPTOR_ONLY","artifact_persisted":False,
  "proof_replay_verified":False,"theorem_claim":False}
 out["descriptor_sha256"]=digest(out);return out

def validate_proof_dependency_graph(nodes:list[dict[str,Any]],edges:list[dict[str,Any]])->dict[str,Any]:
 if not isinstance(nodes,list) or not isinstance(edges,list):raise ValueError("proof_graph_nodes_edges_must_be_lists")
 by={};allowed={"THEOREM","LEMMA","AXIOM"}
 for node in nodes:
  _obj(node,"proof_graph_node");nid=_name(node.get("node_id"),"proof_graph_node_id")
  kind=node.get("kind")
  if kind not in allowed:raise ValueError("proof_graph_node_kind_invalid")
  _sha(node.get("sha256"),"proof_graph_node_sha256")
  if nid in by:raise ValueError("proof_graph_node_duplicate")
  by[nid]=dict(node)
 normalized=[];seen_edges=set();adj={n:set() for n in by}
 for edge in edges:
  _obj(edge,"proof_graph_edge");src=_name(edge.get("depends_on"),"proof_graph_depender");dst=_name(edge.get("dependency"),"proof_graph_dependency")
  if src not in by or dst not in by:raise ValueError("proof_graph_unknown_node")
  if (src,dst) in seen_edges:raise ValueError("proof_graph_duplicate_edge")
  seen_edges.add((src,dst));adj[src].add(dst);normalized.append({"depends_on":src,"dependency":dst})
 visiting=set();visited=set()
 def visit(n):
  if n in visiting:raise ValueError("proof_graph_cycle")
  if n in visited:return
  visiting.add(n)
  for child in adj[n]:visit(child)
  visiting.remove(n);visited.add(n)
 for n in by:visit(n)
 normalized.sort(key=lambda x:(x["depends_on"],x["dependency"]))
 out={"schema":"SUPER1200_PROOF_DEPENDENCY_GRAPH/1","nodes":sorted(by.values(),key=lambda x:x["node_id"]),
  "edges":normalized,"decision":"ACYCLIC_TYPED_GRAPH_VALID","theorem_claim":False}
 out["graph_sha256"]=digest(out);return out

def reverse_invalidation_closure(graph:Any,changed_node_ids:list[str])->dict[str,Any]:
 _obj(graph,"proof_dependency_graph")
 nodes=graph.get("nodes");edges=graph.get("edges")
 if not isinstance(nodes,list) or not isinstance(edges,list):raise ValueError("proof_graph_schema_invalid")
 known={_name(n.get("node_id"),"node_id") for n in nodes if isinstance(n,dict)}
 changed=set()
 for nid in changed_node_ids:
  nid=_name(nid,"changed_node_id")
  if nid not in known:raise ValueError("proof_graph_changed_node_unknown")
  changed.add(nid)
 reverse={n:set() for n in known}
 for edge in edges:
  _obj(edge,"proof_graph_edge");depender=edge.get("depends_on");dependency=edge.get("dependency")
  if depender not in known or dependency not in known:raise ValueError("proof_graph_unknown_node")
  reverse[dependency].add(depender)
 invalid=set(changed);stack=list(changed)
 while stack:
  cur=stack.pop()
  for parent in reverse[cur]:
   if parent not in invalid:invalid.add(parent);stack.append(parent)
 out={"schema":"SUPER1200_PROOF_INVALIDATION_CLOSURE/1","changed":sorted(changed),
  "invalidated_dependents":sorted(invalid-changed),"invalidated_all":sorted(invalid),"theorem_claim":False}
 out["closure_sha256"]=digest(out);return out

def replay_proof_artifact(*,proof_term_sha256:str,source_sha256:str,environment_sha256:str,
                          toolchain_lock_sha256:str,checker_id:str,checker_version:str,
                          trusted_replay:Callable[[dict[str,Any]],bool])->dict[str,Any]:
 for v,f in [(proof_term_sha256,"proof_term_sha256"),(source_sha256,"proof_source_sha256"),
             (environment_sha256,"proof_environment_sha256"),(toolchain_lock_sha256,"toolchain_lock_sha256")]:_sha(v,f)
 checker_id=_name(checker_id,"checker_id");checker_version=_name(checker_version,"checker_version")
 if not callable(trusted_replay):raise ValueError("trusted_replay_callback_required")
 request={"proof_term_sha256":proof_term_sha256,"source_sha256":source_sha256,
  "environment_sha256":environment_sha256,"toolchain_lock_sha256":toolchain_lock_sha256,
  "checker_id":checker_id,"checker_version":checker_version}
 accepted=trusted_replay(dict(request))
 if accepted is not True:raise ValueError("independent_proof_replay_denied")
 out={"schema":"SUPER1200_PROOF_REPLAY_RECEIPT/1","decision":"INDEPENDENT_REPLAY_VERIFIED",
  "request":request,"trusted_checker_callback_returned_true":True,"theorem_claim":False,
  "scope_note":"Receipt confirms exact replay callback result only; no global certification is implied."}
 out["receipt_sha256"]=digest(out);return out
