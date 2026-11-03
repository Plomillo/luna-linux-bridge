#!/usr/bin/env python3
"""Synthetic end-to-end execution harness for the five registered Cajita model adapters.

This verifies task dispatch, real model invocation, exact model/module hash bindings,
non-empty model output where applicable, bounded child memory and fail-closed
orchestration. Synthetic inputs do not prove semantic-quality equivalence.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, re, shutil, subprocess, sys, time, unicodedata, wave
from pathlib import Path

SCHEMA = "LOUKSNA1_TASK_ADAPTER_EVIDENCE/1.0"
MODEL_CASES = [
    {"task_id":"e2e-cerebro-text-generation","domain_id":"D01_CEREBRO","operation":"generate_text",
     "input":{"prompt":"What does a version-controlled repository store? Answer briefly."},
     "limits":{"timeout_seconds":900,"max_new_tokens":12},
     "quality_check":{"id":"repository-storage","mode":"contains_any","phrases":["files","source code","documents"]}},
    {"task_id":"e2e-whisper-audio-pipeline","domain_id":"D03_TRANSCRIPCION","operation":"transcribe_audio",
     "input":{"audio_path":"@AUDIO@"},"limits":{"timeout_seconds":900,"max_new_tokens":8},
     "quality_check":{"id":"known-speech-hello-world","mode":"contains_all","phrases":["hello","world"]}},
    {"task_id":"e2e-seamless-translation","domain_id":"D04_TRADUCTOR_INTELIGENTE","operation":"translate_text",
     "input":{"text":"Good morning. How are you?","src_lang":"eng","tgt_lang":"spa"},
     "limits":{"timeout_seconds":900,"max_new_tokens":12},
     "quality_check":{"id":"english-to-spanish-greeting","mode":"contains_any","phrases":["buenos dias","buen dia"]}},
    {"task_id":"e2e-docling-image-extraction","domain_id":"D05_INTELIGENCIA_DOCUMENTAL","operation":"extract_document_image",
     "input":{"image_path":"@IMAGE@","prompt":"Convert this page to docling."},
     "limits":{"timeout_seconds":900,"max_new_tokens":512},
     "quality_check":{"id":"invoice-total-133-45","mode":"regex","pattern":r"\b133[.,]45\b"}},
    {"task_id":"e2e-qwen3-reasoning","domain_id":"D06_SISTEMA_INTELIGENTE","operation":"analyze_reasoning",
     "input":{"prompt":"What is 2 + 2? Return only the numeric answer."},
     "limits":{"timeout_seconds":900,"max_new_tokens":8},
     "quality_check":{"id":"arithmetic-2-plus-2","mode":"regex","pattern":r"\b4\b"}},
]
def normalized_text(value):
    text=unicodedata.normalize("NFKD",str(value).casefold())
    text="".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+"," ",text).strip()
def quality_acceptance(record, output_text):
    spec=record.get("quality_check",{})
    if not isinstance(spec,dict) or not spec.get("id"):
        return {"status":"NOT_CONFIGURED","reason":"QUALITY_CHECK_SPEC_MISSING"}
    raw=str(output_text or "")
    mode=spec.get("mode")
    if mode=="regex":
        matched=bool(re.search(str(spec.get("pattern","(?!)")),raw,re.IGNORECASE))
        observed=[spec.get("pattern")] if matched else []
    else:
        normalized=normalized_text(raw)
        phrases=[normalized_text(p) for p in spec.get("phrases",[]) if isinstance(p,str) and p.strip()]
        observed=[p for p in phrases if p and (" "+normalized+" ").find(" "+p+" ") >= 0]
        if mode=="contains_any": matched=bool(observed)
        elif mode=="contains_all": matched=bool(phrases) and len(observed)==len(phrases)
        else: return {"status":"FAIL","check_id":spec["id"],"reason":"QUALITY_CHECK_MODE_INVALID"}
    result={"status":"PASS" if matched else "FAIL","check_id":spec["id"],
            "observed_matches":observed,"reference_kind":"FIXED_SYNTHETIC_EXPECTATION",
            "does_not_establish_reference_model_equivalence":True}
    if not matched:
        # These tasks contain only deterministic synthetic prompts/fixtures. A short
        # normalized excerpt is retained solely to diagnose a failed expectation;
        # the full model response and prompt are never written to the evidence file.
        normalized_for_diagnostics=normalized_text(raw)
        result.update({
            "output_char_count":len(raw),
            "output_text_sha256":hashlib.sha256(raw.encode("utf-8",errors="replace")).hexdigest(),
            "normalized_output_excerpt":normalized_for_diagnostics[:180],
        })
    return result
def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def make_audio(path):
    executable=shutil.which("espeak-ng")
    if not executable:
        raise RuntimeError("ESPEAK_NG_REQUIRED_FOR_KNOWN_SPEECH_FIXTURE")
    subprocess.run([executable,"-v","en-us","-s","135","-w",str(path),"hello world"],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=30)
    with wave.open(str(path),"rb") as audio:
        if audio.getnframes()<=0 or audio.getnchannels() not in (1,2) or audio.getsampwidth()!=2:
            raise RuntimeError("ESPEAK_NG_FIXTURE_WAV_INVALID")
def make_image(path):
    from PIL import Image,ImageDraw,ImageFont
    image=Image.new("RGB",(1024,1024),"white");draw=ImageDraw.Draw(image)
    font=ImageFont.load_default(size=32)
    lines=["INVOICE","Invoice number: INV-1042","Date: 2026-10-21",
           "Description                Amount","Document processing        123.45","Tax                          10.00","TOTAL                       133.45"]
    for i,line in enumerate(lines): draw.text((64,64+i*128),line,fill="black",font=font)
    image.save(path,format="PNG")
def run_case(root,outdir,record,timeout):
    request_path=outdir/(record["domain_id"]+".request.json")
    request_path.write_text(json.dumps(record,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    safe_env={k:os.environ[k] for k in ("PATH","HOME","LANG","LC_ALL","TMPDIR","SYSTEMROOT","WINDIR") if k in os.environ}
    safe_env.update({"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1",
                     "TOKENIZERS_PARALLELISM":"false","HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","PYTHONNOUSERSITE":"1",
                     "CAJITA_E2E_DIAGNOSTICS":"1"})
    started=time.monotonic()
    try:
        p=subprocess.run([sys.executable,str(root/"cajita_runtime.py"),"execute-task","--root",str(root),
                          "--request-json",str(request_path),"--timeout",str(timeout)],
                         cwd=str(root),env=safe_env,capture_output=True,text=True,timeout=timeout+30,check=False)
        result=json.loads(p.stdout) if p.stdout.strip() else {}
        # Preserve bounded diagnostics for genuine runtime failures; this harness uses
        # synthetic inputs only and never serializes the input request or prompt here.
        diagnostics = {}
        if p.returncode != 0:
            diagnostics = {
                "stderr_tail": p.stderr[-3000:],
                "stdout_tail": p.stdout[-1200:],
                "stderr_sha256": hashlib.sha256(p.stderr.encode("utf-8", errors="replace")).hexdigest(),
                "stdout_sha256": hashlib.sha256(p.stdout.encode("utf-8", errors="replace")).hexdigest(),
            }
        output_text=result.get("output_text","") if isinstance(result,dict) else ""
        quality=quality_acceptance(record,output_text) if p.returncode==0 else {
            "status":"NOT_RUN","check_id":record.get("quality_check",{}).get("id"),
            "reason":"MODEL_EXECUTION_FAILED","does_not_establish_reference_model_equivalence":True}
        return {"task_id":record["task_id"],"domain_id":record["domain_id"],"target_id":result.get("target_id"),"operation":record["operation"],
                "status":result.get("status","NO_JSON_RESULT"),"exit_code":p.returncode,
                "elapsed_seconds":round(time.monotonic()-started,3),"input_sha256":result.get("input_sha256"),
                "output_sha256":result.get("output_sha256"),"output_char_count":len(str(output_text)),
                "entrypoint_sha256":result.get("entrypoint_sha256"),
                "weight_sha256":result.get("integrity",{}).get("weight_sha256"),
                "module_tree_sha256":result.get("integrity",{}).get("module_tree_sha256"),
                "peak_rss_bytes":result.get("peak_rss_bytes"),"generated_token_count":result.get("generated_token_count"),
                "failure_reason":result.get("reason"),"quality_acceptance":quality,
                "semantic_quality_equivalence":"NOT_ESTABLISHED_REFERENCE_MODEL_EQUIVALENCE",
                "model_runtime_stderr_tail":result.get("diagnostic_stderr_tail"),
                "model_runtime_stdout_tail":result.get("diagnostic_stdout_tail"),
                **diagnostics}
    except subprocess.TimeoutExpired:
        return {"task_id":record["task_id"],"domain_id":record["domain_id"],"target_id":record.get("target"),"operation":record["operation"],
                "status":"FAIL_TIMEOUT","exit_code":124,"elapsed_seconds":round(time.monotonic()-started,3),
                "semantic_quality_equivalence":"NOT_ESTABLISHED"}
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        return {"task_id":record["task_id"],"domain_id":record["domain_id"],"target_id":record.get("target"),"operation":record["operation"],
                "status":"FAIL_HARNESS","exit_code":125,"elapsed_seconds":round(time.monotonic()-started,3),
                "failure_reason":type(exc).__name__,"semantic_quality_equivalence":"NOT_ESTABLISHED"}
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",required=True)
    parser.add_argument("--output-dir",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--timeout",type=int,default=900)
    args=parser.parse_args()
    root=Path(args.root).resolve(strict=True)
    if not root.is_dir() or not (root/"cajita_task_adapters.py").is_file(): parser.error("Runtime adapter is missing")
    outdir=Path(args.output_dir).resolve()
    outdir.mkdir(parents=True,exist_ok=True)
    audio=outdir/"synthetic-test-audio.wav"; image=outdir/"synthetic-test-invoice.png"
    make_audio(audio);make_image(image)
    rows=[]
    for source in MODEL_CASES:
        request=json.loads(json.dumps(source))
        request["schema"]="CAJITA_TASK_REQUEST/1.0"
        request["input"]=dict(request["input"])
        if request["input"].get("audio_path")=="@AUDIO@": request["input"]["audio_path"]=str(audio)
        if request["input"].get("image_path")=="@IMAGE@": request["input"]["image_path"]=str(image)
        rows.append(run_case(root,outdir,request,args.timeout))
    route={
        "schema":"CAJITA_TASK_REQUEST/1.0","task_id":"e2e-orchestration-fail-closed-guard",
        "domain_id":"D02_ORQUESTACION","operation":"route_plan",
        "input":{"request_text":"Transcribe an audio file and translate the result to Spanish."},
        "limits":{"timeout_seconds":min(args.timeout,60)}
    }
    guard=run_case(root,outdir,route,min(args.timeout,60))
    guard_ok=guard.get("status") in {"PLAN_ONLY_BLOCKED","PLAN_READY_NOT_EXECUTED"} and guard.get("exit_code")==3
    guard["status"]="PASS_FAIL_CLOSED_PLAN_ONLY" if guard_ok else "FAIL_ORCHESTRATION_GUARD"
    guard["execution_authorized"]=False
    model_pass=all(
        r.get("status")=="PASS_EXECUTION_QUALITY_UNVERIFIED" and r.get("exit_code")==0
        and r.get("quality_acceptance",{}).get("status")=="PASS"
        and all(isinstance(r.get(k),str) and len(r[k])==64 for k in ("input_sha256","output_sha256","weight_sha256","module_tree_sha256"))
        and isinstance(r.get("peak_rss_bytes"),int) and 0<r["peak_rss_bytes"]<=2_147_483_648
        for r in rows
    )
    try:
        sys.path.insert(0, str(root))
        from cajita_target_adapters import run_target_smokes
        target_engine_report = run_target_smokes(root, os.environ.get("LOUKSNA1_COMPANION_PATH"))
    except Exception as exc:
        target_engine_report = {
            "schema":"CAJITA_RUNTIME_TARGET_ENGINE_E2E/1.0",
            "status":"FAIL_TARGET_ENGINE_E2E_SCOPE",
            "expected_count":6,"pass_count":0,"failed_count":6,"results":[],
            "error_type":type(exc).__name__,"reason":str(exc)[:700],
            "certification":"NOT_GRANTED"
        }
    finally:
        try:
            sys.path.remove(str(root))
        except ValueError:
            pass
    target_engine_ok = (
        target_engine_report.get("status")=="PASS_TARGET_ENGINE_E2E_SCOPE_ONLY"
        and target_engine_report.get("expected_count")==6
        and target_engine_report.get("pass_count")==6
        and target_engine_report.get("failed_count")==0
        and len(target_engine_report.get("results",[]))==6
    )
    passed=model_pass and guard_ok and target_engine_ok
    report={"schema":SCHEMA,"status":"PASS_SYNTHETIC_END_TO_END_EXECUTION_ONLY" if passed else "FAIL",
            "generated_at_utc":utc_now(),"runtime_candidate_id":"CAJITA_LUNA_RUNTIME_V9_20261023",
            "runtime_root":str(root),"adapter_runtime_sha256":digest(root/"cajita_task_adapters.py"),
            "target_engine_adapter_runtime_sha256":digest(root/"cajita_target_adapters.py"),
            "harness_sha256":digest(Path(__file__).resolve()),"weight_manifest_sha256":digest(root/"CAJITA_RUNTIME_V1"/"weights_manifest.json"),
            "tested_model_domain_count":len(rows),"registered_model_domain_count":5,"task_results":rows,
            "target_engine_smoke_status":target_engine_report.get("status","NOT_COMPLETED"),
            "target_engine_expected_count":target_engine_report.get("expected_count",6),
            "target_engine_pass_count":target_engine_report.get("pass_count",0),
            "target_engine_failed_count":target_engine_report.get("failed_count",6),
            "target_engine_results":target_engine_report.get("results",[]),
            "target_engine_scope":target_engine_report.get("scope","SIX_SOURCE_BOUND_TARGET_ENGINE_SMOKES; NO_FULL_TASK_OR_QUALITY_CLAIM"),
            "orchestration_guard":guard,"inputs":"ESPEAK_NG_KNOWN_SPEECH_AND_SYNTHETIC_INVOICE_FIXTURES_PLUS_SIX_SOURCE_BOUND_TARGET_ENGINE_FIXTURES",
            "resource_gate":"EACH_TASK_CHILD_PEAK_RSS_MUST_BE_AT_MOST_2_GIB; TARGET_ENGINE_BUILD_AND_EXECUTION_BOUNDED",
            "functional_scope":"FIVE_MODEL_DOMAIN_TASK_EXECUTIONS_WITH_FIXED_EXPECTATION_ACCEPTANCE_PLUS_SIX_SOURCE_BOUND_TARGET_ENGINE_SMOKES_PLUS_FAIL_CLOSED_ORCHESTRATION_GUARD",
            "synthetic_quality_acceptance":"PASS" if model_pass and guard_ok else "FAIL",
            "full_target_task_coverage":"NOT_ESTABLISHED",
            "semantic_quality_equivalence":"NOT_ESTABLISHED_REFERENCE_MODEL_EQUIVALENCE","all_21_target_adapters":"NOT_ESTABLISHED","global_certification":"NOT_GRANTED"}
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"schema":SCHEMA,"status":report["status"],
       "task_statuses":{r["domain_id"]:r["status"] for r in rows},"orchestration_guard":guard["status"],
       "target_engine_smoke_status":report["target_engine_smoke_status"],
       "target_engine_pass_count":report["target_engine_pass_count"],"target_engine_expected_count":report["target_engine_expected_count"],
       "synthetic_quality_acceptance":report["synthetic_quality_acceptance"],
       "semantic_quality_equivalence":"NOT_ESTABLISHED_REFERENCE_MODEL_EQUIVALENCE","global_certification":"NOT_GRANTED"},ensure_ascii=False,indent=2))
    return 0 if passed else 3
if __name__=="__main__": raise SystemExit(main())
