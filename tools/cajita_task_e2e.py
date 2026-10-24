#!/usr/bin/env python3
"""Synthetic end-to-end execution harness for the five registered Cajita model adapters.

This verifies task dispatch, real model invocation, exact model/module hash bindings,
non-empty model output where applicable, bounded child memory and fail-closed
orchestration. Synthetic inputs do not prove semantic-quality equivalence.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, math, os, struct, subprocess, sys, time, wave
from pathlib import Path

SCHEMA = "LOUKSNA1_TASK_ADAPTER_EVIDENCE/1.0"
MODEL_CASES = [
    {"task_id":"e2e-cerebro-text-generation","domain_id":"D01_CEREBRO","operation":"generate_text",
     "input":{"prompt":"In one sentence, describe the purpose of a version-controlled repository."},
     "limits":{"timeout_seconds":900,"max_new_tokens":8}},
    {"task_id":"e2e-whisper-audio-pipeline","domain_id":"D03_TRANSCRIPCION","operation":"transcribe_audio",
     "input":{"audio_path":"@AUDIO@"},"limits":{"timeout_seconds":900,"max_new_tokens":8}},
    {"task_id":"e2e-seamless-translation","domain_id":"D04_TRADUCTOR_INTELIGENTE","operation":"translate_text",
     "input":{"text":"Good morning. How are you?","src_lang":"eng","tgt_lang":"spa"},
     "limits":{"timeout_seconds":900,"max_new_tokens":8}},
    {"task_id":"e2e-docling-image-extraction","domain_id":"D05_INTELIGENCIA_DOCUMENTAL","operation":"extract_document_image",
     "input":{"image_path":"@IMAGE@","prompt":"Extract the visible invoice text and total."},
     "limits":{"timeout_seconds":900,"max_new_tokens":8}},
    {"task_id":"e2e-qwen3-reasoning","domain_id":"D06_SISTEMA_INTELIGENTE","operation":"analyze_reasoning",
     "input":{"prompt":"What is 2 + 2? Give the answer and a brief reason."},
     "limits":{"timeout_seconds":900,"max_new_tokens":8}},
]
def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def make_audio(path):
    rate=16000
    frames=bytearray()
    # A synthetic tone verifies decoding/resampling/feature extraction, not speech accuracy.
    for i in range(rate//2):
        frames.extend(struct.pack("<h",int(1500*math.sin(2*math.pi*440*i/rate))))
    with wave.open(str(path),"wb") as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes(frames)
def make_image(path):
    from PIL import Image,ImageDraw
    image=Image.new("RGB",(640,480),"white");draw=ImageDraw.Draw(image)
    lines=["INVOICE","Invoice number: INV-1042","Date: 2026-10-21",
           "Description                Amount","Document processing        123.45","Tax                          10.00","TOTAL                       133.45"]
    for i,line in enumerate(lines): draw.text((28,24+i*52),line,fill="black")
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
        return {"task_id":record["task_id"],"domain_id":record["domain_id"],"operation":record["operation"],
                "status":result.get("status","NO_JSON_RESULT"),"exit_code":p.returncode,
                "elapsed_seconds":round(time.monotonic()-started,3),"input_sha256":result.get("input_sha256"),
                "output_sha256":result.get("output_sha256"),"entrypoint_sha256":result.get("entrypoint_sha256"),
                "weight_sha256":result.get("integrity",{}).get("weight_sha256"),
                "module_tree_sha256":result.get("integrity",{}).get("module_tree_sha256"),
                "peak_rss_bytes":result.get("peak_rss_bytes"),"generated_token_count":result.get("generated_token_count"),
                "failure_reason":result.get("reason"),"semantic_quality_equivalence":"NOT_ESTABLISHED",
                "model_runtime_stderr_tail":result.get("diagnostic_stderr_tail"),
                "model_runtime_stdout_tail":result.get("diagnostic_stdout_tail"),
                **diagnostics}
    except subprocess.TimeoutExpired:
        return {"task_id":record["task_id"],"domain_id":record["domain_id"],"operation":record["operation"],
                "status":"FAIL_TIMEOUT","exit_code":124,"elapsed_seconds":round(time.monotonic()-started,3),
                "semantic_quality_equivalence":"NOT_ESTABLISHED"}
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        return {"task_id":record["task_id"],"domain_id":record["domain_id"],"operation":record["operation"],
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
        r.get("status")=="PASS_FUNCTIONAL_EXECUTION" and r.get("exit_code")==0
        and all(isinstance(r.get(k),str) and len(r[k])==64 for k in ("input_sha256","output_sha256","weight_sha256","module_tree_sha256"))
        and isinstance(r.get("peak_rss_bytes"),int) and 0<r["peak_rss_bytes"]<=1_073_741_824
        for r in rows
    )
    passed=model_pass and guard_ok
    report={"schema":SCHEMA,"status":"PASS_SYNTHETIC_END_TO_END_EXECUTION_ONLY" if passed else "FAIL",
            "generated_at_utc":utc_now(),"runtime_candidate_id":"CAJITA_LUNA_RUNTIME_V9_20261023",
            "runtime_root":str(root),"adapter_runtime_sha256":digest(root/"cajita_task_adapters.py"),
            "harness_sha256":digest(Path(__file__).resolve()),"weight_manifest_sha256":digest(root/"CAJITA_RUNTIME_V1"/"weights_manifest.json"),
            "tested_model_domain_count":len(rows),"registered_model_domain_count":5,"task_results":rows,
            "orchestration_guard":guard,"inputs":"SYNTHETIC_FIXTURES_ONLY",
            "resource_gate":"EACH_TASK_CHILD_PEAK_RSS_MUST_BE_AT_MOST_1_GIB",
            "functional_scope":"FIVE_MODEL_DOMAIN_TASK_EXECUTIONS_PLUS_FAIL_CLOSED_ORCHESTRATION_GUARD",
            "semantic_quality_equivalence":"NOT_ESTABLISHED","all_21_target_adapters":"NOT_ESTABLISHED","global_certification":"NOT_GRANTED"}
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"schema":SCHEMA,"status":report["status"],
       "task_statuses":{r["domain_id"]:r["status"] for r in rows},"orchestration_guard":guard["status"],
       "semantic_quality_equivalence":"NOT_ESTABLISHED","global_certification":"NOT_GRANTED"},ensure_ascii=False,indent=2))
    return 0 if passed else 3
if __name__=="__main__": raise SystemExit(main())
