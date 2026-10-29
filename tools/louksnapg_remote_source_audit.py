#!/usr/bin/env python3
"""Read-only audit of pinned Hugging Face model revisions and file identities.

This tool downloads only small repository metadata files (config/index), never
model weight payloads. It reads file sizes and LFS SHA-256 identities from the
revision metadata API, and fails closed when revision/config/index/file inventory
does not match the repository policy.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

POLICY_SCHEMA = "LOUKSNAPG_REMOTE_MODEL_POLICY/1.0"
REPORT_SCHEMA = "LOUKSNAPG_REMOTE_SOURCE_AUDIT/1.0"
HEX_256 = re.compile(r"^[0-9a-f]{64}$")
HEX_40 = re.compile(r"^[0-9a-f]{40}$")
API_LIMIT = 32 * 1024 * 1024
SMALL_FILE_LIMIT = 16 * 1024 * 1024
USER_AGENT = "LOUKSNAPG-Remote-Source-Audit/1.0"


class AuditError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def http_get(url: str, limit: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, application/octet-stream;q=0.9, */*;q=0.8",
            "Cache-Control": "no-cache",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            if response.status != 200:
                raise AuditError("HTTP_STATUS:" + str(response.status))
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > limit:
                raise AuditError("RESPONSE_SIZE_LIMIT_EXCEEDED")
            data = response.read(limit + 1)
    except urllib.error.HTTPError as exc:
        raise AuditError("HTTP_STATUS:" + str(exc.code)) from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        if isinstance(exc, AuditError):
            raise
        raise AuditError("HTTP_FETCH_FAILED:" + type(exc).__name__) from exc
    if len(data) > limit:
        raise AuditError("RESPONSE_SIZE_LIMIT_EXCEEDED")
    return data


def metadata_url(repo_id: str, revision: str) -> str:
    quoted_repo = urllib.parse.quote(repo_id, safe="/")
    return f"https://huggingface.co/api/models/{quoted_repo}/revision/{revision}?blobs=true"


def file_url(repo_id: str, revision: str, relative_path: str) -> str:
    quoted_repo = urllib.parse.quote(repo_id, safe="/")
    quoted_path = urllib.parse.quote(relative_path, safe="/")
    return f"https://huggingface.co/{quoted_repo}/resolve/{revision}/{quoted_path}?download=true"


def observed_lfs_sha(row: dict) -> str | None:
    lfs = row.get("lfs")
    if isinstance(lfs, dict):
        oid = lfs.get("oid")
        if isinstance(oid, str):
            value = oid.lower()
            if value.startswith("sha256:"):
                value = value[7:]
            if HEX_256.fullmatch(value):
                return value
    blob = row.get("blobId")
    if isinstance(blob, str) and HEX_256.fullmatch(blob.lower()):
        # Non-LFS Git blob IDs may be SHA-1 rather than the model file SHA-256.
        return None
    return None


def audit_domain(domain_id: str, spec: dict) -> dict:
    result = {
        "domain_id": domain_id,
        "model_id": spec.get("model_id"),
        "source_repo": spec.get("source_repo"),
        "expected_revision": spec.get("source_revision"),
        "status": "NOT_CHECKED",
        "metadata_files": [],
        "weight_files": [],
        "weight_sha256_pin_status": "UNKNOWN",
        "errors": [],
    }
    try:
        repo = spec.get("source_repo")
        revision = spec.get("source_revision")
        if not isinstance(repo, str) or not repo or not HEX_40.fullmatch(str(revision)):
            raise AuditError("SOURCE_REPOSITORY_OR_REVISION_INVALID")
        raw = http_get(metadata_url(repo, revision), API_LIMIT)
        try:
            info = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AuditError("HUGGINGFACE_MODEL_METADATA_INVALID_JSON") from exc
        if not isinstance(info, dict):
            raise AuditError("HUGGINGFACE_MODEL_METADATA_ROOT_INVALID")
        observed_revision = info.get("sha")
        result["observed_revision"] = observed_revision
        if observed_revision != revision:
            raise AuditError("IMMUTABLE_SOURCE_REVISION_NOT_RESOLVED")
        siblings = info.get("siblings")
        if not isinstance(siblings, list):
            raise AuditError("HUGGINGFACE_SIBLING_INVENTORY_MISSING")
        by_path = {}
        for item in siblings:
            if not isinstance(item, dict) or not isinstance(item.get("rfilename"), str):
                continue
            path = item["rfilename"]
            if path in by_path:
                raise AuditError("DUPLICATE_UPSTREAM_PATH:" + path)
            by_path[path] = item
        required_meta = [("config.json", spec.get("source_config_sha256"))]
        if spec.get("source_index_sha256") is not None:
            required_meta.append(("model.safetensors.index.json", spec.get("source_index_sha256")))
        for name, expected_sha in required_meta:
            if name not in by_path:
                raise AuditError("UPSTREAM_METADATA_FILE_MISSING:" + name)
            data = http_get(file_url(repo, revision, name), SMALL_FILE_LIMIT)
            observed_sha = sha256(data)
            entry = {
                "path": name,
                "bytes": len(data),
                "sha256": observed_sha,
                "expected_sha256": expected_sha,
                "status": "PASS" if observed_sha == expected_sha else "FAIL",
            }
            result["metadata_files"].append(entry)
            if observed_sha != expected_sha:
                raise AuditError("UPSTREAM_METADATA_SHA256_MISMATCH:" + name)
        expected_weights = {row["path"]: row for row in spec.get("weight_files", [])}
        actual_weights = {
            name: row for name, row in by_path.items()
            if name.endswith(".safetensors") and (name.startswith("model-") or name == "model.safetensors")
        }
        if set(actual_weights) != set(expected_weights):
            raise AuditError(
                "UPSTREAM_WEIGHT_FILE_SET_MISMATCH:"
                + json.dumps({
                    "missing": sorted(set(expected_weights) - set(actual_weights)),
                    "unexpected": sorted(set(actual_weights) - set(expected_weights)),
                }, separators=(",", ":"))
            )
        all_hashes_pinned = True
        for name in sorted(expected_weights, key=lambda value: value.encode("utf-8")):
            expected = expected_weights[name]
            source_row = actual_weights[name]
            actual_size = source_row.get("size")
            if actual_size is None and isinstance(source_row.get("lfs"), dict):
                actual_size = source_row["lfs"].get("size")
            if isinstance(actual_size, bool) or not isinstance(actual_size, int) or actual_size <= 0:
                raise AuditError("UPSTREAM_WEIGHT_SIZE_MISSING:" + name)
            digest = observed_lfs_sha(source_row)
            row_result = {
                "path": name,
                "expected_bytes": expected.get("bytes"),
                "observed_bytes": actual_size,
                "expected_sha256": expected.get("sha256"),
                "observed_sha256": digest,
            }
            if expected.get("bytes") is not None and expected["bytes"] != actual_size:
                row_result["status"] = "FAIL_SIZE"
                result["weight_files"].append(row_result)
                raise AuditError("UPSTREAM_WEIGHT_SIZE_MISMATCH:" + name)
            if expected.get("sha256") is not None:
                if digest is None:
                    row_result["status"] = "FAIL_SOURCE_HASH_UNAVAILABLE"
                    result["weight_files"].append(row_result)
                    raise AuditError("UPSTREAM_WEIGHT_SHA256_UNAVAILABLE:" + name)
                if digest != expected["sha256"]:
                    row_result["status"] = "FAIL_SHA256"
                    result["weight_files"].append(row_result)
                    raise AuditError("UPSTREAM_WEIGHT_SHA256_MISMATCH:" + name)
            else:
                all_hashes_pinned = False
            row_result["status"] = "PASS" if expected.get("sha256") is not None and digest == expected["sha256"] else "PASS_REVISION_BOUND_HASH_DISCOVERED"
            result["weight_files"].append(row_result)
        result["weight_sha256_pin_status"] = "ALL_WEIGHT_SHAS_PINNED" if all_hashes_pinned else "REVISION_PINNED_SOME_WEIGHT_SHAS_NOT_YET_IN_POLICY"
        result["status"] = "PASS_SOURCE_REVISION_CONFIG_INDEX_AND_WEIGHT_INVENTORY"
    except AuditError as exc:
        result["status"] = "FAIL_CLOSED"
        result["errors"].append(str(exc)[:1500])
    except Exception as exc:
        result["status"] = "FAIL_CLOSED"
        result["errors"].append("UNEXPECTED_AUDIT_ERROR:" + type(exc).__name__)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "cajita-luna-runtime" / "CAJITA_REMOTE_MODEL_POLICY.json",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    policy_path = args.policy.resolve(strict=True)
    if policy_path.is_symlink() or not policy_path.is_file():
        raise SystemExit("FAIL_CLOSED:POLICY_FILE_MISSING_OR_UNSAFE")
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit("FAIL_CLOSED:POLICY_JSON_INVALID:" + type(exc).__name__)
    if policy.get("schema") != POLICY_SCHEMA:
        raise SystemExit("FAIL_CLOSED:POLICY_SCHEMA_MISMATCH")
    domains = policy.get("domains")
    if not isinstance(domains, dict) or not domains:
        raise SystemExit("FAIL_CLOSED:DOMAIN_POLICY_MISSING")
    results = [
        audit_domain(domain_id, spec)
        for domain_id, spec in sorted(domains.items())
    ]
    errors = [
        f"{row['domain_id']}:{error}"
        for row in results for error in row["errors"]
    ]
    pin_gaps = [
        row["domain_id"] for row in results
        if row["status"] == "PASS_SOURCE_REVISION_CONFIG_INDEX_AND_WEIGHT_INVENTORY"
        and row["weight_sha256_pin_status"] != "ALL_WEIGHT_SHAS_PINNED"
    ]
    report = {
        "schema": REPORT_SCHEMA,
        "observed_at_utc": utc_now(),
        "policy_sha256": sha256(policy_path.read_bytes()),
        "source_audit_mode": "METADATA_AND_SMALL_CONFIG_INDEX_ONLY_NO_WEIGHT_DOWNLOAD",
        "domains": results,
        "all_source_revisions_resolved": not errors,
        "all_config_and_index_hashes_pass": not errors,
        "all_weight_file_sets_sizes_pass": not errors,
        "unresolved_weight_sha256_policy_pins": pin_gaps,
        "status": "PASS_SOURCE_METADATA" if not errors else "FAIL_CLOSED",
        "weight_sha256_pin_status": "ALL_PINNED" if not pin_gaps else "REQUIRES_POLICY_UPDATE",
        "model_weights_downloaded": False,
        "model_inference_executed": False,
        "global_certification": "NOT_GRANTED",
    }
    serialized = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    print(serialized, end="")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(serialized, encoding="utf-8")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
