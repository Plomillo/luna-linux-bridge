"""A plan is not ready unless the capability exists and the case id is safe."""
from __future__ import annotations

import re

from metagente_luna_s3.registry import REGISTRY

_CASE = re.compile(r"MGL5-(INF|TEO)-\d{4}")


def require_case_id(case_id: str) -> str:
    if not _CASE.fullmatch(case_id):
        raise ValueError("unsafe case id")
    return case_id


def authorize(capability_id: str) -> str:
    if capability_id not in REGISTRY:
        raise KeyError(capability_id)
    return "AUTHORIZED"
