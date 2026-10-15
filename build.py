#!/usr/bin/env python3
"""Build CUSTOSZV8.pyz from the exact repository candidate."""
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, sys, zipapp, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
from custoszv8.core import canonical_json, inspect_archive, inspect_wasm, sha256_file, selftest, V8Error

COMPONENT_SPECS = {
    "CUSTOSZ_V7": {
        "source": ROOT / "artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz",
        "target": "custoszv8/data/components/CUSTOSZ.v07.f04_b.pyz",
        "integration_status": "PENDING_CI_NATIVE_SELFTEST_AND_ADAPTER_VALIDATION"
    },
    "RUNTIME_V1_SELECTED_STAGING": {
        "source": ROOT / "artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz",
        "target": "custoszv8/data/components/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz",
        "integration_status": "BLOCKED_UNTIL_NATIVE_INTERFACE_TESTED",
        "variant_scope": "EXACT_SELECTED_STAGING_BYTES_ONLY",
        "skeleton_reference_equivalence": "NOT_ASSERTED"
    },
    "METAOS_WASM": {
        "source": ROOT / "artifacts/custosz-v7/MetaOS.wasm",
        "target": "custoszv8/data/components/MetaOS.wasm",
        "integration_status": "BLOCKED_UNTIL_ABI_AND_EXPORT_CONTRACT_VERIFIED"
    }
}

