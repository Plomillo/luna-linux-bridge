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
    evidence.update({"source_commit":os.environ.get("GITHUB_SHA","LOCAL_UNPINNED"),
        "worker":"CUSTOSZ_V9","action":"BUILD_AND_TEST_FOMA_ENGINE",
        "output_contains_linguistic_transducers":False,
        "latin_greek_translation_status":"BLOCKED_NO_HASH_PINNED_TRANSLATION_TRANSDUCERS"})
    (out/"FOMA_BUILD_EVIDENCE.json").write_text(json.dumps(evidence,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(evidence,ensure_ascii=False,sort_keys=True,indent=2))
    return 0 if evidence.get("status")=="PASS_FOMA_ENGINE_LOOKUP_SMOKE" else 2
if __name__=="__main__": raise SystemExit(main())
