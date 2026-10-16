#!/usr/bin/env python3
"""Run bounded read-only component checks and preserve a report."""
from __future__ import annotations
import ast, hashlib, json, os, re, subprocess, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from custoszv8.core import inspect_archive, inspect_wasm, sha256_file, V8Error

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")


def inspect_python_zipapp_contract(path: Path) -> dict:
    """Statically inspect Python entry points and CLI wiring without executing them."""
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    modules = []
    subcommands = set()
    imports = set()
    effectful_references = set()
    main_source_sha256 = None
    main_head = None
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        unsafe = [i.filename for i in infos if i.filename.startswith("/") or ".." in Path(i.filename).parts]
        if unsafe:
            raise ValueError("unsafe ZIP paths: " + ", ".join(unsafe))
        names = [i.filename for i in infos]
        python_names = [n for n in names if n.endswith(".py") and not n.endswith("/")]
        if len(python_names) > 256:
            raise ValueError("too many Python source modules for bounded static inspection")
        total_source_bytes = 0
        for name in sorted(python_names):
            raw = archive.read(name)
            total_source_bytes += len(raw)
            if total_source_bytes > 2 * 1024 * 1024:
                raise ValueError("Python source exceeds 2 MiB static inspection budget")
            source_hash = hashlib.sha256(raw).hexdigest()
            try:
                text = raw.decode("utf-8")
                tree = ast.parse(text, filename=name)
            except (UnicodeDecodeError, SyntaxError) as exc:
                modules.append({"path": name, "sha256": source_hash, "parse_status": "FAIL",
                                "error": f"{type(exc).__name__}: {exc}"})
                continue
            module_imports = set()
            definitions = []
            calls = []
            critical_source_excerpts = []
            wanted_excerpts = {
                ("Runtime", "__init__"), ("Runtime", "selftest"),
                ("ProcessSupervisor", "run"), ("CheckpointStore", "capture_file"),
                ("CheckpointStore", "restore_file"),
                ("SRExecBoundFME01", "establish_material_execution"),
                ("SRExecBoundFME01", "_run_protocol"),
                ("SRExecBoundFME01", "_create_dispatch"),
                ("SRExecBoundFME01", "_resolve_command")
            }
            current_class = None
            for top in tree.body:
                if isinstance(top, ast.ClassDef):
                    for member in top.body:
                        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and (top.name, member.name) in wanted_excerpts:
                            source = ast.get_source_segment(text, member) or ""
                            critical_source_excerpts.append({
                                "class": top.name, "function": member.name,
                                "lineno": member.lineno,
                                "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                                "source": source[:10000],
                                "truncated": len(source) > 10000
                            })
                elif isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)) and (None, top.name) in wanted_excerpts:
                    source = ast.get_source_segment(text, top) or ""
                    critical_source_excerpts.append({
                        "class": None, "function": top.name,
                        "lineno": top.lineno,
                        "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                        "source": source[:10000],
                        "truncated": len(source) > 10000
                    })
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    module_imports.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    module_imports.add("." * node.level + (node.module or ""))
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    definitions.append({"kind": type(node).__name__, "name": node.name,
                                        "line": getattr(node, "lineno", None)})
                elif isinstance(node, ast.Call):
                    fn = node.func
                    if isinstance(fn, ast.Attribute) and fn.attr == "add_parser" and node.args:
                        first = node.args[0]
                        if isinstance(first, ast.Constant) and isinstance(first.value, str):
                            subcommands.add(first.value)
                    if isinstance(fn, ast.Attribute):
                        calls.append(fn.attr)
                    elif isinstance(fn, ast.Name):
                        calls.append(fn.id)
            imports.update(module_imports)
            for ref in calls:
                if ref in {"Popen", "run", "call", "check_call", "check_output", "system",
                           "socket", "create_connection", "urlopen", "connect", "exec", "eval"}:
                    effectful_references.add(f"{name}:{ref}")
            modules.append({"path": name, "sha256": source_hash, "parse_status": "PASS",
                            "imports": sorted(module_imports), "definitions": definitions[:200],
                            "call_names": sorted(set(calls))[:200],
                            "critical_source_excerpts": critical_source_excerpts,
                            "main_guard": ('if __name__ == "__main__"' in text or "__main__" in text)})
            if name == "__main__.py":
                main_source_sha256 = source_hash
                main_head = "\n".join(text.splitlines()[:120])[:8000]
    return {
        "path": str(path), "sha256": digest, "size_bytes": path.stat().st_size,
        "archive_entry_count": len(names), "python_module_count": len(modules),
        "python_source_bytes_inspected": total_source_bytes,
        "entrypoint_present": "__main__.py" in names,
        "entrypoint_source_sha256": main_source_sha256,
        "entrypoint_source_excerpt": main_head,
        "cli_subcommands_detected": sorted(subcommands),
        "python_imports": sorted(imports),
        "potential_effectful_api_references": sorted(effectful_references),
        "modules": modules, "status": "PASS_STATIC_CONTRACT_INSPECTION",
        "execution_performed": False,
        "limitations": [
            "AST inspection does not establish runtime semantics or absence of dynamic dispatch.",
            "No component code was executed during this inspection.",
            "A static entrypoint/command name is not proof of an authorized or safe operation."
        ]
    }

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
            try:
                contract = inspect_python_zipapp_contract(runtime)
                results.append({"component":"RUNTIME_V1","status":"PASS_STATIC_ONLY","sha256":sha256_file(runtime),
                    "size_bytes":runtime.stat().st_size,"entry_count":item["entry_count"],
                    "entries":item["entries"],"static_contract":contract,
                    "native_execution":"NOT_RUN_UNVERIFIED_NATIVE_INTERFACE",
                    "historical_variant_note":"Selected staging bytes recorded; no equivalence claim for the R4 Skeleton pin."})
            except (OSError, ValueError, zipfile.BadZipFile) as exc:
                results.append({"component":"RUNTIME_V1","status":"FAIL","sha256":sha256_file(runtime),
                    "error":f"STATIC_CONTRACT_INSPECTION_FAILED: {type(exc).__name__}: {exc}"})

    wasm = root / "MetaOS.wasm"
    if not wasm.is_file():
        results.append({"component":"METAOS_WASM","status":"FAIL","error":"MISSING_ARTIFACT"})
    else:
        try:
            item = inspect_wasm(wasm)
            results.append({"component":"METAOS_WASM","status":"PASS_STATIC_METADATA_ONLY","sha256":item["sha256"],
                "size_bytes":item["size_bytes"],"format":item.get("format"),
                "imports":item.get("imports",[]),"exports":item.get("exports",[]),
                "sections":item.get("sections",[]),"embedded_core_modules":item.get("embedded_core_modules",[]),
                "component_import_export_contract":item.get("component_import_export_contract","CORE_MODULE_METADATA"),
                "function_signatures_verified":item.get("function_signatures_verified",False),
                "native_execution":"NOT_RUN_ABI_NOT_FULLY_VERIFIED",
                "limitations":["Static component container recognized; complete Component Model ABI and behavioural integration not demonstrated."]})
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
