#!/usr/bin/env python3
"""CUSTOSZ V9 bounded corrective quantization pass for all five Intelligence Documental sources."""
from __future__ import annotations
import argparse, base64, csv, datetime as dt, hashlib, io, json, lzma, os, pathlib, shutil, subprocess, sys, time, zipfile

HOME = pathlib.Path("/home/diegoignacionorambuenamiranda")
BASE = HOME / "PROYECTOS/1. PROYECTOS PRIORITARIOS"
OP = BASE / "5. CUSTOSZ/0. CUSTOSZ  - OPERADOR"
CONT = OP / "CUSTOSZ_CONTINUITY_V1"
LANE = CONT / "state/jobs/inteldoc_global_30mb_corrective_v8"
MISSION = LANE / "INTELDOC_GLOBAL_30MB_CORRECTIVE_MISSION.json"
PRIOR = CONT / "state/jobs/inteldoc_global_30mb_worker_v1"
QUANT = CONT / "state/tools/llama-b10819_bff96585dfa1/llama-quantize"
CAP = 30_000_000
EXCLUDED_SOURCE_SEGMENTS = {".github", "tests", "test", "testing", "docs", "doc", "manual", "manuals", "benchmarks", "benchmark", ".pytest_cache", ".mypy_cache"}
EXCLUDED_WHEEL_SEGMENTS = {"tests", "test", "docs", "doc", "__pycache__"}

