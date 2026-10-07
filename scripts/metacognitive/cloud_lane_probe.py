#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, http.server, importlib.util, json, os, pathlib, shutil, socketserver, subprocess, tempfile, threading, time, urllib.request

def write(path,obj):
    p=pathlib.Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def load_core(repo_root):
    p=pathlib.Path(repo_root)/"scripts/metacognitive/operational_core.py"
    spec=importlib.util.spec_from_file_location("meta_core",p)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def rclone_lane(args):
    exe=pathlib.Path(args.rclone)
    if not exe.is_file(): raise SystemExit("RCLONE_BINARY_MISSING")
    version=subprocess.run([str(exe),"version"],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    total_files=128; block=(b"LOUKSNA-RCLONE-PROBE\n"*4096)[:65536]
    total_bytes=total_files*len(block)
    rows=[]
    with tempfile.TemporaryDirectory(prefix="rclone-probe-") as td:
        td=pathlib.Path(td); src=td/"src"; src.mkdir()
        for i in range(total_files):
            (src/f"f-{i:04d}.bin").write_bytes(block)
        src_hash=hashlib.sha256(b"".join(hashlib.sha256((src/f"f-{i:04d}.bin").read_bytes()).digest() for i in range(total_files))).hexdigest()
        for workers in (8,16,32,48,64):
            dst=td/f"dst-{workers}"; dst.mkdir()
            t0=time.perf_counter()
            cp=subprocess.run([str(exe),"copy",str(src),str(dst),"--transfers",str(workers),"--checkers",str(workers),"--checksum","--stats","0"],capture_output=True,text=True)
            elapsed=max(time.perf_counter()-t0,1e-9)
            check=subprocess.run([str(exe),"check",str(src),str(dst),"--one-way"],capture_output=True,text=True)
            ok=cp.returncode==0 and check.returncode==0
            dst_hash=None
            if ok:
                dst_hash=hashlib.sha256(b"".join(hashlib.sha256((dst/f"f-{i:04d}.bin").read_bytes()).digest() for i in range(total_files))).hexdigest()
                ok=dst_hash==src_hash
            rows.append({"workers":workers,"throughput_bps":total_bytes/elapsed,"elapsed_seconds":elapsed,
                         "error_rate":0.0 if ok else 1.0,"checksum_pass":bool(ok),
                         "copy_exit":cp.returncode,"check_exit":check.returncode})
    safe=[x for x in rows if x["checksum_pass"] and x["error_rate"]<=.05]
    if not safe: raise SystemExit("NO_SAFE_RCLONE_PROFILE")
    best=max(safe,key=lambda x:x["throughput_bps"])
    write(args.out,{"lane":"rclone","status":"PASS","scope":"CLOUD_SYNTHETIC_LOCAL_BACKEND_CONCURRENCY_AND_CHECKSUM",
                    "version":version,"profiles":rows,"selected_workers":best["workers"],
                    "selection_rule":"MAX_VERIFIED_THROUGHPUT_SUBJECT_TO_CHECKSUM_AND_ERROR_RATE",
                    "dropbox_live_benchmark":False,"user_host_used":False})

class RangeHandler(http.server.BaseHTTPRequestHandler):
    data=b""
    def do_GET(self):
        value=self.headers.get("Range")
        if not value or not value.startswith("bytes="):
            self.send_response(416); self.end_headers(); return
        start_s,end_s=value[6:].split("-",1); start=int(start_s); end=int(end_s)
        if start<0 or end<start or end>=len(self.data):
            self.send_response(416); self.end_headers(); return
        body=self.data[start:end+1]
        self.send_response(206)
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Content-Range",f"bytes {start}-{end}/{len(self.data)}")
        self.end_headers(); self.wfile.write(body)
    def log_message(self,*a): pass

def range_lane(args):
    RangeHandler.data=(b"0123456789abcdef"*1024*1024)  # 16 MiB source object in cloud runner memory
    server=socketserver.TCPServer(("127.0.0.1",0),RangeHandler)
    t=threading.Thread(target=server.serve_forever,daemon=True); t.start()
    start=1024*1024; end=start+(1024*1024)-1
    req=urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/corpus",headers={"Range":f"bytes={start}-{end}"})
    with urllib.request.urlopen(req,timeout=10) as resp:
        body=resp.read(); status=resp.status; cr=resp.headers.get("Content-Range")
    server.shutdown(); server.server_close()
    expected=RangeHandler.data[start:end+1]
    ok=status==206 and len(body)==1024*1024 and body==expected and cr==f"bytes {start}-{end}/{len(RangeHandler.data)}"
    if not ok: raise SystemExit("RANGE_STREAMING_VALIDATION_FAILED")
    write(args.out,{"lane":"remote_range","status":"PASS","scope":"HTTP_RANGE_STREAMING_MECHANISM",
                    "source_bytes":len(RangeHandler.data),"bytes_requested":len(body),
                    "full_materialization_by_consumer":False,"external_provider_certified":False,
                    "user_host_used":False})

def translation_lane(args):
    core=load_core(args.repo_root); tr=core.TranslationOrchestrator()
    n=args.segments; t0=time.perf_counter(); rows=tr.translate_identity(tr.segment(n)); valid=tr.validate(rows); elapsed=time.perf_counter()-t0
    if not valid or len(rows)!=n: raise SystemExit("TRANSLATION_STRUCTURE_VALIDATION_FAILED")
    write(args.out,{"lane":"translation_scale","status":"PASS",
                    "scope":"SEGMENT_IDENTITY_SHARD_REASSEMBLY_AND_HASH_INVARIANTS_ONLY",
                    "segments":n,"elapsed_seconds":elapsed,"semantic_mt_engine_used":False,
                    "semantic_fidelity_certified":False,"structure_integrity":"PASS","user_host_used":False})

def telemetry_lane(args):
    names=["MISSION","METAOS_DECISION","CUSTOSZ_DISPATCH","MODEL_CALL","RAG_QUERY","TOOL_CALL","EVIDENCE","VALIDATOR"]
    trace=hashlib.sha256(b"MIS-META-ECO-20260928-V1").hexdigest()[:32]
    spans=[]; parent=None
    for i,name in enumerate(names):
        span=hashlib.sha256(f"{trace}:{i}:{name}".encode()).hexdigest()[:16]
        spans.append({"trace_id":trace,"span_id":span,"parent_span_id":parent,"name":name,"attributes":{"authority":"Louksna.md","canonical_mutation":False}})
        parent=span
    ids={x["span_id"] for x in spans}; roots=[x for x in spans if x["parent_span_id"] is None]
    linked=all(x["parent_span_id"] is None or x["parent_span_id"] in ids for x in spans)
    if len(roots)!=1 or not linked: raise SystemExit("TRACE_LINKAGE_FAILED")
    write(args.out,{"lane":"telemetry","status":"PASS","scope":"HIGH_RESOLUTION_TRACE_LINKAGE_SCHEMA",
                    "trace_id":trace,"span_count":len(spans),"linked":linked,"spans":spans,
                    "opentelemetry_sdk_certified":False,"user_host_used":False})

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("rclone"); a.add_argument("--rclone",required=True); a.add_argument("--out",required=True)
    a=sub.add_parser("range"); a.add_argument("--out",required=True)
    a=sub.add_parser("translation"); a.add_argument("--repo-root",default="."); a.add_argument("--segments",type=int,default=100000); a.add_argument("--out",required=True)
    a=sub.add_parser("telemetry"); a.add_argument("--out",required=True)
    q=ap.parse_args()
    {"rclone":rclone_lane,"range":range_lane,"translation":translation_lane,"telemetry":telemetry_lane}[q.cmd](q)

if __name__=="__main__":
    main()
