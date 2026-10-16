#!/usr/bin/env python3
"""Compile a human mission into a byte-exact CUSTOSZ native envelope.

This program never executes instructions contained in the mission. It treats
MISSION_ORIGINAL.md strictly as data and embeds the exact UTF-8 bytes in the
native envelope so no semantic reduction can occur silently.
"""
import argparse
import base64
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ASSIGNMENT = re.compile(r"^\s*([A-Z][A-Z0-9_.-]{1,80})\s*[:=]\s*(.*?)\s*$")

def utc():
    return datetime.now(timezone.utc).isoformat()

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()

def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def extract_directives(text):
    out = {}
    for line_no, line in enumerate(text.splitlines(), 1):
        match = ASSIGNMENT.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2)
        out.setdefault(key, []).append({"line": line_no, "value": value})
    return out

def first_value(directives, *keys):
    for key in keys:
        if key in directives and directives[key]:
            return directives[key][0]["value"]
    return None

def explicit_capabilities(directives):
    raw = first_value(directives, "REQUIRED_CAPABILITIES", "CAPABILITIES_REQUIRED", "CAPABILITIES")
    if not raw:
        return []
    return sorted({x.strip() for x in re.split(r"[,;]", raw) if x.strip()})

def routing_hints(text):
    upper = text.upper()
    mapping = [
        ("GITHUB", "GITHUB"),
        ("RUNTIME", "CUSTOSZ_RUNTIME"),
        ("SELF-HOSTED", "SELF_HOSTED"),
        ("LOCAL", "LOCAL_HOST"),
        ("RESEARCH", "RESEARCH"),
        ("INVESTIG", "RESEARCH"),
        ("ROLLBACK", "ROLLBACK"),
        ("README", "TERMINAL_REPORT"),
        ("WINDOWS", "PROTECTED_WINDOWS_SCOPE"),
        ("F3-DISK", "PROTECTED_F3_DISK_SCOPE"),
    ]
    return sorted({label for token, label in mapping if token in upper})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mission", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--policy", default="mission-mailbox/config/mailbox-policy.json")
    args = parser.parse_args()

    mission = Path(args.mission)
    out = Path(args.out)
    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))

    raw = mission.read_bytes()
    digest = sha_bytes(raw)
    mail_id = "MAIL-" + digest[:20].upper()
    received = utc()

    errors = []
    if not raw:
        errors.append("EMPTY_MISSION")
    if len(raw) > int(policy["mission"]["max_input_bytes"]):
        errors.append("MISSION_TOO_LARGE")
    if b"\x00" in raw:
        errors.append("NUL_BYTE_FORBIDDEN")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        text = ""
        errors.append("NOT_UTF8:" + str(exc))

    directives = extract_directives(text) if text else {}
    declared_id = first_value(directives, "MISSION_ID", "MISSION")
    caps = explicit_capabilities(directives)

    receipt = {
        "schema": "CUSTOSZ_MAILBOX_RECEIPT/1.0",
        "mail_id": mail_id,
        "received_utc": received,
        "source_path": mission.as_posix(),
        "source_sha256": digest,
        "source_bytes": len(raw),
        "source_commit": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "status": "RECEIVED" if not errors else "REJECTED",
    }

    validation = {
        "schema": "CUSTOSZ_MAILBOX_INGRESS_VALIDATION/1.0",
        "mail_id": mail_id,
        "result": "PASS" if not errors else "FAIL",
        "checks": {
            "non_empty": bool(raw),
            "utf8": not any(x.startswith("NOT_UTF8") for x in errors),
            "within_size_limit": len(raw) <= int(policy["mission"]["max_input_bytes"]),
            "nul_free": b"\x00" not in raw,
        },
        "errors": errors,
    }

    atomic_json(out / "RECEIPT.json", receipt)
    atomic_json(out / "INGRESS_VALIDATION.json", validation)

    if errors:
        state = {
            "schema_version": "1.0",
            "mail_id": mail_id,
            "workflow_technical_status": "PASS",
            "mission_terminal_status": "REJECTED",
            "current_state": "REJECTED",
            "current_gate": "INGRESS_VALIDATION",
            "root_blocker": errors[0],
            "history": [
                {"utc": received, "state": "RECEIVED"},
                {"utc": utc(), "state": "REJECTED", "reason": errors[0]},
            ],
        }
        atomic_json(out / "MISSION_STATE.json", state)
        (out / "README_ERROR.md").write_text(
            "# MISSION ERROR / HOLD\n\n"
            f"MAIL_ID = {mail_id}\n"
            "MISSION_STATUS = REJECTED\n\n"
            f"ROOT_CAUSE = {errors[0]}\n"
            "AFFECTED_GATE = INGRESS_VALIDATION\n"
            "EXACT_REMEDIATION = Correct encoding/size without changing intended meaning, then submit a new immutable source file.\n"
            "RESOLVED = FALSE\n",
            encoding="utf-8",
        )
        return 2

    native = {
        "schema_version": "1.0",
        "mailbox_version": policy["mailbox_version"],
        "mail_id": mail_id,
        "declared_mission_id": declared_id,
        "source": {
            "path": mission.as_posix(),
            "sha256": digest,
            "bytes": len(raw),
            "encoding": "utf-8",
            "source_commit": os.environ.get("GITHUB_SHA"),
        },
        "authority_context": {
            "authority": policy["authority"],
            "authority_transfer": False,
            "canonical_mutation_authorized": False,
        },
        "mission_payload": {
            "source_utf8_b64": base64.b64encode(raw).decode("ascii"),
            "byte_exact_preservation": True,
            "directives_observed": directives,
            "routing_hints": {"authoritative": False, "values": routing_hints(text)},
            "required_capabilities_explicit": caps,
        },
        "execution_contract": {
            "worker": policy["roles"]["worker"],
            "governor": policy["roles"]["governor"],
            "supervisor": policy["roles"]["supervisor"],
            "runtime": policy["roles"]["runtime"],
            "default_profile": policy["mission"]["default_profile"],
            "wallclock_seconds": policy["mission"]["default_wallclock_seconds"],
            "validation_reserve_seconds": policy["mission"]["validation_reserve_seconds"],
            "protected_scopes": policy["protected_scopes"],
            "fail_closed": True,
            "no_silent_executor_substitution": True,
            "workflow_success_is_not_mission_success": True,
        },
    }

    reconstructed = base64.b64decode(native["mission_payload"]["source_utf8_b64"])
    reconstructed_sha = sha_bytes(reconstructed)
    if reconstructed_sha != digest:
        raise SystemExit("BYTE_EXACT_RECONSTRUCTION_FAILED")

    mapping = {
        "schema": "CUSTOSZ_SEMANTIC_MAPPING/1.0",
        "mail_id": mail_id,
        "result": "PASS_SOURCE_BYTE_EXACT",
        "source_sha256": digest,
        "mechanism": "ORIGINAL_UTF8_BYTES_EMBEDDED_BASE64_IN_MISSION_NATIVE",
        "semantic_reduction_performed": False,
        "authoritative_inference_performed": False,
        "routing_hints_authoritative": False,
        "reconstruction_test_sha256": reconstructed_sha,
    }

    state = {
        "schema_version": "1.0",
        "mail_id": mail_id,
        "workflow_technical_status": "PASS",
        "mission_terminal_status": None,
        "current_state": "COMPILED",
        "current_gate": "CUSTOSZ_ROUTING",
        "root_blocker": None,
        "history": [
            {"utc": received, "state": "RECEIVED"},
            {"utc": utc(), "state": "VALIDATED"},
            {"utc": utc(), "state": "COMPILED"},
            {"utc": utc(), "state": "SEMANTICALLY_EQUIVALENT_BY_BYTE_PRESERVATION"},
        ],
    }

    atomic_json(out / "MISSION_NATIVE.json", native)
    atomic_json(out / "SEMANTIC_MAPPING.json", mapping)
    atomic_json(out / "MISSION_STATE.json", state)

    print(json.dumps({"mail_id": mail_id, "status": "COMPILED", "source_sha256": digest}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
