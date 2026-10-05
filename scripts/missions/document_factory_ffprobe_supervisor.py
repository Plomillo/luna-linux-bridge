#!/usr/bin/env python3
from __future__ import annotations
import json,os,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path

def utc():
    return datetime.now(timezone.utc).isoformat()

def write_json(path,obj):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    tmp.replace(p)

def main():
    if len(sys.argv)!=6:
        raise SystemExit("usage: supervisor MATERIALIZER TARGET_ROOT MAIN_ROOT MAILBOX_ROOT OUT_DIR")
    materializer,target_root,main_root,mailbox_root,outdir=map(lambda x:Path(x).resolve(),sys.argv[1:6])
    outdir.mkdir(parents=True,exist_ok=True)
    hb=outdir/"SUPERVISOR_HEARTBEAT.json"
    completion=outdir/"SUPERVISOR_COMPLETION.json"
    stdout_path=outdir/"MATERIALIZER.stdout.log"
    stderr_path=outdir/"MATERIALIZER.stderr.log"
    write_json(hb,{"schema":"CUSTOSZ_FFPROBE_SUPERVISOR_HEARTBEAT/1.0","state":"STARTING","sequence":0,"pid":os.getpid(),"observed_at_utc":utc()})
    with stdout_path.open("w",encoding="utf-8") as out, stderr_path.open("w",encoding="utf-8") as err:
        p=subprocess.Popen(
            [sys.executable,"-B","-I",str(materializer),str(target_root),str(main_root),str(mailbox_root),str(outdir)],
            stdout=out,stderr=err,text=True
        )
        seq=0
        started=time.monotonic()
        while True:
            code=p.poll()
            seq+=1
            write_json(hb,{
                "schema":"CUSTOSZ_FFPROBE_SUPERVISOR_HEARTBEAT/1.0",
                "state":"RUNNING" if code is None else "EXITED",
                "sequence":seq,
                "pid":os.getpid(),
                "materializer_pid":p.pid,
                "elapsed_seconds":round(time.monotonic()-started,3),
                "observed_at_utc":utc()
            })
            if code is not None:
                break
            time.sleep(1)
    result=outdir/"RESULT.json"
    obj={
      "schema":"CUSTOSZ_FFPROBE_SUPERVISOR_COMPLETION/1.0",
      "status":"PASS" if code==0 and result.is_file() else "FAIL",
      "supervisor_pid":os.getpid(),
      "materializer_pid":p.pid,
      "exit_code":code,
      "result_present":result.is_file(),
      "heartbeat_sequence":seq,
      "elapsed_seconds":round(time.monotonic()-started,3),
      "completed_at_utc":utc()
    }
    write_json(completion,obj)
    write_json(hb,{
        "schema":"CUSTOSZ_FFPROBE_SUPERVISOR_HEARTBEAT/1.0",
        "state":"COMPLETED" if obj["status"]=="PASS" else "FAILED",
        "sequence":seq+1,
        "pid":os.getpid(),
        "materializer_pid":p.pid,
        "elapsed_seconds":obj["elapsed_seconds"],
        "observed_at_utc":utc()
    })
    raise SystemExit(0 if obj["status"]=="PASS" else 1)

if __name__=="__main__":
    main()
