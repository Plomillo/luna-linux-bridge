#!/usr/bin/env python3
"""Additive bounded research adapter using the original staged CUSTOSZ and runtime.
Read-only on host except private temporary mission records. Never install, alter
partitions, write PROYECTOS, activate unknown policy or claim G23/G24.
"""
import datetime as dt, hashlib, json, os, pathlib, subprocess, sys, time, traceback
ROOT=pathlib.Path(os.environ["GITHUB_WORKSPACE"]).resolve()
OUT=ROOT/"docs/missions/LUNA_R4_CUSTOSZ_V7"
TEMP=pathlib.Path(os.environ["RUNNER_TEMP"])/"custosz-r4-research-evidence"
WORKER=ROOT/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
RUNTIME=ROOT/"artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
MISSION=OUT/"MISION_MAESTRA_DEFINITIVA.md"
START=time.monotonic()
NOW=lambda:dt.datetime.now(dt.timezone.utc).isoformat()
EXPECTED={
"LOUKSNA":"5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9",
"CUSTOSZ":"dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2",
"RUNTIME":"a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67",
"A1":"2114188988126aa7a9650c131526c9d7c54ad351db315635569a317114f4eb51",
"SKELETON":"fb9fad37994e684ad54b1ffc2762660eebcb8e41bd9c4ba685ffac55217d5b0f",
}
RESULT={"mission_id":"SYMPHYLAX_R1_LUNA_R4_FINAL_COMPLETION_RESEARCH",
"scope":"GITHUB_READONLY_RESEARCH_ONLY","worker":"CUSTOSZ_V7",
"supervisor":"SYMPHYLAX_R1","governor":"MetaOS",
"started_utc":NOW(),"run_id":os.environ.get("GITHUB_RUN_ID"),
"commit":os.environ.get("GITHUB_SHA"),"budget_seconds":1200,
"checks":[],"findings":[],"blockers":[],"contradictions":[],
"native_receipt":"NOT_VERIFIED","runtime_receipt":"NOT_VERIFIED",
"g23":"HOLD","g24":"HOLD","installation_executed":False,
"windows_modified":False,"projects_modified":False}
def h(data):return hashlib.sha256(data).hexdigest()
def check(name,path,expected=None):
    if not path.is_file():
        RESULT["checks"].append({"name":name,"status":"MISSING"})
        RESULT["blockers"].append("Missing "+name);return False
    digest=h(path.read_bytes())
    ok=expected is None or digest==expected
    RESULT["checks"].append({"name":name,"status":"PASS" if ok else "HASH_MISMATCH","bytes":path.stat().st_size,"sha256":digest})
    if not ok:RESULT["blockers"].append("SHA mismatch "+name)
    return ok
def command(argv,timeout=65,extra=None):
    remaining=1200-(time.monotonic()-START)-25
    if remaining<=0:raise TimeoutError("Twenty minute mission deadline")
    env=os.environ.copy();env["CUSTOSZ_STATE_DIR"]=str(TEMP/"native-state")
    env["PYTHONDONTWRITEBYTECODE"]="1"
    env.update(extra or {})
    p=subprocess.run(argv,cwd=ROOT,env=env,text=True,capture_output=True,
                     timeout=min(timeout,max(1,remaining)))
    try:output=json.loads(p.stdout)
    except ValueError:output={"stdout_excerpt":p.stdout[:500],"stderr_excerpt":p.stderr[:500]}
    return p.returncode,output
def git_get(ref,path):
    p=subprocess.run(["git","show",ref+":"+path],cwd=ROOT,capture_output=True,timeout=75)
    return p.stdout if p.returncode==0 else None
def git_check(name,ref,path,expected=None):
    data=git_get(ref,path)
    if data is None:
        RESULT["checks"].append({"name":name,"status":"UNAVAILABLE"});return
    digest=h(data)
    RESULT["checks"].append({"name":name,"status":"PASS" if expected is None or digest==expected else "HASH_MISMATCH","sha256":digest,"bytes":len(data),"ref":ref,"path":path})
