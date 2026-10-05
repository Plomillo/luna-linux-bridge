#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from runtime import append_audit,sha256_file,write_json,utc

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",required=True)
    ap.add_argument("--provider-id",required=True)
    ap.add_argument("--provider-version",required=True)
    ap.add_argument("--input",required=True,help="UTF-8 Markdown produced by the declared writer provider.")
    ap.add_argument("--target",default="source/report.md")
    args=ap.parse_args()

    root=pathlib.Path(args.workspace)
    source=pathlib.Path(args.input)
    if not source.is_file():
        raise SystemExit("WRITER_INPUT_MISSING")

    target=root/args.target
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(source.read_bytes())

    record={
      "schema":"DOCUMENT_FACTORY_WRITER_EVIDENCE/1.0",
      "provider_id":args.provider_id,
      "provider_version":args.provider_version,
      "input_sha256":sha256_file(source),
      "output_path":target.relative_to(root).as_posix(),
      "output_sha256":sha256_file(target),
      "observed_at_utc":utc(),
      "certification_authority":False,
      "g23_authority":False,
      "g24_authority":False
    }
    write_json(root/"evidence"/"writer.json",record)
    append_audit(root,{"event_type":"WRITE","provider_id":args.provider_id,"output_sha256":record["output_sha256"]})
    print(json.dumps(record,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
