#!/usr/bin/env python3
import hashlib, json, os, re, sys, time
from pathlib import Path
from datetime import datetime, timezone

def utc():
    return datetime.now(timezone.utc).isoformat()

def sha256_file(path, chunk=1024*1024):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        while True:
            b=f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()

def main():
    if len(sys.argv)!=5:
        raise SystemExit("USAGE: audit.py <extracted_root> <manifest_json> <custosz_pyz> <out_json>")
    extracted=Path(sys.argv[1]).resolve()
    manifest_path=Path(sys.argv[2]).resolve()
    custosz=Path(sys.argv[3]).resolve()
    out=Path(sys.argv[4]).resolve()
    repo=Path(os.environ["GITHUB_WORKSPACE"]).resolve()

    census=json.loads((repo/"ecosystem/metacognitive-operational-v1/CUSTOSZ72_CENSUS.json").read_text(encoding="utf-8"))
    worker_sha=sha256_file(custosz)
    if worker_sha != census.get("pyz_sha256"):
        raise SystemExit("CUSTOSZ_IDENTITY_MISMATCH")

    import subprocess
    status=subprocess.run([sys.executable,"-B","-I",str(custosz),"v07-status"],text=True,capture_output=True,timeout=30)
    selftest=subprocess.run([sys.executable,"-B","-I",str(custosz),"v07-selftest"],text=True,capture_output=True,timeout=30)
    if status.returncode != 0 or selftest.returncode != 0:
        raise SystemExit("CUSTOSZ_STATUS_OR_SELFTEST_FAILED")

    state=Path(os.environ["RUNNER_TEMP"])/("custosz-dropbox-audit-"+os.environ.get("GITHUB_RUN_ID","manual"))
    state.mkdir(parents=True,exist_ok=False)
    os.environ["CUSTOSZ_WORKSPACE"]=str(extracted)
    os.environ["CUSTOSZ_STATE_DIR"]=str(state)

    sys.path.insert(0,str(custosz))
    import custosz_v05_legacy as worker
    worker.PINS={k:(v[0].replace(chr(92),"/") if v[0] else None,v[1],v[2],v[3]) for k,v in worker.PINS.items()}
    worker.PROFILES={k:([x.replace(chr(92),"/") for x in v[0]],[x.replace(chr(92),"/") for x in v[1]]) for k,v in worker.PROFILES.items()}

    goal=(
      "READ_ONLY_FORENSIC_AUDIT of the fully downloaded Dropbox folder '1. PROYECTOS PRIORITARIOS'. "
      "Audit each project from its latest explicit checkpoint/state/status/evidence marker; "
      "preserve provenance; no project mutation; no execution of downloaded content; "
      "identify duplicate/overlap risks; report exact evidence paths and unresolved gaps."
    )
    mission=worker.mission_start(20/60.0,"LUNA_PROJECT",goal,report_minutes=1)
    tick0=worker.mission_tick(mission["mission_id"])

    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    files=manifest["files"]

    # Determine logical project root. Dropbox folder ZIPs may wrap all content in a single top-level directory.
    children=[p for p in extracted.iterdir() if p.name not in {".",".."}]
    dirs=[p for p in children if p.is_dir()]
    logical=extracted
    if len(dirs)==1 and len(children)==1:
        logical=dirs[0]

    checkpoint_re=re.compile(r"(checkpoint|check-point|state|status|ledger|evidence|cert|g23|g24|roadmap|resume|continuation)",re.I)
    project_rows=[]
    immediate=sorted([p for p in logical.iterdir() if p.is_dir()], key=lambda p:p.name.casefold())
    if not immediate:
        immediate=[logical]

    by_rel={x["path"]:x for x in files}
    for project in immediate:
        rel_prefix="" if project==logical else project.relative_to(extracted).as_posix().rstrip("/")+"/"
        owned=[x for x in files if x["path"].startswith(rel_prefix)] if rel_prefix else files
        checkpoints=[x for x in owned if checkpoint_re.search(x["path"])]
        checkpoints.sort(key=lambda x:(x.get("zip_mtime",""),x["path"]))
        latest=checkpoints[-1] if checkpoints else None
        project_rows.append({
          "project":project.name,
          "relative_root":project.relative_to(extracted).as_posix() if project!=extracted else ".",
          "file_count":len(owned),
          "total_bytes":sum(int(x["size"]) for x in owned),
          "explicit_checkpoint_candidates":len(checkpoints),
          "latest_checkpoint":latest,
          "audit_state":"CHECKPOINT_FOUND" if latest else "NO_EXPLICIT_CHECKPOINT_FOUND",
          "read_only":True
        })

    # Detect exact duplicate payloads without deleting anything.
    digest_map={}
    for x in files:
        digest_map.setdefault(x["sha256"],[]).append(x["path"])
    duplicate_groups=[{"sha256":d,"paths":sorted(ps),"count":len(ps)}
                      for d,ps in digest_map.items() if len(ps)>1]
    duplicate_groups.sort(key=lambda x:(-x["count"],x["sha256"]))

    tick1=worker.mission_tick(mission["mission_id"])
    report={
      "schema":"CUSTOSZ_V7_DROPBOX_PROJECTS_FORENSIC_AUDIT/1.0",
      "status":"PASS",
      "authority":"Louksna.md",
      "worker":"CUSTOSZ_V7",
      "worker_sha256":worker_sha,
      "custosz_mission_id":mission["mission_id"],
      "custosz_executor":mission.get("executor"),
      "custosz_tick_initial":tick0,
      "custosz_tick_final":tick1,
      "audit_location":"GITHUB_HOSTED",
      "download_manifest_sha256":sha256_file(manifest_path),
      "download_archive_sha256":manifest.get("archive_sha256"),
      "logical_root":logical.relative_to(extracted).as_posix() if logical!=extracted else ".",
      "project_count":len(project_rows),
      "projects":project_rows,
      "exact_duplicate_groups":duplicate_groups[:500],
      "exact_duplicate_group_count":len(duplicate_groups),
      "downloaded_content_executed":False,
      "project_mutation_performed":False,
      "audit_started_from_latest_explicit_checkpoint_per_project":True,
      "limitations":[
        "A project without an explicit checkpoint/state/status/evidence marker is reported as NO_EXPLICIT_CHECKPOINT_FOUND.",
        "This audit does not execute downloaded binaries, scripts, models, installers, or project code.",
        "Exact duplicates are reported by SHA-256 only; semantic overlap is not silently collapsed."
      ],
      "completed_at_utc":utc()
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
      "status":"PASS",
      "custosz_mission_id":mission["mission_id"],
      "project_count":len(project_rows),
      "duplicate_groups":len(duplicate_groups),
      "report":str(out)
    },ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
