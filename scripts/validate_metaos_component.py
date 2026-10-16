#!/usr/bin/env python3
"""Validate MetaOS.wasm with the pinned official Bytecode Alliance wasm-tools release."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tarfile
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
WASM = ROOT / "artifacts/custosz-v7/MetaOS.wasm"
CANDIDATE_WASM = ROOT / "build/MetaOS_V8_candidate.wasm"
CANDIDATE_WAT = ROOT / "build/MetaOS_V8_candidate.wat"
TOOLS_VERSION = "1.254.0"
TOOLS_URL = "https://github.com/bytecodealliance/wasm-tools/releases/download/v1.254.0/wasm-tools-1.254.0-x86_64-linux.tar.gz"
TOOLS_ARCHIVE_SHA256 = "d0efb16c9c859137b7ab3e99151c299cd47caee106ed4594561002f7a04945bd"
TOOLS_ARCHIVE_SIZE = 5862464
TIMEOUT_SECONDS = 20
MAX_WASM_BYTES = 16 * 1024 * 1024
MAX_TOOLS_ARCHIVE_BYTES = 10 * 1024 * 1024
MAX_TOOL_BINARY_BYTES = 64 * 1024 * 1024

def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run(cmd: list[str], timeout: int = TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, timeout=timeout,
                          env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                               "LC_ALL": "C", "LANG": "C"},
                          check=False)

def main() -> int:
    report = {
        "schema": "custoszv8.metaos-component-evidence.v1",
        "candidate_commit": os.environ.get("GITHUB_SHA", "LOCAL_UNBOUND"),
        "observed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "component": "METAOS_WASM",
        "component_validation": "NOT_RUN",
        "wit_status": "NOT_RUN",
        "abi_status": "NOT_DEMONSTRATED",
        "invocation_performed": False,
        "g23": "NOT_GRANTED",
        "g24": "NOT_GRANTED",
        "certification": "NOT_GRANTED",
        "tool": {"name": "wasm-tools", "version_pinned": TOOLS_VERSION,
                 "release_asset_url": TOOLS_URL, "release_asset_sha256_expected": TOOLS_ARCHIVE_SHA256},
        "limitations": [
            "Validation and WIT extraction do not execute the component.",
            "An empty import/export world is not an operational ABI.",
            "Passing binary validation is not proof of cross-component integration.",
        ],
    }
    try:
        if not WASM.is_file():
            raise RuntimeError("MetaOS.wasm missing")
        wasm_size = WASM.stat().st_size
        if wasm_size > MAX_WASM_BYTES:
            raise RuntimeError("MetaOS.wasm exceeds size limit")
        report["wasm_sha256"] = sha256_file(WASM)
        report["wasm_size_bytes"] = wasm_size
        with tempfile.TemporaryDirectory(prefix="custoszv8-wasm-tools-") as td:
            tmp = Path(td)
            archive_path = tmp / "wasm-tools.tar.gz"
            request = urllib.request.Request(TOOLS_URL, headers={"User-Agent": "CUSTOSZV8-Assurance/1.0"})
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                raw_asset = response.read(MAX_TOOLS_ARCHIVE_BYTES + 1)
            if len(raw_asset) > MAX_TOOLS_ARCHIVE_BYTES:
                raise RuntimeError("wasm-tools release asset exceeded download bound")
            if len(raw_asset) != TOOLS_ARCHIVE_SIZE:
                raise RuntimeError(f"wasm-tools asset size mismatch: observed {len(raw_asset)}")
            observed_asset_sha = sha256_bytes(raw_asset)
            report["tool"]["release_asset_size_bytes"] = len(raw_asset)
            report["tool"]["release_asset_sha256_observed"] = observed_asset_sha
            if observed_asset_sha != TOOLS_ARCHIVE_SHA256:
                raise RuntimeError("wasm-tools official asset SHA-256 mismatch")
            archive_path.write_bytes(raw_asset)
            executable_member = None
            with tarfile.open(archive_path, "r:gz") as archive:
                members = archive.getmembers()
                for member in members:
                    p = PurePosixPath(member.name)
                    if p.is_absolute() or ".." in p.parts or member.issym() or member.islnk() or member.isdev():
                        raise RuntimeError(f"unsafe wasm-tools archive member: {member.name}")
                candidates = [m for m in members if PurePosixPath(m.name).name == "wasm-tools" and m.isfile()]
                if len(candidates) != 1:
                    raise RuntimeError(f"expected exactly one wasm-tools binary, found {len(candidates)}")
                executable_member = candidates[0]
                extracted = archive.extractfile(executable_member)
                if extracted is None:
                    raise RuntimeError("cannot read wasm-tools binary from the verified release asset")
                binary = extracted.read(MAX_TOOL_BINARY_BYTES + 1)
                if len(binary) > MAX_TOOL_BINARY_BYTES:
                    raise RuntimeError("wasm-tools binary exceeds expected size bound")
            tool = tmp / "wasm-tools"
            tool.write_bytes(binary)
            tool.chmod(0o700)
            report["tool"]["binary_sha256"] = sha256_file(tool)
            version = run([str(tool), "--version"])
            report["tool"]["version_stdout"] = version.stdout.strip()
            report["tool"]["version_stderr"] = version.stderr[-2000:]
            if version.returncode != 0 or TOOLS_VERSION not in version.stdout:
                raise RuntimeError("pinned wasm-tools executable version check failed")
            validate = run([str(tool), "validate", str(WASM)])
            report["component_validation"] = "PASS" if validate.returncode == 0 else "FAIL"
            report["validation_stdout"] = validate.stdout[-4000:]
            report["validation_stderr"] = validate.stderr[-8000:]
            if validate.returncode != 0:
                raise RuntimeError("wasm-tools validate rejected MetaOS.wasm")

            wit = run([str(tool), "component", "wit", str(WASM)])
            report["wit_status"] = "PASS" if wit.returncode == 0 else "FAIL"
            report["wit_stdout"] = wit.stdout[-16000:]
            report["wit_stderr"] = wit.stderr[-8000:]
            report["wit_sha256"] = sha256_bytes(wit.stdout.encode("utf-8"))
            if wit.returncode != 0:
                raise RuntimeError("wasm-tools could not extract a Component Model WIT contract")

            printed = run([str(tool), "print", str(WASM)])
            report["component_wat_status"] = "PASS" if printed.returncode == 0 else "FAIL"
            report["component_wat_sha256"] = sha256_bytes(printed.stdout.encode("utf-8"))
            report["component_wat"] = printed.stdout[-24000:]
            report["component_wat_stderr"] = printed.stderr[-4000:]
            if printed.returncode != 0:
                raise RuntimeError("wasm-tools could not disassemble the component for semantic review")

            # Create a new, explicitly versioned candidate. Preserve the original WASM bytes untouched.
            patch_specs = [
                {
                    "export": "provider-failure-is-mission-failure",
                    "old": '(func (;8;) (type 0) (result i32)\n      i32.const 0\n    )',
                    "new": '(func (;8;) (type 0) (result i32)\n      i32.const 1\n    )',
                    "reason": "The named invariant must be true: provider failure is a mission failure."
                },
                {
                    "export": "resource-red-is-mission-failure",
                    "old": '(func (;9;) (type 0) (result i32)\n      i32.const 0\n    )',
                    "new": '(func (;9;) (type 0) (result i32)\n      i32.const 1\n    )',
                    "reason": "The named invariant must be true: a resource RED condition is a mission failure."
                },
            ]
            candidate_wat = printed.stdout
            for patch in patch_specs:
                hits = candidate_wat.count(patch["old"])
                if hits != 1:
                    raise RuntimeError(f"refusing ambiguous MetaOS patch for {patch['export']}: expected 1 exact match, found {hits}")
                candidate_wat = candidate_wat.replace(patch["old"], patch["new"], 1)
            if candidate_wat == printed.stdout:
                raise RuntimeError("versioned MetaOS candidate contains no effective approved patch")
            CANDIDATE_WASM.parent.mkdir(parents=True, exist_ok=True)
            CANDIDATE_WAT.write_text(candidate_wat, encoding="utf-8")
            parsed = run([str(tool), "parse", str(CANDIDATE_WAT), "-o", str(CANDIDATE_WASM)])
            report["candidate_parse_status"] = "PASS" if parsed.returncode == 0 else "FAIL"
            report["candidate_parse_stdout"] = parsed.stdout[-4000:]
            report["candidate_parse_stderr"] = parsed.stderr[-8000:]
            if parsed.returncode != 0 or not CANDIDATE_WASM.is_file():
                raise RuntimeError("versioned MetaOS candidate WAT could not be parsed to a component binary")
            candidate_validation = run([str(tool), "validate", str(CANDIDATE_WASM)])
            candidate_wit = run([str(tool), "component", "wit", str(CANDIDATE_WASM)])
            report["candidate_component_validation"] = "PASS" if candidate_validation.returncode == 0 else "FAIL"
            report["candidate_component_validation_stderr"] = candidate_validation.stderr[-8000:]
            report["candidate_wit_status"] = "PASS" if candidate_wit.returncode == 0 else "FAIL"
            report["candidate_wit_sha256"] = sha256_bytes(candidate_wit.stdout.encode("utf-8"))
            report["candidate_wit_unchanged"] = candidate_wit.stdout == wit.stdout
            report["versioned_candidate"] = {
                "artifact_id": "MetaOS_V8_CANDIDATE_1_0_1",
                "source_artifact_id": "MetaOS.wasm",
                "source_sha256": report["wasm_sha256"],
                "output_path": str(CANDIDATE_WASM.relative_to(ROOT)),
                "output_sha256": sha256_file(CANDIDATE_WASM),
                "output_size_bytes": CANDIDATE_WASM.stat().st_size,
                "wat_source_path": str(CANDIDATE_WAT.relative_to(ROOT)),
                "wat_source_sha256": sha256_bytes(candidate_wat.encode("utf-8")),
                "patches": patch_specs,
                "original_preserved": sha256_file(WASM) == report["wasm_sha256"],
                "abi_wit_unchanged": candidate_wit.returncode == 0 and candidate_wit.stdout == wit.stdout,
                "host_imports_count": len(imports),
                "host_imports": imports
            }
            report["versioned_candidate_component_validation"] = report["candidate_component_validation"]
            report["versioned_candidate_wit_sha256"] = report["candidate_wit_sha256"]
            if candidate_validation.returncode != 0 or candidate_wit.returncode != 0 or candidate_wit.stdout != wit.stdout:
                raise RuntimeError("versioned MetaOS candidate failed validation or changed the WIT ABI")
            report["approved_semantic_corrections"] = [
                "provider-failure-is-mission-failure returns true",
                "resource-red-is-mission-failure returns true"
            ]

            lines = wit.stdout.splitlines()
            imports = [line.strip() for line in lines if re.match(r"^\s*import\s+", line)]
            exports = [line.strip() for line in lines if re.match(r"^\s*export\s+", line)]
            report["wit_import_declarations"] = imports
            report["wit_export_declarations"] = exports
            report["declared_import_count"] = len(imports)
            report["declared_export_count"] = len(exports)
            report["abi_status"] = "WIT_CONTRACT_EXTRACTED" if (imports or exports) else "NO_DECLARED_IMPORTS_OR_EXPORTS"
            report["integration_ready"] = bool(exports)
            if not exports:
                report["limitations"].append("wasm-tools found no externally callable exports; MetaOS invocation remains blocked.")
    except Exception as exc:
        report["result"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
    else:
        report["result"] = "PASS_VERSIONED_CANDIDATE_BUILT" if report["component_validation"] == "PASS" and report["wit_status"] == "PASS" and report.get("versioned_candidate_component_validation") == "PASS" and report.get("candidate_wit_unchanged") is True else "FAIL"
    output = ROOT / "evidence/custoszv8-metaos-component.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS_VERSIONED_CANDIDATE_BUILT" else 1

if __name__ == "__main__":
    raise SystemExit(main())
