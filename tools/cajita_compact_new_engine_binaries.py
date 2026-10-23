#!/usr/bin/env python3
"""Second, lossless binary compaction pass over the ten new Cajita asset containers.

This pass scans the extracted, already-compressed new-engine assets for PE/ELF
binaries, tries UPX on every detected candidate, accepts a transform only after
UPX integrity testing and exact decompression SHA-256 equality, and keeps a new
7z/LZMA2 container only if it is smaller. The six pre-existing model-weight
artifacts are fail-closed protected. Runtime path repair is deferred.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "cajita-luna-runtime"
PLACEMENT_PATH = RUNTIME / "EXTERNALIZED_ASSET_PLACEMENT.json"
WEIGHT_MANIFEST = RUNTIME / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
REPORT_PATH = ROOT / "docs" / "cajita-luna" / "CAJITA_NEW_ENGINE_BINARY_COMPACTION_20261023.json"
HARD_CAP = 470_000_000
PROTECTED = [
    "1. Cerebro/model.safetensors",
    "3. Transcripción/model.safetensors",
    "4. Traductor Inteligente/Traducción general/model.safetensors",
    "5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_weights.bin",
    "6. Sistema Inteligente/Análisis Avanzado/model.safetensors",
    "6. Sistema Inteligente/Anti-Alucinaciones/model.onnx",
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def fingerprint(root: Path) -> dict[str, dict[str, object]]:
    out = {}
    for p in sorted(root.rglob("*"), key=lambda q: q.relative_to(root).as_posix()):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            out[rel] = {"kind":"symlink","target":os.readlink(p),"mode":p.lstat().st_mode & 0o7777}
        elif p.is_file():
            out[rel] = {"kind":"file","sha256":sha256(p),"bytes":p.stat().st_size,"mode":p.stat().st_mode & 0o7777}
    return out

def run(args, timeout=600):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)

def upx_transform(path: Path) -> dict[str, object] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        with path.open("rb") as f:
            magic=f.read(4)
        if magic not in (b"\x7fELF", b"MZ"):
            return None
        old_size=path.stat().st_size
        old_hash=sha256(path)
        old_mode=stat.S_IMODE(path.stat().st_mode)
        old_times=(path.stat().st_atime, path.stat().st_mtime)
        with tempfile.TemporaryDirectory(prefix="cajita-upx-") as tmp:
            packed=Path(tmp)/"packed.bin"
            decoded=Path(tmp)/"decoded.bin"
            p=run(["upx","-9","--lzma","--force","-o",str(packed),str(path)],timeout=180)
            if p.returncode != 0 or not packed.is_file() or packed.stat().st_size >= old_size:
                return None
            t=run(["upx","-t",str(packed)],timeout=60)
            if t.returncode != 0:
                return None
            d=run(["upx","-d","-o",str(decoded),str(packed)],timeout=180)
            if d.returncode != 0 or not decoded.is_file() or sha256(decoded) != old_hash:
                return None
            new_size=packed.stat().st_size
            shutil.copyfile(packed,path)
            path.chmod(old_mode)
            os.utime(path,old_times,follow_symlinks=False)
            if sha256(path) != sha256(packed):
                raise RuntimeError(f"UPX copy hash mismatch: {path}")
            return {
                "relative_path": path.name,
                "format_magic": magic.hex(),
                "before_bytes": old_size,
                "after_bytes": new_size,
                "saved_bytes": old_size-new_size,
                "before_sha256": old_hash,
                "packed_sha256": sha256(path),
                "upx_test": "PASS",
                "decompression_exact_sha256_roundtrip": "PASS",
                "mode_preserved": oct(old_mode),
            }
    except (OSError, subprocess.TimeoutExpired):
        return None

def payload_estimate() -> int:
    manifest=json.loads(WEIGHT_MANIFEST.read_text(encoding="utf-8"))
    lfs={item["path"]:int(item["bytes"]) for item in manifest.get("artifacts",[])}
    total=0
    for p in RUNTIME.rglob("*"):
        if not p.is_file() or p.name=="MACRODOWN_MANIFEST.json":
            continue
        rel=p.relative_to(RUNTIME).as_posix()
        size=p.stat().st_size
        if rel in lfs and size<=1024:
            size=lfs[rel]
        total+=size
    return total

def main():
    if not shutil.which("7z") or not shutil.which("upx"):
        raise RuntimeError("Fail closed: both 7z and upx must be installed")
    placement=json.loads(PLACEMENT_PATH.read_text(encoding="utf-8"))
    if len(placement.get("assets",[])) != 10:
        raise RuntimeError("Fail closed: expected exactly ten registered new assets")
    protected_before={rel:sha256(RUNTIME/rel) for rel in PROTECTED}
    upxver=run(["upx","--version"])
    szver=run(["7z"])
    results=[]
    initial_container_bytes=0
    final_container_bytes=0
    total_saved=0

    for asset in sorted(placement["assets"],key=lambda x:(-int(x.get("size_bytes",0)),x["id"])):
        asset_id=asset["id"]
        rel=asset["placed_path"]
        container=ROOT/rel
        if not container.is_file() or not rel.endswith(".7z"):
            raise RuntimeError(f"Fail closed: expected compacted 7z container at {rel}")
        expected=int(asset["size_bytes"])
        if container.stat().st_size!=expected or sha256(container)!=asset["sha256"]:
            raise RuntimeError(f"Fail closed: container size/hash mismatch for {asset_id}")
        old_container_size=container.stat().st_size
        initial_container_bytes+=old_container_size
        item={"id":asset_id,"path":rel,"container_before_bytes":old_container_size,"container_before_sha256":sha256(container)}
        with tempfile.TemporaryDirectory(prefix="cajita-inner-binary-") as tmp_name:
            tmp=Path(tmp_name)
            extracted=tmp/"members"
            extracted.mkdir()
            ex=run(["7z","x","-y",f"-o{extracted}",str(container)],timeout=900)
            if ex.returncode!=0:
                raise RuntimeError(f"Fail closed: cannot extract {rel}: {ex.stdout[-1000:]} {ex.stderr[-1000:]}")
            before_tree=fingerprint(extracted)
            transformed=[]
            candidate_count=0
            for p in sorted(extracted.rglob("*")):
                if not p.is_file() or p.is_symlink():
                    continue
                try:
                    with p.open("rb") as f:
                        magic=f.read(4)
                except OSError:
                    continue
                if magic in (b"\x7fELF",b"MZ"):
                    candidate_count+=1
                    before_name=p.name
                    change=upx_transform(p)
                    if change:
                        change["relative_path"]=p.relative_to(extracted).as_posix()
                        transformed.append(change)
            new_container=tmp/"candidate.7z"
            add=run(["7z","a","-t7z","-mx=9","-m0=lzma2","-md=64m","-mfb=273","-ms=on","-mmt=on","-snl",str(new_container),"."],timeout=1800)
            if add.returncode not in (0,1) or not new_container.is_file():
                raise RuntimeError(f"7z recompression failed for {asset_id}: {add.stdout[-1500:]} {add.stderr[-1500:]}")
            test=run(["7z","t",str(new_container)],timeout=900)
            if test.returncode!=0:
                raise RuntimeError(f"7z integrity test failed for {asset_id}: {test.stdout[-1500:]}")
            check=tmp/"roundtrip"
            check.mkdir()
            out=run(["7z","x","-y",f"-o{check}",str(new_container)],timeout=900)
            if out.returncode != 0:
                raise RuntimeError(f"Fail closed: cannot extract candidate for {asset_id}: {out.stdout[-1000:]} {out.stderr[-1000:]}")
            expected_tree=fingerprint(extracted)
            actual_tree=fingerprint(check)
            if expected_tree != actual_tree:
                keys=sorted(set(expected_tree)|set(actual_tree))
                mismatches=[
                    {"path":k,"expected":expected_tree.get(k),"actual":actual_tree.get(k)}
                    for k in keys if expected_tree.get(k)!=actual_tree.get(k)
                ][:30]
                item.update({
                    "recognized_pe_elf_candidate_count":candidate_count,
                    "upx_transforms_candidate_not_promoted":transformed,
                    "candidate_7z_test":"PASS",
                    "member_tree_roundtrip":"FAIL_CANDIDATE_REJECTED",
                    "roundtrip_mismatch_count_capped":len(mismatches),
                    "roundtrip_mismatches_first_30":mismatches,
                    "status":"CANDIDATE_REJECTED_ROUNDTRIP_MISMATCH_ORIGINAL_CONTAINER_RETAINED",
                    "container_after_bytes":old_container_size,
                    "container_after_sha256":item["container_before_sha256"],
                    "container_saved_bytes":0,
                })
                asset.setdefault("optimization",{})["binary_compaction_pass"]={
                    "status":"CANDIDATE_REJECTED_ROUNDTRIP_MISMATCH_ORIGINAL_CONTAINER_RETAINED",
                    "candidate_upx_transforms_not_promoted":transformed,
                    "roundtrip":"FAIL_CANDIDATE_REJECTED",
                    "original_container_preserved":True,
                    "mismatch_examples":mismatches,
                }
                results.append(item)
                final_container_bytes+=old_container_size
                print(json.dumps(item,ensure_ascii=False))
                continue
            candidate_size=new_container.stat().st_size
            candidate_hash=sha256(new_container)
            item.update({
                "recognized_pe_elf_candidate_count":candidate_count,
                "upx_transforms":transformed,
                "upx_saved_bytes":sum(int(x["saved_bytes"]) for x in transformed),
                "container_candidate_bytes":candidate_size,
                "container_candidate_sha256":candidate_hash,
                "candidate_7z_test":"PASS",
                "member_tree_roundtrip":"PASS",
            })
            if candidate_size < old_container_size:
                shutil.copyfile(new_container,container)
                if sha256(container)!=candidate_hash:
                    raise RuntimeError(f"Post-copy container hash mismatch: {rel}")
                saved=old_container_size-candidate_size
                asset["size_bytes"]=candidate_size
                asset["sha256"]=candidate_hash
                asset.setdefault("optimization",{})["binary_compaction_pass"]={
                    "status":"REPACKED_SMALLER",
                    "prior_container_bytes":old_container_size,
                    "new_container_bytes":candidate_size,
                    "saved_bytes":saved,
                    "upx_transforms":transformed,
                    "roundtrip":"PASS",
                }
                item.update({"status":"REPACKED_SMALLER","container_after_bytes":candidate_size,"container_after_sha256":candidate_hash,"container_saved_bytes":saved})
                total_saved+=saved
                final_container_bytes+=candidate_size
            else:
                asset.setdefault("optimization",{})["binary_compaction_pass"]={
                    "status":"NO_STRICT_CONTAINER_SIZE_GAIN",
                    "prior_container_bytes":old_container_size,
                    "candidate_container_bytes":candidate_size,
                    "upx_transforms_not_promoted":transformed,
                    "roundtrip":"PASS",
                    "reason":"Candidate archive did not reduce total container size; current container retained unchanged.",
                }
                item.update({"status":"NO_STRICT_CONTAINER_SIZE_GAIN","container_after_bytes":old_container_size,"container_after_sha256":item["container_before_sha256"],"container_saved_bytes":0})
                final_container_bytes+=old_container_size
        results.append(item)
        print(json.dumps(item,ensure_ascii=False))

    # Recheck each protected legacy model-weight blob hash exactly.
    protected_after={rel:sha256(RUNTIME/rel) for rel in PROTECTED}
    if protected_before != protected_after:
        raise RuntimeError("Fail closed: at least one pre-existing model weight changed")

    placement["hard_cap_bytes"]=HARD_CAP
    placement["status"]="BINARY_COMPACTION_COMPLETE_RUNTIME_PATH_REPAIR_PENDING"
    placement["placed_assets_raw_bytes"]=int(sum(int(a["size_bytes"]) for a in placement["assets"]))
    placement["binary_compaction_pass"]={
        "completed_at_utc":datetime.now(timezone.utc).isoformat(),
        "algorithm":"UPX_ALL_DETECTED_PE_ELF_CANDIDATES_THEN_7Z_LZMA2_MAX",
        "targeted_assets":10,
        "new_asset_container_bytes_before":initial_container_bytes,
        "new_asset_container_bytes_after":final_container_bytes,
        "new_asset_container_bytes_saved":total_saved,
        "protected_legacy_weight_paths_unchanged":True,
        "runtime_repair":"DEFERRED_BY_USER_ORDER",
        "results":results,
        "certification":"NOT_GRANTED",
    }
    # Keep documentation/report metadata out of the packaged runtime payload itself.
    PLACEMENT_PATH.write_text(json.dumps(placement,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    doc=RUNTIME/"CajitadeLuna.md"
    doctext=doc.read_text(encoding="utf-8")
    marker="## Segunda pasada de compactación binaria de motores nuevos — 2026-10-23"
    if marker not in doctext:
        doctext += f"""

