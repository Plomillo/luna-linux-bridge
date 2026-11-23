#!/usr/bin/env python3
"""Build distinct louksna-cajita candidates and reload the authentic Cerebro runtime.

Does not retrain, fine-tune, edit cerebro_180mb_runtime.py, or replace
LOUKSNA.deb / LOUKSNA.sh. A host unpack is not a Debian VM install.
Quality equivalence stays NOT_ESTABLISHED. Product certification stays NOT_CERTIFIED.
Does not re-execute the 803, the 36, or SUB-001..SUB-053.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ORIGINAL_DEB = "fa372953f47c61019202995754cec7d688adf973c4491218e3b4db2465163657"
ORIGINAL_SH = "d74a0b5eefeba4a5777c87b97008169a540aee25861fb883f0943379cf7db8f7"
ARCHIVE_SHA256 = "b40150508f702ee456da4041927611c5f0f78639d45a8582eff2e88258eb6abf"
W01_SHA256 = "935d226a65faca9b59a7742c7c31208ef0ba671509d475c1a4e2f3489cecc19e"
PACKAGE_NAME = "louksna-cajita"
VERSION = "3.0.0+cajita1"
CANDIDATE_ID = "CAJITA_LUNA_RUNTIME_V9_20261023"
DEB_NAME = "LOUKSNA-cajita-candidate.deb"
SH_NAME = "LOUKSNA-cajita-candidate.sh"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def disk_free(path: Path) -> int:
    usage = shutil.disk_usage(path)
    return int(usage.free)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, **kwargs)


def link_or_copy(src: str, dst: str) -> None:
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def verify_weights(package: Path, artifacts: list[dict]) -> list[dict]:
    rows = []
    for row in artifacts:
        path = package / row["path"]
        got = sha256(path) if path.is_file() else ""
        size = path.stat().st_size if path.is_file() else 0
        ok = path.is_file() and got == row["sha256"] and size == row["bytes"]
        rows.append({
            "id": row["id"],
            "path": row["path"],
            "expected": row["sha256"],
            "got": got,
            "bytes": size,
            "ok": ok,
        })
    return rows


def stage_tree(package: Path, dest: Path, identity: dict) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copytree(package, dest, copy_function=link_or_copy, dirs_exist_ok=True)
    identity_path = dest / "CANDIDATE_IDENTITY.json"
    if identity_path.exists():
        raise RuntimeError("IDENTITY_PATH_COLLIDES_WITH_AUTHENTIC_TREE")
    identity_path.write_text(json.dumps(identity, indent=2) + "\n")


def build_deb(stage_root: Path, deb_path: Path) -> None:
    deb_path.parent.mkdir(parents=True, exist_ok=True)
    if deb_path.name in {"LOUKSNA.deb", "LOUKSNA.sh"}:
        raise RuntimeError("REFUSING_TO_OVERWRITE_ORIGINAL_NAME")
    proc = run(
        ["dpkg-deb", "-Znone", "--root-owner-group", "--build", str(stage_root), str(deb_path)],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("DPKG_DEB_BUILD_FAILED:" + (proc.stderr or proc.stdout or "")[-2000:])


def sh_header() -> str:
    return """#!/bin/bash
# louksna-cajita candidate installer. Distinct from LOUKSNA.sh.
# Does not replace LOUKSNA.sh. Does not retrain Megaagent Luna.
set -euo pipefail
PREFIX=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)
      PREFIX="${2:-}"
      shift 2
      ;;
    *)
      echo "UNKNOWN_ARG:$1" >&2
      exit 2
      ;;
  esac
done
if [[ -z "$PREFIX" ]]; then
  echo "PREFIX_REQUIRED" >&2
  exit 2
