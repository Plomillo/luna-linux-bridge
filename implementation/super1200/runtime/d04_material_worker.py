#!/usr/bin/env python3
"""Task-specific D04 material worker for capabilities 87-92.

It runs behavior tests against implemented code, then marks only the exact tested
capabilities EVIDENCED and emits hash-bound evidence. It never certifies G23/G24.
"""
from __future__ import annotations
import hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOMAIN = ROOT / "implementation/super1200/domains/D04.json"
REGISTRY = ROOT / "implementation/super1200/registry/capabilities.json"
MODULE = ROOT / "implementation/super1200/domains/D04_runtime.py"
TEST = ROOT / "implementation/super1200/tests/test_d04_runtime.py"
OUT = ROOT / "continuity/runtime-evidence/D04"
TASKS = [
    (87, "GITHUB_ARTIFACT_ATTESTATION_PROVIDER",
     "test_github_attestation_binds_subject_and_declares_unsigned_state"),
    (88, "SIGSTORE_PROVIDER",
     "test_sigstore_bundle_requires_trusted_crypto_verifier_and_exact_subject"),
    (89, "REKOR_TRANSPARENCY_PROVIDER",
     "test_rekor_entry_requires_valid_inclusion_proof"),
    (90, "SPDX_PROVIDER",
     "test_spdx_sbom_is_sorted_hash_bound_and_rejects_duplicate_ids"),
    (91, "CYCLONEDX_PROVIDER",
     "test_cyclonedx_sbom_hashes_components_and_rejects_bad_digest"),
    (92, "CERTIFICATION_SCOPE_IDENTITY",
     "test_certification_scope_is_subject_bound_and_non_transitive"),
]
def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
def main() -> int:
    for p in (DOMAIN, REGISTRY, MODULE, TEST):
        if not p.is_file():
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY MISSING={p.relative_to(ROOT)}")
    domain = json.loads(DOMAIN.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if registry.get("count") != 1200 or len(registry.get("items", [])) != 1200:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY REGISTRY_COUNT_MISMATCH")
    by_id = {item.get("capability_id"): item for item in registry["items"]}
    domain_by_id = {item.get("capability_id"): item for item in domain.get("capabilities", [])}
    for cid, name, _ in TASKS:
        if cid not in by_id or by_id[cid].get("canonical_name") != name:
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY REGISTRY_IDENTITY_MISMATCH ID={cid}")
        if cid not in domain_by_id or domain_by_id[cid].get("canonical_name") != name:
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY DOMAIN_IDENTITY_MISMATCH ID={cid}")
    OUT.mkdir(parents=True, exist_ok=True)
    run = subprocess.run(
        [sys.executable, "-B", str(TEST)], cwd=ROOT, text=True,
        capture_output=True, timeout=180
    )
    started = datetime.now(timezone.utc).isoformat()
    if run.returncode != 0:
        print("SUPER1200_TELEMETRY " + json.dumps({
            "event":"D04_MATERIAL_TESTS_FAILED", "exit_code":run.returncode,
            "stdout":run.stdout[-12000:], "stderr":run.stderr[-12000:],
            "module_sha256":digest(MODULE), "test_sha256":digest(TEST),
        }, sort_keys=True), flush=True)
        return run.returncode or 1
    module_hash, test_hash = digest(MODULE), digest(TEST)
    for cid, name, test_name in TASKS:
        evidence = {
            "schema":"SUPER1200_D04_MATERIAL_EVIDENCE/1",
            "capability_id":cid, "canonical_name":name,
            "executor":"implementation/super1200/runtime/d04_material_worker.py",
            "implementation_artifact":"implementation/super1200/domains/D04_runtime.py",
            "test_artifact":"implementation/super1200/tests/test_d04_runtime.py",
            "test_case":test_name, "status":"PASS",
            "validated_at_utc":datetime.now(timezone.utc).isoformat(),
            "module_sha256":module_hash, "test_sha256":test_hash,
            "suite_stdout_sha256":hashlib.sha256(run.stdout.encode()).hexdigest(),
            "suite_stderr_sha256":hashlib.sha256(run.stderr.encode()).hexdigest(),
            "suite_exit_code":run.returncode, "g23":"PENDING_INDEPENDENT_VALIDATION",
            "g24":"PENDING_G23", "certification_granted":False,
        }
        evidence["evidence_sha256"] = hashlib.sha256(
            json.dumps(evidence, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()
        ).hexdigest()
        (OUT / f"capability-{cid:04d}.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        item = by_id[cid]
        item["implementation_state"] = "EVIDENCED"
        item["implementation_artifact"] = "implementation/super1200/domains/D04_runtime.py"
        item["test_artifact"] = "implementation/super1200/tests/test_d04_runtime.py"
        item["materialization"] = "CODE+SCHEMA+BEHAVIOR_TEST"
        domain_by_id[cid]["implementation_state"] = "EVIDENCED"
    DOMAIN.write_text(json.dumps(domain, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print("SUPER1200_TELEMETRY " + json.dumps({
        "event":"D04_MATERIAL_IMPLEMENTATION_PASS", "capabilities":[x[0] for x in TASKS],
        "count":len(TASKS), "module_sha256":module_hash, "test_sha256":test_hash,
        "suite_exit_code":run.returncode, "g23":"PENDING_INDEPENDENT_VALIDATION",
        "g24":"PENDING_G23", "certification_granted":False,
    }, sort_keys=True), flush=True)
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