{marker}

Se recorrieron los diez contenedores de activos nuevos buscando todos los candidatos binarios PE/ELF. Cada transformación UPX solo se aceptó tras prueba UPX y descompresión con SHA-256 idéntico al binario previo. Los contenedores 7z/LZMA2 solo se sustituyeron cuando disminuyó estrictamente el tamaño total, y cada candidato aceptado pasó prueba de integridad y comparación del árbol extraído. Los seis pesos/modelos preexistentes permanecieron inalterados por SHA-256. La reparación funcional de rutas y consumidores continúa pendiente; no se declara certificación ni equivalencia funcional.

Informe de evidencia: ../docs/cajita-luna/CAJITA_NEW_ENGINE_BINARY_COMPACTION_20261023.json.
"""
    doc.write_text(doctext.rstrip()+"\n",encoding="utf-8")
    projected=payload_estimate()
    report={
        "schema":"CAJITA_NEW_ENGINE_BINARY_COMPACTION/1.0",
        "audit_id":"CAJITA_NEW_ENGINE_BINARY_COMPACTION_20261023",
        "completed_at_utc":datetime.now(timezone.utc).isoformat(),
        "repository":"Plomillo/luna-linux-bridge",
        "branch":"main",
        "hard_cap_bytes":HARD_CAP,
        "method":"UPX-9-LZMA on each detected PE/ELF binary, only accepted after exact decompression SHA-256 round-trip; maximum 7z LZMA2 outer container retained only when strictly smaller.",
        "scope":"All ten newly incorporated engine/runtime asset containers registered in EXTERNALIZED_ASSET_PLACEMENT.json.",
        "legacy_assets":"Six old model-weight artifacts were hash-checked before/after and not mutated.",
        "tools":{"upx":(upxver.stdout or upxver.stderr).splitlines()[:2],"7z":(szver.stdout or szver.stderr).splitlines()[:3]},
        "totals":{
            "new_asset_container_bytes_before":initial_container_bytes,
            "new_asset_container_bytes_after":final_container_bytes,
            "new_asset_container_bytes_saved":total_saved,
            "projected_runtime_input_bytes_with_declared_lfs_weights_excluding_static_manifest":projected,
            "projected_over_cap_bytes_before_new_manifest_growth":max(0,projected-HARD_CAP),
            "post_manifest_growth_still_to_be_rechecked":True,
        },
        "protected_legacy_weight_hashes":{
            p:{"before":protected_before[p],"after":protected_after[p],"unchanged":protected_before[p]==protected_after[p]} for p in PROTECTED
        },
        "assets":results,
        "runtime_path_repair":"PENDING",
        "functional_equivalence":"NOT_ESTABLISHED",
        "independent_validation":"NOT_RUN",
        "certification":"NOT_GRANTED",
    }
    REPORT_PATH.parent.mkdir(parents=True,exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report["totals"],ensure_ascii=False))
    print("LEGACY_MODEL_WEIGHTS_UNCHANGED=PASS")
    print("REPORT="+REPORT_PATH.relative_to(ROOT).as_posix())

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print(f"BINARY_COMPACTION_ABORTED: {type(exc).__name__}: {exc}",file=sys.stderr)
        raise
