#!/usr/bin/env python3
"""Authenticated, source-bound remote execution client for the Cajita runtime.

The client is opt-in (LOUKSNAPG_REMOTE_MODE=required). It never falls back to
the compact local weights after a remote identity, transport, or task failure.
Only the source identities declared in CAJITA_REMOTE_MODEL_POLICY.json are accepted.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_SCHEMA = "LOUKSNAPG_REMOTE_MODEL_POLICY/1.0"
IDENTITY_SCHEMA = "LOUKSNAPG_REMOTE_MODEL_IDENTITY/1.0"
SIGNED_IDENTITY_SCHEMA = "LOUKSNAPG_SIGNED_REMOTE_IDENTITY/1.0"
REQUEST_SCHEMA = "LOUKSNAPG_REMOTE_REQUEST/1.0"
RESPONSE_SCHEMA = "LOUKSNAPG_REMOTE_RESPONSE/1.0"
HEX_256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_AUDIO_BYTES = 32 * 1024 * 1024
MAX_REQUEST_BYTES = 48 * 1024 * 1024
MAX_RESPONSE_BYTES = 1 * 1024 * 1024


class RemoteExecutionError(RuntimeError):
    """A remote request was not executed or could not be independently verified."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_utc(value: str) -> float:
    if not isinstance(value, str):
        raise RemoteExecutionError("REMOTE_TIMESTAMP_MISSING")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RemoteExecutionError("REMOTE_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None:
        raise RemoteExecutionError("REMOTE_TIMESTAMP_WITHOUT_TIMEZONE")
    return parsed.timestamp()


def load_policy(root: Path) -> dict:
    path = Path(root) / "CAJITA_REMOTE_MODEL_POLICY.json"
    if path.is_symlink() or not path.is_file():
        raise RemoteExecutionError("REMOTE_MODEL_POLICY_MISSING_OR_UNSAFE")
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RemoteExecutionError("REMOTE_MODEL_POLICY_INVALID_JSON") from exc
    if not isinstance(policy, dict) or policy.get("schema") != POLICY_SCHEMA:
        raise RemoteExecutionError("REMOTE_MODEL_POLICY_SCHEMA_MISMATCH")
    domains = policy.get("domains")
    if not isinstance(domains, dict) or not domains:
        raise RemoteExecutionError("REMOTE_MODEL_POLICY_DOMAINS_MISSING")
    for domain_id, spec in domains.items():
        if not isinstance(domain_id, str) or not isinstance(spec, dict):
            raise RemoteExecutionError("REMOTE_MODEL_POLICY_ENTRY_INVALID")
        if spec.get("source_repo") != spec.get("model_id"):
            raise RemoteExecutionError("REMOTE_MODEL_REPOSITORY_ID_MISMATCH:" + domain_id)
        if not REVISION_RE.fullmatch(str(spec.get("source_revision", ""))):
            raise RemoteExecutionError("REMOTE_MODEL_REVISION_NOT_IMMUTABLE:" + domain_id)
        for key in ("source_config_sha256",):
            if not HEX_256_RE.fullmatch(str(spec.get(key, ""))):
                raise RemoteExecutionError("REMOTE_MODEL_SOURCE_HASH_INVALID:" + domain_id + ":" + key)
        index_sha = spec.get("source_index_sha256")
        if index_sha is not None and not HEX_256_RE.fullmatch(str(index_sha)):
            raise RemoteExecutionError("REMOTE_MODEL_SOURCE_HASH_INVALID:" + domain_id + ":source_index_sha256")
        files = spec.get("weight_files")
        if not isinstance(files, list) or not files:
            raise RemoteExecutionError("REMOTE_MODEL_WEIGHT_FILES_MISSING:" + domain_id)
        seen = set()
        for row in files:
            if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                raise RemoteExecutionError("REMOTE_MODEL_WEIGHT_ROW_INVALID:" + domain_id)
            rel = Path(row["path"])
            if rel.is_absolute() or ".." in rel.parts or rel.as_posix() != row["path"] or row["path"] in seen:
                raise RemoteExecutionError("REMOTE_MODEL_WEIGHT_PATH_UNSAFE:" + domain_id)
            seen.add(row["path"])
            size = row.get("bytes")
            if size is not None and (isinstance(size, bool) or not isinstance(size, int) or size <= 0):
                raise RemoteExecutionError("REMOTE_MODEL_WEIGHT_SIZE_INVALID:" + domain_id)
            digest = row.get("sha256")
            if digest is not None and not HEX_256_RE.fullmatch(str(digest)):
                raise RemoteExecutionError("REMOTE_MODEL_WEIGHT_HASH_INVALID:" + domain_id)
        if not all(isinstance(spec.get(k), str) and spec[k] for k in ("url_env", "key_env", "key_id", "operation")):
            raise RemoteExecutionError("REMOTE_MODEL_ENDPOINT_BINDING_INCOMPLETE:" + domain_id)
    return policy


def _key_from_environment(spec: dict) -> bytes:
    name = spec["key_env"]
    raw = os.environ.get(name, "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", raw):
        raise RemoteExecutionError("REMOTE_HMAC_KEY_MISSING_OR_INVALID:" + name)
    key = bytes.fromhex(raw)
    if len(key) != 32:
        raise RemoteExecutionError("REMOTE_HMAC_KEY_LENGTH_INVALID")
    return key


def _endpoint_origin(value: str) -> str:
    try:
        parts = urllib.parse.urlsplit(value)
        port = parts.port
    except ValueError as exc:
        raise RemoteExecutionError("REMOTE_ENDPOINT_INVALID") from exc
    if parts.username or parts.password or parts.query or parts.fragment:
        raise RemoteExecutionError("REMOTE_ENDPOINT_CONTAINS_CREDENTIALS_OR_QUERY")
    if parts.path not in ("", "/") or not parts.hostname:
        raise RemoteExecutionError("REMOTE_ENDPOINT_MUST_BE_ORIGIN_ONLY")
    if parts.scheme == "https":
        pass
    elif parts.scheme == "http":
        host = parts.hostname.lower()
        is_loopback = host == "localhost"
        try:
            is_loopback = is_loopback or ipaddress.ip_address(host).is_loopback
        except ValueError:
            pass
        if not is_loopback:
            raise RemoteExecutionError("REMOTE_ENDPOINT_REQUIRES_HTTPS")
    else:
        raise RemoteExecutionError("REMOTE_ENDPOINT_SCHEME_NOT_ALLOWED")
    netloc = parts.hostname.lower()
    if port is not None:
        netloc += ":" + str(port)
    return parts.scheme + "://" + netloc


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http_json(url: str, *, method: str, payload: dict | None, headers: dict,
               timeout_seconds: int, response_limit: int) -> dict:
    data = None if payload is None else canonical_json(payload)
    if data is not None and len(data) > MAX_REQUEST_BYTES:
        raise RemoteExecutionError("REMOTE_REQUEST_SIZE_LIMIT_EXCEEDED")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=max(1, min(int(timeout_seconds), 1800))) as response:
            if response.status != 200:
                raise RemoteExecutionError("REMOTE_HTTP_STATUS:" + str(response.status))
            raw = response.read(response_limit + 1)
    except urllib.error.HTTPError as exc:
        raise RemoteExecutionError("REMOTE_HTTP_STATUS:" + str(exc.code)) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RemoteExecutionError("REMOTE_TRANSPORT_FAILED:" + type(exc).__name__) from exc
    if len(raw) > response_limit:
        raise RemoteExecutionError("REMOTE_RESPONSE_SIZE_LIMIT_EXCEEDED")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RemoteExecutionError("REMOTE_RESPONSE_INVALID_JSON") from exc
    if not isinstance(value, dict):
        raise RemoteExecutionError("REMOTE_RESPONSE_ROOT_NOT_OBJECT")
    return value


