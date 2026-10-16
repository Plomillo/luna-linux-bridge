#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, urllib.request
from pathlib import Path

DEFAULT="https://huggingface.co/datasets/HuggingFaceFW/finewiki/resolve/main/data/enwiki/000_00000.parquet"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",default=DEFAULT)
    ap.add_argument("--bytes",type=int,default=65536)
    ap.add_argument("--out",required=True)
    q=ap.parse_args()
    req=urllib.request.Request(q.url,headers={
      "Range":f"bytes=0-{q.bytes-1}",
      "User-Agent":"louksna-remote-corpus-probe/1.0"
    })
    with urllib.request.urlopen(req,timeout=60) as r:
        data=r.read(q.bytes+1)
        status=getattr(r,"status",None)
        headers={k.lower():v for k,v in r.headers.items()}
    if len(data)>q.bytes:
        raise SystemExit("REMOTE_READ_EXCEEDED_BOUND")
    partial=(status==206 or "content-range" in headers)
    if not partial:
        raise SystemExit("REMOTE_RANGE_NOT_HONORED")
    result={
      "schema":"REMOTE_CORPUS_RANGE_PROBE/1.0",
      "status":"PASS",
      "source_url":q.url,
      "http_status":status,
      "content_range":headers.get("content-range"),
      "content_length_header":headers.get("content-length"),
      "bytes_materialized":len(data),
      "byte_limit":q.bytes,
      "full_corpus_materialized":False,
      "sample_sha256":hashlib.sha256(data).hexdigest()
    }
    p=Path(q.out); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
