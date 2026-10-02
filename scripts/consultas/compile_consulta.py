#!/usr/bin/env python3
import argparse, hashlib, json, pathlib
from datetime import datetime, timezone

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out",required=True)
    ns=ap.parse_args()
    src=pathlib.Path(ns.source)
    raw=src.read_bytes()
    if not raw:
        raise SystemExit("EMPTY_CONSULTA")
    digest=hashlib.sha256(raw).hexdigest()
    env={
      "schema":"LOUKSNA_CONSULTA_ENVELOPE/1.0",
      "consulta_id":"CONSULTA-"+digest[:20].upper(),
      "kind":"CONSULTA",
      "source_path":str(src),
      "source_sha256":digest,
      "source_bytes":len(raw),
      "execution_authorized":False,
      "mutation_authorized":False,
      "state":"RECEIVED",
      "authority":"Louksna.md",
      "created_at_utc":datetime.now(timezone.utc).isoformat(),
      "provenance":{"compiler":"scripts/consultas/compile_consulta.py"}
    }
    out=pathlib.Path(ns.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(env,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(env,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
