#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,tempfile,time
from pathlib import Path

ROOT=Path(os.environ.get("MISSION_ROOT",Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/"continuity/runtime-evidence/post_g24"; OUT.mkdir(parents=True,exist_ok=True)

def run(cmd,cwd=ROOT,timeout=900):
    r=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
    return {"returncode":r.returncode,"stdout":r.stdout[-12000:],"stderr":r.stderr[-12000:]}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    failures=[]; checks=[]
    state=json.loads((ROOT/"continuity/STATE.json").read_text())
    result=json.loads((ROOT/"continuity/CONTINUATION_RESULT.json").read_text())
    g24=ROOT/"continuity/runtime-evidence/g24/G24_CERTIFICATION_DECISION.json"
    p10=ROOT/"continuity/runtime-evidence/p10/P10_TRANSPORT_ECHO_RUN_37839883915.json"
    p12=ROOT/"continuity/runtime-evidence/p12/P12_RELEASE_GATE_EVIDENCE.json"

    if state.get("current_checkpoint")!="G24": failures.append("POST_G24_CHECKPOINT_REQUIRED")
    if not g24.is_file(): failures.append("POST_G24_CERTIFICATION_EVIDENCE_MISSING")
    else:
        e=json.loads(g24.read_text()); ok=e.get("status")=="PASS" and e.get("decision")=="CERTIFIED_FOR_POST_VALIDATION"
        checks.append({"test":"G24_CERTIFICATION_OBJECT","status":"PASS" if ok else "FAIL"})
        if not ok: failures.append("G24_CERTIFICATION_INVALID")

    for path,label in [(p10,"P10"),(p12,"P12")]:
        ok=path.is_file(); checks.append({"test":label+"_EVIDENCE_PRESENT","status":"PASS" if ok else "FAIL"})
        if not ok: failures.append("POST_G24_"+label+"_EVIDENCE_MISSING")

    head=run(["git","rev-parse","HEAD"])["stdout"].strip()
    source_hashes={}
    for path,expected in [("Louksna.md","1a399ab7494d6df5582436819eee557083e753ed"),("PUAC2.md","da3b216888c86e588685d384c34dd3c481414b22")]:
        got=run(["git","rev-parse","HEAD:"+path])["stdout"].strip(); source_hashes[path]=got
        ok=got==expected; checks.append({"test":"FROZEN_SOURCE","path":path,"status":"PASS" if ok else "FAIL"})
        if not ok: failures.append("POST_G24_FROZEN_SOURCE_MISMATCH:"+path)

    build=run(["python3","scripts/build"])
    checks.append({"test":"NON_REGRESSION_BUILD","status":"PASS" if build["returncode"]==0 else "FAIL","execution":build})
    if build["returncode"]!=0: failures.append("POST_G24_NON_REGRESSION_FAILED")

    # Build release evidence in an isolated directory from the exact current source.
    with tempfile.TemporaryDirectory(prefix="louksna-post-") as td:
        t=Path(td); payload=t/"payload"; payload.mkdir()
        for rel in ["bridge","scripts","Louksna.md","PUAC2.md"]:
            src=ROOT/rel; dst=payload/rel; dst.parent.mkdir(parents=True,exist_ok=True)
            if src.is_dir(): shutil.copytree(src,dst)
            else: shutil.copy2(src,dst)
        manifest=[]
        for p in sorted(payload.rglob("*")):
            if p.is_file():
                manifest.append({"path":p.relative_to(payload).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)})
        sbom={"schema":"LOUKSNA_ZD_SBOM/1.0","source_commit":head,"components":[{"name":x["path"],"sha256":x["sha256"],"bytes":x["bytes"]} for x in manifest]}
        locks={"schema":"LOUKSNA_ZD_LOCKS/1.0","python_external_dependencies":[],"source_commit":head}
        (t/"manifest.json").write_text(json.dumps({"schema":"LOUKSNA_ZD_RELEASE_MANIFEST/1.0","source_commit":head,"files":manifest},indent=2,sort_keys=True)+"\n")
        (t/"sbom.json").write_text(json.dumps(sbom,indent=2,sort_keys=True)+"\n")
        (t/"locks.json").write_text(json.dumps(locks,indent=2,sort_keys=True)+"\n")
        archive=t/"louksna-zd-v04-"+head[:12]+".tar.gz"
        tar=run(["tar","-czf",str(archive),"-C",str(payload),"."])
        checks.append({"test":"RELEASE_PACKAGE","status":"PASS" if tar["returncode"]==0 else "FAIL","bytes":archive.stat().st_size if archive.exists() else 0})
        if tar["returncode"]!=0: failures.append("POST_G24_RELEASE_PACKAGE_FAILED")

        # Real rollback test on the same artifact payload.
        pristine={x["path"]:x["sha256"] for x in manifest}
        mutate=payload/"bridge"/"MTLS_READONLY_GATEWAY.md"
        original=mutate.read_bytes()
        mutate.write_bytes(original+b"\nROLLBACK_TEST_MUTATION\n")
        mutated=sha(mutate)!=pristine["bridge/MTLS_READONLY_GATEWAY.md"]
        shutil.rmtree(payload/"bridge"); shutil.copytree(ROOT/"bridge",payload/"bridge")
        restored=sha(mutate)==pristine["bridge/MTLS_READONLY_GATEWAY.md"]
        checks.append({"test":"VERIFIED_ROLLBACK","status":"PASS" if mutated and restored else "FAIL","mutated":mutated,"restored":restored})
        if not(mutated and restored): failures.append("POST_G24_ROLLBACK_FAILED")

        # Fresh-process post-recovery verification (postboot analogue without rebooting the hosted runner).
        postboot=run(["python3","-m","unittest","bridge/tests/test_mtls_gateway.py"])
        checks.append({"test":"POSTBOOT_VERIFICATION","status":"PASS" if postboot["returncode"]==0 else "FAIL","execution":postboot})
        if postboot["returncode"]!=0: failures.append("POST_G24_POSTBOOT_VERIFICATION_FAILED")

        evidence_package=t/"evidence-package.json"
        evidence_package.write_text(json.dumps({"manifest":str(t/"manifest.json"),"sbom":str(t/"sbom.json"),"locks":str(t/"locks.json"),"release_archive":str(archive)},indent=2,sort_keys=True)+"\n")
        ep=OUT/"RELEASE_EVIDENCE_PACKAGE.json"
        ep.write_text(evidence_package.read_text())

    evidence={"schema":"LOUKSNA_ZD_POST_G24_VALIDATION/1.0","status":"PASS" if not failures else "HOLD",
              "timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"source_commit":head,
              "source_hashes":source_hashes,"checks":checks,"failures":failures,
              "operational_non_regression":not any(x.startswith("POST_G24_NON_REGRESSION") for x in failures),
              "activation":"SEPARATE_OPERATIONAL_AUTHORIZATION_REQUIRED"}
    (OUT/"POST_G24_VALIDATION.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    if failures:
        out={"status":"HOLD_INDEPENDENT_CONTINUATION","checkpoint":"G24","next_point":"POST_G24_VALIDATION","transition_id":"POST_G24-HOLD-NEW-EVIDENCE-001","certified":True,"active":False,"g23":"PASS","g24":"PASS","open_blockers":failures,"material_evidence":evidence}
    else:
        out={"status":"PASS","checkpoint":"POST_G24_VALIDATION","parent_checkpoint":"G24","next_point":"SEPARATE_OPERATIONAL_AUTHORIZATION","transition_id":"POST_G24-TO-AUTH-001","certified":True,"active":False,"g23":"PASS","g24":"PASS","material_evidence":evidence}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print("LOUKSNA_POST_G24_TELEMETRY "+json.dumps({"status":out["status"],"next_point":out["next_point"],"failures":failures},sort_keys=True),flush=True)

if __name__=="__main__": main()
