#!/usr/bin/env python3
"""Load Cajita INT8-factor or blockwise signed-INT4-packed safetensors state."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import torch
from safetensors.torch import load_file

SCHEMA = "CAJITA_Q4_BLOCK_PACKED/1.0"

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_model_state(path: str | Path) -> dict[str, torch.Tensor]:
    """Read a normal state dict unchanged, or unpack the governed Q4 sidecar format."""
    path = Path(path)
    state = load_file(str(path), device="cpu")
    sidecar = path.with_name(path.name + ".q4.json")
    if not sidecar.is_file():
        return state
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    if metadata.get("schema") != SCHEMA:
        raise RuntimeError("Q4_PACKING_SCHEMA_MISMATCH")
    if _sha256(path) != metadata.get("candidate_sha256"):
        raise RuntimeError("Q4_PACKED_WEIGHT_SHA256_MISMATCH")
    group_size = int(metadata.get("group_size", 0))
    if group_size < 8 or group_size & (group_size - 1):
        raise RuntimeError("Q4_GROUP_SIZE_INVALID")
    result = dict(state)
    for item in metadata.get("tensors", []) + metadata.get("additional_tensors", []):
        name = item["name"]
        packed_key = item["packed_key"]
        scales_key = item["scales_key"]
        shape = tuple(int(x) for x in item["shape"])
        numel = int(item["numel"])
        if packed_key not in result or scales_key not in result:
            raise RuntimeError("Q4_PACKED_TENSOR_OR_SCALE_MISSING:" + name)
        packed = result.pop(packed_key).reshape(-1).to(torch.uint8)
        scales = result.pop(scales_key).reshape(-1).to(torch.float32)
        if packed.numel() != math.ceil(numel / 2):
            raise RuntimeError("Q4_PACKED_TENSOR_LENGTH_MISMATCH:" + name)
        item_group_size = int(item.get("group_size", group_size))
        if item_group_size < 8 or item_group_size & (item_group_size - 1):
            raise RuntimeError("Q4_ITEM_GROUP_SIZE_INVALID:" + name)
        expected_groups = math.ceil(numel / item_group_size)
        if scales.numel() != expected_groups:
            raise RuntimeError("Q4_SCALE_COUNT_MISMATCH:" + name)
        lo = torch.bitwise_and(packed, 0x0F).to(torch.int16)
        hi = torch.bitwise_right_shift(packed, 4).to(torch.int16)
        codes = torch.stack((lo, hi), dim=1).reshape(-1)[:numel]
        codes = torch.where(codes >= 8, codes - 16, codes).to(torch.float32)
        padded = expected_groups * item_group_size
        if codes.numel() < padded:
            codes = torch.nn.functional.pad(codes, (0, padded - codes.numel()))
        values = codes.reshape(expected_groups, item_group_size) * scales[:, None]
        tensor = values.reshape(-1)[:numel].reshape(shape).contiguous()
        dtype_name = item.get("original_dtype")
        if dtype_name:
            if not hasattr(torch, dtype_name):
                raise RuntimeError("Q4_ORIGINAL_DTYPE_UNSUPPORTED:" + str(dtype_name))
            tensor = tensor.to(dtype=getattr(torch, dtype_name))
        else:
            tensor = tensor.to(dtype=torch.float32)
        result[name] = tensor
    if any(k.startswith("__cajita_q4_packed__.") or k.startswith("__cajita_q4_scales__.") or k.startswith("__cajita_q4_extra_packed__.") or k.startswith("__cajita_q4_extra_scales__.") for k in result):
        raise RuntimeError("Q4_UNCONSUMED_PACKED_TENSORS")
    return result
