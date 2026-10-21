#!/usr/bin/env python3
"""D08 reviewed name-specific material for capabilities 333-336. No certification."""
from __future__ import annotations

SPECS = {333: ('ENTROPY_ESTIMATOR', 'ANALYSIS_ENGINE', 'sample method and confidence recorded'),
 334: ('COMPRESSIBILITY_PROBE',
       'BENCHMARK_ENGINE',
       'sample representative chunks before full work'),
 335: ('COMPRESSION_BENCHMARK_ENGINE',
       'BENCHMARK_ENGINE',
       'ratio/time/RAM/CPU/seekability/integrity measured under same corpus'),
 336: ('ZSTD_PROVIDER', 'EXT_LIBRARY_TOOL', 'version/options/dictionary/hash')}


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
