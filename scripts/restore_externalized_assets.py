#!/usr/bin/env python3
"""Recover externally listed Cajita assets into repository staging, outside the runtime package."""
from __future__ import annotations
import base64, hashlib, json, os, shutil, tempfile, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STAGE_ROOT = REPO_ROOT / "externalized-assets-staging"
REPORT_PATH = REPO_ROOT / "EXTERNALIZED_ASSET_RECOVERY_REPORT.json"
USER_AGENT = "luna-linux-bridge-externalized-recovery/1.0"

def request_bytes(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()

def download_to(url: str, target: Path, timeout: int = 240) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as response, target.open("wb") as out:
        shutil.copyfileobj(response, out, length=1024 * 1024)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha3_256_file(path: Path) -> str:
    h = hashlib.sha3_256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha512_file(path: Path) -> str:
    h = hashlib.sha512()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def pypi_onnx_metadata() -> tuple[str, str, int]:
    meta = json.loads(request_bytes("https://pypi.org/pypi/onnxruntime/1.29.0/json").decode("utf-8"))
    filename = "onnxruntime-1.29.0-cp311-cp311-manylinux_2_28_x86_64.whl"
    item = next((x for x in meta["urls"] if x.get("filename") == filename), None)
    if not item:
        raise RuntimeError("PyPI metadata did not contain the exact pinned ONNX Runtime wheel")
    return item["url"], item["digests"]["sha256"], int(item.get("size") or 0)

def opa_metadata() -> tuple[str, str, int, str]:
    url = "https://api.github.com/repos/open-policy-agent/opa/releases/tags/v1.21.3"
    meta = json.loads(request_bytes(url).decode("utf-8"))
    item = next((x for x in meta["assets"] if x.get("name") == "opa_linux_amd64_static"), None)
    if not item or not str(item.get("digest", "")).startswith("sha256:"):
        raise RuntimeError("OPA release metadata lacked an authoritative SHA-256 digest")
    return item["browser_download_url"], item["digest"].split(":", 1)[1], int(item["size"]), meta["tag_name"]

def artifact_specs() -> list[dict]:
    opa_url, opa_sha, opa_size, opa_version = opa_metadata()
    onnx_url, onnx_sha, onnx_size = pypi_onnx_metadata()
    return [
      {
        "id":"APACHE_JENA_6_2_0",
        "original_externalized_path":"2. Orquestación/Multi + Interdisciplinar/apache-jena-6.2.0.tar.gz",
        "stage_path":"2-Orquestacion/Multi-Interdisciplinar/apache-jena-6.2.0.tar.gz",
        "url":"https://archive.apache.org/dist/jena/binaries/apache-jena-6.2.0.tar.gz",
        "original_sha256":"14c12ef4aa2f0078a473be4b10b015e0e0b85e767d6867e8581679de8fec3f6e",
        "original_size_bytes":23986647,
        "source_version":"6.2.0",
        "source_authentication":"official Apache archive URL plus expected externalization SHA-256",
      },
      {
        "id":"PLAYWRIGHT_1_63_0_SOURCE",
        "original_externalized_path":"2. Orquestación/Orquestador/playwright-1.63.0.tar.gz",
        "stage_path":"2-Orquestacion/Orquestador/playwright-1.63.0.tar.gz",
        "url":"https://github.com/microsoft/playwright/archive/refs/tags/v1.63.0.tar.gz",
        "original_sha256":"bc3d50b5a6c51cd401b2b4a71514be75ffd91223e129abcee51b8913746e4c6d",
        "original_size_bytes":40525667,
        "source_version":"v1.63.0",
        "source_authentication":"official Microsoft Playwright tag archive plus expected externalization SHA-256",
      },
      {
        "id":"ONNX_RUNTIME_1_29_0_CP311",
        "original_externalized_path":"6. Sistema Inteligente/Anti-Alucinaciones/onnxruntime-1.29.0-cp311-cp311-manylinux_2_28_x86_64.whl",
        "stage_path":"6-Sistema-Inteligente/Anti-Alucinaciones/onnxruntime-1.29.0-cp311-cp311-manylinux_2_28_x86_64.whl",
        "url":onnx_url,
        "original_sha256":"7d85eb77dddc3b9f2bda38f8dbcb6804a2c4b06e19ebbbc8f2fd54e8d7468321",
        "original_size_bytes":23020724,
        "source_sha256":onnx_sha,
        "source_size_bytes":onnx_size,
        "source_version":"1.29.0",
        "source_authentication":"official PyPI release JSON SHA-256 for the exact filename",
      },
      {
        "id":"DAGGER_0_21_8_LINUX_AMD64",
        "original_externalized_path":"6. Sistema Inteligente/Cognitive CI - CD/dagger_v0.21.8_linux_amd64.tar.gz",
        "stage_path":"6-Sistema-Inteligente/Cognitive-CI-CD/dagger_v0.21.8_linux_amd64.tar.gz",
        "url":"https://github.com/dagger/dagger/releases/download/v0.21.8/dagger_v0.21.8_linux_amd64.tar.gz",
        "original_sha256":"53e226c7da8fb75171e58c35759d736d961ce8b3a12db0baa7b7107954fccc5a",
        "original_size_bytes":21927634,
        "source_sha256":"53e226c7da8fb75171e58c35759d736d961ce8b3a12db0baa7b7107954fccc5a",
        "source_size_bytes":21927634,
        "source_version":"v0.21.8",
        "source_authentication":"official GitHub release asset digest",
      },
      {
        "id":"OPA_STATIC_LINUX_AMD64_CANDIDATE",
        "original_externalized_path":"6. Sistema Inteligente/Cognitive CI - CD/opa_linux_amd64_static",
        "stage_path":"6-Sistema-Inteligente/Cognitive-CI-CD/opa_linux_amd64_static",
        "url":opa_url,
        "original_sha256":"64529d378ebf1c8ed18795df06353a7c34b0fc797629d80d10636b7ad9880e62",
        "original_size_bytes":38436344,
        "source_sha256":opa_sha,
        "source_size_bytes":opa_size,
        "source_version":opa_version,
        "source_authentication":"official Open Policy Agent GitHub release asset digest; refreshed candidate because external record did not pin a version",
      },
      {
        "id":"RQLITE_10_2_7_LINUX_AMD64",
        "original_externalized_path":"6. Sistema Inteligente/Migración y Persistencia/rqlite-v10.2.7-linux-amd64.tar.gz",
        "stage_path":"6-Sistema-Inteligente/Migracion-y-Persistencia/rqlite-v10.2.7-linux-amd64.tar.gz",
        "url":"https://github.com/rqlite/rqlite/releases/download/v10.2.7/rqlite-v10.2.7-linux-amd64.tar.gz",
        "original_sha256":"0b4e8ffbbacc84e421c49915bbd82cc67ac6488e22d4ce58b678fc1219c6a38a",
        "original_size_bytes":17600273,
        "source_sha256":"0b4e8ffbbacc84e421c49915bbd82cc67ac6488e22d4ce58b678fc1219c6a38a",
        "source_size_bytes":17600273,
        "source_version":"v10.2.7",
        "source_authentication":"official rqlite release SHA-256 shown in release metadata",
      },
      {
        "id":"SQLITE_SOURCE_3_53_4",
        "original_externalized_path":"6. Sistema Inteligente/Migración y Persistencia/sqlite-src-3530400.zip",
        "stage_path":"6-Sistema-Inteligente/Migracion-y-Persistencia/sqlite-src-3530400.zip",
        "url":"https://www.sqlite.org/2026/sqlite-src-3530400.zip",
        "original_sha256":"d18fa15aec74d8c17e1463f861095adc01b5ad190256acb4f91d22f0368d232b",
        "original_size_bytes":14557315,
        "source_sha3_256":"b834d474b9b393d85a9e3ee4cc11f1329e007e9376a424ee740796f5c4bda3a8",
        "source_version":"3.53.4",
        "source_authentication":"official SQLite download page SHA3-256 for sqlite-src-3530400.zip",
      },
      {
        "id":"CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE",
        "original_externalized_path":"6. Sistema Inteligente/Portabilidad base/cmake-4.4.3-windows-x86_64.optimized.zip",
        "stage_path":"6-Sistema-Inteligente/Portabilidad-base/cmake-4.4.3-windows-x86_64.zip",
        "url":"https://github.com/Kitware/CMake/releases/download/v4.4.3/cmake-4.4.3-windows-x86_64.zip",
        "original_sha256":"75bdd838bc5d806dfa025f2c7cfed945f04f83ac7391aa5d2a704b2fe3ef1324",
        "original_size_bytes":22576162,
        "source_sha256":"4d52ebab7193a698651639ed80d8d04fd903358843572cf44c7fd234cb7c26ab",
        "source_size_bytes":54408599,
        "source_version":"v4.4.3",
        "source_authentication":"official Kitware GitHub release asset digest; upstream base package, not the missing optimized variant",
      },
      {
        "id":"AVALONIA_12_1_1_NUGET",
        "original_externalized_path":"6. Sistema Inteligente/Runtime Android Windows/avalonia.12.1.1.nupkg",
        "stage_path":"6-Sistema-Inteligente/Runtime-Android-Windows/avalonia.12.1.1.nupkg",
        "url":"https://api.nuget.org/v3-flatcontainer/avalonia/12.1.1/avalonia.12.1.1.nupkg",
        "original_sha256":"193bf6ae8b90293acb72bca8a1d62e8e46b460a48527f5f1f18f629073d9d77d",
        "original_size_bytes":10112805,
        "source_version":"12.1.1",
        "source_authentication":"official NuGet flat-container package URL",
      },
      {
        "id":"TAURI_2_11_5_SOURCE_ZIP",
        "original_externalized_path":"6. Sistema Inteligente/Runtime Android Windows/tauri-tauri-v2.11.5.zip",
        "stage_path":"6-Sistema-Inteligente/Runtime-Android-Windows/tauri-tauri-v2.11.5.zip",
        "url":"https://github.com/tauri-apps/tauri/archive/refs/tags/tauri-v2.11.5.zip",
        "original_sha256":"a85eb38b0ffc7b37b5c2eadbd637dc1206fb7f719bfe5b3ceca37ad5dac42cdd",
        "original_size_bytes":16117618,
        "source_version":"tauri-v2.11.5",
        "source_authentication":"official Tauri tagged source archive plus expected externalization SHA-256",
      },
    ]

def classify(spec: dict, actual_sha: str, actual_size: int, verified_source: bool) -> str:
    if actual_sha == spec.get("original_sha256") and actual_size == spec.get("original_size_bytes"):
        return "EXACT_EXTERNALIZED_BYTES_RECOVERED"
    if verified_source:
        return "OFFICIAL_SOURCE_CANDIDATE_RECOVERED_HASH_OR_SIZE_DIFFERS_FROM_EXTERNALIZED_RECORD"
    return "SOURCE_VERIFICATION_FAILED_NOT_STAGED"

def main() -> int:
    STAGE_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    staged = 0
    with tempfile.TemporaryDirectory(prefix="cajita-recovery-") as td:
        temp = Path(td)
        for spec in artifact_specs():
            rec = {k: spec.get(k) for k in (
                "id","original_externalized_path","stage_path","url","original_sha256",
                "original_size_bytes","source_version","source_authentication","source_sha256",
                "source_size_bytes","source_sha3_256"
            ) if k in spec}
            target_temp = temp / spec["id"]
            try:
                download_to(spec["url"], target_temp)
                actual_sha = sha256_file(target_temp)
                actual_size = target_temp.stat().st_size
                verified_source = False
                verification_detail = None

                if spec["id"] == "ONNX_RUNTIME_1_29_0_CP311":
                    verified_source = actual_sha == spec["source_sha256"] and actual_size == spec["source_size_bytes"]
                    verification_detail = "matched PyPI's published digest for the exact wheel filename" if verified_source else "did not match the PyPI JSON digest/size"
                elif spec["id"] == "OPA_STATIC_LINUX_AMD64_CANDIDATE":
                    verified_source = actual_sha == spec["source_sha256"] and actual_size == spec["source_size_bytes"]
                    verification_detail = "matched the official GitHub release asset digest and size" if verified_source else "did not match the official GitHub release asset digest/size"
                elif spec["id"] == "CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE":
                    verified_source = actual_sha == spec["source_sha256"] and actual_size == spec["source_size_bytes"]
                    verification_detail = "matched the official Kitware release asset digest and size" if verified_source else "did not match the official Kitware release asset digest/size"
                elif spec["id"] == "DAGGER_0_21_8_LINUX_AMD64" or spec["id"] == "RQLITE_10_2_7_LINUX_AMD64":
                    verified_source = actual_sha == spec["source_sha256"] and actual_size == spec["source_size_bytes"]
                    verification_detail = "matched the official release SHA-256 and size" if verified_source else "did not match the official release SHA-256/size"
                elif spec["id"] == "SQLITE_SOURCE_3_53_4":
                    actual_sha3 = sha3_256_file(target_temp)
                    rec["actual_sha3_256"] = actual_sha3
                    verified_source = actual_sha3 == spec["source_sha3_256"]
                    verification_detail = "matched SQLite's published SHA3-256" if verified_source else "did not match SQLite's published SHA3-256"
                else:
                    verified_source = actual_sha == spec["original_sha256"] and actual_size == spec["original_size_bytes"]
                    verification_detail = "matched the externalization record's SHA-256 and size" if verified_source else "official URL download did not match the exact externalization hash/size"

                rec.update({
                    "actual_sha256": actual_sha,
                    "actual_size_bytes": actual_size,
                    "verified_official_source": verified_source,
                    "verification_detail": verification_detail,
                })
                if verified_source:
                    target = STAGE_ROOT / spec["stage_path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target_temp, target)
                    staged += 1
                    rec["staged_path"] = target.relative_to(REPO_ROOT).as_posix()
                    rec["status"] = classify(spec, actual_sha, actual_size, verified_source)
                else:
                    rec["staged_path"] = None
                    rec["status"] = "BLOCKED_CHECKSUM_OR_SOURCE_VERIFICATION"
                results.append(rec)
            except Exception as exc:
                rec.update({
                    "actual_sha256": None,
                    "actual_size_bytes": None,
                    "verified_official_source": False,
                    "verification_detail": str(exc)[:1000],
                    "staged_path": None,
                    "status": "DOWNLOAD_OR_VERIFICATION_ERROR",
                })
                results.append(rec)

    report = {
        "schema":"CAJITA_EXTERNALIZED_ASSET_RECOVERY/1.0",
        "created_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
        "repository":"Plomillo/luna-linux-bridge",
        "branch":os.environ.get("GITHUB_REF_NAME","repair/restore-externalized-assets-20261023"),
        "scope":"Recover the ten externalized software/runtime assets to a repository staging area outside cajita-luna-runtime.",
        "staging_root":"externalized-assets-staging/",
        "runtime_package_mutated":False,
        "macrodown_manifest_mutated":False,
        "hard_cap_bytes":470000000,
        "source_manifests":{
            "externalization_manifest_blob_sha":"c9781166127e44a421bf7156127f61f2241b574c",
            "macrodown_manifest_blob_sha":"70d1dcc738801cff8dd3aaae17ea551594148bfc",
        },
        "counts":{
            "requested":len(results),
            "staged":sum(1 for x in results if x.get("staged_path")),
            "blocked_or_failed":sum(1 for x in results if not x.get("staged_path")),
            "exact_externalized_bytes":sum(1 for x in results if x.get("status")=="EXACT_EXTERNALIZED_BYTES_RECOVERED"),
            "official_candidate_hash_or_size_differs":sum(1 for x in results if x.get("status")=="OFFICIAL_SOURCE_CANDIDATE_RECOVERED_HASH_OR_SIZE_DIFFERS_FROM_EXTERNALIZED_RECORD"),
        },
        "assets":results,
        "notes":[
            "Staged files are at repository root, outside cajita-luna-runtime, so they do not enter the current .macrodown automatically.",
            "A source candidate with a different hash or size is not represented as byte-identical to the externalized candidate.",
            "The externalization manifest and runtime package manifest were left unchanged.",
            "The missing cmake optimized archive is not reconstructed here; the official CMake v4.4.3 Windows ZIP is staged as a baseline candidate with its actual official digest.",
            "OPA was not version-pinned in the externalization record; the staged candidate is the official v1.21.3 release, with its version and digest recorded.",
        ],
    }
    REPORT_PATH.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report["counts"], ensure_ascii=False))
    for x in results:
        print(f'{x["status"]}: {x["id"]} -> {x.get("staged_path") or "NOT_STAGED"} ({x.get("verification_detail")})')
    return 0 if staged > 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
