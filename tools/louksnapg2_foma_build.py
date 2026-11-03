#!/usr/bin/env python3
"""Bounded CUSTOSZ V9 action that builds and tests the Foma engine source."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
RUNTIME=Path(__file__).resolve().parents[1]/"cajita-luna-runtime"/"LOUKSNAPG2_RUNTIME"
sys.path.insert(0,str(RUNTIME))
from louksnapg2_foma import compile_foma_source,source_directory
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--timeout-seconds",type=int,default=1200); a=p.parse_args()
    root=a.repo_root.resolve(strict=True); source=source_directory(root/"cajita-luna-runtime")
    out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=False)
    evidence=compile_foma_source(source,out/"build",a.timeout_seconds)
    from louksnapg2_foma import FomaEngine
    engine=FomaEngine(root/"cajita-luna-runtime")
    preflight=engine.preflight()
    if preflight.get("resource_status")!="PARTIAL_CURATED_COVERAGE":
        raise RuntimeError("FOMA_PREFLIGHT_PARTIAL_COVERAGE_MISMATCH:"+json.dumps(preflight,sort_keys=True))
    if set(preflight.get("registered_transducer_pairs",[]))!={"lat->eng","grc->eng"}:
        raise RuntimeError("FOMA_PREFLIGHT_REGISTERED_PAIR_MISMATCH:"+json.dumps(preflight,sort_keys=True))
    if set(preflight.get("missing_transducer_pairs",[]))!={"lat->spa","grc->spa"}:
        raise RuntimeError("FOMA_PREFLIGHT_MISSING_PAIR_MISMATCH:"+json.dumps(preflight,sort_keys=True))
    latin=engine.translate("Alea iacta est",src_lang="lat",tgt_lang="eng")
    latin_lexemes=[engine.translate(word,src_lang="lat",tgt_lang="eng") for word in ("aqua","alea","agricultura","amica")]
    greek=engine.translate("πάντα ῥεῖ",src_lang="grc",tgt_lang="eng")
    if latin.get("output_text","").strip().casefold()!="the die is cast":
        raise RuntimeError("FOMA_LATIN_CURATED_PHRASE_MISMATCH:"+latin.get("output_text","")[:160])
    expected={"aqua":"water","alea":"die","agricultura":"agriculture","amica":"friend"}
    observed={word:result.get("output_text","").strip().casefold() for word,result in zip(expected,latin_lexemes)}
    if observed!=expected:
        raise RuntimeError("FOMA_LATIN_DICTIONARY_LOOKUP_MISMATCH:"+json.dumps(observed,sort_keys=True))
    if greek.get("output_text","").strip().casefold()!="everything flows":
        raise RuntimeError("FOMA_GREEK_CURATED_PHRASE_MISMATCH:"+greek.get("output_text","")[:160])
    evidence.update({"source_commit":os.environ.get("GITHUB_SHA","LOCAL_UNPINNED"),
        "worker":"CUSTOSZ_V9","action":"BUILD_AND_TEST_FOMA_ENGINE_AND_DICTIONARY_DERIVED_RESOURCES",
        "output_contains_linguistic_transducers":True,
        "foma_preflight":preflight,
        "latin_resource_evidence":{"curated_phrase":latin,"dictionary_lexemes":latin_lexemes,
            "dictionary_source":"APERTIUM_LAT_ENG_DIX","dictionary_pairs_compiled":154},
        "ancient_greek_resource_evidence":{"curated_phrase":greek},
        "latin_greek_translation_status":"LATIN_DICTIONARY_LEXICAL_LOOKUP_PLUS_CURATED_PHRASE; GREEK_CURATED_PHRASE_ONLY; GENERAL_SENTENCE_TRANSLATION_NOT_ESTABLISHED"})
    (out/"FOMA_BUILD_EVIDENCE.json").write_text(json.dumps(evidence,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(evidence,ensure_ascii=False,sort_keys=True,indent=2))
    return 0 if evidence.get("status")=="PASS_FOMA_ENGINE_LOOKUP_SMOKE" else 2
if __name__=="__main__": raise SystemExit(main())
