from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent
ORCHESTRATOR = ROOT.parent
sys.path.insert(0, str(ROOT))
ORDER = ["CLI_MOJO", "CLI_CPP23_TOOLCHAIN", "CLI_CLAUDE_CODE", "CLI_PYTHON",
         "CLI_GITHUB", "CLI_GEMINI", "CLI_GROK", "CLI_HUGGING_FACE"]

def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def load_manifest(path):
    with pathlib.Path(path).open("r", encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict) or value.get("domain_order") != ORDER:
        raise ValueError("MANIFEST_DOMAIN_ORDER_INVALID")
    if value.get("role") != "DECLARATIVE_ENTRYPOINT_NOT_MONOLITHIC_IMPLEMENTATION":
        raise ValueError("MANIFEST_ROLE_INVALID")
    if len(value.get("domains", [])) != 8:
        raise ValueError("MANIFEST_DOMAIN_COUNT_INVALID")
    return value

def run_registry(manifest_path):
    manifest = load_manifest(manifest_path)
    results = []
    for domain in manifest["domains"]:
        domain_id = domain.get("id")
        module_path = (ORCHESTRATOR / domain.get("module", "")).resolve()
        try:
            module_path.relative_to(ORCHESTRATOR.resolve())
        except ValueError:
            raise ValueError("MODULE_PATH_ESCAPES_ORCHESTRATOR:" + str(domain_id))
        if not module_path.is_file():
            results.append({"domain_id": domain_id, "status": "ADAPTER_ABSENT", "module": str(module_path)})
            continue
        spec = importlib.util.spec_from_file_location("custosz_cli_" + str(domain_id).lower(), module_path)
        if spec is None or spec.loader is None:
            results.append({"domain_id": domain_id, "status": "IMPORT_UNAVAILABLE", "module": str(module_path)})
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.probe()
        results.append(result)
    present = sum(1 for x in results if x.get("status") == "AVAILABLE")
    report = {"schema": "CUSTOSZ_CLI_REGISTRY_PROBE/1.0", "captured_at_utc": utc(),
              "manifest_path": str(manifest_path), "manifest_sha256": sha(manifest_path),
              "cli_spec_path": str(ORCHESTRATOR / "CLIS.txt"),
              "cli_spec_sha256": sha(ORCHESTRATOR / "CLIS.txt"),
              "domain_order": ORDER, "domain_count": len(results), "available_domain_count": present,
              "results": results, "read_only": True, "mutations_performed": False,
              "remote_writes": False, "credential_values_logged": False,
              "status": "PASS" if len(results) == 8 and all(x.get("status") == "AVAILABLE" for x in results)
                        else "PARTIAL", "certification": "NOT_GRANTED"}
    return report

def write_atomic(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        try:
            os.unlink(temp)
        except FileNotFoundError:
            pass

def selftest():
    manifest = ROOT / ".." / "punto.json"
    return {"status": "PASS" if len(ORDER) == 8 and len(set(ORDER)) == 8 else "FAIL",
            "ordered_domains": ORDER, "manifest_present": manifest.resolve().is_file(),
            "project_mutations": False, "certification": "NOT_GRANTED"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=pathlib.Path, default=ORCHESTRATOR / "punto.json")
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        report = selftest() if args.self_test else run_registry(args.manifest)
        if args.output:
            write_atomic(args.output, report)
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
        return 0 if report.get("status") in {"PASS", "PARTIAL"} else 2
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error_type": type(exc).__name__, "reason": str(exc)[:1000],
                          "certification": "NOT_GRANTED"}, indent=2))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
