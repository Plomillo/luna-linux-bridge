#!/usr/bin/env python3
"""Versioned resumable SeamlessM4T rank-4 low-rank + INT8 compression lane.
Creates an isolated derived candidate. Source weights and the source model is read-only.
The 50,000,000-byte limit is fail-closed and applies to the complete candidate directory.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import shutil
import sys
import time
import traceback

import torch
from safetensors import safe_open
from safetensors.torch import save_file, load_file

TARGET_BYTES = 50_000_000
RANK = 4
OVERSAMPLE = 8
BLOCK_ROWS = 64
GROUP_TENSORS = 8
SCHEMA = "CUSTOSZ_CAJITA_SEAMLESSM4T_LOW_RANK_INT8_TARGET50/2.0"
HOME = pathlib.Path("/home/diegoignacionorambuenamiranda")
ROOT = HOME / "Proyectos/1. PROYECTOS PRIORITARIOS/5. CUSTOSZ/0. CUSTOSZ  - OPERADOR"
RT = ROOT / "CUSTOSZ_CONTINUITY_V1"
STATE = RT / "state"
JOB_DIR = pathlib.Path(os.environ.get("SEAMLESSM4T_JOB_DIR", str(STATE / "jobs/seamlessm4t_50mb_worker_v2"))).resolve()
STAGING = JOB_DIR / "staging"
REPORTS = STATE / "worker_outputs"
WORKER_LOCK_PATH = STATE / "locks/seamlessm4t_50mb_worker_v2.lock"
MODEL = HOME / "Proyectos/1. PROYECTOS PRIORITARIOS/1. PROYECTO LUNA/2. Cajita de Luna/4. Traductor Inteligente/Traducción general"
INDEX = MODEL / "model.safetensors.index.json"
CONFIG = MODEL / "config.json"
MISSION = ROOT / "MISION1.txt"
AUTH = RT / "operator_authorization.json"
BINDING = RT / "worker_binding_v2.json"
V9 = ROOT / "CUSTOSZV9.pyz"
EXPECTED_MISSION_SHA = "0a36c59d4baf5d547f5217dc9c6db2a58ad9f8f3ea65d88f9b16a0dbe1604f8f"
EXPECTED_CONFIG_SHA = "4b2fa9d863cc3033adaf261e6c3e32ad90347ee2f199a349ba1c77d5e26a605f"
EXPECTED_INDEX_SHA = "79d33aa045308d1a93b11952f2a3e6a647c107b688e5fdf1124c4601626dcdb2"
EXPECTED_V9_SHA = "667ceac7d7e59682292c864777ec3e1c228074716dc5dba17fe150e4d826ccf3"
ASSET_NAMES = ("config.json", "preprocessor_config.json", "added_tokens.json",
               "special_tokens_map.json", "tokenizer_config.json", "sentencepiece.bpe.model", "spm_char_lang38_tc.model")
RUNTIME_SOURCE = r'''#!/usr/bin/env python3
"""Inference smoke runtime for a low-rank, INT8-factor SeamlessM4T v2 candidate."""
from __future__ import annotations
import json, pathlib, time
import torch
from torch import nn
from torch.nn import functional as F
from safetensors.torch import load_file
from transformers import AutoConfig, AutoProcessor, SeamlessM4Tv2Model

ROOT = pathlib.Path(__file__).resolve().parent

class LowRankLinear(nn.Module):
    def __init__(self, base, rank):
        super().__init__()
        self.in_features, self.out_features = base.in_features, base.out_features
        self.weight_u = nn.Parameter(torch.empty((self.out_features, rank), dtype=torch.int8, device="meta"), requires_grad=False)
        self.weight_v = nn.Parameter(torch.empty((rank, self.in_features), dtype=torch.int8, device="meta"), requires_grad=False)
        self.scale_u = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.scale_v = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.bias = base.bias
    def forward(self, x):
        v = self.weight_v.to(dtype=x.dtype) * self.scale_v.to(dtype=x.dtype).unsqueeze(1)
        u = self.weight_u.to(dtype=x.dtype) * self.scale_u.to(dtype=x.dtype).unsqueeze(0)
        return F.linear(F.linear(x, v), u, self.bias)

class LowRankEmbedding(nn.Module):
    def __init__(self, base, rank):
        super().__init__()
        self.num_embeddings, self.embedding_dim = base.num_embeddings, base.embedding_dim
        self.padding_idx = base.padding_idx
        self.max_norm, self.norm_type = base.max_norm, base.norm_type
        self.scale_grad_by_freq, self.sparse = base.scale_grad_by_freq, base.sparse
        self.weight_u = nn.Parameter(torch.empty((self.num_embeddings, rank), dtype=torch.int8, device="meta"), requires_grad=False)
        self.weight_v = nn.Parameter(torch.empty((rank, self.embedding_dim), dtype=torch.int8, device="meta"), requires_grad=False)
        self.scale_u = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.scale_v = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
    def forward(self, ids):
        u = F.embedding(ids, self.weight_u).to(dtype=torch.float32)
        u = u * self.scale_u.to(dtype=u.dtype)
        v = self.weight_v.to(dtype=u.dtype) * self.scale_v.to(dtype=u.dtype).unsqueeze(1)
        return torch.matmul(u, v)

class LowRankConv1d(nn.Module):
    def __init__(self, base, rank):
        super().__init__()
        self.in_channels, self.out_channels = base.in_channels, base.out_channels
        self.kernel_size, self.stride, self.padding = base.kernel_size, base.stride, base.padding
        self.dilation, self.groups, self.padding_mode = base.dilation, base.groups, base.padding_mode
        self.weight_u = nn.Parameter(torch.empty((self.out_channels, rank), dtype=torch.int8, device="meta"), requires_grad=False)
        self.weight_v = nn.Parameter(torch.empty((rank, (self.in_channels // self.groups) * self.kernel_size[0]), dtype=torch.int8, device="meta"), requires_grad=False)
        self.scale_u = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.scale_v = nn.Parameter(torch.empty((rank,), dtype=torch.float32, device="meta"), requires_grad=False)
        self.bias = base.bias
    def forward(self, x):
        u = self.weight_u.to(dtype=x.dtype) * self.scale_u.to(dtype=x.dtype).unsqueeze(0)
        v = self.weight_v.to(dtype=x.dtype) * self.scale_v.to(dtype=x.dtype).unsqueeze(1)
        k = self.kernel_size[0]
        if self.groups == self.in_channels == self.out_channels:
            if u.shape[1] != 1:
                raise RuntimeError("DEPTHWISE_CONV_REQUIRES_RANK_ONE")
            w = u[:, 0].reshape(self.out_channels, 1, 1) * v[0].reshape(1, 1, k)
            return F.conv1d(x, w, self.bias, self.stride, self.padding, self.dilation, self.groups)
        if self.groups != 1:
            raise RuntimeError("UNSUPPORTED_GROUPED_CONV1D:" + str(self.groups))
        v = v.reshape(v.shape[0], self.in_channels, k)
        if self.padding_mode != "zeros":
            pad = self.padding
            if isinstance(pad, str):
                raise RuntimeError("NONZERO_PADDING_MODE_WITH_STRING_PADDING")
            left = right = int(pad[0])
            x = F.pad(x, (left, right), mode=self.padding_mode)
            padding = 0
        else:
            padding = self.padding
        mid = F.conv1d(x, v, None, self.stride, padding, self.dilation, 1)
        u = u.unsqueeze(-1)
        return F.conv1d(mid, u, self.bias, 1, 0, 1, 1)

def load_candidate():
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    cfg = AutoConfig.from_pretrained(ROOT, local_files_only=True)
    if getattr(cfg, "model_type", None) != "seamless_m4t_v2":
        raise RuntimeError("MODEL_IDENTITY_MISMATCH")
    meta = json.loads((ROOT / "compression_metadata.json").read_text(encoding="utf-8"))
    rank = int(meta["rank"])
    with torch.device("meta"):
        model = SeamlessM4Tv2Model(cfg)
    modules = dict(model.named_modules())
    factorized = 0
    for name, module in list(modules.items()):
        if not name:
            continue
        if isinstance(module, nn.Embedding):
            replacement = LowRankEmbedding(module, rank)
        elif isinstance(module, nn.Linear):
            replacement = LowRankLinear(module, rank)
        elif isinstance(module, nn.Conv1d):
            replacement = LowRankConv1d(module, rank)
        else:
            continue
        parent_name, _, leaf = name.rpartition(".")
        setattr(modules[parent_name], leaf, replacement)
        factorized += 1
    if factorized < 300:
        raise RuntimeError("MODEL_MAPPING_INCOMPLETE:" + str(factorized))
    weights = load_file(str(ROOT / "model.safetensors"), device="cpu")
    missing, unexpected = model.load_state_dict(weights, strict=True, assign=True)
    if missing or unexpected:
        raise RuntimeError("STATE_MAPPING_MISMATCH:" + json.dumps({"missing": missing[:20], "unexpected": unexpected[:20]}))
    model.eval()
    return model

def smoke_test():
    t0 = time.monotonic()
    processor = AutoProcessor.from_pretrained(ROOT, local_files_only=True)
    model = load_candidate()
    inputs = processor(text="Hello world.", src_lang="eng", return_tensors="pt")
    with torch.inference_mode():
        generated = model.generate(**inputs, tgt_lang="spa", max_new_tokens=4)
    if not isinstance(generated, torch.Tensor) or generated.ndim != 2 or generated.shape[0] != 1:
        raise RuntimeError("MALFORMED_TEXT_TRANSLATION_OUTPUT")
    decoded = processor.batch_decode(generated, skip_special_tokens=True)
    return {"status": "PASS_TEXT_TRANSLATION_GENERATION", "model_type": model.config.model_type,
            "input_token_count": int(inputs["input_ids"].shape[-1]), "generated_token_count": int(generated.shape[-1]),
            "decoded": decoded[0] if decoded else "", "elapsed_seconds": round(time.monotonic()-t0, 3),
            "quality_equivalence": "NOT_ESTABLISHED_BY_SMOKE_TEST"}
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    if not args.smoke_test:
        parser.error("Use --smoke-test")
    print(json.dumps(smoke_test(), indent=2, ensure_ascii=False))
'''

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()

def sha_file(p):
    h = hashlib.sha256()
    with pathlib.Path(p).open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def atomic_json(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n"); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def file_stat(p):
    s = pathlib.Path(p).stat()
    return {"path": str(p), "bytes": s.st_size, "mtime_ns": s.st_mtime_ns}

class Job:
    def __init__(self):
        JOB_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        STAGING.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.progress_path = JOB_DIR / "progress.json"
        self.journal_path = JOB_DIR / "events.jsonl"
        self.progress = json.loads(self.progress_path.read_text()) if self.progress_path.exists() else {}
        self.prev_event_hash = "0" * 64
        if self.journal_path.exists():
            for line in self.journal_path.read_text().splitlines():
                row = json.loads(line); self.prev_event_hash = row["event_sha256"]
        self.log_path = JOB_DIR / "job.log"

    def log(self, message):
        line = f"[{utc()}] {message}"
        print(line, flush=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n"); f.flush()

    def event(self, event_type, payload):
        row = {"sequence": self._event_count()+1, "timestamp_utc": utc(), "event_type": event_type,
               "mission_sha256": EXPECTED_MISSION_SHA, "previous_event_sha256": self.prev_event_hash,
               "payload": payload}
        row["event_sha256"] = sha_bytes(canonical(row))
        with self.journal_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"); f.flush(); os.fsync(f.fileno())
        self.prev_event_hash = row["event_sha256"]
        return row

    def _event_count(self):
        if not self.journal_path.exists(): return 0
        with self.journal_path.open("r", encoding="utf-8") as f: return sum(1 for _ in f)

    def save_progress(self):
        atomic_json(self.progress_path, self.progress)

def check_authority(job):
    if not MISSION.is_file() or sha_file(MISSION) != EXPECTED_MISSION_SHA:
        raise RuntimeError("MISSION_HASH_MISMATCH")
    if sha_file(CONFIG) != EXPECTED_CONFIG_SHA or sha_file(INDEX) != EXPECTED_INDEX_SHA:
        raise RuntimeError("SOURCE_CONFIG_OR_INDEX_HASH_MISMATCH")
    auth = json.loads(AUTH.read_text())
    bind = json.loads(BINDING.read_text())
    if auth.get("mission_sha256") != EXPECTED_MISSION_SHA or bind.get("mission_sha256") != EXPECTED_MISSION_SHA:
        raise RuntimeError("MISSION_AUTHORIZATION_HASH_MISMATCH")
    if "WRITE_CAJITA_WITH_CHECKPOINTS" not in bind.get("allowed_effects", []):
        raise RuntimeError("SCOPED_CAJITA_WRITE_NOT_AUTHORIZED")
    if bind.get("certification_authority") is not False or bind.get("canonical_promotion_authority") is not False:
        raise RuntimeError("AUTHORITY_BOUNDARY_UNEXPECTED")
    if bind.get("status") != "VALIDATED":
        raise RuntimeError("WORKER_BINDING_NOT_VALIDATED")
    if sha_file(V9) != EXPECTED_V9_SHA:
        raise RuntimeError("PINNED_CUSTOSZ_PACKAGE_HASH_MISMATCH")
    if not MODEL.is_dir() or not (MODEL / "model.safetensors.index.json").is_file():
        raise RuntimeError("SEAMLESSM4T_SOURCE_MODEL_MISSING")
    cfg = json.loads(CONFIG.read_text())
    if cfg.get("model_type") != "seamless_m4t_v2" or "SeamlessM4Tv2Model" not in cfg.get("architectures", []):
        raise RuntimeError("MODEL_IDENTITY_MISMATCH")
    if job.progress.get("candidate_id"):
        if job.progress.get("mission_sha256") != EXPECTED_MISSION_SHA or job.progress.get("rank") != RANK or job.progress.get("target_bytes") != TARGET_BYTES:
            raise RuntimeError("RESUME_STATE_SCOPE_MISMATCH")
    return auth, bind, cfg

def source_shard_inventory(job, weight_map):
    paths = sorted(set(MODEL / name for name in weight_map.values()))
    old = job.progress.get("source_shards", {})
    result = {}
    for p in paths:
        stat = file_stat(p)
        prior = old.get(p.name, {})
        if prior and (prior.get("bytes") != stat["bytes"] or prior.get("mtime_ns") != stat["mtime_ns"]):
            raise RuntimeError("SOURCE_SHARD_MUTATED_DURING_RESUME:" + p.name)
        result[p.name] = {**stat, **({"sha256": prior["sha256"]} if prior.get("sha256") else {})}
    job.progress["source_shards"] = result
    job.progress["source_hashes_complete"] = False
    job.save_progress()
    job.event("SOURCE_SHARD_STAT_INVENTORY_PINNED", {"shards": result, "source_hashes_pending": True})
    return result

def finalize_source_shard_hashes(job, inventory):
    result = {}
    for name, row in inventory.items():
        p = MODEL / name
        before = file_stat(p)
        if before["bytes"] != row["bytes"] or before["mtime_ns"] != row["mtime_ns"]:
            raise RuntimeError("SOURCE_SHARD_CHANGED_DURING_COMPRESSION:" + name)
        digest = sha_file(p)
        after = file_stat(p)
        if before != after:
            raise RuntimeError("SOURCE_SHARD_CHANGED_DURING_HASH:" + name)
        result[name] = {**after, "sha256": digest}
        job.log("SOURCE_HASH_COMPLETE file=" + name + " bytes=" + str(after["bytes"]) + " sha256=" + digest)
    job.progress["source_shards"] = result
    job.progress["source_hashes_complete"] = True
    job.save_progress()
    job.event("SOURCE_HASHES_VERIFIED_POST_FACTORISATION", {"shards": result})
    return result

def copy_candidate_assets(job, candidate):
    candidate.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in ASSET_NAMES:
        src, dst = MODEL / name, candidate / name
        if not src.is_file():
            if name in ("config.json", "preprocessor_config.json", "tokenizer_config.json", "sentencepiece.bpe.model", "spm_char_lang38_tc.model"):
                raise RuntimeError("REQUIRED_ASSET_MISSING:" + name)
            continue
        if dst.exists():
            if sha_file(src) != sha_file(dst):
                raise RuntimeError("CANDIDATE_ASSET_COLLISION:" + name)
        else:
            shutil.copy2(src, dst)
        if sha_file(src) != sha_file(dst):
            raise RuntimeError("ASSET_COPY_HASH_MISMATCH:" + name)
    runtime = candidate / "lowrank_runtime.py"
    runtime_raw = RUNTIME_SOURCE.encode()
    if runtime.exists():
        if runtime.read_bytes() != runtime_raw:
            raise RuntimeError("RUNTIME_COLLISION_NO_OVERWRITE")
    else:
        runtime.write_bytes(runtime_raw)
    job.log("CANDIDATE_ASSETS_READY current_bytes=" + str(directory_bytes(candidate)))

def directory_bytes(p):
    return sum(f.stat().st_size for f in pathlib.Path(p).rglob("*") if f.is_file())

def tensor_lowrank(sl, key, rank, job):
    shape = tuple(sl.get_shape())
    if len(shape) not in (2, 3):
        raise RuntimeError("UNSUPPORTED_FACTOR_TENSOR_RANK:" + key + ":" + str(shape))
    m, n = shape[0], math.prod(shape[1:])
    qdim = min(rank + OVERSAMPLE, m, n)
    r = min(rank, m, n)
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") & ((1 << 63) - 1)
    gen = torch.Generator(device="cpu"); gen.manual_seed(seed)
    omega = torch.randn((n, qdim), generator=gen, dtype=torch.float32) / (qdim ** 0.5)
    y = torch.empty((m, qdim), dtype=torch.float32)
    norm_sq = 0.0
    for start in range(0, m, BLOCK_ROWS):
        end = min(m, start + BLOCK_ROWS)
        w = sl[start:end].to(torch.float32).reshape(end-start, n)
        y[start:end] = w @ omega
        norm_sq += float(torch.sum(w * w).item())
    qmat, _ = torch.linalg.qr(y, mode="reduced")
    bmat = torch.zeros((qdim, n), dtype=torch.float32)
    for start in range(0, m, BLOCK_ROWS):
        end = min(m, start + BLOCK_ROWS)
        w = sl[start:end].to(torch.float32).reshape(end-start, n)
        bmat.add_(qmat[start:end].T @ w)
    ub, sval, vh = torch.linalg.svd(bmat, full_matrices=False)
    sr = sval[:r].clamp_min(0)
    root_s = torch.sqrt(sr)
    a = (qmat @ ub[:, :r]) * root_s.unsqueeze(0)
    b = root_s.unsqueeze(1) * vh[:r, :]
    scale_u = (a.abs().amax(dim=0) / 127.0).clamp_min(1e-12)
    scale_v = (b.abs().amax(dim=1) / 127.0).clamp_min(1e-12)
    uq = torch.round(a / scale_u.unsqueeze(0)).clamp(-127, 127).to(torch.int8).contiguous()
    vq = torch.round(b / scale_v.unsqueeze(1)).clamp(-127, 127).to(torch.int8).contiguous()
    uqf = uq.to(torch.float32) * scale_u.unsqueeze(0)
    vqf = vq.to(torch.float32) * scale_v.unsqueeze(1)
    residual_sq = 0.0
    for start in range(0, m, BLOCK_ROWS):
        end = min(m, start + BLOCK_ROWS)
        w = sl[start:end].to(torch.float32).reshape(end-start, n)
        approx = uqf[start:end] @ vqf
        d = w - approx
        residual_sq += float(torch.sum(d * d).item())
    rel_error = (max(residual_sq, 0.0) / max(norm_sq, 1e-30)) ** 0.5
    lowrank_resid = (max(norm_sq - float(torch.sum(sr * sr).item()), 0.0) / max(norm_sq, 1e-30)) ** 0.5
    base = key[:-len(".weight")]
    out = {
        base + ".weight_u": uq.cpu(),
        base + ".weight_v": vq.cpu(),
        base + ".scale_u": scale_u.cpu().to(torch.float32).contiguous(),
        base + ".scale_v": scale_v.cpu().to(torch.float32).contiguous(),
    }
    return out, {"tensor": key, "shape": list(shape), "rank": r, "factor_dtype": "INT8",
                 "factor_bytes": sum(t.numel() * t.element_size() for t in out.values()),
                 "relative_frobenius_error_after_int8": rel_error,
                 "relative_residual_before_factor_int8": lowrank_resid,
                 "source_norm_sq": norm_sq, "captured_projected_energy": float(torch.sum(sr * sr).item())}

def stage_path(i):
    return STAGING / f"factors_{i:04d}.safetensors"

def run():
    os.environ.update({"OMP_NUM_THREADS":"1","OMP_THREAD_LIMIT":"1","OPENBLAS_NUM_THREADS":"1",
                       "MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1","TOKENIZERS_PARALLELISM":"false",
                       "PYTHONDONTWRITEBYTECODE":"1"})
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    job = Job()
    auth, bind, cfg = check_authority(job)
    index_doc = json.loads(INDEX.read_text())
    weight_map = index_doc["weight_map"]
    keys = sorted(weight_map)
    if not keys:
        raise RuntimeError("WEIGHT_INDEX_EMPTY")
    matrices = []
    for k in keys:
        src = MODEL / weight_map[k]
        with safe_open(str(src), framework="pt", device="cpu") as f:
            shape = tuple(f.get_slice(k).get_shape())
        if len(shape) in (2, 3) and not k.endswith(".weight"):
            raise RuntimeError("UNSUPPORTED_MATRIX_KEY:" + k)
        matrices.append({"key": k, "shard": weight_map[k], "shape": list(shape), "ndim": len(shape)})
    if len(matrices) != 2232 or sum(x["ndim"] == 2 for x in matrices) != 677 or sum(x["ndim"] == 3 for x in matrices) != 187 or sum(x["ndim"] == 1 for x in matrices) != 1368:
        raise RuntimeError("PINNED_SOURCE_TENSOR_INVENTORY_MISMATCH")
    source_hashes = source_shard_inventory(job, weight_map)
    if not job.progress.get("candidate_id"):
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        candidate_id = "SEAMLESSM4T_TRANSLATION_LOWRANK_INT8_RANK4_" + stamp
        candidate = STATE / "cajita_candidates" / candidate_id
        job.progress = {
            "schema": SCHEMA, "job_id": "CAJITA_SEAMLESSM4T_LOWRANK_INT8_TARGET50_RANK4_V2",
            "mission_sha256": EXPECTED_MISSION_SHA, "model_id": "CAJITA_TRADUCCION_SEAMLESSM4T_V2_LARGE",
            "architecture": "SeamlessM4Tv2Model", "source_model_dir": str(MODEL),
            "candidate_id": candidate_id, "candidate_dir": str(candidate), "target_bytes": TARGET_BYTES,
            "rank": RANK, "oversample": OVERSAMPLE, "quantization": "per-factor symmetric signed INT8 with FP32 scales",
            "completed_tensor_count": 0, "completed_groups": [], "tensor_metrics": [],
            "started_at_utc": utc(), "source_config_sha256": EXPECTED_CONFIG_SHA,
            "source_index_sha256": EXPECTED_INDEX_SHA,
            "source_shards": source_hashes, "source_hashes_complete": False,
            "certification": "NOT_GRANTED", "mission_completion_claim": False
        }
        job.event("JOB_CREATED_CHECKPOINTED", {"candidate_id": candidate_id, "rank": RANK, "target_bytes": TARGET_BYTES,
                   "source_model_id": job.progress["model_id"], "source_inventory": "HASHED_POST_FACTORIZATION"})
        job.save_progress()
    candidate = pathlib.Path(job.progress["candidate_dir"])
    copy_candidate_assets(job, candidate)
    # Resume only from complete, individually hashed staging groups.
    done = int(job.progress.get("completed_tensor_count", 0))
    if done % GROUP_TENSORS != 0 and done != len(keys):
        raise RuntimeError("RESUME_CHECKPOINT_NOT_GROUP_ALIGNED")
    staged_tensors = {}
    for rec in job.progress.get("completed_groups", []):
        p = STAGING / rec["file"]
        if not p.is_file() or sha_file(p) != rec["sha256"]:
            raise RuntimeError("STAGING_CHECKPOINT_HASH_MISMATCH:" + str(p))
        staged_tensors.update(load_file(str(p), device="cpu"))
    if done > len(keys) or (done and not staged_tensors):
        raise RuntimeError("RESUME_PROGRESS_INCONSISTENT")
    batch, batch_metrics = {}, []
    group_id = len(job.progress.get("completed_groups", []))
    started = time.monotonic()
    job.log(f"REAL_COMPRESSION_START model=SeamlessM4T rank={RANK} factors=INT8 target_bytes={TARGET_BYTES} tensors={len(keys)} completed={done}")
    job.event("REAL_COMPRESSION_STARTED", {"candidate_id": job.progress["candidate_id"], "completed_tensor_count": done,
                   "source_shards": source_hashes, "resource_policy": {"block_rows": BLOCK_ROWS, "torch_threads": 1}})
    for i in range(done, len(keys)):
        item = matrices[i]; key = item["key"]; shard = MODEL / item["shard"]
        with safe_open(str(shard), framework="pt", device="cpu") as sf:
            sl = sf.get_slice(key)
            if item["ndim"] in (2, 3):
                factor_tensors, metric = tensor_lowrank(sl, key, RANK, job)
                batch.update(factor_tensors); batch_metrics.append(metric)
            elif item["ndim"] == 1:
                batch[key] = sl[:].contiguous()
            else:
                raise RuntimeError("UNSUPPORTED_TENSOR_RANK:" + key)
        current_count = i + 1
        if current_count % GROUP_TENSORS == 0 or current_count == len(keys):
            p = stage_path(group_id)
            temp = p.with_suffix(".safetensors.tmp")
            save_file(batch, str(temp), metadata={"schema": SCHEMA, "mission_sha256": EXPECTED_MISSION_SHA,
                                                  "source_index_sha256": EXPECTED_INDEX_SHA, "group": str(group_id)})
            os.replace(temp, p)
            group_rec = {"file": p.name, "sha256": sha_file(p), "bytes": p.stat().st_size,
                         "completed_tensor_count": current_count}
            job.progress.setdefault("completed_groups", []).append(group_rec)
            job.progress["completed_tensor_count"] = current_count
            job.progress["tensor_metrics"].extend(batch_metrics)
            job.progress["last_progress_utc"] = utc()
            job.progress["stage"] = "FACTORIZE_INT8_RUNNING" if current_count < len(keys) else "FACTORIZE_INT8_COMPLETE"
            job.save_progress()
            job.event("TENSOR_GROUP_CHECKPOINTED", {"group": group_id, "completed_tensor_count": current_count,
                         "group_bytes": p.stat().st_size, "group_sha256": group_rec["sha256"],
                         "model_tensor": key, "elapsed_seconds": round(time.monotonic()-started, 2)})
            job.log(f"CHECKPOINT tensors={current_count}/{len(keys)} groups={group_id+1} staged_bytes={sum(x['bytes'] for x in job.progress['completed_groups'])} elapsed_s={time.monotonic()-started:.1f} last={key}")
            batch, batch_metrics = {}, []
            group_id += 1
    source_hashes = finalize_source_shard_hashes(job, source_hashes)
    # A versioned checkpoint exists before candidate assembly; merge only hash-verified chunks.
    output_weights = {}
    for rec in job.progress["completed_groups"]:
        p = STAGING / rec["file"]
        if sha_file(p) != rec["sha256"]:
            raise RuntimeError("STAGING_CHECKPOINT_CHANGED_BEFORE_ASSEMBLY")
        output_weights.update(load_file(str(p), device="cpu"))
    temp_weights = JOB_DIR / "model.target50.build.safetensors"
    if temp_weights.exists():
        if job.progress.get("assembly_sha256") and sha_file(temp_weights) == job.progress["assembly_sha256"]:
            pass
        else:
            temp_weights.unlink()
    if not temp_weights.exists():
        save_file(output_weights, str(temp_weights), metadata={
            "format": "pt", "source_model_id": job.progress["model_id"], "source_config_sha256": EXPECTED_CONFIG_SHA,
            "method": "randomized_truncated_svd_rank1_symmetric_int8_factors", "rank": str(RANK),
            "mission_sha256": EXPECTED_MISSION_SHA})
    temp_size = temp_weights.stat().st_size
    current_candidate_bytes = directory_bytes(candidate)
    if current_candidate_bytes + temp_size > TARGET_BYTES:
        job.progress.update({"stage": "BLOCKED_HARD_SIZE_GATE", "candidate_bytes_before_weights": current_candidate_bytes,
                             "weight_file_bytes": temp_size, "would_exceed_target_by_bytes": current_candidate_bytes+temp_size-TARGET_BYTES,
                             "mission_completion_claim": False, "certification": "NOT_GRANTED"})
        job.save_progress()
        job.event("HARD_SIZE_GATE_BLOCKED", {"candidate_bytes": current_candidate_bytes, "weight_file_bytes": temp_size, "target_bytes": TARGET_BYTES})
        raise RuntimeError("HARD_SIZE_GATE:refusing to publish an over-limit candidate")
    os.replace(temp_weights, candidate / "model.safetensors")
    matrices_metrics = job.progress.get("tensor_metrics", [])
    meta = {"schema": SCHEMA, "model_id": job.progress["model_id"], "model_type": cfg.get("model_type"),
            "architecture": "SeamlessM4Tv2Model", "source_model_identity_preserved": True,
            "source_config_sha256": EXPECTED_CONFIG_SHA, "source_index_sha256": EXPECTED_INDEX_SHA,
            "source_shard_sha256": {k:v["sha256"] for k,v in source_hashes.items()},
            "mission_sha256": EXPECTED_MISSION_SHA,
            "method": "randomized_truncated_SVD_low_rank_factorization_plus_symmetric_INT8_factor_quantization",
            "rank": RANK, "oversample": OVERSAMPLE, "target_bytes": TARGET_BYTES,
            "hard_cap_behavior": "candidate is never published if final measured bytes exceed TARGET_BYTES; no padding",
            "weight_count_source": len(keys), "matrix_count_factorized": sum(1 for x in matrices if x["ndim"] in (2, 3)),
            "vector_count_preserved": sum(1 for x in matrices if x["ndim"] == 1),
            "runtime": "lowrank_runtime.py", "quality_equivalence": "NOT_ESTABLISHED",
            "certification": "NOT_GRANTED", "created_at_utc": utc()}
    atomic_json(candidate / "compression_metadata.json", meta)
    final_bytes = directory_bytes(candidate)
    if final_bytes > TARGET_BYTES:
        # Preserve evidence but refuse to report a usable target candidate.
        (candidate / "compression_metadata.json").unlink(missing_ok=True)
        job.progress.update({"stage": "BLOCKED_HARD_SIZE_GATE_POSTCHECK", "candidate_bytes": final_bytes,
                             "target_bytes": TARGET_BYTES, "mission_completion_claim": False, "certification": "NOT_GRANTED"})
        job.save_progress()
        job.event("HARD_SIZE_GATE_POSTCHECK_BLOCKED", {"candidate_bytes": final_bytes, "target_bytes": TARGET_BYTES})
        raise RuntimeError("HARD_SIZE_GATE_POSTCHECK")
    job.progress.update({"stage": "CANDIDATE_ASSEMBLED_AWAITING_RUNTIME_TEST", "candidate_bytes": final_bytes,
                         "model_safetensors_bytes": (candidate / "model.safetensors").stat().st_size,
                         "model_safetensors_sha256": sha_file(candidate / "model.safetensors"),
                         "candidate_sha256_manifest": None, "mission_completion_claim": False, "certification": "NOT_GRANTED"})
    job.save_progress()
    job.event("CANDIDATE_ASSEMBLED_UNDER_HARD_CAP", {"candidate_dir": str(candidate), "candidate_bytes": final_bytes,
                 "target_bytes": TARGET_BYTES, "model_safetensors_sha256": job.progress["model_safetensors_sha256"]})
    job.log(f"CANDIDATE_ASSEMBLED bytes={final_bytes}/{TARGET_BYTES} model_weights={temp_size} candidate={candidate}")
    # Validate the real local runtime, not merely the artifact's presence.
    job.progress["stage"] = "RUNTIME_SMOKE_TEST_RUNNING"; job.save_progress()
    import subprocess
    env = os.environ.copy(); env.update({"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","TOKENIZERS_PARALLELISM":"false"})
    cmd = [sys.executable, "-B", str(candidate / "lowrank_runtime.py"), "--smoke-test"]
    probe = subprocess.run(cmd, cwd=str(candidate), env=env, capture_output=True, text=True, timeout=600, check=False)
    smoke = {"returncode": probe.returncode, "stdout": probe.stdout[-8000:], "stderr": probe.stderr[-8000:],
             "command": cmd, "completed_at_utc": utc()}
    atomic_json(JOB_DIR / "runtime_smoke_test.json", smoke)
    job.progress["runtime_smoke_test"] = smoke
    if probe.returncode != 0:
        job.progress.update({"stage": "RUNTIME_SMOKE_TEST_FAILED", "mission_completion_claim": False, "certification": "NOT_GRANTED"})
        job.save_progress()
        job.event("RUNTIME_SMOKE_TEST_FAILED", smoke)
        raise RuntimeError("RUNTIME_SMOKE_TEST_FAILED:" + probe.stderr[-1000:])
    job.progress.update({"stage": "SIZE_TARGET_MET_RUNTIME_SMOKE_PASS_QUALITY_UNVALIDATED",
                         "runtime_smoke_status": "PASS", "completed_at_utc": utc(),
                         "candidate_bytes": directory_bytes(candidate), "mission_completion_claim": False,
                         "certification": "NOT_GRANTED",
                         "quality_gate": "PENDING_BENCHMARKS_AND_FUNCTIONAL_REGRESSION"})
    job.save_progress()
    # Seal a compact completion receipt outside the payload; never promote to canonical.
    receipt = {"schema": SCHEMA, "status": job.progress["stage"], "mission_sha256": EXPECTED_MISSION_SHA,
               "candidate_id": job.progress["candidate_id"], "candidate_dir": str(candidate),
               "candidate_bytes": directory_bytes(candidate), "target_bytes": TARGET_BYTES,
               "candidate_file_inventory": [{"path": str(p.relative_to(candidate)), "bytes": p.stat().st_size, "sha256": sha_file(p)}
                                             for p in sorted(candidate.rglob("*")) if p.is_file()],
               "compression_metrics": matrices_metrics,
               "runtime_smoke_test": smoke, "source_model_modified": False,
               "mission_completion_claim": False, "certification": "NOT_GRANTED",
               "quality_equivalence": "NOT_ESTABLISHED", "timestamp_utc": utc()}
    report = REPORTS / ("CAJITA_SEAMLESSM4T_LOW_RANK_TARGET50_" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
    receipt["report_path"] = str(report)
    atomic_json(report, receipt)
    report_hash = sha_file(report)
    job.progress.update({"report_path": str(report), "report_sha256": report_hash})
    job.save_progress()
    job.event("RUNTIME_SMOKE_PASS_SIZE_TARGET_MET", {"candidate_id": job.progress["candidate_id"], "candidate_bytes": receipt["candidate_bytes"],
                 "target_bytes": TARGET_BYTES, "report_path": str(report), "report_sha256": report_hash,
                 "mission_completion_claim": False, "certification": "NOT_GRANTED"})
    job.log(f"TARGET50_RESULT status={job.progress['stage']} bytes={receipt['candidate_bytes']} target={TARGET_BYTES} report={report} report_sha256={report_hash}")
    return receipt

_WORKER_LOCK_FD = None
def acquire_worker_lock():
    global _WORKER_LOCK_FD
    WORKER_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(str(WORKER_LOCK_PATH), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise RuntimeError("WORKER_SINGLETON_LOCK_HELD")
    _WORKER_LOCK_FD = fd

def main():
    try:
        acquire_worker_lock()
        result = run()
        print(json.dumps({"status": result["status"], "candidate_dir": result["candidate_dir"],
                          "candidate_bytes": result["candidate_bytes"], "target_bytes": result["target_bytes"],
                          "report_path": result.get("report_path")}, ensure_ascii=False))
        return 0
    except Exception as exc:
        try:
            job = Job()
            job.progress.update({"last_error": type(exc).__name__ + ": " + str(exc),
                                 "last_error_at_utc": utc(), "mission_completion_claim": False, "certification": "NOT_GRANTED"})
            if job.progress.get("stage") not in ("SIZE_TARGET_MET_RUNTIME_SMOKE_PASS_QUALITY_UNVALIDATED",):
                job.progress["stage"] = job.progress.get("stage", "FAILED_OR_BLOCKED")
            job.save_progress()
            job.event("JOB_ERROR_OR_BLOCKER", {"type": type(exc).__name__, "error": str(exc)[:2000],
                         "traceback": traceback.format_exc()[-5000:]})
            job.log("JOB_ERROR " + type(exc).__name__ + ": " + str(exc))
        except Exception:
            traceback.print_exc()
        return 2

if __name__ == "__main__":
    raise SystemExit(main())

[executed on device: LOUKSNA (98c2b7f6-ee30-4f31-9444-06f7ba58f353)]