def run_research():
    ok=all([check("A0",ROOT/"Louksna.md",EXPECTED["LOUKSNA"]),
            check("PUAC2",ROOT/"PUAC2.md"),
            check("CUSTOSZ",WORKER,EXPECTED["CUSTOSZ"]),
            check("RUNTIME",RUNTIME,EXPECTED["RUNTIME"]),
            check("METAOS",ROOT/"artifacts/custosz-v7/MetaOS.wasm"),
            check("MISSION",MISSION)])
    if not ok:return
    import sys
    sys.path.insert(0,str(RUNTIME))
    from runtime_core import Runtime,TimeBudgetController
    TEMP.mkdir(parents=True,exist_ok=True)
    rt=Runtime(TEMP/"runtime",ROOT/"Louksna.md",EXPECTED["LOUKSNA"])
    test=rt.selftest()
    rt.budget=TimeBudgetController(1200)
    rt.journal.append("GITHUB_RESEARCH_MISSION_RECEIVED",
                      {"mission_sha256":h(MISSION.read_bytes()),"worker":"CUSTOSZ_V7","budget_seconds":1200,
                       "scope":"READONLY","run":RESULT["run_id"]})
    RESULT["runtime_receipt"]="SELFTEST_AND_READONLY_JOURNAL_PASS" if test.get("status")=="PASS" and rt.journal.verify() else "FAILED"
    RESULT["checks"].append({"name":"Runtime API selftest and mission journal","status":RESULT["runtime_receipt"],"anatomy":test.get("anatomy")})
    for mode in ("v07-status","v07-selftest"):
        code,payload=command([sys.executable,"-B",str(WORKER),mode])
        RESULT["checks"].append({"name":"CUSTOSZ "+mode,"status":"PASS" if code==0 else "FAILED","exit_code":code,"reported_status":payload.get("status"),"version":payload.get("version")})
    code,ack=command([sys.executable,"-B",str(WORKER),"mission-start",str(1/3),
        "Investigacion integral de la mision R4 en issue 5; publicar README; NO instalar ni alterar host",
        "--project","LUNA_PROJECT","--report-minutes","5"])
    if code==0 and isinstance(ack,dict) and ack.get("mission_id"):
        RESULT["native_receipt"]="SUPERVISORY_CLOCK_STARTED"
        RESULT["native_mission_id"]=ack["mission_id"]
        RESULT["native_deadline_utc"]=ack.get("deadline_utc")
        RESULT["checks"].append({"name":"CUSTOSZ native mission-start","status":"PASS","mission_id":ack["mission_id"],"executor":ack.get("executor")})
    else:
        RESULT["checks"].append({"name":"CUSTOSZ native mission-start","status":"FAIL_CLOSED","exit_code":code,"detail":str(ack.get("detail") or ack.get("error") or ack.get("status"))[:180]})
        RESULT["blockers"].append("Native CUSTOSZ requires a real resolved LUNA_PROJECT workspace; never manufacture one to fake receipt.")
    git_check("A1 original bytes","origin/staging/architecture-louksnamejorada-20260927",
              "LOUKSNAMEJORADA.md",EXPECTED["A1"])
    git_check("R4 Skeleton original bytes","origin/staging/luna-r4-context-recovery-20260927",
              "docs/luna-r4/source/SKELETON_CANONICO_REFERENCIA.txt",EXPECTED["SKELETON"])
    cas=git_get("origin/staging/contenedor-semantico-e826-20260927",
                "artifacts/semantic-container/TRANSFER_STATUS.json")
    if cas:
        data=json.loads(cas)
        RESULT["checks"].append({"name":"CAS source manifest","status":"PASS","expected":data.get("cas_object_count_expected"),"github_uploaded":data.get("cas_objects_uploaded"),"github_pending":data.get("cas_objects_pending")})
    else:RESULT["blockers"].append("CAS status not available at the inspected branch")
    lock=git_get("origin/staging/architecture-louksnamejorada-20260927",
                 "docs/architecture/SYMPHYLAX_R1_NIGHT_MISSION_LOCK_CANDIDATE.json")
    if lock:
        data=json.loads(lock)
        RESULT["checks"].append({"name":"Installation authorization contract","status":data.get("state"),"user_authorized":data.get("user_authorized"),"automation_armed":data.get("automation_armed")})
    RESULT["contradictions"].append("Staged runtime hash "+EXPECTED["RUNTIME"]+" differs from runtime hash 4e9bf0e799487ea0fd6a6d32359176bdce996010e33ed151ce0f186155d11df0 stated in the R4 Skeleton; variant and provenance require reconciliation.")
    RESULT["findings"].append("The original CUSTOSZ executable was invoked. Its mission-start controls a supervisory clock; it is not an autonomous researcher without an authorized executor binding.")
    RESULT["findings"].append("The original runtime API accepted a read-only GitHub research mission in an isolated runner temporary evidence journal.")
    RESULT["findings"].append("Firefox is already uninstalled according to the owner; this research did not repeat removal.")
