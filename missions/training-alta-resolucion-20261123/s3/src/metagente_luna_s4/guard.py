"""Authorization denies by default. A local test is not a sandbox."""
from __future__ import annotations

import re

from metagente_luna_s3.registry import REGISTRY

_CASE = re.compile(r"MGL5-(INF|TEO)-\d{4}")


def require_case_id(case_id: str) -> str:
    if not isinstance(case_id, str) or not _CASE.fullmatch(case_id):
        raise ValueError("unsafe case id")
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