def main() -> int:
    build_root = ROOT / "build/custoszv8-pyz-root"
    dist = ROOT / "dist"
    if build_root.exists():
        shutil.rmtree(build_root)
    build_root.mkdir(parents=True)
    dist.mkdir(parents=True, exist_ok=True)
    package_dir = build_root / "custoszv8"
    shutil.copytree(SRC / "custoszv8", package_dir)
    components = {}
    blockers = []
    for name, spec in COMPONENT_SPECS.items():
        src = spec["source"]
        if not src.is_file():
            blockers.append(f"required component missing: {src.relative_to(ROOT)}")
            components[name] = {"path": spec["target"], "sha256": None, "size_bytes": None,
                                "status": "MISSING", "integration_status": "BLOCKED"}
            continue
        dest = build_root / spec["target"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        digest, size = sha256_file(dest), dest.stat().st_size
        record = {
            "path": spec["target"], "sha256": digest, "size_bytes": size,
            "status": "HASHED_FROM_EXACT_BUILD_BYTES",
            "integration_status": spec["integration_status"],
            "source_path": str(src.relative_to(ROOT))
        }
        for key in ("variant_scope", "skeleton_reference_equivalence"):
            if key in spec: record[key] = spec[key]
        try:
            if dest.suffix == ".wasm":
                abi = inspect_wasm(dest)
                abi.pop("path", None)
                record["static_abi_observation"] = abi
            elif dest.suffix in {".pyz", ".zip"}:
                inspection = inspect_archive(dest)
                inspection.pop("path", None)
                record["static_archive_observation"] = inspection
        except (V8Error, OSError, ValueError) as exc:
            record["static_inspection_error"] = f"{type(exc).__name__}: {exc}"
            record["integration_status"] = "BLOCKED_STATIC_INSPECTION_FAILED"
            blockers.append(f"{name} static inspection failed: {exc}")
        components[name] = record

    ownership_doc = json.loads((package_dir / "data/capability_ownership.json").read_text(encoding="utf-8"))
    interfaces_doc = json.loads((package_dir / "data/interfaces.json").read_text(encoding="utf-8"))
    contracts_doc = json.loads((package_dir / "data/contract_registry.json").read_text(encoding="utf-8"))
    runtime_policy_doc = json.loads((package_dir / "data/runtime_policy.json").read_text(encoding="utf-8"))
    translation_policy_doc = json.loads((package_dir / "data/translation_policy.json").read_text(encoding="utf-8"))
    manifest = {
        "schema_version": "1.0.0",
        "artifact_id": "CUSTOSZV8",
        "artifact_version": "8.0.0-candidate",
        "artifact_status": "CANDIDATE_BUILD",
        "package_status": "CANDIDATE_BLOCKED_PENDING_FULL_INTEGRATION_AND_G23_G24",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
        "source_commit": os.environ.get("GITHUB_SHA", "LOCAL_UNBOUND"),
        "source_branch": os.environ.get("GITHUB_REF_NAME", "LOCAL"),
        "canonical_authority_ref": {
            "artifact_id": "Louksna.md",
            "authority": True,
            "mutation_permitted": False
        },
        "protected_baseline_ref": {
            "artifact_id": "LUNACORE_final_formalized_v25.md",
            "status": "PROTECTED_NOT_MUTATED_BY_BUILD"
        },
        "governance": {
            "doctrine": "EXTEND_DO_NOT_REPLACE",
            "construction": "APPEND_ONLY_WHERE_CANONICAL",
            "failure_policy": "FAIL_CLOSED",
            "puac2_version": "2.0.0-CANDIDATE",
            "local_controls": [f"PUAC.C{i}" for i in range(25,33)],
            "local_control_promotion": "NOT_AUTHORIZED"
        },
        "components": components,
        "capability_ownership": ownership_doc.get("capabilities", []),
        "interface_registry": interfaces_doc,
        "contract_registry": contracts_doc,
        "policies": {
            "runtime": runtime_policy_doc,
            "translation": translation_policy_doc
        },
        "interfaces": {
            "V7": "ADAPTER_MUST_BIND_ONLY_TO_VERIFIED_NATIVE_INTERFACE",
            "RUNTIME_V1": "NATIVE_INTERFACE_TEST_REQUIRED",
            "METAOS_WASM": "ABI_INCOMPLETE_UNTIL_SIGNATURES_AND_EXPORT_USAGE_VERIFIED"
        },
        "gates": [{"gate_id":f"G{i:02d}","state":"NOT_EVALUATED_FOR_V8_RELEASE"} for i in range(1,25)],
        "certification": {
            "g23": "NOT_GRANTED",
            "g24": "NOT_GRANTED",
            "canonical_admission": "NOT_GRANTED",
            "operational_authorization": "NOT_GRANTED",
            "self_certification": False
        },
        "limitations": [
            "The package selftest assesses V8 internal primitives only.",
            "Historical component hashes are not substituted for build-time SHA-256.",
            "The selected staging Runtime bytes are identified exactly; equivalence to the separate R4 Skeleton pin is not asserted.",
            "Static WASM imports/exports do not prove complete ABI signatures or operational behaviour.",
            "Component tests do not prove cross-component integration.",
            "No G23/G24 or operational authorization is issued by the build."
        ],
        "blockers": blockers
    }
    data_dir = package_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "build_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    launcher = "from custoszv8.cli import main\nraise SystemExit(main())\n"
    (build_root / "__main__.py").write_text(launcher, encoding="utf-8")
    target = dist / "CUSTOSZV8.pyz"
    if target.exists(): target.unlink()
    zipapp.create_archive(build_root, target=target, interpreter="/usr/bin/env python3", compressed=True)
    target.chmod(0o755)
    with zipfile.ZipFile(target) as archive:
        bad = archive.testzip()
        if bad: raise SystemExit(f"zip integrity failed at {bad}")
        if "__main__.py" not in archive.namelist(): raise SystemExit("missing ZIPAPP __main__.py")
        for spec in COMPONENT_SPECS.values():
            if (build_root / spec["target"]).exists() and spec["target"] not in archive.namelist():
                raise SystemExit(f"embedded component missing from package: {spec['target']}")
    check = subprocess.run([sys.executable, str(target), "selftest"], capture_output=True, text=True, timeout=30)
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence/custoszv8-selftest.json").write_text(check.stdout or check.stderr, encoding="utf-8")
    if check.returncode:
        print(check.stdout); print(check.stderr, file=sys.stderr)
        raise SystemExit(f"CUSTOSZV8.pyz selftest failed ({check.returncode})")
    report = {
        "status": "PASS_FOR_PACKAGE_BUILD_AND_INTERNAL_SELFTEST",
        "artifact": "dist/CUSTOSZV8.pyz",
        "sha256": sha256_file(target),
        "size_bytes": target.stat().st_size,
        "source_commit": os.environ.get("GITHUB_SHA", "LOCAL_UNBOUND"),
        "internal_selftest": json.loads(check.stdout),
        "native_integration": "NOT_CERTIFIED",
        "g23": "NOT_GRANTED",
        "g24": "NOT_GRANTED"
    }
    (ROOT / "evidence/custoszv8-build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
