#!/usr/bin/env python3
"""Operational materialization for the genuine MCAP gaps.

The module intentionally reuses CUSTOSZ primitives for generic memory, evidence,
currentness, resources and invariants. It implements only domain semantics that
Family 9 classified as genuine gaps.
"""
from __future__ import annotations
import hashlib, json, os, re, sqlite3, tempfile
from dataclasses import dataclass
from pathlib import Path

def cjson(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def sha(x): return hashlib.sha256(x if isinstance(x,(bytes,bytearray)) else cjson(x)).hexdigest()
def atomic_json(path,obj):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp"); t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8"); os.replace(t,p)

class NodeFamilyRegistry:
    VALID={"REFERENCED","TOOL_READY","AUTHORIZED","EXECUTOR"}
    def __init__(self,path): self.path=Path(path)
    def _load(self):
        if not self.path.exists(): return {"schema":"MCAP013_NODE_FAMILY/1.0","nodes":{}}
        return json.loads(self.path.read_text(encoding="utf-8"))
    def register(self,node_id,provider,model,adapter_ref=None,status="REFERENCED",evidence=None):
        if status not in self.VALID: raise ValueError("INVALID_NODE_STATUS")
        d=self._load()
        if node_id in d["nodes"]: raise ValueError("DUPLICATE_NODE_ID")
        if status in {"AUTHORIZED","EXECUTOR"}: raise ValueError("CANNOT_REGISTER_DIRECTLY_AS_EXECUTOR")
        d["nodes"][node_id]={"provider":provider,"model":model,"adapter_ref":adapter_ref,"status":status,"evidence":list(evidence or [])}
        atomic_json(self.path,d); return d["nodes"][node_id]
    def promote(self,node_id,target,evidence):
        d=self._load(); n=d["nodes"].get(node_id)
        if not n: raise KeyError("UNKNOWN_NODE")
        if target not in self.VALID: raise ValueError("INVALID_NODE_STATUS")
        order=["REFERENCED","TOOL_READY","AUTHORIZED","EXECUTOR"]
        if order.index(target)!=order.index(n["status"])+1: raise ValueError("NON_SEQUENTIAL_NODE_PROMOTION")
        if not evidence: raise ValueError("EVIDENCE_REQUIRED")
        if target=="EXECUTOR" and not n.get("adapter_ref"): raise ValueError("EXECUTOR_ADAPTER_REQUIRED")
        n["status"]=target; n["evidence"].append(evidence); atomic_json(self.path,d); return n