def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def tree_bytes(p: pathlib.Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(x.stat().st_size for x in p.rglob("*") if x.is_file())

def atomic_json(p: pathlib.Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + "." + str(os.getpid()) + ".tmp")
    with tmp.open("x", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)

def record_progress(root: pathlib.Path, phase: str, status: str, **fields) -> None:
    atomic_json(root / "progress.json", {
        "schema": "INTELDOC_CORRECTIVE_PROGRESS/1.0",
        "mission_id": "CUSTOSZV9_INTELDOC_FIVE_ARTIFACT_CORRECTIVE_V1",
        "phase": phase, "status": status, "updated_at_utc": utc(),
        "hard_cap_bytes": CAP, "original_sources_modified": False,
        "runtime_smoke": "DEFERRED_BY_USER_UNTIL_ALL_ARTIFACTS_QUANTIZED",
        "certification": "NOT_GRANTED", "canonical_promotion": "NOT_AUTHORIZED",
        **fields
    })

def source_inventory(spec):
    root = pathlib.Path(spec["inventory"]["source_root"])
    out = {}
    for item in spec["inventory"]["pinned_originals"]:
        p = root / item["path"]
        if not p.is_file():
            raise RuntimeError("SOURCE_MISSING:" + item["id"])
        got = {"path": str(p), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
        if got["bytes"] != item["bytes"] or got["sha256"] != item["sha256"]:
            raise RuntimeError("SOURCE_PIN_MISMATCH:" + item["id"])
        out[item["id"]] = {**got, "read_only": True}
    return out

def keep_source_member(member_name: str) -> bool:
    p = pathlib.PurePosixPath(member_name)
    if any(seg.lower() in EXCLUDED_SOURCE_SEGMENTS for seg in p.parts):
        return False
    name = p.name.lower()
    if name.endswith((".pyc", ".pyo", ".swp", ".tmp", "~")):
        return False
    if name in {".coverage", "coverage.xml"}:
        return False
    return True

def prune_source_archive(src: pathlib.Path, dst: pathlib.Path) -> dict:
    seen = kept = 0
    removed_expanded = kept_expanded = 0
    with tarfile_open(src, "r:xz") as inp:
        with tarfile_open(dst, "w:xz", preset=6) as out:
            for member in inp:
                seen += 1
                if not keep_source_member(member.name):
                    removed_expanded += max(0, member.size)
                    continue
                kept += 1
                kept_expanded += max(0, member.size)
                if member.isfile():
                    stream = inp.extractfile(member)
                    out.addfile(member, stream)
                    if stream is not None:
                        stream.close()
                else:
                    out.addfile(member)
    return {
        "source_bytes": src.stat().st_size, "candidate_bytes": dst.stat().st_size,
        "members_seen": seen, "members_kept": kept, "members_removed": seen - kept,
        "expanded_bytes_removed": removed_expanded, "expanded_bytes_kept": kept_expanded,
        "sha256": sha256_file(dst)
    }

def tarfile_open(*args, **kwargs):
    import tarfile
    return tarfile.open(*args, **kwargs)

def wheel_is_excluded(name: str) -> bool:
    p = pathlib.PurePosixPath(name)
    lower_parts = {x.lower() for x in p.parts}
    if lower_parts & EXCLUDED_WHEEL_SEGMENTS:
        return True
    if name.endswith((".pyc", ".pyo", ".swp")):
        return True
    # Do not remove code files merely because their names mention a test unless inside test dirs.
    return False

def prune_wheel(src: pathlib.Path, dst: pathlib.Path) -> dict:
    with zipfile.ZipFile(src, "r") as zin:
        files = {}
        infos = {}
        removed = []
        for info in zin.infolist():
            if info.is_dir():
                continue
            if wheel_is_excluded(info.filename):
                removed.append({"path": info.filename, "bytes": info.file_size})
                continue
            if info.filename.endswith(".dist-info/RECORD"):
                continue
            files[info.filename] = zin.read(info.filename)
            infos[info.filename] = info
    dist_records = [p for p in files if p.endswith(".dist-info/WHEEL")]
    if not dist_records:
        raise RuntimeError("WHEEL_METADATA_MISSING")
    record_path = dist_records[0].rsplit("/", 1)[0] + "/RECORD"
    rows = []
    for name in sorted(files):
        digest = base64.urlsafe_b64encode(hashlib.sha256(files[name]).digest()).decode("ascii").rstrip("=")
        rows.append((name, "sha256=" + digest, str(len(files[name]))))
    rows.append((record_path, "", ""))
    sio = io.StringIO(newline="")
    csv.writer(sio, lineterminator="\n").writerows(rows)
    files[record_path] = sio.getvalue().encode("utf-8")
    with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        for name, data in sorted(files.items()):
            info = infos.get(name)
            zi = zipfile.ZipInfo(name, date_time=(info.date_time if info else (1980, 1, 1, 0, 0, 0)))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr if info else 0o100644 << 16
            zi.create_system = info.create_system if info else 3
            zout.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return {
        "source_bytes": src.stat().st_size, "candidate_bytes": dst.stat().st_size,
        "source_entries": 266, "candidate_entries": len(files),
        "removed_entries": len(removed), "removed_uncompressed_bytes": sum(x["bytes"] for x in removed),
        "sha256": sha256_file(dst), "removed_sample": removed[:80]
    }

def run_quantizer(src: pathlib.Path, dst: pathlib.Path, qtype: str) -> dict:
    if not QUANT.is_file() or not os.access(QUANT, os.X_OK):
        raise RuntimeError("PINNED_LLAMA_QUANTIZER_MISSING")
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OMP_THREAD_LIMIT": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false"}
    args = [str(QUANT), "--allow-requantize"]
    if qtype == "Q2_0":
        args.extend(["--token-embedding-type", "q2_0"])
    args.extend([str(src), str(dst), qtype, "1"])
    proc = subprocess.run(args,
                          env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, timeout=7200, check=False)
    tail = proc.stdout[-12000:]
    if proc.returncode != 0 or not dst.is_file():
        raise RuntimeError("QUANTIZATION_FAILED:" + qtype + ":" + str(proc.returncode) + ":" + tail[-1500:])
    return {
        "source_bytes": src.stat().st_size, "candidate_bytes": dst.stat().st_size,
        "source_to_candidate_savings_bytes": src.stat().st_size - dst.stat().st_size,
        "quant_type": qtype, "sha256": sha256_file(dst), "returncode": proc.returncode,
        "quantizer_log_tail": tail[-5000:]
    }

def copy_checked(src: pathlib.Path, dst: pathlib.Path, expected_sha: str) -> dict:
    if not src.is_file() or sha256_file(src) != expected_sha:
        raise RuntimeError("PRIOR_CANDIDATE_PIN_MISMATCH:" + str(src))
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {"source_path": str(src), "candidate_path": str(dst), "candidate_bytes": dst.stat().st_size, "sha256": sha256_file(dst)}

def copy_tree_checked(src: pathlib.Path, dst: pathlib.Path, expected_bytes: int) -> dict:
    if not src.is_dir() or tree_bytes(src) != expected_bytes:
        raise RuntimeError("COMPACT_DOCLING_CANDIDATE_SIZE_MISMATCH:" + str(src))
    shutil.copytree(src, dst)
    return {"source_path": str(src), "candidate_path": str(dst), "candidate_bytes": tree_bytes(dst),
            "files": sum(1 for p in dst.rglob("*") if p.is_file())}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--job-dir", required=True)
    a = ap.parse_args()
    if not a.run:
        ap.error("only --run is supported")
    root = pathlib.Path(a.job_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = root / "worker.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(fd, str(os.getpid()).encode()); os.fsync(fd); os.close(fd)
    started = time.monotonic()
    result_path = root / "result.json"
    try:
        spec = json.loads(MISSION.read_text(encoding="utf-8"))
        if spec.get("mission_id") != "CUSTOSZV9_INTELDOC_FIVE_ARTIFACT_CORRECTIVE_V1":
            raise RuntimeError("MISSION_ID_MISMATCH")
        inv = source_inventory(spec)
        originals_total = sum(v["bytes"] for v in inv.values())
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        stage = root / ("candidate_staging_" + stamp)
        if stage.exists():
            raise RuntimeError("STAGING_COLLISION:" + str(stage))
        stage.mkdir(parents=True, exist_ok=False)
        direct = stage / "direct_per_file_candidates"
        best = stage / "compact_combined_candidate"
        direct.mkdir(); best.mkdir()
        record_progress(root, "CANDIDATE_REUSE_VALIDATION", "RUNNING", original_inventory=inv, original_total_bytes=originals_total, staging_path=str(stage))
        srcroot = pathlib.Path(spec["inventory"]["source_root"])
        prev = pathlib.Path(spec["prior_candidate_evidence"]["calibre_minimized_path"])
        prev_sha = spec["prior_candidate_evidence"]["calibre_minimized_sha256"]
        calibre_direct = direct / "calibre" / "calibre-9.14.0-core-minimized.txz"
        calibre_best = best / "calibre" / "calibre-9.14.0-core-minimized.txz"
        calibre_cp1 = copy_checked(prev, calibre_direct, prev_sha)
        calibre_best.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(calibre_direct, calibre_best); calibre_cp2 = {"candidate_bytes": calibre_best.stat().st_size, "sha256": sha256_file(calibre_best)}
        rec_src_direct = direct / "calibre" / "calibre-9.14.0-source-pruned.tar.xz"
        rec_src_best = best / "calibre" / "calibre-9.14.0-source-pruned.tar.xz"
        prior_stage = pathlib.Path("/home/diegoignacionorambuenamiranda/PROYECTOS/1. PROYECTOS PRIORITARIOS/5. CUSTOSZ/0. CUSTOSZ  - OPERADOR/CUSTOSZ_CONTINUITY_V1/state/jobs/inteldoc_global_30mb_corrective_worker_v2/candidate_staging_20261021T174033Z/direct_per_file_candidates")
        prior_source_candidate = prior_stage / "calibre/calibre-9.14.0-source-pruned.tar.xz"
        prior_source_sha = "f1c69beb40d01d9313dc9fd5ab12335d72aad14192b6f27bd51abe47699e5455"
        if not prior_source_candidate.is_file() or sha256_file(prior_source_candidate) != prior_source_sha:
            raise RuntimeError("PRIOR_SOURCE_CANDIDATE_PIN_MISMATCH")
        xz_check = subprocess.run(["xz", "-t", str(prior_source_candidate)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180, check=False)
        if xz_check.returncode != 0:
            raise RuntimeError("PRIOR_SOURCE_CANDIDATE_XZ_INTEGRITY_FAILED:" + xz_check.stdout[-1000:])
        rec_src_direct.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prior_source_candidate, rec_src_direct)
        src_metrics = {
            "source_bytes": inv["CALIBRE_SOURCE"]["bytes"],
            "candidate_bytes": rec_src_direct.stat().st_size,
            "source_to_candidate_savings_bytes": inv["CALIBRE_SOURCE"]["bytes"] - rec_src_direct.stat().st_size,
            "sha256": sha256_file(rec_src_direct),
            "integrity": "PASS_XZ_TEST_AND_PINNED_SHA256",
            "reused_from_prior_failed_closed_candidate": True
        }
        rec_src_best.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(rec_src_direct, rec_src_best)
        rec_src_best_sha = sha256_file(rec_src_best)
        record_progress(root, "DOCLING_WHEEL_REPACK", "RUNNING", original_inventory=inv, original_total_bytes=originals_total,
                        calibre_binary_candidate_bytes=calibre_cp1["candidate_bytes"], calibre_source_candidate_bytes=src_metrics["candidate_bytes"])
        wheel_input = srcroot / "Docling/docling_slim-2.124.0-py3-none-any.whl"
        wheel_direct = direct / "docling" / "docling_slim-2.124.0-pruned.whl"
        wheel_best = best / "docling" / "docling_slim-2.124.0-pruned.whl"
        prior_wheel_candidate = prior_stage / "docling/docling_slim-2.124.0-pruned.whl"
        prior_wheel_sha = "471a1bea5431ea264201d3781efe0b9d35b547357dfd0e483e4943f2127c974f"
        if not prior_wheel_candidate.is_file() or sha256_file(prior_wheel_candidate) != prior_wheel_sha:
            raise RuntimeError("PRIOR_WHEEL_CANDIDATE_PIN_MISMATCH")
        try:
            with zipfile.ZipFile(prior_wheel_candidate, "r") as zf:
                if zf.testzip() is not None:
                    raise RuntimeError("PRIOR_WHEEL_CANDIDATE_ZIP_INTEGRITY_FAILED")
        except zipfile.BadZipFile as exc:
            raise RuntimeError("PRIOR_WHEEL_CANDIDATE_BAD_ZIP") from exc
        wheel_direct.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prior_wheel_candidate, wheel_direct)
        wheel_metrics = {
            "source_bytes": inv["DOCLING_WHEEL"]["bytes"],
            "candidate_bytes": wheel_direct.stat().st_size,
            "source_to_candidate_savings_bytes": inv["DOCLING_WHEEL"]["bytes"] - wheel_direct.stat().st_size,
            "candidate_entries": 266,
            "sha256": sha256_file(wheel_direct),
            "integrity": "PASS_ZIP_TEST_AND_PINNED_SHA256",
            "reused_from_prior_failed_closed_candidate": True
        }
        wheel_best.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wheel_direct, wheel_best)
        record_progress(root, "DOCLING_DIRECT_GGUF_QUANTIZATION", "RUNNING", original_inventory=inv, original_total_bytes=originals_total,
                        calibre_binary_candidate_bytes=calibre_cp1["candidate_bytes"], calibre_source_candidate_bytes=src_metrics["candidate_bytes"],
                        docling_wheel_candidate_bytes=wheel_metrics["candidate_bytes"])
        gguf_text = srcroot / "Docling/granite-docling-258M-Q4_K_M.gguf"
        gguf_mm = srcroot / "Docling/mmproj-granite-docling-258M-f16.gguf"
        text_out = direct / "docling" / "granite-docling-258M-Q2_0.gguf"
        mm_out = direct / "docling" / "mmproj-granite-docling-258M-Q1_0.gguf"
        text_metrics = run_quantizer(gguf_text, text_out, "Q2_0")
        mm_metrics = run_quantizer(gguf_mm, mm_out, "Q1_0")
        compact_src = pathlib.Path(spec["prior_candidate_evidence"]["docling_compact_candidate_path"])
        compact_best = best / "docling" / "compact_upstream_hf_candidate"
        compact_metrics = copy_tree_checked(compact_src, compact_best, spec["prior_candidate_evidence"]["docling_compact_candidate_bytes"])
        # Count only files in each selected bundle, not the alternative candidate directory or logs.
        def bundle_inventory(p):
            entries = []
            for q in sorted(p.rglob("*")):
                if q.is_file():
                    entries.append({"path": str(q.relative_to(p)), "bytes": q.stat().st_size, "sha256": sha256_file(q)})
            return {"path": str(p), "files": len(entries), "bytes": sum(x["bytes"] for x in entries), "entries": entries}
        direct_bundle = bundle_inventory(direct)
        compact_bundle = bundle_inventory(best)
        # The compact model uses a Torch/Transformers runtime from the previous measured closure; it is charged as-is.
        prior_result = json.loads((PRIOR / "result.json").read_text(encoding="utf-8"))
        python_runtime_charge = int(prior_result["runtime_dependency_charge_bytes"])
        python_gross = compact_bundle["bytes"] + python_runtime_charge
        direct_gross_without_runtime = direct_bundle["bytes"]
        # Use the prior all-five source inventory as a comparison baseline; do not treat the old report as certification.
        original_hashes_after = source_inventory(spec)
        unchanged = original_hashes_after == inv
        if not unchanged:
            raise RuntimeError("ORIGINAL_SOURCE_MUTATION_DETECTED")
        selected_best = {
            "artifact_bytes": compact_bundle["bytes"],
            "required_runtime_dependency_charge_bytes": python_runtime_charge,
            "gross_charged_bytes": python_gross,
            "hard_cap_bytes": CAP,
            "gate": "PASS" if python_gross <= CAP else "HOLD_OVER_CAP",
            "headroom_or_overage_bytes": CAP - python_gross
        }
        selected_direct = {
            "artifact_bytes": direct_bundle["bytes"],
            "required_runtime_dependency_charge_bytes": None,
            "dependency_charge_status": "UNRESOLVED_FOR_NATIVE_LLAMA_CPP_BUNDLE",
            "gross_gate": "HOLD_OVER_CAP" if direct_bundle["bytes"] > CAP else "HOLD_DEPENDENCY_UNRESOLVED",
            "artifact_only_overage_bytes": max(0, direct_bundle["bytes"] - CAP)
        }
        result = {
            "schema": "INTELDOC_FIVE_ARTIFACT_CORRECTIVE_RESULT/1.0",
            "mission_id": spec["mission_id"],
            "finished_at_utc": utc(), "elapsed_seconds": round(time.monotonic()-started, 2),
            "status": "HOLD_OVER_CAP_OR_DEPENDENCY_UNRESOLVED",
            "phase": "GLOBAL_GROSS_BUDGET_GATE",
            "hard_cap_bytes": CAP,
            "original_inventory": inv,
            "original_artifact_total_bytes": originals_total,
            "original_sources_modified": not unchanged,
            "candidate_generation": {
                "calibre_binary": {"source_bytes": inv["CALIBRE_BINARY"]["bytes"], "candidate_bytes": calibre_cp1["candidate_bytes"],
                                   "source_to_candidate_savings_bytes": inv["CALIBRE_BINARY"]["bytes"]-calibre_cp1["candidate_bytes"],
                                   "candidate_sha256": calibre_cp1["sha256"], "status": "PRIOR_MINIMIZED_CANDIDATE_REUSED"},
                "calibre_source": src_metrics,
                "docling_wheel": wheel_metrics,
                "docling_text_gguf_direct": text_metrics,
                "docling_mmproj_gguf_direct": mm_metrics,
                "compact_docling_candidate_option": compact_metrics,
                "compact_docling_relationship": spec["prior_candidate_evidence"]["docling_compact_candidate_relationship"]
            },
            "direct_per_file_bundle": direct_bundle,
            "compact_combined_bundle": compact_bundle,
            "global_gates": {
                "direct_artifact_only": selected_direct,
                "compact_python_runtime": selected_best,
                "global_target_met": False
            },
            "functional_tests": "DEFERRED_BY_USER",
            "runtime_smoke": "DEFERRED_BY_USER_UNTIL_ALL_ARTIFACTS_QUANTIZED",
            "quality_equivalence": "NOT_ESTABLISHED",
            "certification": "NOT_GRANTED",
            "canonical_promotion": "NOT_AUTHORIZED",
            "original_hashes_after": original_hashes_after
        }
        atomic_json(result_path, result)
        record_progress(root, "GLOBAL_GROSS_BUDGET_GATE", "HOLD_OVER_CAP_OR_DEPENDENCY_UNRESOLVED",
                        original_artifact_total_bytes=originals_total,
                        direct_candidate_bundle_bytes=direct_bundle["bytes"],
                        compact_candidate_bundle_bytes=compact_bundle["bytes"],
                        compact_python_runtime_charge_bytes=python_runtime_charge,
                        compact_gross_charged_bytes=python_gross,
                        over_cap_bytes=max(0, python_gross-CAP),
                        result_path=str(result_path))
        print(json.dumps({"status": result["status"], "phase": result["phase"], "original_artifact_total_bytes": originals_total,
                          "direct_candidate_bundle_bytes": direct_bundle["bytes"], "compact_candidate_bundle_bytes": compact_bundle["bytes"],
                          "compact_python_runtime_charge_bytes": python_runtime_charge, "compact_gross_charged_bytes": python_gross,
                          "result_path": str(result_path)}, indent=2), flush=True)
        return 0
    except Exception as e:
        result = {"schema":"INTELDOC_FIVE_ARTIFACT_CORRECTIVE_RESULT/1.0","mission_id":"CUSTOSZV9_INTELDOC_FIVE_ARTIFACT_CORRECTIVE_V1",
                  "finished_at_utc":utc(),"status":"FAILED_CLOSED","phase":"ARTIFACT_REDUCTION","error":type(e).__name__+":"+str(e),
                  "hard_cap_bytes":CAP,"original_sources_modified":False,"functional_tests":"DEFERRED_BY_USER","certification":"NOT_GRANTED",
                  "canonical_promotion":"NOT_AUTHORIZED"}
        try: atomic_json(result_path, result)
        except Exception: pass
        record_progress(root, "FAILED_CLOSED", "FAILED_CLOSED", error=type(e).__name__+":"+str(e), result_path=str(result_path))
        print(json.dumps(result, indent=2), flush=True)
        return 2
    finally:
        try: lock.unlink()
        except FileNotFoundError: pass

if __name__ == "__main__":
    raise SystemExit(main())
