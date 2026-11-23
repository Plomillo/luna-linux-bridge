#!/usr/bin/env python3
"""Identify the published Cajita de Luna weights and try the authentic Cerebro runtime.

Does not retrain, fine-tune, or replace weights. Does not re-execute the 803, the 36,
or SUB-001..SUB-053. A forward pass is not product certification.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ARCHIVE_SHA256 = "b40150508f702ee456da4041927611c5f0f78639d45a8582eff2e88258eb6abf"
RELEASE = "cajita-luna-archive-2026-10-23-b4015050"
ORIGINAL_DEB = "fa372953f47c61019202995754cec7d688adf973c4491218e3b4db2465163657"
ORIGINAL_SH = "d74a0b5eefeba4a5777c87b97008169a540aee25861fb883f0943379cf7db8f7"
REFERENCE_RUN = "45010622254"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, **kwargs)


def payload_contains_weights(path: Path, needles: list[str]) -> dict:
    data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": sha256(path),
        "bytes": len(data),
        "contains_weight_sha": {needle: needle.encode() in data for needle in needles},
        "contains_model_safetensors_name": b"model.safetensors" in data,
        "contains_cajita_marker": b"CAJITA_LUNA_RUNTIME_V9_20261023" in data,
    }


def main() -> int:
    root = Path(os.environ.get("CAJITA_WORK", "/tmp/cajita-probe"))
    evidence = Path(os.environ.get("EVIDENCE", "evidence/luna-cajita"))
    root.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    archive = root / "CajitadeLuna.7z"
    if not archive.is_file():
        proc = run(["gh", "release", "download", RELEASE, "--repo", "Plomillo/luna-linux-bridge", "--pattern", "CajitadeLuna.7z", "--dir", str(root)])
        if proc.returncode != 0:
            write(evidence / "report.json", {"status": "BLOCKED", "reason": "CAJITA_DOWNLOAD_FAILED", "stderr": (proc.stderr or "")[-1000:]})
            return 2
    archive_hash = sha256(archive)
    if archive_hash != ARCHIVE_SHA256:
        write(evidence / "report.json", {"status": "FAIL", "reason": "ARCHIVE_HASH_MISMATCH", "got": archive_hash})
        return 2
    extracted = root / "extracted"
    if not (extracted / "CajitadeLuna.md").is_file():
        proc = run(["7z", "x", "-y", f"-o{extracted}", str(archive)], capture_output=True)
        if proc.returncode != 0:
            import py7zr
            with py7zr.SevenZipFile(archive, mode="r") as handle:
                handle.extractall(path=extracted)
    blob = extracted / "CajitadeLuna.md"
    package = root / "package"
    if not (package / "CAJITA_RUNTIME_V1" / "weights_manifest.json").is_file():
        if package.exists():
            shutil.rmtree(package)
        package.mkdir()
        with zipfile.ZipFile(blob) as handle:
            handle.extractall(package)
    manifest = json.loads((package / "CAJITA_RUNTIME_V1" / "weights_manifest.json").read_text())
    weights = []
    weight_ok = True
    for row in manifest["artifacts"]:
        path = package / row["path"]
        got = sha256(path) if path.is_file() else ""
        ok = got == row["sha256"] and path.stat().st_size == row["bytes"] if path.is_file() else False
        weight_ok = weight_ok and ok
        weights.append({"id": row["id"], "path": row["path"], "expected": row["sha256"], "got": got, "bytes": path.stat().st_size if path.is_file() else 0, "ok": ok})
    installers = root / "originals"
    installers.mkdir(exist_ok=True)
    deb = installers / "LOUKSNA.deb"
    sh = installers / "LOUKSNA.sh"
    if not deb.is_file() or sha256(deb) != ORIGINAL_DEB:
        proc = run(["gh", "run", "download", REFERENCE_RUN, "--repo", "Plomillo/luna-linux-bridge", "--name", "louksna-installers", "--dir", str(installers)])
        if proc.returncode != 0:
            write(evidence / "report.json", {"status": "BLOCKED", "reason": "ORIGINAL_INSTALLER_DOWNLOAD_FAILED"})
            return 2
    needles = [row["expected"] for row in weights]
    originals = {
        "deb": payload_contains_weights(deb, needles),
        "sh": payload_contains_weights(sh, needles),
    }
    originals_intact = originals["deb"]["sha256"] == ORIGINAL_DEB and originals["sh"]["sha256"] == ORIGINAL_SH
    originals_lack_weights = not any(originals["deb"]["contains_weight_sha"].values()) and not any(originals["sh"]["contains_weight_sha"].values()) and not originals["deb"]["contains_cajita_marker"] and not originals["sh"]["contains_cajita_marker"]
    smoke = {"attempted": False}
    if weight_ok and os.environ.get("CAJITA_SMOKE", "1") == "1":
        runtime = package / "1. Cerebro" / "cerebro_180mb_runtime.py"
        trace = (evidence / "cerebro-openat.txt").resolve()
        trace.parent.mkdir(parents=True, exist_ok=True)
        proc = run(["strace", "-f", "-e", "trace=openat", "-o", str(trace), sys.executable, str(runtime), "--generate-test"], cwd=package, capture_output=True, timeout=int(os.environ.get("CAJITA_SMOKE_TIMEOUT", "2400")))
        opened = False
        if trace.is_file():
            opened = "model.safetensors" in trace.read_text(errors="replace")
        smoke = {
            "attempted": True,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[-4000:],
            "stderr": (proc.stderr or "")[-4000:],
            "opened_model_safetensors": opened,
            "runtime": str(runtime),
            "runtime_sha256": sha256(runtime),
        }
    historical = {
        "original_803_reexecuted": 0,
        "historical_36_reexecuted": 0,
        "substitute_53_reexecuted": 0,
        "note": "This probe does not re-execute historical cases. Aggregate VERIFY counts are not individual records.",
    }
    report = {
        "status": "FAIL",
        "archive_sha256": archive_hash,
        "release": RELEASE,
        "candidate_id": manifest.get("candidate_id"),
        "functional_equivalence": manifest.get("functional_equivalence"),
        "cajita_certification": manifest.get("certification"),
        "weights": weights,
        "weights_ok": weight_ok,
        "originals": originals,
        "originals_intact": originals_intact,
        "originals_lack_cajita_weights": originals_lack_weights,
        "smoke": smoke,
        "historical": historical,
        "product_certification": "NOT_CERTIFIED",
        "retrained": False,
    }
    smoke_pass = False
    if smoke.get("attempted") and smoke.get("returncode") == 0 and smoke.get("opened_model_safetensors"):
        try:
            parsed = json.loads(smoke["stdout"][smoke["stdout"].find("{"):])
        except json.JSONDecodeError:
            parsed = {}
        smoke["parsed"] = {k: parsed.get(k) for k in ("status", "generation_status", "argmax_token_id", "quality_equivalence", "compression_rank", "logits_shape")}
        smoke_pass = parsed.get("status") == "PASS_MODEL_START_AND_FORWARD" and parsed.get("generation_status") == "PASS_GENERATE_ONE_TOKEN" and parsed.get("quality_equivalence") == "NOT_ESTABLISHED_BY_SMOKE_TEST"
    report["cerebro_forward"] = "PASS_LOAD_AND_ONE_TOKEN" if smoke_pass else "FAIL"
    report["integration_in_original_installers"] = "FAIL_WEIGHTS_ABSENT" if originals_lack_weights else "UNEXPECTED_PRESENT"
    report["status"] = "PASS_IDENTIFIED_NOT_INTEGRATED" if weight_ok and originals_intact and originals_lack_weights else "FAIL"
    if smoke.get("attempted") and not smoke_pass:
        report["status"] = "FAIL_SMOKE"
    write(evidence / "report.json", report)
    print(json.dumps({"status": report["status"], "cerebro_forward": report["cerebro_forward"], "weights_ok": weight_ok, "originals_lack": originals_lack_weights}, indent=2))
    return 0 if report["status"] == "PASS_IDENTIFIED_NOT_INTEGRATED" and (not smoke.get("attempted") or smoke_pass) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.TimeoutExpired as exc:
        evidence = Path(os.environ.get("EVIDENCE", "evidence/luna-cajita"))
        write(evidence / "report.json", {"status": "FAIL_SMOKE_TIMEOUT", "product_certification": "NOT_CERTIFIED", "error": str(exc)[:500]})
        raise SystemExit(2)