class TranslationMemoryOntology:
    def __init__(self,path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(self.path)
        try:
            db.execute("""CREATE TABLE IF NOT EXISTS term(
              domain TEXT NOT NULL, source_lang TEXT NOT NULL, target_lang TEXT NOT NULL,
              source_term TEXT NOT NULL, target_term TEXT NOT NULL, version INTEGER NOT NULL,
              source_hash TEXT NOT NULL, status TEXT NOT NULL,
              PRIMARY KEY(domain,source_lang,target_lang,source_term,version))""")
            db.commit()
        finally:
            db.close()
    def add(self,domain,source_lang,target_lang,source_term,target_term,version,source_hash,status="VALIDATED"):
        if status not in {"DECLARED","VALIDATED","CERTIFIED"}: raise ValueError("INVALID_TERM_STATE")
        db=sqlite3.connect(self.path)
        try:
            db.execute("INSERT INTO term VALUES(?,?,?,?,?,?,?,?)",(domain,source_lang,target_lang,source_term,target_term,int(version),source_hash,status))
            db.commit()
        finally:
            db.close()
    def resolve(self,domain,source_lang,target_lang,source_term):
        db=sqlite3.connect(self.path)
        try:
            row=db.execute("""SELECT target_term,version,source_hash,status FROM term
              WHERE domain=? AND source_lang=? AND target_lang=? AND source_term=?
              ORDER BY version DESC LIMIT 1""",(domain,source_lang,target_lang,source_term)).fetchone()
        finally:
            db.close()
        return None if not row else {"target_term":row[0],"version":row[1],"source_hash":row[2],"status":row[3]}

class ExtremeTranslationOrchestrator:
    def plan(self,segments,shard_size=500,terminology_version=None):
        if shard_size<1: raise ValueError("INVALID_SHARD_SIZE")
        ids=[str(x["segment_id"]) for x in segments]
        if len(ids)!=len(set(ids)): raise ValueError("DUPLICATE_SEGMENT_ID")
        ordered=sorted(segments,key=lambda x:str(x["segment_id"]))
        shards=[]
        for i in range(0,len(ordered),shard_size):
            part=ordered[i:i+shard_size]
            records=[{"segment_id":str(x["segment_id"]),"source_hash":x["source_hash"],"context_ref":x.get("context_ref")} for x in part]
            shards.append({"shard_id":f"S{i//shard_size:08d}","segments":records,"shard_digest":sha(records)})
        plan={"schema":"MCAP044_TRANSLATION_PLAN/1.0","segment_count":len(ordered),"shard_count":len(shards),"terminology_version":terminology_version,"shards":shards,"reassembly_order":ids}
        plan["plan_digest"]=sha(plan); return plan
    def verify_completion(self,plan,results):
        by={str(x["segment_id"]):x for x in results}
        expected=[str(x["segment_id"]) for s in plan["shards"] for x in s["segments"]]
        missing=[x for x in expected if x not in by]
        extra=sorted(set(by)-set(expected))
        dup=len(results)!=len(by)
        bad=[x for x in expected if x in by and not by[x].get("target_hash")]
        return {"status":"PASS" if not (missing or extra or dup or bad) else "FAIL","missing":missing,"extra":extra,"duplicates":dup,"missing_target_hash":bad}

_NUM=re.compile(r"(?<!\w)[+-]?(?:\d+(?:[.,]\d+)?)")
class TranslationFidelityValidator:
    def validate(self,source_segments,target_segments,terminology=None,semantic_evaluation=None):
        s={str(x["segment_id"]):x for x in source_segments}; t={str(x["segment_id"]):x for x in target_segments}
        findings=[]
        if set(s)!=set(t): findings.append("SEGMENT_SET_MISMATCH")
        for sid in sorted(set(s)&set(t)):
            st=str(s[sid].get("text","")); tt=str(t[sid].get("text",""))
            if sorted(_NUM.findall(st))!=sorted(_NUM.findall(tt)): findings.append("NUMERIC_FIDELITY:"+sid)
            for src_term,dst_term in (terminology or {}).items():
                if src_term in st and dst_term not in tt: findings.append("TERMINOLOGY:"+sid+":"+src_term)
        semantic_state="NOT_EVALUATED"
        if semantic_evaluation:
            if semantic_evaluation.get("result")=="PASS" and semantic_evaluation.get("independent") is True:
                semantic_state="PASS"
            else: findings.append("SEMANTIC_EVALUATION_NOT_INDEPENDENT_PASS")
        return {"status":"PASS" if not findings else "FAIL","structural_numeric_terminology":"PASS" if not findings else "FAIL","semantic_fidelity":semantic_state,"findings":findings}

class DomainDataFabric:
    ALLOWED_KINDS={"ECONOMIC","MARKET","STABLECOIN_ISSUER","STABLECOIN_ONCHAIN","STABLECOIN_MARKET","LABOR"}
    def normalize(self,kind,source_id,observed_at,event_at,measure,value,unit,dimensions=None,source_uri=None):
        if kind not in self.ALLOWED_KINDS: raise ValueError("INVALID_DATA_KIND")
        if not source_id or not observed_at or value is None: raise ValueError("INCOMPLETE_SOURCE_RECORD")
        rec={"kind":kind,"source_id":source_id,"observed_at":observed_at,"event_at":event_at,"measure":measure,"value":value,"unit":unit,"dimensions":dimensions or {},"source_uri":source_uri}
        rec["record_hash"]=sha(rec); return rec

class StablecoinLiquidityIntelligence:
    def fuse(self,issuer,onchain,market):
        layers={"ISSUER_DATA":issuer,"ONCHAIN_OBSERVATION":onchain,"MARKET_DATA":market}
        if not all(x and x.get("record_hash") for x in layers.values()):
            return {"status":"HOLD","reason":"INCOMPLETE_EVIDENCE_LAYERS","layers":layers}
        return {"status":"PASS","layers":layers,"rule":"ISSUER_DATA != ONCHAIN_OBSERVATION != MARKET_DATA","fusion_digest":sha(layers)}

class LaborMarketOpportunityIntelligence:
    def normalize_posting(self,source_id,observed_at,title,skills,location,compensation=None,source_uri=None):
        rec={"kind":"LABOR","source_id":source_id,"observed_at":observed_at,"title":title,"skills":sorted(set(skills or [])),"location":location,"compensation":compensation,"source_uri":source_uri}
        rec["record_hash"]=sha(rec); return rec
    def match(self,profile_skills,postings):
        have=set(profile_skills)
        out=[]
        for p in postings:
            req=set(p.get("skills",[])); score=(len(have&req)/len(req)) if req else 0.0
            out.append({"source_id":p["source_id"],"skill_coverage":round(score,6),"matched":sorted(have&req),"missing":sorted(req-have)})
        return sorted(out,key=lambda x:(-x["skill_coverage"],x["source_id"]))

class EconomicTheoryMultiLens:
    def analyze(self,evidence,lenses):
        if not evidence: raise ValueError("EVIDENCE_REQUIRED")
        return {"schema":"MCAP057_MULTI_LENS/1.0","empirical_evidence":evidence,"interpretations":[{"lens_id":x["lens_id"],"assumptions":x.get("assumptions",[]),"interpretation":x.get("interpretation"),"is_empirical_fact":False} for x in lenses],"rule":"EMPIRICAL_DATA != INTERPRETATION","digest":sha({"evidence":evidence,"lenses":lenses})}

class GovernedTrainingGate:
    def admit(self,request,g24,evidence_manifest,evaluation_plan):
        findings=[]
        if g24.get("decision")!="PASS": findings.append("G24_NOT_PASS")
        if g24.get("candidate_digest")!=request.get("base_candidate_digest"): findings.append("BASE_DIGEST_MISMATCH")
        if request.get("training_position")!="LAST": findings.append("TRAINING_NOT_LAST")
        if not evidence_manifest.get("admitted") or evidence_manifest.get("contaminated"): findings.append("TRAINING_CORPUS_NOT_ADMITTED")
        if not evaluation_plan.get("post_training_full_revalidation"): findings.append("FULL_REVALIDATION_REQUIRED")
        return {"status":"PASS" if not findings else "HOLD","authorization":"TRAINING_CANDIDATE_ONLY" if not findings else "DENIED","findings":findings,"rule":"TRAINING != AUTHORITY != CERTIFICATION"}

def selftest():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        nodes=NodeFamilyRegistry(td/"nodes.json")
        nodes.register("codex-cloud","OpenAI","codex",adapter_ref="github-agentic")
        nodes.promote("codex-cloud","TOOL_READY","CLI_VERSION_VERIFIED")
        try:
            nodes.promote("codex-cloud","EXECUTOR","BAD_SKIP")
            raise AssertionError("node promotion skip accepted")
        except ValueError: pass
        tm=TranslationMemoryOntology(td/"tm.db")
        tm.add("theology","la","es","gratia","gracia",1,"a"*64)
        assert tm.resolve("theology","la","es","gratia")["target_term"]=="gracia"
        seg=[{"segment_id":"2","source_hash":"b"*64},{"segment_id":"1","source_hash":"a"*64}]
        plan=ExtremeTranslationOrchestrator().plan(seg,1,1)
        assert plan["segment_count"]==2 and plan["shard_count"]==2
        assert ExtremeTranslationOrchestrator().verify_completion(plan,[{"segment_id":"1","target_hash":"c"*64},{"segment_id":"2","target_hash":"d"*64}])["status"]=="PASS"
        fv=TranslationFidelityValidator().validate([{"segment_id":"1","text":"gratia 1536"}],[{"segment_id":"1","text":"gracia 1536"}],{"gratia":"gracia"})
        assert fv["status"]=="PASS"
        fab=DomainDataFabric()
        issuer=fab.normalize("STABLECOIN_ISSUER","issuer", "2026-09-28T00:00:00Z",None,"supply",1,"USD")
        chain=fab.normalize("STABLECOIN_ONCHAIN","chain","2026-09-28T00:00:00Z",None,"supply",1,"USD")
        market=fab.normalize("STABLECOIN_MARKET","market","2026-09-28T00:00:00Z",None,"price",1,"USD")
        assert StablecoinLiquidityIntelligence().fuse(issuer,chain,market)["status"]=="PASS"
        labor=LaborMarketOpportunityIntelligence()
        p=labor.normalize_posting("job1","2026-09-28T00:00:00Z","Engineer",["python","git"],"remote")
        assert labor.match(["python"],[p])[0]["skill_coverage"]==0.5
        ml=EconomicTheoryMultiLens().analyze([{"source":"official","fact":"x"}],[{"lens_id":"AUSTRIAN","interpretation":"y"},{"lens_id":"MAINSTREAM","interpretation":"z"}])
        assert all(not x["is_empirical_fact"] for x in ml["interpretations"])
        gate=GovernedTrainingGate().admit({"base_candidate_digest":"x","training_position":"LAST"},{"decision":"HOLD","candidate_digest":"x"},{"admitted":True,"contaminated":False},{"post_training_full_revalidation":True})
        assert gate["status"]=="HOLD" and "G24_NOT_PASS" in gate["findings"]
    return {"status":"PASS","tested":["MCAP-013","MCAP-044","MCAP-045","MCAP-046","MCAP-054","MCAP-055","MCAP-056","MCAP-057","MCAP-059"]}

if __name__=="__main__":
    print(json.dumps(selftest(),sort_keys=True))
