#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, importlib.util, json, re, sys
from pathlib import Path

def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def toks(text):
    return sorted(set(re.findall(r"[a-z0-9]+", str(text).casefold())))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--evidence",required=True)
    ap.add_argument("--pyz",required=True)
    ap.add_argument("--extractor",required=True)
    ap.add_argument("--out",required=True)
    q=ap.parse_args()

    manifest=json.loads(Path(q.manifest).read_text(encoding="utf-8"))
    evidence=json.loads(Path(q.evidence).read_text(encoding="utf-8"))
    extractor=load_module(q.extractor,"custosz_census_extractor")
    census=extractor.extract(Path(q.pyz))
    if census["capability_count"]!=72 or census["unique_capability_count"]!=72:
        raise SystemExit("CUSTOSZ72_CENSUS_NOT_EXACT")

    pyz=str(Path(q.pyz).resolve())
    sys.path.insert(0,pyz)
    import custosz_v07_families as f9

    overlap_engine=f9.SemanticOverlapAnalyzer()
    anti=f9.AntiDuplicationEngine()
    gap=f9.GapProofEngine()
    evolution=f9.EvolutionAdmissionEngine()

    caps_by_id={x["capability_id"]:x for x in census["capabilities"]}
    manifest_by_id={x["id"]:x for x in manifest["capabilities"]}
    rows=evidence["rows"]
    if len(rows)!=59 or set(x["mcap_id"] for x in rows)!=set(manifest_by_id):
        raise SystemExit("DEDUP_MAPPING_NOT_EXACT_MCAP59")

    results=[]
    failures=[]
    counts=collections.Counter()
    for row in rows:
        mid=row["mcap_id"]
        m=manifest_by_id[mid]
        cov=row["coverage"]
        refs=row.get("existing_capabilities",[])
        runtime=row.get("runtime_components",[])
        missing=[x for x in refs if x not in caps_by_id]
        if missing:
            failures.append({"mcap_id":mid,"failure":"UNKNOWN_CUSTOSZ_CAPABILITY","missing":missing})
            continue
        if cov in ("full","partial") and not refs:
            failures.append({"mcap_id":mid,"failure":"COVERAGE_REQUIRES_EXISTING_CAPABILITY"})
            continue
        if cov=="composable" and len(set(refs+runtime))<2:
            failures.append({"mcap_id":mid,"failure":"COMPOSITION_REQUIRES_AT_LEAST_TWO_COMPONENTS"})
            continue
        if cov not in {"full","partial","composable","shared","novel"}:
            failures.append({"mcap_id":mid,"failure":"INVALID_COVERAGE"})
            continue

        target_tokens=toks(m["name"]+" "+m["boundary"])
        scores=[]
        for cid,rec in caps_by_id.items():
            source_tokens=toks(cid+" "+rec["implementation"])
            score=overlap_engine.overlap(target_tokens,source_tokens)
            scores.append((score,cid))
        scores.sort(reverse=True)
        max_score,max_cid=scores[0]

        flags={
          "full":cov=="full",
          "partial":cov=="partial",
          "composable":cov=="composable",
          "shared":cov=="shared",
          "novel":cov=="novel",
        }
        action=evolution.decide(flags)
        gap_proof=gap.prove(
          m["name"],
          {k:flags[k] for k in ("full","partial","composable")},
          {"max_token_overlap":max_score,"closest_capability":max_cid}
        )
        anti_result=anti.admit(mid,caps_by_id.keys(),max_score)

        expected={
          "full":"REUSE",
          "partial":"EXTEND_OWNER_FAMILY",
          "composable":"COMPOSE_VIA_CONTRACT",
          "shared":"PLACE_IN_F08_COMMON_CORE",
          "novel":"GAP_PROOF_THEN_CREATE",
        }[cov]
        if action!=expected:
            failures.append({"mcap_id":mid,"failure":"F09_ACTION_MISMATCH","expected":expected,"actual":action})
        if cov=="novel":
            if not gap_proof.get("true_gap"):
                failures.append({"mcap_id":mid,"failure":"NOVEL_WITHOUT_TRUE_GAP"})
            if not anti_result.get("admit"):
                failures.append({"mcap_id":mid,"failure":"ANTI_DUPLICATION_DENIED","detail":anti_result})
        else:
            if cov in ("full","partial","composable") and gap_proof.get("true_gap"):
                failures.append({"mcap_id":mid,"failure":"REUSABLE_COVERAGE_MISREAD_AS_TRUE_GAP"})

        counts[action]+=1
        results.append({
          "mcap_id":mid,
          "mcap_name":m["name"],
          "coverage":cov,
          "family9_action":action,
          "existing_capabilities":refs,
          "runtime_components":runtime,
          "gap_proof":gap_proof,
          "anti_duplication":anti_result,
          "max_token_overlap":round(max_score,6),
          "closest_custosz_capability":max_cid,
          "rationale":row["rationale"],
        })

    status="PASS" if not failures and len(results)==59 else "FAIL"
    report={
      "schema":"MCAP59_CUSTOSZ72_F09_DEDUP_VALIDATION/1.0",
      "status":status,
      "scope":"PRE_G23_NON_DUPLICATION_AND_PLACEMENT",
      "custosz_family9_engine":"MATERIAL_EXECUTION_FROM_PINNED_CUSTOSZ_V7_PYZ",
      "custosz_capability_count":census["capability_count"],
      "custosz_unique_capability_count":census["unique_capability_count"],
      "mcap_count":len(manifest_by_id),
      "mapped_count":len(results),
      "family9_action_counts":dict(sorted(counts.items())),
      "failures":failures,
      "results":results,
      "g16_precheck":"PASS" if status=="PASS" else "FAIL",
      "g16_canonical_gate":"NOT_PERFORMED",
      "g23":"NOT_PERFORMED",
      "g24":"NOT_PERFORMED",
    }
    out=Path(q.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
      "status":status,
      "custosz72":census["capability_count"],
      "mcap59":len(manifest_by_id),
      "mapped":len(results),
      "actions":report["family9_action_counts"],
      "failure_count":len(failures),
      "g16_precheck":report["g16_precheck"],
    },sort_keys=True))
    if status!="PASS":
        raise SystemExit(3)

if __name__=="__main__":
    main()