fi
case "$PREFIX" in
  /usr/lib/louksna|/usr/lib/louksna/*)
    echo "REFUSING_ORIGINAL_PREFIX" >&2
    exit 3
    ;;
esac
mkdir -p "$PREFIX"
line=$(awk '/^__LOUKSNA_CAJITA_PAYLOAD__$/ {print NR+1; exit}' "$0")
if [[ -z "${line}" ]]; then
  echo "PAYLOAD_MARKER_MISSING" >&2
  exit 2
fi
tail -n +"$line" "$0" | tar --no-same-owner -x -C "$PREFIX"
echo "EXTRACT_OK $PREFIX"
exit 0
__LOUKSNA_CAJITA_PAYLOAD__
"""


def build_sh(tree: Path, sh_path: Path) -> None:
    sh_path.parent.mkdir(parents=True, exist_ok=True)
    if sh_path.name in {"LOUKSNA.deb", "LOUKSNA.sh"}:
        raise RuntimeError("REFUSING_TO_OVERWRITE_ORIGINAL_NAME")
    with tempfile.TemporaryDirectory(prefix="cajita-tar-") as tmp:
        tar_path = Path(tmp) / "payload.tar"
        proc = run(["tar", "-C", str(tree), "-cf", str(tar_path), "."], capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError("TAR_FAILED:" + (proc.stderr or "")[-1000:])
        with sh_path.open("wb") as handle:
            handle.write(sh_header().encode())
            with tar_path.open("rb") as payload:
                shutil.copyfileobj(payload, handle, length=8 * 1024 * 1024)
    sh_path.chmod(0o755)


def unpack_sh(sh_path: Path, prefix: Path) -> None:
    if prefix.exists():
        shutil.rmtree(prefix)
    prefix.mkdir(parents=True)
    proc = run(["bash", str(sh_path), "--prefix", str(prefix)], capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError("SH_EXTRACT_FAILED:" + (proc.stderr or proc.stdout or "")[-2000:])


def reload_runtime(runtime: Path, model: Path, trace: Path) -> dict:
    if os.environ.get("CAJITA_SKIP_RELOAD") == "1":
        return {"attempted": False, "skipped": True, "reason": "CAJITA_SKIP_RELOAD"}
    trace.parent.mkdir(parents=True, exist_ok=True)
    if trace.exists():
        trace.unlink()
    hf_home = Path(tempfile.mkdtemp(prefix="cajita-hf-"))
    env = os.environ.copy()
    env.update({
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "HF_HOME": str(hf_home),
        "TOKENIZERS_PARALLELISM": "false",
    })
    started = time.monotonic()
    try:
        proc = run(
            ["strace", "-f", "-e", "trace=openat", "-o", str(trace), sys.executable, str(runtime.resolve()), "--generate-test"],
            cwd=runtime.parent,
            capture_output=True,
            timeout=int(os.environ.get("CAJITA_SMOKE_TIMEOUT", "2400")),
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return {"attempted": True, "returncode": None, "error": "TIMEOUT", "stdout": str(exc.stdout or "")[-1000:], "elapsed_seconds": round(time.monotonic() - started, 3)}
    finally:
        shutil.rmtree(hf_home, ignore_errors=True)
    opened_exact = False
    opened_name = False
    if trace.is_file():
        text = trace.read_text(errors="replace")
        opened_exact = str(model.resolve()) in text
        opened_name = "model.safetensors" in text
    parsed = {}
    stdout = proc.stdout or ""
    start = stdout.find("{")
    if start >= 0:
        try:
            parsed = json.loads(stdout[start:])
        except json.JSONDecodeError:
            parsed = {}
    return {
        "attempted": True,
        "skipped": False,
        "returncode": proc.returncode,
        "stdout": stdout[-4000:],
        "stderr": (proc.stderr or "")[-2000:],
        "opened_exact_model_path": opened_exact,
        "opened_model_safetensors": opened_name,
        "model_path": str(model.resolve()),
        "runtime": str(runtime.resolve()),
        "runtime_sha256": sha256(runtime) if runtime.is_file() else "",
        "model_sha256": sha256(model) if model.is_file() else "",
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "parsed": {key: parsed.get(key) for key in ("status", "generation_status", "argmax_token_id", "quality_equivalence", "compression_rank", "logits_shape", "finite_logits")},
        "offline_env": "HF_HUB_OFFLINE=1",
    }


def generation_ok(reload: dict) -> bool:
    parsed = reload.get("parsed") or {}
    return bool(
        reload.get("attempted")
        and not reload.get("skipped")
        and reload.get("returncode") == 0
        and reload.get("opened_exact_model_path")
        and reload.get("model_sha256") == W01_SHA256
        and parsed.get("status") == "PASS_MODEL_START_AND_FORWARD"
        and parsed.get("generation_status") == "PASS_GENERATE_ONE_TOKEN"
        and parsed.get("quality_equivalence") == "NOT_ESTABLISHED_BY_SMOKE_TEST"
    )


def remove_tree(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.is_file():
        path.unlink(missing_ok=True)


def main() -> int:
    root = Path(os.environ.get("CAJITA_WORK", "/tmp/cajita-probe"))
    evidence = Path(os.environ.get("EVIDENCE", "evidence/luna-cajita"))
    evidence.mkdir(parents=True, exist_ok=True)
    report_path = evidence / "candidate-report.json"
    report: dict = {
        "status": "FAIL",
        "product_certification": "NOT_CERTIFIED",
        "retrained": False,
        "replaces_original": False,
        "debian_vm_install": "NOT_RUN",
        "kde_wayland_session": "NOT_RUN",
        "audio_correlation": "NOT_RUN",
        "whisper_wer": "NOT_RUN",
        "historical": {
            "original_803_reexecuted": 0,
            "historical_36_reexecuted": 0,
            "substitute_53_reexecuted": 0,
        },
        "package_name": PACKAGE_NAME,
        "version": VERSION,
        "candidate_id": CANDIDATE_ID,
        "source_archive_sha256": ARCHIVE_SHA256,
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "quality_equivalence": "NOT_ESTABLISHED",
        "cajita_certification": "NOT_GRANTED",
        "dependency_closure": "INCOMPLETE_TORCH_AND_TRANSFORMERS_NOT_VENDORED",
        "tests": [],
    }
    write_json(report_path, report)
    package = root / "package"
    manifest_path = package / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
    if not manifest_path.is_file():
        report["status"] = "BLOCKED"
        report["reason"] = "EXTRACTED_PACKAGE_ABSENT"
        write_json(report_path, report)
        print(json.dumps({"status": report["status"], "reason": report["reason"]}))
        return 2
    free = disk_free(root if root.exists() else Path("/tmp"))
    report["disk_free_before_bytes"] = free
    if free < 6 * 1024 * 1024 * 1024:
        report["status"] = "BLOCKED"
        report["reason"] = "DISK_BELOW_6G_BEFORE_CANDIDATE_BUILD"
        write_json(report_path, report)
        print(json.dumps({"status": report["status"], "reason": report["reason"], "disk_free_before_bytes": free}))
        return 2
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("candidate_id") != CANDIDATE_ID:
        report["status"] = "FAIL"
        report["reason"] = "CANDIDATE_ID_MISMATCH"
        report["manifest_candidate_id"] = manifest.get("candidate_id")
        write_json(report_path, report)
        return 2
    weights = verify_weights(package, manifest["artifacts"])
    report["weights"] = weights
    report["weights_ok"] = all(row["ok"] for row in weights) and any(row["id"] == "W01" and row["got"] == W01_SHA256 for row in weights)
    if not report["weights_ok"]:
        report["reason"] = "WEIGHT_HASH_MISMATCH"
        write_json(report_path, report)
        print(json.dumps({"status": "FAIL", "reason": report["reason"]}))
        return 2
    runtime_src = package / "1. Cerebro" / "cerebro_180mb_runtime.py"
    if not runtime_src.is_file():
        report["reason"] = "AUTHENTIC_RUNTIME_ABSENT"
        write_json(report_path, report)
        return 2
    runtime_sha = sha256(runtime_src)
    report["authentic_runtime_sha256"] = runtime_sha
    originals = root / "originals"
    original_state = {}
    for name, expected in (("LOUKSNA.deb", ORIGINAL_DEB), ("LOUKSNA.sh", ORIGINAL_SH)):
        path = originals / name
        if path.is_file():
            original_state[name] = {"sha256": sha256(path), "expected": expected, "intact": sha256(path) == expected}
    report["originals_before"] = original_state
    identity = {
        "name": PACKAGE_NAME,
        "version": VERSION,
        "candidate_id": CANDIDATE_ID,
        "replaces_original": False,
        "retrained": False,
        "quality_equivalence": "NOT_ESTABLISHED",
        "certification": "NOT_GRANTED",
        "source_release": "cajita-luna-archive-2026-10-23-b4015050",
        "source_archive_sha256": ARCHIVE_SHA256,
        "authentic_runtime_sha256": runtime_sha,
        "w01_sha256": W01_SHA256,
        "build_commit": os.environ.get("GITHUB_SHA", ""),
        "debian_vm_install": "NOT_RUN",
        "runtime_dependencies_not_vendored": ["torch", "transformers==4.56.2", "safetensors"],
    }
    # The zip member and 7z are no longer needed once the tree hashes match.
    remove_tree(root / "extracted")
    remove_tree(root / "CajitadeLuna.7z")
    stage = root / "deb-stage"
    payload_root = stage / "usr" / "lib" / "louksna-cajita"
    stage_tree(package, payload_root, identity)
    control = stage / "DEBIAN"
    control.mkdir(parents=True, exist_ok=True)
    installed = sum(path.stat().st_size for path in stage.rglob("*") if path.is_file())
    (control / "control").write_text(
        "\n".join([
            f"Package: {PACKAGE_NAME}",
            f"Version: {VERSION}",
            "Section: misc",
            "Priority: optional",
            "Architecture: all",
            f"Installed-Size: {max(1, installed // 1024)}",
            "Maintainer: Plomillo <diegonorambuenamiranda2@gmail.com>",
            "Description: Distinct candidate embedding the authentic Cajita de Luna tree",
            " Does not replace LOUKSNA.deb or LOUKSNA.sh.",
            " Does not retrain Megaagent Luna.",
            " Quality equivalence is NOT_ESTABLISHED and certification is NOT_GRANTED.",
            " torch and transformers are not vendored in this package.",
            "",
        ])
    )
    deb_path = evidence / "candidates" / DEB_NAME
    sh_path = evidence / "candidates" / SH_NAME
    build_deb(stage, deb_path)
    remove_tree(stage)
    deb_root = root / "deb-root"
    if deb_root.exists():
        shutil.rmtree(deb_root)
    proc = run(["dpkg-deb", "-x", str(deb_path), str(deb_root)], capture_output=True)
    if proc.returncode != 0:
        report["reason"] = "DPKG_DEB_EXTRACT_FAILED"
        report["stderr"] = (proc.stderr or "")[-1000:]
        write_json(report_path, report)
        return 2
    deb_sha = sha256(deb_path)
    installed_tree = deb_root / "usr" / "lib" / "louksna-cajita"
    deb_weights = verify_weights(installed_tree, manifest["artifacts"])
    deb_runtime = installed_tree / "1. Cerebro" / "cerebro_180mb_runtime.py"
    deb_model = installed_tree / "1. Cerebro" / "model.safetensors"
    deb_runtime_sha = sha256(deb_runtime) if deb_runtime.is_file() else ""
    report["deb"] = {
        "test_id": "PKG-DEB-CAJITA-001",
        "path": str(deb_path),
        "sha256": deb_sha,
        "bytes": deb_path.stat().st_size,
        "distinct_from_original_deb": deb_sha != ORIGINAL_DEB,
        "distinct_from_original_sh": deb_sha != ORIGINAL_SH,
        "replaces_original": False,
        "weights": deb_weights,
        "weights_ok": all(row["ok"] for row in deb_weights),
        "runtime_sha256": deb_runtime_sha,
        "runtime_unchanged": deb_runtime_sha == runtime_sha,
        "install_method": "dpkg-deb -x host unpack, not dpkg -i, not a Debian VM",
        "debian_vm_install": "NOT_RUN",
    }
    cajita_tree = root / "sh-tree"
    stage_tree(package, cajita_tree, identity)
    build_sh(cajita_tree, sh_path)
    remove_tree(cajita_tree)
    remove_tree(package)
    sh_root = root / "sh-root"
    unpack_sh(sh_path, sh_root)
    sh_sha = sha256(sh_path)
    sh_weights = verify_weights(sh_root, manifest["artifacts"])
    sh_runtime = sh_root / "1. Cerebro" / "cerebro_180mb_runtime.py"
    sh_model = sh_root / "1. Cerebro" / "model.safetensors"
    sh_runtime_sha = sha256(sh_runtime) if sh_runtime.is_file() else ""
    report["sh"] = {
        "test_id": "PKG-SH-CAJITA-001",
        "path": str(sh_path),
        "sha256": sh_sha,
        "bytes": sh_path.stat().st_size,
        "distinct_from_original_deb": sh_sha != ORIGINAL_DEB,
        "distinct_from_original_sh": sh_sha != ORIGINAL_SH,
        "distinct_from_candidate_deb": sh_sha != report["deb"]["sha256"],
        "replaces_original": False,
        "weights": sh_weights,
        "weights_ok": all(row["ok"] for row in sh_weights),
        "runtime_sha256": sh_runtime_sha,
        "runtime_unchanged": sh_runtime_sha == runtime_sha,
        "install_method": "bash --prefix host unpack, not executed on a DEB-prepared system, not a Debian VM",
        "debian_vm_install": "NOT_RUN",
    }
    report["luna_deb"] = reload_runtime(deb_runtime, deb_model, (evidence / "deb-openat.txt").resolve())
    report["luna_deb"]["test_id"] = "LUNA-DEB-CAJITA-001"
    report["luna_sh"] = reload_runtime(sh_runtime, sh_model, (evidence / "sh-openat.txt").resolve())
    report["luna_sh"]["test_id"] = "LUNA-SH-CAJITA-001"
    originals_after = {}
    for name, expected in (("LOUKSNA.deb", ORIGINAL_DEB), ("LOUKSNA.sh", ORIGINAL_SH)):
        path = originals / name
        if path.is_file():
            originals_after[name] = {"sha256": sha256(path), "intact": sha256(path) == expected}
    report["originals_after"] = originals_after
    originals_intact = all(row.get("intact") for row in originals_after.values()) if originals_after else True
    packaged_ok = bool(
        report["deb"]["weights_ok"]
        and report["deb"]["runtime_unchanged"]
        and report["deb"]["distinct_from_original_deb"]
        and report["sh"]["weights_ok"]
        and report["sh"]["runtime_unchanged"]
        and report["sh"]["distinct_from_original_sh"]
        and report["sh"]["distinct_from_candidate_deb"]
        and originals_intact
    )
    deb_infer = generation_ok(report["luna_deb"])
    sh_infer = generation_ok(report["luna_sh"])
    skipped = bool(report["luna_deb"].get("skipped") or report["luna_sh"].get("skipped"))
    report["tests"] = [
        {"test_id": "PKG-DEB-CAJITA-001", "validation_status": "PASS" if report["deb"]["weights_ok"] and report["deb"]["runtime_unchanged"] else "FAIL"},
        {"test_id": "PKG-SH-CAJITA-001", "validation_status": "PASS" if report["sh"]["weights_ok"] and report["sh"]["runtime_unchanged"] else "FAIL"},
        {"test_id": "LUNA-DEB-CAJITA-001", "validation_status": "SKIPPED" if report["luna_deb"].get("skipped") else ("PASS" if deb_infer else "FAIL")},
        {"test_id": "LUNA-SH-CAJITA-001", "validation_status": "SKIPPED" if report["luna_sh"].get("skipped") else ("PASS" if sh_infer else "FAIL")},
        {"test_id": "VM-DEB-CAJITA-001", "validation_status": "NOT_RUN"},
        {"test_id": "VM-SH-CAJITA-001", "validation_status": "NOT_RUN"},
        {"test_id": "AUDIO-DEB-CAJITA-001", "validation_status": "NOT_RUN"},
        {"test_id": "AUDIO-SH-CAJITA-001", "validation_status": "NOT_RUN"},
        {"test_id": "WHISPER-DEB-CAJITA-001", "validation_status": "NOT_RUN"},
        {"test_id": "WHISPER-SH-CAJITA-001", "validation_status": "NOT_RUN"},
    ]
    if packaged_ok and deb_infer and sh_infer and not skipped:
        report["status"] = "PASS_CANDIDATE_HOST_RELOAD_NOT_CERTIFIED"
    elif packaged_ok and skipped:
        report["status"] = "PACKAGED_RELOAD_SKIPPED"
    elif packaged_ok:
        report["status"] = "FAIL_CANDIDATE_RELOAD"
    else:
        report["status"] = "FAIL_CANDIDATE_PACKAGE"
    report["integration_in_original_installers"] = "FAIL_WEIGHTS_ABSENT"
    report["product_certification"] = "NOT_CERTIFIED"
    report["disk_free_after_bytes"] = disk_free(Path("/tmp"))
    write_json(report_path, report)
    (evidence / "candidate-sha256.txt").write_text(
        f"{report['deb']['sha256']}  {DEB_NAME}\n{report['sh']['sha256']}  {SH_NAME}\n"
    )
    for heavy in (deb_root, sh_root, root / "extracted", package, stage, cajita_tree):
        remove_tree(heavy)
    summary = {
        "status": report["status"],
        "deb_sha256": report["deb"]["sha256"],
        "sh_sha256": report["sh"]["sha256"],
        "deb_infer": deb_infer,
        "sh_infer": sh_infer,
        "product_certification": "NOT_CERTIFIED",
        "debian_vm_install": "NOT_RUN",
    }
    print(json.dumps(summary, indent=2))
    return 0 if report["status"] == "PASS_CANDIDATE_HOST_RELOAD_NOT_CERTIFIED" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        evidence = Path(os.environ.get("EVIDENCE", "evidence/luna-cajita"))
        write_json(evidence / "candidate-report.json", {
            "status": "FAIL_EXCEPTION",
            "product_certification": "NOT_CERTIFIED",
            "debian_vm_install": "NOT_RUN",
            "retrained": False,
            "replaces_original": False,
            "error": f"{type(exc).__name__}: {exc}"[:2000],
        })
        print(f"FAIL_EXCEPTION {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
