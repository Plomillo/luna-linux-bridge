#!/usr/bin/env python3
"""Execute SRExecBoundFME01 once in an isolated CI fixture with a harmless temporary-file effect."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from custoszv8.core import RUNTIME_V1_SELECTED_SHA256

RUNTIME = ROOT / "artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
EXPECTED_MEMBERS = {"__main__.py", "runtime_core.py", "sr_exec_bound_fme_01.py"}
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024
MAX_MEMBER_BYTES = 512 * 1024
TIMEOUT_SECONDS = 20


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def atomic_json(path: Path, value: dict) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> int:
    report = {
        "schema": "custoszv8.runtime-v1-sr-exec-bounded-fixture.v1",
        "candidate_commit": os.environ.get("CUSTOSZV8_CANDIDATE_SHA") or os.environ.get("GITHUB_SHA", "LOCAL_UNBOUND"),
        "observed_at_utc": now(),
        "runtime_path": str(RUNTIME.relative_to(ROOT)),
        "expected_runtime_sha256": RUNTIME_V1_SELECTED_SHA256,
        "status": "HOLD",
        "production_mission_dispatch": "NOT_AUTHORIZED",
        "canonical_authority_binding": "NOT_TESTED_SYNTHETIC_AUTHORITY_ONLY",
        "production_restore": "NOT_TESTED",
        "g22": "NOT_DEMONSTRATED",
        "g23": "NOT_GRANTED",
        "g24": "NOT_GRANTED",
        "execution_authorized": False,
        "limitations": [
            "This exercises the actual SRExecBoundFME01 protocol only against a temporary CI fixture and a benign Python child.",
            "The authority document is synthetic, not Louksna.md.",
            "The material effect is a temporary test-file write; no production file, service, host executor, or user mission is touched.",
            "The test proves protocol behavior in this fixture only, not global integration or non-regression.",
            "G23 and G24 remain separate governance decisions and are not inferred from CI."
        ],
    }
    try:
        if not RUNTIME.is_file():
            raise RuntimeError("selected Runtime V1 archive is missing")
        if RUNTIME.stat().st_size > MAX_ARCHIVE_BYTES:
            raise RuntimeError("Runtime V1 archive exceeds the bounded inspection size")
        runtime_sha = sha256_file(RUNTIME)
        report.update({"runtime_observed_sha256": runtime_sha, "runtime_size_bytes": RUNTIME.stat().st_size})
        if runtime_sha != RUNTIME_V1_SELECTED_SHA256:
            raise RuntimeError("Runtime V1 digest differs from the pinned staging artifact")

        with zipfile.ZipFile(RUNTIME) as archive:
            infos = archive.infolist()
            names = [entry.filename for entry in infos]
            if len(names) != len(EXPECTED_MEMBERS) or set(names) != EXPECTED_MEMBERS:
                raise RuntimeError(f"Runtime V1 member-set mismatch: {names!r}")
            if sum(entry.file_size for entry in infos) > MAX_ARCHIVE_BYTES:
                raise RuntimeError("Runtime V1 uncompressed members exceed the bounded inspection size")
            source_bytes = {}
            for entry in infos:
                item = Path(entry.filename)
                if item.is_absolute() or ".." in item.parts or entry.is_dir() or entry.file_size > MAX_MEMBER_BYTES:
                    raise RuntimeError(f"unsafe Runtime V1 archive member: {entry.filename}")
                if entry.filename in {"runtime_core.py", "sr_exec_bound_fme_01.py"}:
                    source_bytes[entry.filename] = archive.read(entry)
        if set(source_bytes) != {"runtime_core.py", "sr_exec_bound_fme_01.py"}:
            raise RuntimeError("reviewed Runtime V1 API modules are missing")

        with tempfile.TemporaryDirectory(prefix="custoszv8-sr-exec-fixture-") as td:
            base = Path(td).resolve()
            source_dir = base / "source"
            source_dir.mkdir()
            for filename, raw in source_bytes.items():
                text = raw.decode("utf-8")
                compile(text, filename, "exec")
                (source_dir / filename).write_bytes(raw)

            authority = base / "SYNTHETIC_AUTHORITY_FIXTURE.md"
            authority_bytes = b"CI ONLY: SYNTHETIC AUTHORITY; NOT Louksna.md; NO PRODUCTION AUTHORITY.\n"
            authority.write_bytes(authority_bytes)
            authority_sha = sha256_file(authority)
            runtime_root = base / "runtime-state"
            target = base / "mission-effect.txt"
            original = b"PRE-DISPATCH-STATE\n"
            target.write_bytes(original)
            runtime_digest = runtime_sha
            executable_sha = sha256_file(Path(sys.executable).resolve())
            child_script = base / "bounded_executor.py"
            child_script.write_text(
                "import argparse, hashlib, json, os, sys, time\n"
                f"sys.path.insert(0, {str(source_dir)!r})\n"
                "from sr_exec_bound_fme_01 import _record_digest\n"
                "p=argparse.ArgumentParser()\n"
                "p.add_argument('--dispatch',required=True); p.add_argument('--ack',required=True)\n"
                "p.add_argument('--fme',required=True); p.add_argument('--target',required=True)\n"
                "a=p.parse_args()\n"
                "dispatch=json.loads(open(a.dispatch,encoding='utf-8').read())\n"
                "pid=os.getpid()\n"
                "ack={'mission_id':dispatch['mission_id'],'dispatch_id':dispatch['dispatch_id'],"
                "'executor_id':dispatch['executor_id'],'accepted':True,'pid':pid,"
                "'process_or_execution_token':'CI-BOUNDED-CHILD-'+str(pid)}\n"
                "ack['ack_digest']=_record_digest(ack,'ack_digest')\n"
                "with open(a.ack,'w',encoding='utf-8') as f: json.dump(ack,f,sort_keys=True); f.write('\\n'); f.flush(); os.fsync(f.fileno())\n"
                "time.sleep(0.25)\n"
                "target=os.path.abspath(a.target); payload=b'CUSTOSZV8-SR-EXEC-BOUNDED-EFFECT\\n'\n"
                "with open(target,'wb') as f: f.write(payload); f.flush(); os.fsync(f.fileno())\n"
                "after=hashlib.sha256(open(target,'rb').read()).hexdigest()\n"
                "fme={'mission_id':dispatch['mission_id'],'dispatch_id':dispatch['dispatch_id'],"
                "'binding_id':dispatch['binding_id'],'pid':pid,'target':target,'after_digest':after,"
                "'effect_type':dispatch['expected_effect']['effect_type'],'effect_is_material':True,"
                "'effect_is_mission_relevant':True,'effect_is_authorized':True,'effect_is_observable':True,"
                "'fme_id':'FME-CI-BOUNDED-'+str(pid)}\n"
                "fme['fme_digest']=_record_digest(fme,'fme_digest')\n"
                "with open(a.fme,'w',encoding='utf-8') as f: json.dump(fme,f,sort_keys=True); f.write('\\n'); f.flush(); os.fsync(f.fileno())\n"
                "time.sleep(0.4)\n",
                encoding="utf-8"
            )

            harness = r'''
import hashlib, json, sys
from pathlib import Path
from types import SimpleNamespace
source_dir, runtime_root, authority_path, authority_sha, worker, target, runtime_sha, executable_sha = sys.argv[1:9]
sys.path.insert(0, source_dir)
from runtime_core import Runtime
from sr_exec_bound_fme_01 import SRExecBoundFME01
rt = Runtime(runtime_root, authority_path, authority_sha)
target_path = Path(target)
original = b"PRE-DISPATCH-STATE
"
checkpoint = rt.checkpoints.capture_file("V8-SR-EXEC-BOUNDED-CHECKPOINT", target_path)
name = "ci-bounded-python-executor"
rt.executors.register(SimpleNamespace(
    name=name, kind="PYTHON_PROCESS", command=sys.executable, model=None,
    capabilities={"bounded_test_write": 1.0}
))
payload_digest = hashlib.sha256(b"CI-BOUNDED-PAYLOAD-NO-PRODUCTION-EFFECT").hexdigest()
spec = {
  "mission_id":"MIS-CUSTOSZV8-SR-EXEC-BOUNDED-FIXTURE",
  "mission_spec_digest":hashlib.sha256(b"CUSTOSZV8-FIXTURE-SPEC").hexdigest(),
  "required_abilities":{"bounded_test_write":1.0},
  "authority_context":{"authority_id":"SYNTHETIC_AUTHORITY_FIXTURE","authority_sha256":authority_sha,"canonical":False},
  "policy_context":{"allow":True,"scope":"one temporary fixture file only","policy_id":"CI-BOUNDED-TEST-ONLY"},
  "execution_payload_digest":payload_digest,
  "expected_effect":{"target":str(target_path),"effect_type":"BOUNDED_TEST_FIXTURE_WRITE"},
  "checkpoint_pointer":str(checkpoint["snapshot"]),
  "runtime_digest":runtime_sha,
  "mission_state":"DISPATCH_READY",
  "executor_metadata":{name:{"identity_valid":True,"provenance_valid":True,"digest":executable_sha}},
  "executor_policy":{name:{"permissions_valid":True,"resource_envelope_valid":True,"policy_allow":True,"risk":0.0,"cost":0.0}},
  "probe_argv":{name:["{COMMAND}","-I","-c","print('CUSTOSZV8_EXECUTOR_PROBE_OK')"]},
  "probe_timeout_s":5.0,
  "dispatch":{
    "cwd":str(Path(runtime_root).parent),"timeout_s":8.0,"ack_timeout_s":3.0,"fme_timeout_s":3.0,
    "argv_template":["{COMMAND}","-I",worker,"--dispatch","{DISPATCH_PATH}","--ack","{ACK_PATH}","--fme","{FME_PATH}","--target","{TARGET}"]
  }
}
result = SRExecBoundFME01(rt).establish_material_execution(spec)
if result.get("result") != "PASS" or result.get("material_execution_proven") is not True:
    raise RuntimeError("SRExecBoundFME01 did not prove the bounded fixture dispatch")
if result.get("global_step_gate") != 1 or result.get("execution_bootstrap_gate") != 1:
    raise RuntimeError("SRExecBoundFME01 terminal gates did not pass")
if result.get("process",{}).get("returncode") != 0:
    raise RuntimeError("bounded worker did not exit successfully")
if rt.journal.verify() is not True:
    raise RuntimeError("Runtime V1 journal did not verify after bounded mission dispatch")
dispatch=json.loads((Path(runtime_root)/"03_DISPATCH.json").read_text(encoding="utf-8"))
ack=json.loads((Path(runtime_root)/"04_DISPATCH_ACK.json").read_text(encoding="utf-8"))
fme=json.loads((Path(runtime_root)/"05_FIRST_MATERIAL_EVENT.json").read_text(encoding="utf-8"))
if ack.get("dispatch_id") != dispatch["dispatch_id"] or fme.get("dispatch_id") != dispatch["dispatch_id"]:
    raise RuntimeError("ACK/FME are not bound to the exact generated dispatch ID")
if fme.get("binding_id") != result.get("binding_id") or fme.get("after_digest") != hashlib.sha256(Path(target).read_bytes()).hexdigest():
    raise RuntimeError("FME is not bound to the exact executor binding/effect digest")
changed_digest=hashlib.sha256(Path(target).read_bytes()).hexdigest()
if not rt.checkpoints.restore_file(checkpoint["checkpoint_id"], target):
    raise RuntimeError("bounded fixture rollback returned false")
restored_digest=hashlib.sha256(Path(target).read_bytes()).hexdigest()
if restored_digest != checkpoint["sha256"] or Path(target).read_bytes() != original:
    raise RuntimeError("bounded fixture rollback did not restore the original target bytes")
if rt.journal.verify() is not True:
    raise RuntimeError("journal did not verify after fixture rollback")
out={
 "status":"PASS_BOUNDED_SR_EXEC_MATERIAL_DISPATCH",
 "mission_id":spec["mission_id"],"mission_result":result["result"],
 "material_execution_proven":result["material_execution_proven"],
 "execution_bootstrap_gate":result["execution_bootstrap_gate"],
 "global_step_gate":result["global_step_gate"],"runtime_journal_verified":True,
 "dispatch_id":dispatch["dispatch_id"],"binding_id":result["binding_id"],"fme_id":fme["fme_id"],
 "worker_returncode":result["process"]["returncode"],
 "material_effect_sha256":changed_digest,"checkpoint_sha256":checkpoint["sha256"],
 "restored_sha256":restored_digest,"fixture_rollback":"PASS",
 "authority":{"kind":"SYNTHETIC_TEST_FIXTURE","canonical":False,"authority_transfer":False},
 "scope":"ONE_TEMPORARY_FILE_AND_ONE_BENIGN_CI_CHILD_PROCESS",
 "production_mission_dispatch":"NOT_AUTHORIZED","production_restore":"NOT_TESTED",
 "canonical_authority_binding":"NOT_TESTED","execution_authorized":False,
 "g22":"NOT_DEMONSTRATED","g23":"NOT_GRANTED","g24":"NOT_GRANTED"
}
print(json.dumps(out,sort_keys=True))
'''
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "HOME": str(base / "home"),
                "TMPDIR": str(base),
            }
            Path(env["HOME"]).mkdir()
            import subprocess
            proc = subprocess.run(
                [sys.executable, "-I", "-c", harness, str(source_dir), str(runtime_root), str(authority),
                 authority_sha, str(child_script), str(target), runtime_digest, executable_sha],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                timeout=TIMEOUT_SECONDS, cwd=str(base), env=env, check=False
            )
            report["harness_exit_code"] = proc.returncode
            report["harness_stdout"] = proc.stdout[-12000:]
            report["harness_stderr"] = proc.stderr[-12000:]
            if proc.returncode != 0:
                raise RuntimeError("bounded SRExecBoundFME01 fixture failed")
            result = json.loads(proc.stdout.strip().splitlines()[-1])
            if result.get("status") != "PASS_BOUNDED_SR_EXEC_MATERIAL_DISPATCH":
                raise RuntimeError("bounded SRExecBoundFME01 result lacks PASS")
            report["probe"] = result
            report["status"] = "PASS_BOUNDED_SR_EXEC_MATERIAL_DISPATCH"
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
    outpath = ROOT / "evidence/custoszv8-runtime-v1-material-dispatch.json"
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS_BOUNDED_SR_EXEC_MATERIAL_DISPATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
