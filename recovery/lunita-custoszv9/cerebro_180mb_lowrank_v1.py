#!/usr/bin/env python3
"""Checkpointed rank-1 INT8-factor candidate builder for the original GPT-OSS MXFP4 Cerebro.

Source weights are read-only. This is an aggressively lossy research candidate, not a claim of
functional equivalence or a certified release. Final candidate directory has an exact byte cap.
"""
from __future__ import annotations
import argparse
import datetime as dt
import fcntl
import gc
import hashlib
import json
import math
import os
import pathlib
import shutil
import sys
import time
import traceback
import uuid

os.environ.update({
    "OMP_NUM_THREADS": "1", "OMP_THREAD_LIMIT": "1", "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1",
    "TOKENIZERS_PARALLELISM": "false", "PYTHONDONTWRITEBYTECODE": "1",
})
# Acquire this process-wide mutex before importing torch/transformers. A concurrent
# invocation exits without reading or mutating progress, checkpoints or the hash journal.
_WORKER_LOCK_PATH = pathlib.Path(
    "/home/diegoignacionorambuenamiranda/Proyectos/1. PROYECTOS PRIORITARIOS/"
    "5. CUSTOSZ/0. CUSTOSZ  - OPERADOR/CUSTOSZ_CONTINUITY_V1/state/locks/"
    "cerebro_180mb_worker.lock"
)
_WORKER_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
_WORKER_LOCK_FD = os.open(str(_WORKER_LOCK_PATH), os.O_CREAT | os.O_RDWR, 0o600)
try:
    fcntl.flock(_WORKER_LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    os.lseek(_WORKER_LOCK_FD, 0, os.SEEK_SET)
    owner = os.read(_WORKER_LOCK_FD, 2048).decode("utf-8", "replace").strip()
    print("WORKER_ALREADY_RUNNING: refusing shared-state access; " + owner, file=sys.stderr, flush=True)
    os.close(_WORKER_LOCK_FD)
    raise SystemExit(75)
_lock_payload = json.dumps({"pid": os.getpid(), "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                            "job_dir_env": os.environ.get("CEREBRO_JOB_DIR", "default")},
                           sort_keys=True, separators=(",", ":")).encode("utf-8")
os.ftruncate(_WORKER_LOCK_FD, 0)
os.write(_WORKER_LOCK_FD, _lock_payload)
os.fsync(_WORKER_LOCK_FD)

import torch
from safetensors import safe_open
from safetensors.torch import save_file, load_file
from transformers.integrations.mxfp4 import convert_moe_packed_tensors

HOME = pathlib.Path("/home/diegoignacionorambuenamiranda")
ROOT = HOME / "Proyectos/1. PROYECTOS PRIORITARIOS/5. CUSTOSZ/0. CUSTOSZ  - OPERADOR"
RT = ROOT / "CUSTOSZ_CONTINUITY_V1"
STATE = RT / "state"
MODEL = HOME / "Proyectos/1. PROYECTOS PRIORITARIOS/1. PROYECTO LUNA/2. Cajita de Luna/1. Cerebro"
INDEX = MODEL / "model.safetensors.index.json"
CONFIG = MODEL / "config.json"
SCRIPT_DIR = STATE / "jobs/cerebro_180mb_lowrank_v1"
JOB_DIR = pathlib.Path(os.environ.get("CEREBRO_JOB_DIR", str(SCRIPT_DIR))).resolve()
BASE_CHUNKS = JOB_DIR / "base_chunks"
EXPERT_CHUNKS = JOB_DIR / "expert_chunks"
REPORTS = STATE / "worker_outputs"
RUNTIME_SOURCE = SCRIPT_DIR / "cerebro_180mb_lowrank_runtime_v1.py"
TARGET_BYTES = 180_000_000
RANK = 1
OVERSAMPLE = 3
BLOCK_ROWS = 128
DENSE_GROUP_WIDTH = 16
EXPERT_GROUP_WIDTH = 8
EXPECTED_MISSION_SHA = "0a36c59d4baf5d547f5217dc9c6db2a58ad9f8f3ea65d88f9b16a0dbe1604f8f"
SCHEMA = "CUSTOSZ_CEREBRO_GPTOSS_RANK1_INT8_TARGET180/1.0"
ASSETS = (
    "generation_config.json", "tokenizer.json", "tokenizer_config.json",
    "special_tokens_map.json", "chat_template.jinja", "USAGE_POLICY", "README.md", "LICENSE",
)

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()

def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()

def sha_file(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def stat_file(path):
    s = pathlib.Path(path).stat()
    return {"bytes": s.st_size, "mtime_ns": s.st_mtime_ns}

def atomic_json(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with tmp.open("x", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)

class Job:
    def __init__(self):
        JOB_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        BASE_CHUNKS.mkdir(parents=True, exist_ok=True, mode=0o700)
        EXPERT_CHUNKS.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.progress_path = JOB_DIR / "progress.json"
        self.journal_path = JOB_DIR / "events.jsonl"
        self.log_path = JOB_DIR / "job.log"
        progress_existed = self.progress_path.is_file()
        journal_existed = self.journal_path.is_file()
        self.progress = json.loads(self.progress_path.read_text()) if progress_existed else {}
        self.prev_hash = "0" * 64
        self.event_count = 0
        if self.journal_path.exists():
            for line_no, line in enumerate(self.journal_path.read_text().splitlines(), 1):
                row = json.loads(line)
                recorded = row.pop("event_sha256", None)
                if row.get("sequence") != self.event_count + 1:
                    raise RuntimeError(f"EVENT_SEQUENCE_INVALID:{line_no}")
                if row.get("previous_event_sha256") != self.prev_hash or sha_bytes(canonical(row)) != recorded:
                    raise RuntimeError(f"EVENT_CHAIN_INVALID:{line_no}")
                self.prev_hash = recorded
                self.event_count += 1
        if not self.progress:
            stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            candidate_id = "GPTOSS_CEREBRO_RANK1_INT8_" + stamp
            self.progress = {
                "schema": SCHEMA, "job_id": "CUSTOSZ_CEREBRO_180MB_RANK1_V1",
                "mission_sha256": EXPECTED_MISSION_SHA, "candidate_id": candidate_id,
                "candidate_dir": str(STATE / "cajita_candidates" / candidate_id),
                "target_bytes": TARGET_BYTES, "rank": RANK, "oversample": OVERSAMPLE,
                "stage": "INITIALIZED", "dense_source_key_count": 0,
                "base_groups": [], "expert_chunks": {},
                "dense_metrics": [], "expert_metrics_aggregate": {"norm_sq": 0.0, "residual_sq": 0.0, "matrix_count": 0},
                "source_hashes_complete": False, "quality_equivalence": "NOT_ESTABLISHED",
                "certification": "NOT_GRANTED", "canonical_promotion": "NOT_AUTHORIZED",
                "mission_completion_claim": False, "created_at_utc": utc(),
            }
            self.event("JOB_CREATED_CHECKPOINTED", {"candidate_id": candidate_id, "target_bytes": TARGET_BYTES,
                        "rank": RANK, "factor_dtype": "INT8", "source_format": "GPT-OSS MXFP4"})
            self.save()
        if self.progress.get("schema") != SCHEMA or self.progress.get("mission_sha256") != EXPECTED_MISSION_SHA:
            raise RuntimeError("RESUME_SCOPE_OR_MISSION_MISMATCH")
        if self.progress.get("target_bytes") != TARGET_BYTES or self.progress.get("rank") != RANK:
            raise RuntimeError("RESUME_TARGET_OR_RANK_MISMATCH")
        if progress_existed and not journal_existed:
            provenance = self.progress.get("recovery_provenance")
            if not isinstance(provenance, dict) or not provenance.get("previous_events_sha256"):
                raise RuntimeError("UNJOURNALED_CHECKPOINT_REFUSED")
            self.event("RECOVERY_CHECKPOINT_IMPORTED", {
                "recovery_id": provenance.get("recovery_id"),
                "previous_job_root": provenance.get("previous_job_root"),
                "previous_progress_sha256": provenance.get("previous_progress_sha256"),
                "previous_events_sha256": provenance.get("previous_events_sha256"),
                "verified_base_groups": provenance.get("verified_base_groups"),
                "verified_expert_chunks": provenance.get("verified_expert_chunks"),
                "checkpoint_manifest_sha256": provenance.get("checkpoint_manifest_sha256"),
                "source_config_sha256": self.progress.get("source_config_sha256"),
                "source_index_sha256": self.progress.get("source_index_sha256"),
            })
            self.log("RECOVERY_CHECKPOINT_IMPORTED " + json.dumps(provenance, sort_keys=True))

    def log(self, msg):
        line = f"[{utc()}] {msg}"
        print(line, flush=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

    def event(self, kind, payload):
        row = {"sequence": self.event_count + 1, "timestamp_utc": utc(), "event_type": kind,
               "mission_sha256": EXPECTED_MISSION_SHA, "previous_event_sha256": self.prev_hash,
               "payload": payload}
        digest = sha_bytes(canonical(row))
        encoded = (json.dumps({**row, "event_sha256": digest}, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        fd = os.open(str(self.journal_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            written = os.write(fd, encoded)
            if written != len(encoded):
                raise RuntimeError("EVENT_APPEND_SHORT_WRITE")
            os.fsync(fd)
        finally:
            os.close(fd)
        self.event_count += 1
        self.prev_hash = digest
        return digest

    def save(self):
        self.progress["last_progress_utc"] = utc()
        atomic_json(self.progress_path, self.progress)

    def stage(self, stage, **fields):
        self.progress.update(fields)
        self.progress["stage"] = stage
        self.save()
        self.event("STAGE_CHANGED", {"stage": stage, **fields})
        self.log("STAGE=" + stage + " " + json.dumps(fields, sort_keys=True, ensure_ascii=False))

def source_snapshot(job, weight_map):
    if not CONFIG.is_file() or not INDEX.is_file():
        raise RuntimeError("SOURCE_CONFIG_OR_INDEX_MISSING")
    cfg_hash, idx_hash = sha_file(CONFIG), sha_file(INDEX)
    cfg = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    idx = json.loads(INDEX.read_text(encoding="utf-8-sig"))
    if cfg.get("model_type") != "gpt_oss" or "GptOssForCausalLM" not in cfg.get("architectures", []):
        raise RuntimeError("CEREBRO_MODEL_IDENTITY_MISMATCH")
    if cfg_hash != job.progress.get("source_config_sha256", cfg_hash) or idx_hash != job.progress.get("source_index_sha256", idx_hash):
        raise RuntimeError("SOURCE_CONFIG_OR_INDEX_CHANGED_DURING_RESUME")
    shards = sorted(set(str(x) for x in weight_map.values()))
    rows = {}
    for name in shards:
        p = MODEL / name
        if not p.is_file():
            raise RuntimeError("SOURCE_SHARD_MISSING:" + name)
        cur = stat_file(p)
        old = (job.progress.get("source_shards") or {}).get(name)
        if old and (old["bytes"] != cur["bytes"] or old["mtime_ns"] != cur["mtime_ns"]):
            raise RuntimeError("SOURCE_SHARD_CHANGED_DURING_RESUME:" + name)
        rows[name] = {"name": name, **cur}
    if not job.progress.get("source_config_sha256"):
        job.progress["source_config_sha256"] = cfg_hash
        job.progress["source_index_sha256"] = idx_hash
        job.progress["source_model_type"] = cfg.get("model_type")
        job.progress["source_architecture"] = cfg.get("architectures")
        job.progress["source_total_size_bytes"] = int((idx.get("metadata") or {}).get("total_size", 0))
        job.progress["source_shards"] = rows
        job.progress["source_shard_count"] = len(rows)
        job.save()
        job.event("SOURCE_IDENTITY_PINNED", {"config_sha256": cfg_hash, "index_sha256": idx_hash,
                    "shard_count": len(rows), "declared_tensor_bytes": job.progress["source_total_size_bytes"],
                    "source_files_modified": False})
    return cfg, idx, rows

def copy_assets(job, candidate):
    candidate.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not (candidate / "config.json").exists():
        cfg = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
        cfg.pop("quantization_config", None)
        cfg["torch_dtype"] = "bfloat16"
        cfg["louksna_derived_compression"] = {
            "schema": SCHEMA, "rank": RANK, "factor_dtype": "INT8",
            "source_config_sha256": job.progress["source_config_sha256"],
            "quality_equivalence": "NOT_ESTABLISHED",
        }
        atomic_json(candidate / "config.json", cfg)
    for name in ASSETS:
        src = MODEL / name
        dst = candidate / name
        if not src.is_file():
            if name in {"tokenizer.json", "tokenizer_config.json"}:
                raise RuntimeError("REQUIRED_TOKENIZER_ASSET_MISSING:" + name)
            continue
        if dst.exists():
            if sha_file(src) != sha_file(dst):
                raise RuntimeError("CANDIDATE_ASSET_COLLISION_NO_OVERWRITE:" + name)
        else:
            shutil.copy2(src, dst)
        if sha_file(src) != sha_file(dst):
            raise RuntimeError("ASSET_COPY_HASH_MISMATCH:" + name)
    if not RUNTIME_SOURCE.is_file():
        raise RuntimeError("CANDIDATE_RUNTIME_SOURCE_MISSING")
    runtime_dst = candidate / "cerebro_180mb_runtime.py"
    runtime_hash = sha_file(RUNTIME_SOURCE)
    if runtime_dst.exists() and sha_file(runtime_dst) != runtime_hash:
        raise RuntimeError("RUNTIME_COLLISION_NO_OVERWRITE")
    if not runtime_dst.exists():
        shutil.copy2(RUNTIME_SOURCE, runtime_dst)
    job.progress["runtime_sha256"] = runtime_hash
    job.progress["candidate_assets_bytes"] = sum(p.stat().st_size for p in candidate.rglob("*") if p.is_file())
    job.save()

def lowrank_from_reader(key, m, n, read_rows):
    rank = RANK
    qdim = min(rank + OVERSAMPLE, m, n)
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") & ((1 << 63) - 1)
    gen = torch.Generator(device="cpu")
    gen.manual_seed(seed)
    omega = torch.randn((n, qdim), generator=gen, dtype=torch.float32) / (qdim ** 0.5)
    y = torch.empty((m, qdim), dtype=torch.float32)
    norm_sq = 0.0
    for start in range(0, m, BLOCK_ROWS):
        end = min(m, start + BLOCK_ROWS)
        w = read_rows(start, end).to(torch.float32)
        if w.shape != (end - start, n):
            raise RuntimeError(f"READ_MATRIX_SHAPE_MISMATCH:{key}:{tuple(w.shape)}")
        y[start:end] = w @ omega
        norm_sq += float(torch.sum(w * w).item())
        del w
    qmat, _ = torch.linalg.qr(y, mode="reduced")
    bmat = torch.zeros((qdim, n), dtype=torch.float32)
    for start in range(0, m, BLOCK_ROWS):
        end = min(m, start + BLOCK_ROWS)
        w = read_rows(start, end).to(torch.float32)
        bmat.add_(qmat[start:end].T @ w)
        del w
    ub, sval, vh = torch.linalg.svd(bmat, full_matrices=False)
    sigma = sval[0].clamp_min(0)
    root = torch.sqrt(sigma)
    a = (qmat @ ub[:, :1]) * root
    b = root * vh[:1, :]
    scale_u = (a.abs().amax(dim=0) / 127.0).clamp_min(1e-12)
    scale_v = (b.abs().amax(dim=1) / 127.0).clamp_min(1e-12)
    aq = torch.round(a / scale_u.unsqueeze(0)).clamp(-127, 127).to(torch.int8).contiguous()
    bq = torch.round(b / scale_v.unsqueeze(1)).clamp(-127, 127).to(torch.int8).contiguous()
    aqf = aq.to(torch.float32) * scale_u.unsqueeze(0)
    bqf = bq.to(torch.float32) * scale_v.unsqueeze(1)
    residual_sq = 0.0
    for start in range(0, m, BLOCK_ROWS):
        end = min(m, start + BLOCK_ROWS)
        w = read_rows(start, end).to(torch.float32)
        delta = w - (aqf[start:end] @ bqf)
        residual_sq += float(torch.sum(delta * delta).item())
        del w, delta
    metrics = {
        "shape": [m, n], "rank": rank, "factor_dtype": "INT8",
        "factor_bytes": int(aq.numel() + bq.numel() + scale_u.numel()*4 + scale_v.numel()*4),
        "source_norm_sq": norm_sq, "residual_sq_after_int8": residual_sq,
        "relative_frobenius_error_after_int8": math.sqrt(max(residual_sq, 0.0) / max(norm_sq, 1e-30)),
        "captured_projected_energy": float(sigma.item() ** 2),
    }
    return aq, bq, scale_u.to(torch.float32), scale_v.to(torch.float32), metrics

def factor_source_weight(sf, key):
    sl = sf.get_slice(key)
    shape = tuple(sl.get_shape())
    if len(shape) != 2:
        raise RuntimeError("EXPECTED_MATRIX_WEIGHT:" + key + ":" + str(shape))
    m, n = shape
    read_rows = lambda start, end: sl[start:end]
    a, b, su, sv, metrics = lowrank_from_reader(key, m, n, read_rows)
    base = key[:-len(".weight")]
    return {
        base + ".weight_u": a, base + ".weight_v": b,
        base + ".scale_u": su, base + ".scale_v": sv,
    }, metrics

def copy_small_source_tensor(sf, key):
    sl = sf.get_slice(key)
    shape = tuple(sl.get_shape())
    if len(shape) == 1:
        return sl[:].contiguous()
    if len(shape) == 2:
        # Only expert biases use two-dimensional source tensors without ".weight".
        if ".mlp.experts." in key and (key.endswith("gate_up_proj_bias") or key.endswith("down_proj_bias")):
            return sl[:].contiguous()
        raise RuntimeError("UNEXPECTED_UNFACTORIZED_MATRIX:" + key + ":" + str(shape))
    raise RuntimeError("UNSUPPORTED_SOURCE_TENSOR_RANK:" + key + ":" + str(shape))

def dense_quantization(job, index, weight_map):
    keys = sorted(weight_map.keys())
    done = int(job.progress.get("dense_source_key_count", 0))
    if done > len(keys) or (done and not job.progress.get("base_groups")):
        raise RuntimeError("DENSE_RESUME_CHECKPOINT_INCONSISTENT")
    if done == 0:
        job.stage("DENSE_WEIGHT_FACTORIZATION_RUNNING", source_keys_total=len(keys), completed_source_keys=0,
                  note="First real matrix low-rank/INT8 factorization is now executing")
        job.event("REAL_QUANTIZATION_STARTED", {"model_type": "gpt_oss", "method": "rank1 randomized SVD + symmetric INT8 factors",
                    "source_key_count": len(keys), "target_bytes": TARGET_BYTES, "memory_cap_bytes": 1024**3})
    group_num = len(job.progress.get("base_groups", []))
    batch = {}
    batch_metrics = []
    start_idx = done
    for i in range(done, len(keys)):
        key = keys[i]
        if key.endswith((".mlp.experts.gate_up_proj_blocks", ".mlp.experts.gate_up_proj_scales",
                         ".mlp.experts.down_proj_blocks", ".mlp.experts.down_proj_scales")):
            pass
        else:
            shard = MODEL / weight_map[key]
            with safe_open(str(shard), framework="pt", device="cpu") as sf:
                shape = tuple(sf.get_slice(key).get_shape())
                if key.endswith(".weight") and len(shape) == 2:
                    factors, metric = factor_source_weight(sf, key)
                    batch.update(factors)
                    batch_metrics.append({"tensor": key, **metric})
                else:
                    batch[key] = copy_small_source_tensor(sf, key)
        source_end = i + 1
        if source_end % DENSE_GROUP_WIDTH == 0 or source_end == len(keys):
            entry = {"group": group_num, "source_start_index": start_idx, "source_end_index": source_end,
                     "source_keys_processed": source_end - start_idx, "file": None, "sha256": None, "bytes": 0,
                     "metrics": batch_metrics}
            if batch:
                p = BASE_CHUNKS / f"base_{group_num:04d}.safetensors"
                if p.exists():
                    raise RuntimeError("BASE_CHUNK_COLLISION_NO_OVERWRITE:" + p.name)
                tmp = p.with_suffix(".tmp")
                save_file(batch, str(tmp), metadata={"schema": SCHEMA, "mission_sha256": EXPECTED_MISSION_SHA,
                                                      "source_end_index": str(source_end)})
                os.replace(tmp, p)
                entry.update({"file": p.name, "sha256": sha_file(p), "bytes": p.stat().st_size})
            job.progress.setdefault("base_groups", []).append(entry)
            job.progress.setdefault("dense_metrics", []).extend(batch_metrics)
            job.progress["dense_source_key_count"] = source_end
            job.progress["completed_dense_tensor_count"] = len(job.progress["dense_metrics"])
            job.save()
            job.event("DENSE_GROUP_CHECKPOINTED", {"group": group_num, "source_end_index": source_end,
                       "source_keys_total": len(keys), "file": entry["file"], "bytes": entry["bytes"],
                       "sha256": entry["sha256"]})
            job.log(f"DENSE_CHECKPOINT source_keys={source_end}/{len(keys)} tensors={len(job.progress['dense_metrics'])} file={entry['file']}")
            group_num += 1
            batch, batch_metrics = {}, []
            start_idx = source_end
    job.stage("DENSE_FACTORIZATION_COMPLETE", completed_source_keys=len(keys),
              dense_matrix_count=len(job.progress.get("dense_metrics", [])))

def decode_one_expert(block_path, scale_path, block_key, scale_key, expert):
    if block_path != scale_path:
        raise RuntimeError("MXFP4_BLOCK_SCALE_SHARDS_DIFFER:" + block_key)
    with safe_open(str(block_path), framework="pt", device="cpu") as sf:
        bsl = sf.get_slice(block_key)
        ssl = sf.get_slice(scale_key)
        blocks = bsl[expert:expert + 1]
        scales = ssl[expert:expert + 1]
    matrix = convert_moe_packed_tensors(blocks, scales, dtype=torch.float32)[0].contiguous()
    del blocks, scales
    if matrix.ndim != 2 or not torch.isfinite(matrix).all():
        raise RuntimeError("MXFP4_DEQUANTIZATION_FAILED:" + block_key + f":expert={expert}")
    return matrix

def expert_factor_chunk(job, layer, start, end, weight_map):
    base = f"model.layers.{layer}.mlp.experts."
    keys = {
        "gu_blocks": base + "gate_up_proj_blocks", "gu_scales": base + "gate_up_proj_scales",
        "down_blocks": base + "down_proj_blocks", "down_scales": base + "down_proj_scales",
    }
    for k in keys.values():
        if k not in weight_map:
            raise RuntimeError("MXFP4_EXPERT_TENSOR_MISSING:" + k)
    paths = {name: MODEL / weight_map[key] for name, key in keys.items()}
    # Hugging Face sharding can place one layer's gate/up and down expert tensors
    # in distinct shards. Only each packed-block/scales pair needs co-location.
    if paths["gu_blocks"] != paths["gu_scales"]:
        raise RuntimeError("MXFP4_GATE_UP_BLOCK_SCALE_SHARDS_DIFFER:" + str(paths))
    if paths["down_blocks"] != paths["down_scales"]:
        raise RuntimeError("MXFP4_DOWN_BLOCK_SCALE_SHARDS_DIFFER:" + str(paths))
    if any(not p.is_file() for p in paths.values()):
        raise RuntimeError("MXFP4_EXPERT_SHARD_MISSING")
    collected = {name: [] for name in ("gate_up_proj_u", "gate_up_proj_v", "gate_up_proj_scale_u",
                "gate_up_proj_scale_v", "down_proj_u", "down_proj_v", "down_proj_scale_u", "down_proj_scale_v")}
    norm_sq_total, residual_sq_total, count = 0.0, 0.0, 0
    for expert in range(start, end):
        gu = decode_one_expert(paths["gu_blocks"], paths["gu_scales"], keys["gu_blocks"], keys["gu_scales"], expert)
        if tuple(gu.shape) != (2880, 5760):
            raise RuntimeError(f"MXFP4_GATE_UP_SHAPE_MISMATCH:{tuple(gu.shape)}")
        au, bu, asu, bsu, met_gu = lowrank_from_reader(f"{keys['gu_blocks']}:expert={expert}", gu.shape[0], gu.shape[1],
            lambda a, b, x=gu: x[a:b])
        del gu
        down = decode_one_expert(paths["down_blocks"], paths["down_scales"], keys["down_blocks"], keys["down_scales"], expert)
        if tuple(down.shape) != (2880, 2880):
            raise RuntimeError(f"MXFP4_DOWN_SHAPE_MISMATCH:{tuple(down.shape)}")
        ad, bd, asd, bsd, met_down = lowrank_from_reader(f"{keys['down_blocks']}:expert={expert}", down.shape[0], down.shape[1],
            lambda a, b, x=down: x[a:b])
        del down
        collected["gate_up_proj_u"].append(au); collected["gate_up_proj_v"].append(bu)
        collected["gate_up_proj_scale_u"].append(asu); collected["gate_up_proj_scale_v"].append(bsu)
        collected["down_proj_u"].append(ad); collected["down_proj_v"].append(bd)
        collected["down_proj_scale_u"].append(asd); collected["down_proj_scale_v"].append(bsd)
        norm_sq_total += met_gu["source_norm_sq"] + met_down["source_norm_sq"]
        residual_sq_total += met_gu["residual_sq_after_int8"] + met_down["residual_sq_after_int8"]
        count += 2
        del au, bu, asu, bsu, ad, bd, asd, bsd, met_gu, met_down
        if (expert + 1) % 2 == 0:
            gc.collect()
    data = {}
    for k, values in collected.items():
        data[base + k] = torch.stack(values, dim=0).contiguous()
    return data, {"norm_sq": norm_sq_total, "residual_sq": residual_sq_total, "matrix_count": count}

def quantize_expert_matrices(job, weight_map):
    completed = job.progress.setdefault("expert_chunks", {})
    job.stage("MXFP4_EXPERT_FACTORISATION_RUNNING", experts_total=36*128, expert_chunk_width=EXPERT_GROUP_WIDTH,
              note="Packed MXFP4 expert weights are being dequantized one expert at a time and rank-1 INT8-factorized")
    for layer in range(36):
        for start in range(0, 128, EXPERT_GROUP_WIDTH):
            end = min(128, start + EXPERT_GROUP_WIDTH)
            key = f"{layer}:{start}"
            rec = completed.get(key)
            p = EXPERT_CHUNKS / f"layer_{layer:02d}_experts_{start:03d}_{end-1:03d}.safetensors"
            if rec:
                if not p.is_file() or sha_file(p) != rec.get("sha256") or p.stat().st_size != rec.get("bytes"):
                    raise RuntimeError("EXPERT_CHECKPOINT_HASH_MISMATCH:" + key)
                continue
            if p.exists():
                raise RuntimeError("EXPERT_CHECKPOINT_COLLISION_NO_OVERWRITE:" + p.name)
            data, metrics = expert_factor_chunk(job, layer, start, end, weight_map)
            tmp = p.with_suffix(".tmp")
            save_file(data, str(tmp), metadata={"schema": SCHEMA, "mission_sha256": EXPECTED_MISSION_SHA,
                                                "layer": str(layer), "expert_start": str(start), "expert_end": str(end)})
            os.replace(tmp, p)
            chunk_rec = {"file": p.name, "sha256": sha_file(p), "bytes": p.stat().st_size,
                         "layer": layer, "expert_start": start, "expert_end": end,
                         **metrics}
            completed[key] = chunk_rec
            job.progress["expert_chunks"] = completed
            job.save()
            job.event("MXFP4_EXPERT_CHUNK_CHECKPOINTED", {"key": key, **chunk_rec})
            job.log(f"EXPERT_CHECKPOINT layer={layer+1}/36 experts={end}/128 chunk={p.name} bytes={p.stat().st_size}")
            del data
            gc.collect()
    job.stage("MXFP4_EXPERT_FACTORIZATION_COMPLETE", completed_expert_chunks=len(completed),
              experts_processed=36*128)

def assemble_candidate(job, weight_map):
    candidate = pathlib.Path(job.progress["candidate_dir"])
    temp_weights = JOB_DIR / "model.candidate.assembling.safetensors"
    if temp_weights.exists():
        raise RuntimeError("ASSEMBLY_TEMP_EXISTS_NO_OVERWRITE")
    state = {}
    for rec in job.progress.get("base_groups", []):
        if not rec.get("file"):
            continue
        p = BASE_CHUNKS / rec["file"]
        if not p.is_file() or sha_file(p) != rec["sha256"]:
            raise RuntimeError("BASE_CHECKPOINT_HASH_MISMATCH:" + rec["file"])
        state.update(load_file(str(p), device="cpu"))
    for layer in range(36):
        base = f"model.layers.{layer}.mlp.experts."
        full_shapes = {
            "gate_up_proj_u": (128, 2880, 1), "gate_up_proj_v": (128, 1, 5760),
            "gate_up_proj_scale_u": (128, 1), "gate_up_proj_scale_v": (128, 1),
            "down_proj_u": (128, 2880, 1), "down_proj_v": (128, 1, 2880),
            "down_proj_scale_u": (128, 1), "down_proj_scale_v": (128, 1),
        }
        layer_data = {k: torch.empty(shape, dtype=torch.float32 if "scale_" in k else torch.int8)
                      for k, shape in full_shapes.items()}
        for start in range(0, 128, EXPERT_GROUP_WIDTH):
            end = min(128, start + EXPERT_GROUP_WIDTH)
            key = f"{layer}:{start}"
            rec = job.progress["expert_chunks"].get(key)
            if not rec:
                raise RuntimeError("EXPERT_CHUNK_MISSING:" + key)
            p = EXPERT_CHUNKS / rec["file"]
            if sha_file(p) != rec["sha256"]:
                raise RuntimeError("EXPERT_CHUNK_HASH_MISMATCH:" + key)
            chunk = load_file(str(p), device="cpu")
            for k in full_shapes:
                layer_data[k][start:end] = chunk[base + k]
            del chunk
        for k in full_shapes:
            state[base + k] = layer_data.pop(k)
        del layer_data
        gc.collect()
        job.log(f"ASSEMBLY_LAYER_COMPLETE layer={layer+1}/36 tensors={len(state)}")
    for key in list(state):
        if not isinstance(state[key], torch.Tensor) or state[key].device.type != "cpu":
            raise RuntimeError("INVALID_ASSEMBLY_TENSOR:" + key)
    job.stage("ASSEMBLING_CANDIDATE_WEIGHTS", output_tensor_count=len(state))
    save_file(state, str(temp_weights), metadata={
        "format": "pt", "source_model_id": "OPENAI_GPT_OSS_CEREBRO_MXFP4",
        "method": "rank1_randomized_svd_symmetric_int8_factors", "rank": str(RANK),
        "source_config_sha256": job.progress["source_config_sha256"],
        "source_index_sha256": job.progress["source_index_sha256"],
        "mission_sha256": EXPECTED_MISSION_SHA,
    })
    temp_size = temp_weights.stat().st_size
    pre_weights_bytes = sum(p.stat().st_size for p in candidate.rglob("*") if p.is_file())
    if pre_weights_bytes + temp_size > TARGET_BYTES:
        job.progress.update({"stage": "BLOCKED_HARD_SIZE_GATE", "candidate_assets_bytes": pre_weights_bytes,
                             "assembled_weights_bytes": temp_size, "predicted_total_bytes": pre_weights_bytes + temp_size,
                             "mission_completion_claim": False, "certification": "NOT_GRANTED"})
        job.save()
        job.event("HARD_SIZE_GATE_BLOCKED", {"candidate_assets_bytes": pre_weights_bytes,
                   "weights_bytes": temp_size, "target_bytes": TARGET_BYTES})
        raise RuntimeError("HARD_SIZE_GATE:refusing to publish over 180,000,000 bytes")
    os.replace(temp_weights, candidate / "model.safetensors")
    weight_map_out = {k: "model.safetensors" for k in state.keys()}
    atomic_json(candidate / "model.safetensors.index.json", {"metadata": {"total_size": sum(t.numel()*t.element_size() for t in state.values())},
                                                             "weight_map": weight_map_out})
    dense_norm = sum(m.get("source_norm_sq", 0.0) for m in job.progress.get("dense_metrics", []))
    dense_resid = sum(m.get("residual_sq_after_int8", 0.0) for m in job.progress.get("dense_metrics", []))
    expert_agg = {"norm_sq": 0.0, "residual_sq": 0.0, "matrix_count": 0}
    for rec in job.progress.get("expert_chunks", {}).values():
        for k in expert_agg:
            expert_agg[k] += rec.get(k, 0.0)
    norm_total = dense_norm + expert_agg["norm_sq"]
    resid_total = dense_resid + expert_agg["residual_sq"]
    aggregate_error = math.sqrt(max(resid_total, 0.0) / max(norm_total, 1e-30))
    meta = {
        "schema": SCHEMA, "model_id": "OPENAI_GPT_OSS_CEREBRO_MXFP4",
        "architecture": "GptOssForCausalLM", "source_config_sha256": job.progress["source_config_sha256"],
        "source_index_sha256": job.progress["source_index_sha256"],
        "source_shards_inventory": job.progress["source_shards"],
        "source_shard_mutation": "NO_SOURCE_WRITES_PERFORMED; SIZE_AND_MTIME_POSTCHECK_REQUIRED",
        "method": "randomized_truncated_svd_rank1_plus_symmetric_int8_factor_quantization",
        "rank": RANK, "oversample": OVERSAMPLE, "target_bytes": TARGET_BYTES,
        "candidate_total_bytes_before_metadata": sum(p.stat().st_size for p in candidate.rglob("*") if p.is_file()),
        "source_tensor_keys": len(weight_map), "dense_matrices_factorized": len(job.progress.get("dense_metrics", [])),
        "expert_matrices_factorized": int(expert_agg["matrix_count"]),
        "aggregate_relative_frobenius_error_after_int8": aggregate_error,
        "quality_equivalence": "NOT_ESTABLISHED", "one_token_generation_test": "PENDING",
        "certification": "NOT_GRANTED", "canonical_promotion": "NOT_AUTHORIZED",
        "created_at_utc": utc(),
    }
    atomic_json(candidate / "compression_metadata.json", meta)
    final_bytes = sum(p.stat().st_size for p in candidate.rglob("*") if p.is_file())
    if final_bytes > TARGET_BYTES:
        # Do not expose an over-limit candidate as deliverable.
        (candidate / "compression_metadata.json").unlink(missing_ok=True)
        (candidate / "model.safetensors.index.json").unlink(missing_ok=True)
        (candidate / "model.safetensors").unlink(missing_ok=True)
        job.progress.update({"stage": "BLOCKED_HARD_SIZE_GATE_POSTCHECK", "candidate_bytes": final_bytes,
                             "target_bytes": TARGET_BYTES, "mission_completion_claim": False,
                             "certification": "NOT_GRANTED"})
        job.save()
        job.event("HARD_SIZE_GATE_POSTCHECK_BLOCKED", {"candidate_bytes": final_bytes, "target_bytes": TARGET_BYTES})
        raise RuntimeError("HARD_SIZE_GATE_POSTCHECK")
    job.progress.update({"candidate_bytes": final_bytes, "model_safetensors_bytes": (candidate/"model.safetensors").stat().st_size,
                         "model_safetensors_sha256": sha_file(candidate/"model.safetensors"),
                         "candidate_dir": str(candidate), "candidate_id": candidate.name,
                         "aggregate_relative_frobenius_error_after_int8": aggregate_error,
                         "stage": "CANDIDATE_ASSEMBLED_AWAITING_RUNTIME_TEST",
                         "mission_completion_claim": False, "certification": "NOT_GRANTED"})
    job.save()
    job.event("CANDIDATE_ASSEMBLED_UNDER_HARD_CAP", {"candidate_bytes": final_bytes, "target_bytes": TARGET_BYTES,
               "weights_bytes": (candidate/"model.safetensors").stat().st_size,
               "model_safetensors_sha256": job.progress["model_safetensors_sha256"],
               "quality_equivalence": "NOT_ESTABLISHED"})
    job.log(f"CANDIDATE_ASSEMBLED bytes={final_bytes}/{TARGET_BYTES} weights={temp_size} quality=UNVALIDATED")
    # Release factor dictionaries before starting the isolated runtime child under the same 1 GiB scope.
    del state
    gc.collect()
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass
    return candidate

def postcheck_source(job):
    before = job.progress.get("source_shards", {})
    changed = []
    for name, rec in before.items():
        p = MODEL / name
        if not p.is_file() or stat_file(p) != {"bytes": rec["bytes"], "mtime_ns": rec["mtime_ns"]}:
            changed.append(name)
    if changed:
        raise RuntimeError("SOURCE_SHARD_STAT_MISMATCH:" + ",".join(changed))
    if sha_file(CONFIG) != job.progress["source_config_sha256"] or sha_file(INDEX) != job.progress["source_index_sha256"]:
        raise RuntimeError("SOURCE_CONFIG_OR_INDEX_CHANGED")
    job.event("SOURCE_NONMUTATION_POSTCHECK_PASS", {"source_shards_stat_unchanged": len(before),
               "config_sha256_unchanged": True, "index_sha256_unchanged": True})
    job.progress["source_nonmutation_postcheck"] = "PASS_SIZE_MTIME_CONFIG_INDEX"
    job.save()

def write_report(job, candidate, smoke=None, error=None):
    report = {
        "schema": "CUSTOSZ_CEREBRO_180MB_QUANTIZATION_REPORT/1.0",
        "timestamp_utc": utc(), "job_id": job.progress["job_id"],
        "candidate_id": candidate.name if candidate else job.progress.get("candidate_id"),
        "candidate_dir": str(candidate) if candidate else job.progress.get("candidate_dir"),
        "target_bytes": TARGET_BYTES, "candidate_bytes": job.progress.get("candidate_bytes"),
        "stage": job.progress.get("stage"), "last_progress_utc": job.progress.get("last_progress_utc"),
        "completed_dense_source_keys": job.progress.get("dense_source_key_count"),
        "dense_source_keys_total": len(json.loads(INDEX.read_text())["weight_map"]),
        "expert_chunks_complete": len(job.progress.get("expert_chunks", {})),
        "expert_chunks_total": 36 * (128 // EXPERT_GROUP_WIDTH),
        "aggregate_relative_frobenius_error_after_int8": job.progress.get("aggregate_relative_frobenius_error_after_int8"),
        "runtime_smoke": smoke, "error": error, "mission_sha256": EXPECTED_MISSION_SHA,
        "source_weights_written": False, "source_nonmutation_postcheck": job.progress.get("source_nonmutation_postcheck"),
        "quality_equivalence": "NOT_ESTABLISHED", "certification": "NOT_GRANTED",
        "canonical_promotion": "NOT_AUTHORIZED", "mission_completion_claim": False,
    }
    REPORTS.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = REPORTS / f"CEREBRO_180MB_QUANTIZATION_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    atomic_json(path, report)
    report["report_path"] = str(path)
    report["report_sha256"] = sha_file(path)
    return report

def run():
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    job = Job()
    idx = json.loads(INDEX.read_text(encoding="utf-8-sig"))
    weight_map = idx["weight_map"]
    cfg, idxdoc, rows = source_snapshot(job, weight_map)
    if len(weight_map) != 687 or len(rows) != 15:
        raise RuntimeError(f"PINNED_CEREBRO_INVENTORY_MISMATCH:keys={len(weight_map)} shards={len(rows)}")
    candidate = pathlib.Path(job.progress["candidate_dir"])
    copy_assets(job, candidate)
    dense_quantization(job, idxdoc, weight_map)
    quantize_expert_matrices(job, weight_map)
    candidate = assemble_candidate(job, weight_map)
    postcheck_source(job)
    job.stage("CANDIDATE_ASSEMBLED_AWAITING_RUNTIME_TEST", candidate_bytes=job.progress["candidate_bytes"])
    smoke_result = None
    runtime = candidate / "cerebro_180mb_runtime.py"
    job.stage("RUNTIME_SMOKE_TEST_RUNNING", candidate_bytes=job.progress["candidate_bytes"])
    env = os.environ.copy()
    env.update({"OMP_NUM_THREADS":"1", "OMP_THREAD_LIMIT":"1", "OPENBLAS_NUM_THREADS":"1",
                "MKL_NUM_THREADS":"1", "NUMEXPR_NUM_THREADS":"1", "TOKENIZERS_PARALLELISM":"false"})
    try:
        import subprocess
        test = subprocess.run([sys.executable, "-B", str(runtime), "--generate-test"],
                              cwd=str(candidate), env=env, capture_output=True, text=True, timeout=1800, check=False)
        smoke_result = {"returncode": test.returncode, "stdout": test.stdout[-12000:],
                        "stderr": test.stderr[-12000:], "completed_at_utc": utc()}
        atomic_json(JOB_DIR / "runtime_generation_test.json", smoke_result)
        if test.returncode != 0:
            job.stage("RUNTIME_SMOKE_TEST_FAILED", runtime_generation_test=smoke_result,
                      mission_completion_claim=False, certification="NOT_GRANTED")
        else:
            job.stage("RUNTIME_GENERATION_ONE_TOKEN_PASS_QUALITY_UNVALIDATED", runtime_generation_test=smoke_result,
                      mission_completion_claim=False, certification="NOT_GRANTED")
    except Exception as exc:
        smoke_result = {"status": "NOT_COMPLETED", "error": type(exc).__name__ + ":" + str(exc)}
        job.progress.update({"runtime_generation_test": smoke_result, "stage": "RUNTIME_TEST_NOT_COMPLETED",
                             "mission_completion_claim": False, "certification": "NOT_GRANTED"})
        job.save()
    report = write_report(job, candidate, smoke_result)
    job.event("WORKER_FINAL_RECEIPT_WRITTEN", {"report_path": report["report_path"],
               "report_sha256": report["report_sha256"], "stage": job.progress.get("stage"),
               "certification": "NOT_GRANTED", "quality_equivalence": "NOT_ESTABLISHED"})
    job.log("REPORT_WRITTEN " + json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if job.progress.get("stage") == "RUNTIME_GENERATION_ONE_TOKEN_PASS_QUALITY_UNVALIDATED" else 2

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("Use --run")
    try:
        return run()
    except BaseException as exc:
        if "EVENT_CHAIN_INVALID:" in str(exc) or "EVENT_SEQUENCE_INVALID:" in str(exc):
            # Preserve an invalid historical journal verbatim. Resume only from a new,
            # explicitly linked recovery directory after verifying checkpoint hashes.
            print("FAILURE_REPORT_SKIPPED: refusing to mutate invalid historical event journal: "
                  + type(exc).__name__ + ":" + str(exc), file=sys.stderr, flush=True)
            return 2
        try:
            job = Job()
            detail = {"error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()[-10000:]}
            job.progress.update({"stage": "FAILED_OR_BLOCKED", "last_error": detail,
                                 "mission_completion_claim": False, "certification": "NOT_GRANTED"})
            job.save()
            job.event("WORKER_FAILED_OR_BLOCKED", detail)
            job.log("FAILED_OR_BLOCKED " + json.dumps(detail, ensure_ascii=False))
            write_report(job, pathlib.Path(job.progress["candidate_dir"]), error=detail)
        except Exception as report_exc:
            print("FAILURE_REPORT_FAILED:" + repr(report_exc), file=sys.stderr, flush=True)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())

[executed on device: LOUKSNA (98c2b7f6-ee30-4f31-9444-06f7ba58f353)]