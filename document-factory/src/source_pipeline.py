from __future__ import annotations
import json,re
from pathlib import Path
CITE_RE=re.compile(r"\[@([A-Za-z0-9_.:-]+)(?:[^\]]*)\]")
def _load(x): return json.loads(Path(x).read_text(encoding="utf-8")) if isinstance(x,(str,Path)) else x
def validate_ledger(ledger,minimum_distinct_sources=0):
    obj=_load(ledger); rows=obj.get("sources") or []; seen=set(); failures=[]
    for i,row in enumerate(rows):
        sid=str(row.get("source_id","")).strip()
        if not sid: failures.append(f"SOURCE_ID_MISSING:{i}"); continue
        if sid in seen: failures.append("DUPLICATE_SOURCE_ID:"+sid)
        seen.add(sid)
        if row.get("verified") is True:
            if not str(row.get("title","")).strip(): failures.append("VERIFIED_SOURCE_TITLE_MISSING:"+sid)
            if row.get("fabricated_metadata") is True: failures.append("FABRICATED_METADATA_FORBIDDEN:"+sid)
    verified={str(x.get("source_id")) for x in rows if x.get("verified") is True and x.get("source_id")}
    if len(verified)<int(minimum_distinct_sources): failures.append(f"MINIMUM_VERIFIED_SOURCES_NOT_MET:{len(verified)}<{minimum_distinct_sources}")
    return {"status":"PASS" if not failures else "FAIL","failures":failures,"distinct_verified":len(verified)}
def extract_citation_ids(text): return sorted(set(CITE_RE.findall(text or "")))
def validate_citations(text,ledger):
    obj=_load(ledger); rows={str(x.get("source_id")):x for x in obj.get("sources",[]) if x.get("source_id")}; failures=[]
    cited=extract_citation_ids(text)
    for cid in cited:
        if cid not in rows: failures.append("CITATION_NOT_IN_LEDGER:"+cid)
        elif rows[cid].get("verified") is not True: failures.append("CITATION_SOURCE_NOT_VERIFIED:"+cid)
    return {"status":"PASS" if not failures else "FAIL","cited_ids":cited,"failures":failures}
def compile_csl_json(ledger):
    obj=_load(ledger); out=[]
    for row in obj.get("sources",[]):
        if row.get("verified") is not True: continue
        sid=str(row.get("source_id","")).strip(); title=str(row.get("title","")).strip()
        if not sid or not title: raise ValueError("CSL_REQUIRES_VERIFIED_ID_AND_TITLE")
        item={"id":sid,"type":row.get("csl_type") or "article","title":title}
        if row.get("author"):
            authors=[]
            for a in row["author"]:
                if isinstance(a,dict):
                    clean={k:a[k] for k in ("family","given","literal") if a.get(k)}
                    if clean: authors.append(clean)
            if authors: item["author"]=authors
        if row.get("issued"): item["issued"]=row["issued"]
        if row.get("container_title"): item["container-title"]=row["container_title"]
        for key in ("DOI","URL","page","volume","issue","publisher"):
            if row.get(key): item[key]=row[key]
        out.append(item)
    return out