def finish():
    RESULT["ended_utc"]=NOW();RESULT["elapsed_seconds"]=round(time.monotonic()-START,3)
    RESULT["deadline_status"]="WITHIN_20_MINUTES" if RESULT["elapsed_seconds"]<=1200 else "EXCEEDED"
    RESULT["status"]="PARTIAL_OR_BLOCKED" if RESULT["blockers"] else "GITHUB_RESEARCH_COMPLETED_WITH_SCOPE_LIMITS"
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"RESEARCH_EVIDENCE.json").write_text(json.dumps(RESULT,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    lines=["# README — conclusiones verificables del despacho CUSTOSZ V7","",
           "El presente informe registra solamente comprobaciones realmente realizadas. No constituye G23/G24 ni autoriza instalaciones.",
           "","## Identidad y plazo","",
           "- Misión: "+RESULT["mission_id"],"- Inicio UTC: "+RESULT["started_utc"],"- Fin UTC: "+RESULT["ended_utc"],
           "- Duración real: "+str(RESULT["elapsed_seconds"])+" segundos.",
           "- Plazo máximo: 1200 segundos; "+RESULT["deadline_status"],
           "- Acuse nativo CUSTOSZ: "+RESULT["native_receipt"],"- Acuse runtime: "+RESULT["runtime_receipt"],
           "- GitHub Actions run ID: "+str(RESULT["run_id"]),"- Commit examinado: "+str(RESULT["commit"]),
           "","## Pruebas reales","",
           "| Prueba | Estado | Evidencia |","|---|---|---|"]
    for c in RESULT["checks"]:
        evidence=", ".join(str(k)+"="+str(v) for k,v in c.items() if k not in ("name","status"))
        lines.append("| "+c["name"]+" | "+str(c["status"])+" | "+evidence[:250]+" |")
    lines+=["","## Conclusiones",""]+["- "+s for s in RESULT["findings"]]
    lines+=["","## Contradicciones",""]+["- "+s for s in RESULT["contradictions"]]
    lines+=["","## Bloqueos",""]+["- "+s for s in RESULT["blockers"]]
    lines+=["","## No realizado","",
            "- No se instaló ningún componente en el host ni se activó un runtime de producción.",
            "- No se tocó Windows, EFI, GPT, particiones ni PROYECTOS.",
            "- No se obtuvieron dictámenes independientes G23/G24.",
            "- No se realizó investigación externa fuera del repositorio y sus artefactos.",
            "- Un selftest de PYZ no equivale a una misión de ingeniería completa.",
            "","## Siguiente hito",
            "Resolver los bloqueos documentados; evaluar adaptador de ejecución autenticado y pruebas independientes. F3-DISK exige autorización separada H2/H4.",
            "","[Misión íntegra](MISION_MAESTRA_DEFINITIVA.md) · [Orden GitHub #5](https://github.com/Plomillo/luna-linux-bridge/issues/5) · [Evidencia](RESEARCH_EVIDENCE.json)",""]
    (OUT/"README_CONCLUSIONES_CUSTOSZ_V7.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"status":RESULT["status"],"elapsed_seconds":RESULT["elapsed_seconds"],"native_receipt":RESULT["native_receipt"],"runtime_receipt":RESULT["runtime_receipt"],"checks":len(RESULT["checks"])},sort_keys=True),flush=True)
try:run_research()
except Exception as exc:
    RESULT["blockers"].append(type(exc).__name__+": "+str(exc)[:400])
    print("FAIL_CLOSED",type(exc).__name__,str(exc)[:180],flush=True)
finally:finish()
