#!/usr/bin/env python3
"""Run bounded read-only component checks and preserve a report."""
from __future__ import annotations
import json, os, subprocess, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from custoszv8.core import inspect_archive, inspect_wasm, sha256_file, V8Error

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def main():
    root = ROOT / "artifacts/custosz-v7"
    results = []
    v7 = root / "CUSTOSZ.v07.f04_b.pyz"
    if not v7.is_file():
        raise SystemExit(f"missing required component: {v7}")
    v7_hash = sha256_file(v7)
    for command in ("v07-status", "v07-selftest"):
        try:
            proc = subprocess.run([sys.executable, "-I", str(v7), command],
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                timeout=30, check=False, env={"PATH":os.environ.get("PATH",""),
                    "PYTHONIOENCODING":"utf-8","PYTHONDONTWRITEBYTECODE":"1"})
            results.append({"component":"CUSTOSZ_V7","command":command,"sha256":v7_hash,
                "status":"PASS" if proc.returncode == 0 else "FAIL",
                "exit_code":proc.returncode,"stdout":proc.stdout[-12000:],"stderr":proc.stderr[-12000:]})
        except subprocess.TimeoutExpired as exc:
            results.append({"component":"CUSTOSZ_V7","command":command,"sha256":v7_hash,
                "status":"FAIL","error":"TIMEOUT_30_SECONDS","stdout":str(exc.stdout or ""),"stderr":str(exc.stderr or "")})

    runtime = root / "CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
    if not runtime.is_file():
        results.append({"component":"RUNTIME_V1","status":"FAIL","error":"MISSING_ARTIFACT"})
    else:
        item = inspect_archive(runtime)
        if not item.get("has_main"):
            results.append({"component":"RUNTIME_V1","status":"FAIL","sha256":sha256_file(runtime),
                            "error":"ZIPAPP_ENTRYPOINT_MISSING","inspection":item})
        else:
            results.append({"component":"RUNTIME_V1","status":"PASS_STATIC_ONLY","sha256":sha256_file(runtime),
                "size_bytes":runtime.stat().st_size,"entry_count":item["entry_count"],
                "entries":item["entries"],"native_execution":"NOT_RUN_UNVERIFIED_NATIVE_INTERFACE",
                "historical_variant_note":"Selected staging bytes recorded; no equivalence claim for the R4 Skeleton pin."})

    wasm = root / "MetaOS.wasm"
    if not wasm.is_file():
        results.append({"component":"METAOS_WASM","status":"FAIL","error":"MISSING_ARTIFACT"})
    else:
        try:
            item = inspect_wasm(wasm)
            results.append({"component":"METAOS_WASM","status":"PASS_STATIC_METADATA","sha256":item["sha256"],
                "size_bytes":item["size_bytes"],"imports":item["imports"],"exports":item["exports"],
                "function_signatures_verified":False,"native_execution":"NOT_RUN_ABI_NOT_FULLY_VERIFIED"})
        except (V8Error, OSError) as exc:
            results.append({"component":"METAOS_WASM","status":"FAIL","sha256":sha256_file(wasm),
                            "error":f"{type(exc).__name__}: {exc}"})

    report = {"report_id":"CUSTOSZV8-COMPONENT-CHECKS","observed_at_utc":now(),
        "candidate_commit":os.environ.get("GITHUB_SHA","LOCAL_UNBOUND"),"checks":results,
        "summary":{"v7_native_readonly_checks_passed":sum(x.get("component")=="CUSTOSZ_V7" and x.get("status")=="PASS" for x in results),
                   "v7_native_readonly_checks_total":2,
                   "runtime_native_execution":"NOT_RUN",
                   "metaos_runtime_invocation":"NOT_RUN",
                   "integration_certification":"NOT_GRANTED",
                   "g23":"NOT_GRANTED","g24":"NOT_GRANTED"}}
    out = ROOT / "evidence/custoszv8-component-checks.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    critical_failures = [x for x in results if x.get("status") == "FAIL"]
    # Runtime native execution and MetaOS ABI execution are explicitly scoped as not run.
    # Static/runtime-readonly tests fail the job; documented unknown interfaces remain a hold.
    return 1 if critical_failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
