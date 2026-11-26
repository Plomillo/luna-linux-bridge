"""Authorization denies by default. A local test is not a sandbox."""
from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

from metagente_luna_s3.registry import REGISTRY

_CASE = re.compile(r"MGL5-(INF|TEO)-\d{4}")


@cache
def catalog() -> frozenset[str]:
    payload = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) != 1050:
        raise RuntimeError("case catalog is not the 1000 INF plus 50 TEO ids")
    return frozenset(payload)


def require_case_id(case_id: str) -> str:
    if not isinstance(case_id, str) or not _CASE.fullmatch(case_id):
        raise ValueError("unsafe case id")
    if case_id not in catalog():
        raise ValueError("case id is not in the program catalog")
    return case_id


def authorize(capability_id: str, backend: str = "LOCAL_TEST_ONLY") -> str:
    if capability_id not in REGISTRY:
        raise KeyError(capability_id)
    capability = REGISTRY[capability_id]
    if capability.oracle_id == capability_id:
        raise PermissionError("executor cannot be its own oracle")
    if backend != "LOCAL_TEST_ONLY":
        raise PermissionError("sandbox is not available; production execution is denied")
    if capability.status != "TESTED":
        raise PermissionError("capability is not tested")
    return "AUTHORIZED_LOCAL_TEST_ONLY"
