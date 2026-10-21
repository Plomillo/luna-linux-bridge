#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 393-396. No certification."""
from __future__ import annotations

SPECS = {393: ('ANDROID_NATIVE_MODEL_RUNTIME',
       'MODEL_RUNTIME',
       'model runtime selected by device capability and benchmarks'),
 394: ('ONNX_RUNTIME_MOBILE',
       'EXT_LIBRARY_RUNTIME',
       'version/EPs/model opset/device compatibility'),
 395: ('EXECUTORCH_PROVIDER', 'EXT_LIBRARY_RUNTIME', 'version/backend/model export identity'),
 396: ('GGUF_ANDROID_PROVIDER',
       'MODEL_RUNTIME_PROVIDER',
       'runtime/version/model hash/quantization/device benchmark')}


def _bind(ctx, name: str, kind: str, hardening: str):
    if not isinstance(ctx, dict):
        return {"error": "missing_ctx"}
    claimed = ctx.get("canonical_name")
    if claimed not in (None, name):
        raise ValueError(f"identity mismatch for {name}")
    return {
        "binding": name.lower(),
        "kind": kind,
        "hardening": hardening,
        "status": "bound",
    }


def run(capability_id: int, ctx=None):
    if capability_id not in SPECS:
        raise ValueError(f"unregistered capability {capability_id}")
    name, kind, hardening = SPECS[capability_id]
    result = _bind(ctx, name, kind, hardening)
    result["canonical_name"] = name
    result["capability_id"] = capability_id
    result["certification_granted"] = False
    return result


FUNCS = {
    cid: (spec[0], (lambda ctx, cid=cid: run(cid, ctx)))
    for cid, spec in SPECS.items()
}
