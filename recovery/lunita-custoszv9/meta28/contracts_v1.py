"""Versioned request/response contracts. No eval, no exec, no implicit trust."""

from __future__ import annotations

import re
import uuid

CONTRACT_VERSION = "1.0"
STATUSES = {
    "SUCCESS",
    "PARTIAL",
    "FAILED",
    "REJECTED",
    "TIMEOUT",
    "UNAVAILABLE",
    "VALIDATION_FAILED",
    "DENIED",
}
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


class ContractError(Exception):
    pass


def _require_uuid(value: object, field: str) -> None:
    if not isinstance(value, str) or _UUID.match(value) is None:
        raise ContractError(f"BAD_{field}")


def validate_request(doc: dict) -> dict:
    required = (
        "request_id",
        "mission_id",
        "caller",
        "component_id",
        "operation",
        "input",
        "constraints",
        "permissions",
        "provenance_required",
        "timeout_ms",
        "contract_version",
    )
    missing = [key for key in required if key not in doc]
    if missing:
        raise ContractError("MISSING_FIELDS:" + ",".join(missing))
    if doc["contract_version"] != CONTRACT_VERSION:
        raise ContractError("BAD_CONTRACT_VERSION")
    if doc["caller"] != "LUNITA":
        raise ContractError("CALLER_IS_NOT_LUNITA")
    _require_uuid(doc["request_id"], "REQUEST_ID")
    _require_uuid(doc["mission_id"], "MISSION_ID")
    if not isinstance(doc["component_id"], str) or not doc["component_id"]:
        raise ContractError("BAD_COMPONENT")
    if not isinstance(doc["operation"], str) or not doc["operation"]:
        raise ContractError("BAD_OPERATION")
    if not isinstance(doc["input"], dict) or not isinstance(doc["constraints"], dict):
        raise ContractError("BAD_OBJECT")
    if not isinstance(doc["permissions"], list):
        raise ContractError("BAD_PERMISSIONS")
    if doc["provenance_required"] is not True:
        raise ContractError("PROVENANCE_REQUIRED")
    timeout = doc["timeout_ms"]
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ContractError("BAD_TIMEOUT")
    if "eval" in doc["operation"] or "exec" in doc["operation"]:
        raise ContractError("ARBITRARY_EXECUTION_FORBIDDEN")
    return doc


def validate_response(doc: dict) -> dict:
    required = (
        "request_id",
        "mission_id",
        "component_id",
        "status",
        "output",
        "evidence",
        "artifacts",
        "warnings",
        "errors",
        "provenance",
        "execution_metadata",
        "contract_version",
    )
    missing = [key for key in required if key not in doc]
    if missing:
        raise ContractError("MISSING_FIELDS:" + ",".join(missing))
    if doc["contract_version"] != CONTRACT_VERSION:
        raise ContractError("BAD_CONTRACT_VERSION")
    if doc["status"] not in STATUSES:
        raise ContractError("BAD_STATUS")
    _require_uuid(doc["request_id"], "REQUEST_ID")
    _require_uuid(doc["mission_id"], "MISSION_ID")
    for key in ("output", "provenance", "execution_metadata"):
        if not isinstance(doc[key], dict):
            raise ContractError(f"BAD_{key}")
    for key in ("evidence", "artifacts", "warnings", "errors"):
        if not isinstance(doc[key], list):
            raise ContractError(f"BAD_{key}")
    if doc["status"] == "SUCCESS" and not doc["evidence"]:
        raise ContractError("SUCCESS_WITHOUT_EVIDENCE")
    return doc


def new_id() -> str:
    return str(uuid.uuid4())