def _verify_signature(envelope: dict, key: bytes, *, schema: str, max_age_seconds: int,
                      clock_skew_seconds: int) -> dict:
    if envelope.get("schema") != schema:
        raise RemoteExecutionError("REMOTE_SIGNED_ENVELOPE_SCHEMA_MISMATCH")
    signature = envelope.get("signature")
    if not isinstance(signature, str) or not HEX_256_RE.fullmatch(signature):
        raise RemoteExecutionError("REMOTE_SIGNATURE_MISSING_OR_INVALID")
    issued_at = envelope.get("issued_at_utc")
    delta = abs(time.time() - parse_utc(issued_at))
    if delta > max_age_seconds + clock_skew_seconds:
        raise RemoteExecutionError("REMOTE_SIGNED_ENVELOPE_EXPIRED")
    unsigned = {k: v for k, v in envelope.items() if k != "signature"}
    expected = hmac.new(key, canonical_json(unsigned), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise RemoteExecutionError("REMOTE_SIGNATURE_VERIFICATION_FAILED")
    return unsigned


def verify_identity(identity: dict, spec: dict, domain_id: str) -> str:
    if identity.get("schema") != IDENTITY_SCHEMA or identity.get("model_loaded") is not True:
        raise RemoteExecutionError("REMOTE_MODEL_NOT_LOADED_OR_IDENTITY_SCHEMA_INVALID")
    if not isinstance(identity.get("gateway_version"), str) or not identity["gateway_version"]:
        raise RemoteExecutionError("REMOTE_GATEWAY_VERSION_MISSING")
    if not HEX_256_RE.fullmatch(str(identity.get("gateway_code_sha256", ""))):
        raise RemoteExecutionError("REMOTE_GATEWAY_CODE_HASH_MISSING")
    if not REVISION_RE.fullmatch(str(identity.get("gateway_source_commit", ""))):
        raise RemoteExecutionError("REMOTE_GATEWAY_SOURCE_COMMIT_MISSING_OR_INVALID")
    fields = (
        "domain_id", "model_id", "source_repo", "source_revision",
        "source_config_sha256", "source_index_sha256",
    )
    expected = {
        "domain_id": domain_id,
        "model_id": spec["model_id"],
        "source_repo": spec["source_repo"],
        "source_revision": spec["source_revision"],
        "source_config_sha256": spec["source_config_sha256"],
        "source_index_sha256": spec.get("source_index_sha256"),
    }
    for field in fields:
        if identity.get(field) != expected[field]:
            raise RemoteExecutionError("REMOTE_SOURCE_IDENTITY_MISMATCH:" + field)
    files = identity.get("weight_files")
    if not isinstance(files, list):
        raise RemoteExecutionError("REMOTE_WEIGHT_INVENTORY_MISSING")
    actual_map = {}
    for item in files:
        if not isinstance(item, dict):
            raise RemoteExecutionError("REMOTE_WEIGHT_INVENTORY_ROW_INVALID")
        path = item.get("path")
        if not isinstance(path, str) or path in actual_map or not HEX_256_RE.fullmatch(str(item.get("sha256", ""))):
            raise RemoteExecutionError("REMOTE_WEIGHT_INVENTORY_ROW_INVALID")
        size = item.get("bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise RemoteExecutionError("REMOTE_WEIGHT_INVENTORY_SIZE_INVALID")
        actual_map[path] = {"path": path, "bytes": size, "sha256": item["sha256"]}
    expected_rows = spec["weight_files"]
    expected_map = {item["path"]: item for item in expected_rows}
    if set(actual_map) != set(expected_map):
        raise RemoteExecutionError("REMOTE_WEIGHT_INVENTORY_PATH_SET_MISMATCH")
    normalized_rows = []
    for path in sorted(expected_map, key=lambda item: item.encode("utf-8")):
        wanted, actual = expected_map[path], actual_map[path]
        if wanted.get("bytes") is not None and wanted["bytes"] != actual["bytes"]:
            raise RemoteExecutionError("REMOTE_WEIGHT_SIZE_MISMATCH:" + path)
        if wanted.get("sha256") is not None and not hmac.compare_digest(wanted["sha256"], actual["sha256"]):
            raise RemoteExecutionError("REMOTE_WEIGHT_SHA256_MISMATCH:" + path)
        normalized_rows.append(actual)
    inventory_sha = sha256_bytes(canonical_json(normalized_rows))
    if identity.get("weight_inventory_sha256") != inventory_sha:
        raise RemoteExecutionError("REMOTE_WEIGHT_INVENTORY_DIGEST_MISMATCH")
    return sha256_bytes(canonical_json(identity))


def _prepare_input(row: dict) -> dict:
    data = dict(row.get("input", {}))
    domain = row.get("domain_id")
    if domain == "D03_TRANSCRIPCION":
        audio_path = data.pop("audio_path", None)
        if not isinstance(audio_path, str) or not audio_path:
            raise RemoteExecutionError("REMOTE_AUDIO_PATH_REQUIRED")
        path = Path(audio_path)
        if path.is_symlink() or not path.is_file():
            raise RemoteExecutionError("REMOTE_AUDIO_PATH_MISSING_OR_SYMLINK")
        size = path.stat().st_size
        if not 1 <= size <= MAX_AUDIO_BYTES:
            raise RemoteExecutionError("REMOTE_AUDIO_SIZE_OUT_OF_RANGE")
        audio = path.read_bytes()
        if len(audio) != size:
            raise RemoteExecutionError("REMOTE_AUDIO_SIZE_CHANGED_DURING_READ")
        data["audio_base64"] = base64.b64encode(audio).decode("ascii")
        data["audio_sha256"] = sha256_bytes(audio)
    elif domain in ("D01_CEREBRO", "D06_SISTEMA_INTELIGENTE"):
        if not isinstance(data.get("prompt"), str) or not data["prompt"].strip():
            raise RemoteExecutionError("REMOTE_PROMPT_REQUIRED")
    elif domain == "D04_TRADUCTOR_INTELIGENTE":
        if not isinstance(data.get("text"), str) or not data["text"].strip():
            raise RemoteExecutionError("REMOTE_TRANSLATION_TEXT_REQUIRED")
        if not isinstance(data.get("src_lang"), str) or not isinstance(data.get("tgt_lang"), str):
            raise RemoteExecutionError("REMOTE_TRANSLATION_LANGUAGE_REQUIRED")
    else:
        raise RemoteExecutionError("REMOTE_DOMAIN_NOT_SUPPORTED:" + str(domain))
    return data


def execute_remote_task(row: dict, root: Path) -> dict:
    """Run one task remotely and return signed provenance, never a quality verdict."""
    domain_id = row.get("domain_id")
    try:
        policy = load_policy(root)
        spec = policy["domains"].get(domain_id)
        if spec is None:
            raise RemoteExecutionError("REMOTE_DOMAIN_NOT_REGISTERED:" + str(domain_id))
        if row.get("operation") != spec["operation"]:
            raise RemoteExecutionError("REMOTE_OPERATION_NOT_REGISTERED")
        endpoint_value = os.environ.get(spec["url_env"], "").strip()
        if not endpoint_value:
            raise RemoteExecutionError("REMOTE_ENDPOINT_NOT_CONFIGURED:" + spec["url_env"])
        origin = _endpoint_origin(endpoint_value)
        key = _key_from_environment(spec)
        identity_envelope = _http_json(
            origin + "/v1/identity", method="GET", payload=None,
            headers={"Accept": "application/json", "Cache-Control": "no-cache"},
            timeout_seconds=15, response_limit=MAX_RESPONSE_BYTES,
        )
        identity_unsigned = _verify_signature(
            identity_envelope, key, schema=SIGNED_IDENTITY_SCHEMA,
            max_age_seconds=int(policy.get("identity_max_age_seconds", 300)),
            clock_skew_seconds=int(policy.get("request_clock_skew_seconds", 120)),
        )
        identity = identity_unsigned.get("identity")
        if not isinstance(identity, dict) or identity_envelope.get("key_id") != spec["key_id"]:
            raise RemoteExecutionError("REMOTE_IDENTITY_KEY_OR_PAYLOAD_MISMATCH")
        identity_sha = verify_identity(identity, spec, domain_id)
        limits = dict(row.get("limits", {}))
        max_tokens = limits.get("max_new_tokens", 32)
        timeout = limits.get("timeout_seconds", 600)
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= int(policy["max_new_tokens"]):
            raise RemoteExecutionError("REMOTE_TOKEN_LIMIT_INVALID")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= int(policy["max_timeout_seconds"]):
            raise RemoteExecutionError("REMOTE_TIMEOUT_LIMIT_INVALID")
        request_payload = {
            "schema": REQUEST_SCHEMA,
            "request_id": str(uuid.uuid4()),
            "nonce": secrets.token_hex(24),
            "issued_at_utc": utc_now(),
            "key_id": spec["key_id"],
            "domain_id": domain_id,
            "operation": row["operation"],
            "model_id": spec["model_id"],
            "source_revision": spec["source_revision"],
            "identity_sha256": identity_sha,
            "input": _prepare_input(row),
            "limits": {"max_new_tokens": max_tokens, "timeout_seconds": timeout},
        }
        request_sha = sha256_bytes(canonical_json(request_payload))
        signature = hmac.new(key, canonical_json(request_payload), hashlib.sha256).hexdigest()
        response_envelope = _http_json(
            origin + "/v1/infer", method="POST", payload=request_payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Louksnapg-Key-Id": spec["key_id"],
                "X-Louksnapg-Request-Signature": signature,
            },
            timeout_seconds=timeout, response_limit=int(policy.get("max_response_bytes", MAX_RESPONSE_BYTES)),
        )
        response = _verify_signature(
            response_envelope, key, schema=RESPONSE_SCHEMA,
            max_age_seconds=120, clock_skew_seconds=int(policy.get("request_clock_skew_seconds", 120)),
        )
        comparisons = {
            "request_id": request_payload["request_id"],
            "request_sha256": request_sha,
            "identity_sha256": identity_sha,
            "domain_id": domain_id,
            "model_id": spec["model_id"],
            "source_revision": spec["source_revision"],
            "status": "PASS_REMOTE_EXECUTION",
        }
        for field, expected_value in comparisons.items():
            if response.get(field) != expected_value:
                raise RemoteExecutionError("REMOTE_RESPONSE_BINDING_MISMATCH:" + field)
        output_text = response.get("output_text")
        token_count = response.get("generated_token_count")
        if not isinstance(output_text, str) or not output_text.strip() or len(output_text) > int(policy["max_text_characters"]):
            raise RemoteExecutionError("REMOTE_OUTPUT_TEXT_INVALID")
        if isinstance(token_count, bool) or not isinstance(token_count, int) or not 1 <= token_count <= max_tokens:
            raise RemoteExecutionError("REMOTE_OUTPUT_TOKEN_COUNT_INVALID")
        response_sha = sha256_bytes(canonical_json(response))
        return {
            "status": "PASS_REMOTE_EXECUTION",
            "execution_authorized": True,
            "model_runtime_status": "PASS_REMOTE_EXECUTION",
            "output_text": output_text,
            "generated_token_count": token_count,
            "output_sha256": sha256_bytes(canonical_json({"output_text": output_text, "generated_token_count": token_count})),
            "input_sha256": sha256_bytes(canonical_json({
                "domain_id": domain_id, "operation": row.get("operation"),
                "input": row.get("input"), "input_files": row.get("input_files", []),
                "limits": row.get("limits", {}),
            })),
            "quality_equivalence": "NOT_ESTABLISHED",
            "semantic_quality_equivalence": "NOT_ESTABLISHED",
            "certification": "NOT_GRANTED",
            "remote_evidence": {
                "schema": "LOUKSNAPG_REMOTE_TASK_EVIDENCE/1.0",
                "request_id": request_payload["request_id"],
                "endpoint_origin": origin,
                "key_id": spec["key_id"],
                "domain_id": domain_id,
                "model_id": spec["model_id"],
                "source_revision": spec["source_revision"],
                "identity_sha256": identity_sha,
                "weight_inventory_sha256": identity["weight_inventory_sha256"],
                "gateway_version": identity["gateway_version"],
                "gateway_code_sha256": identity["gateway_code_sha256"],
                "gateway_source_commit": identity["gateway_source_commit"],
                "request_sha256": request_sha,
                "response_sha256": response_sha,
                "received_at_utc": utc_now(),
                "quality_gate": "NOT_RUN_BY_TRANSPORT",
                "certification": "NOT_GRANTED",
            },
        }
    except RemoteExecutionError as exc:
        return {
            "status": "FAIL_REMOTE_EXECUTION",
            "execution_authorized": False,
            "reason": str(exc)[:240],
            "quality_equivalence": "NOT_ESTABLISHED",
            "semantic_quality_equivalence": "NOT_ESTABLISHED",
            "certification": "NOT_GRANTED",
        }
    except Exception as exc:
        return {
            "status": "FAIL_REMOTE_EXECUTION",
            "execution_authorized": False,
            "reason": "REMOTE_CLIENT_INTERNAL_ERROR:" + type(exc).__name__,
            "quality_equivalence": "NOT_ESTABLISHED",
            "semantic_quality_equivalence": "NOT_ESTABLISHED",
            "certification": "NOT_GRANTED",
        }
