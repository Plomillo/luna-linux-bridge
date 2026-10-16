#!/usr/bin/env python3
"""Run only the inspected, read-only Runtime V1 selftest under a bounded isolated subprocess."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
EXPECTED_RUNTIME_SHA256 = "a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67"
EXPECTED_MEMBERS = {"__main__.py", "runtime_core.py", "sr_exec_bound_fme_01.py"}
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024
MAX_MEMBER_BYTES = 512 * 1024
TIMEOUT_SECONDS = 10

def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def record_source_contract(source: str, module: str) -> dict:
    tree = ast.parse(source, filename=module)
    targets = {
        ("Runtime", "selftest"),
        ("Runtime", "__init__"),
        ("GovernanceKernel", "preflight"),
        ("EvidenceJournal", "verify"),
        ("EvidenceJournal", "append"),
    }
    excerpts = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for member in node.body:
            if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if (node.name, member.name) not in targets:
                continue
            fragment = ast.get_source_segment(source, member) or ""
            calls = sorted({
                item.func.attr if isinstance(item.func, ast.Attribute)
                else item.func.id if isinstance(item.func, ast.Name)
                else type(item.func).__name__
                for item in ast.walk(member) if isinstance(item, ast.Call)
            })
            excerpts.append({
                "class": node.name, "function": member.name,
                "source_line": member.lineno, "source_sha256": sha256_bytes(fragment.encode()),
                "calls": calls, "source": fragment,
            })
    found = {(item["class"], item["function"]) for item in excerpts}
    if found != targets:
        raise RuntimeError(f"required Runtime source methods missing: {sorted(targets - found)}")
    selftest = next(x for x in excerpts if (x["class"], x["function"]) == ("Runtime", "selftest"))
    if sorted(selftest["calls"]) != ["preflight", "verify"]:
        raise RuntimeError("Runtime.selftest call surface changed; manual re-audit required")
    preflight = next(x for x in excerpts if (x["class"], x["function"]) == ("GovernanceKernel", "preflight"))
    if any(call in preflight["calls"] for call in ("Popen", "run", "call", "urlopen", "connect", "system", "exec", "eval")):
        raise RuntimeError("Runtime preflight has an unexpected effectful API; refusing execution")
    verify = next(x for x in excerpts if (x["class"], x["function"]) == ("EvidenceJournal", "verify"))
    if any(call in verify["calls"] for call in ("Popen", "run", "call", "urlopen", "connect", "system", "exec", "eval")):
        raise RuntimeError("EvidenceJournal.verify has an unexpected effectful API; refusing execution")
    return {"functions": excerpts, "source_sha256": sha256_bytes(source.encode())}

def main() -> int:
    report = {
        "schema": "custoszv8.runtime-v1-selftest-evidence.v1",
        "candidate_commit": os.environ.get("CUSTOSZV8_CANDIDATE_SHA") or os.environ.get("GITHUB_SHA", "LOCAL_UNBOUND"),
        "observed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "component": "RUNTIME_V1_SELECTED_STAGING",
        "expected_runtime_sha256": EXPECTED_RUNTIME_SHA256,
        "result": "HOLD",
        "execution_scope": "Runtime.selftest only; no mission dispatch, process executor, or SRExecBoundFME01 invocation",
        "canonical_binding": "NOT_TESTED_WITH_CANONICAL_AUTHORITY; isolated non-canonical fixture only",
        "g23": "NOT_GRANTED",
        "g24": "NOT_GRANTED",
        "certification": "NOT_GRANTED",
        "limitations": [
            "This proves only the narrow Runtime.selftest API contract.",
            "The CLI launcher embeds an absolute Windows authority path; portability of that launcher is not verified.",
            "The test authority is a synthetic fixture and is explicitly not Louksna.md.",
            "No executor, native mission, Runtime V1/SRExecBoundFME01 material action, or production restore operation is invoked."
        ],
    }
    try:
        if not RUNTIME.is_file():
            raise RuntimeError("required Runtime V1 archive is missing")
        archive_sha = sha256_file(RUNTIME)
        report["runtime_sha256"] = archive_sha
        report["runtime_size_bytes"] = RUNTIME.stat().st_size
        if archive_sha != EXPECTED_RUNTIME_SHA256:
            raise RuntimeError("Runtime V1 SHA-256 differs from the explicitly selected staging pin")
        if RUNTIME.stat().st_size > MAX_ARCHIVE_BYTES:
            raise RuntimeError("Runtime V1 archive exceeds inspection size limit")
        with zipfile.ZipFile(RUNTIME) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            if set(names) != EXPECTED_MEMBERS or len(names) != len(EXPECTED_MEMBERS):
                raise RuntimeError(f"Runtime V1 member-set mismatch: {names}")
            for info in infos:
                p = PurePosixPath(info.filename)
                if p.is_absolute() or ".." in p.parts or info.is_dir():
                    raise RuntimeError(f"unsafe Runtime V1 entry: {info.filename}")
                if info.file_size > MAX_MEMBER_BYTES:
                    raise RuntimeError(f"Runtime V1 member exceeds size limit: {info.filename}")
            sources = {name: archive.read(name) for name in sorted(EXPECTED_MEMBERS)}
        for name, raw in sources.items():
            report.setdefault("module_sha256", {})[name] = sha256_bytes(raw)
        main_text = sources["__main__.py"].decode("utf-8")
        m = re.search(r"(?m)^AUTH_SHA\s*=\s*['\"]([0-9a-f]{64})['\"]", main_text)
        report["launcher_pinned_authority_sha256"] = m.group(1) if m else None
        report["launcher_has_absolute_windows_authority_path"] = bool(re.search(r"(?m)^AUTH\s*=\s*Path\(r?['\"][A-Za-z]:\\", main_text))
        runtime_core = sources["runtime_core.py"].decode("utf-8")
        report["source_contract"] = record_source_contract(runtime_core, "runtime_core.py")

        with tempfile.TemporaryDirectory(prefix="custoszv8-runtime-selftest-") as outer:
            sandbox = Path(outer)
            extracted = sandbox / "source"
            extracted.mkdir()
            for name, raw in sources.items():
                (extracted / name).write_bytes(raw)
            authority = sandbox / "SELFTEST_FIXTURE_NOT_CANONICAL.md"
            authority_bytes = b"CUSTOSZV8 RUNTIME V1 SELFTEST FIXTURE; NOT CANONICAL AUTHORITY.\n"
            authority.write_bytes(authority_bytes)
            authority_sha = sha256_file(authority)
            state_root = sandbox / "runtime-state"
            harness = (
                "import json,sys\n"
                "sys.path.insert(0, sys.argv[1])\n"
                "from runtime_core import Runtime\n"
                "runtime=Runtime(sys.argv[2],sys.argv[3],sys.argv[4])\n"
                "result=runtime.selftest()\n"
                "print(json.dumps(result,sort_keys=True,separators=(',',':')))\n"
                "raise SystemExit(0 if result.get('status')=='PASS' and result.get('journal') is True else 21)\n"
            )
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "HOME": str(sandbox / "home"),
                "TMPDIR": str(sandbox),
            }
            Path(env["HOME"]).mkdir()
            proc = subprocess.run(
                [sys.executable, "-I", "-c", harness, str(extracted), str(state_root), str(authority), authority_sha],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=TIMEOUT_SECONDS, cwd=str(sandbox), env=env, check=False,
            )
            report["test_fixture_authority"] = {
                "sha256": authority_sha, "size_bytes": len(authority_bytes),
                "canonical": False, "purpose": "exercise exact-hash preflight in isolated selftest only",
            }
            report["child_exit_code"] = proc.returncode
            report["child_stdout"] = proc.stdout[-16000:]
            report["child_stderr"] = proc.stderr[-8000:]
            if proc.returncode != 0:
                raise RuntimeError(f"Runtime.selftest subprocess returned {proc.returncode}")
            result = json.loads(proc.stdout.strip().splitlines()[-1])
            if result.get("status") != "PASS" or result.get("journal") is not True:
                raise RuntimeError("Runtime.selftest did not return PASS with a valid evidence journal")
            ledger = state_root / "09_EVIDENCE.jsonl"
            if not ledger.is_file():
                raise RuntimeError("Runtime selftest did not produce its expected evidence journal")
            ledger_records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
            if len(ledger_records) != 1 or ledger_records[0].get("event") != "GOVERNANCE_PREFLIGHT":
                raise RuntimeError("Runtime selftest wrote an unexpected event set")
            payload = ledger_records[0].get("payload", {})
            if payload.get("pass") is not True or payload.get("self_certification") is not False or payload.get("authority_transfer") is not False:
                raise RuntimeError("Runtime selftest evidence journal does not prove a passing non-self-certifying preflight")
            report["runtime_selftest_result"] = result
            report["runtime_journal"] = {
                "record_count": len(ledger_records), "sha256": sha256_file(ledger),
                "event_types": [ledger_records[0].get("event")],
                "authority_hash_check": payload.get("pass"),
                "self_certification": payload.get("self_certification"),
                "authority_transfer": payload.get("authority_transfer"),
            }
            report["result"] = "PASS_RUNTIME_SELFTEST_ONLY"
    except Exception as exc:
        report["result"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
    out = ROOT / "evidence/custoszv8-runtime-v1-selftest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS_RUNTIME_SELFTEST_ONLY" else 1

if __name__ == "__main__":
    raise SystemExit(main())
