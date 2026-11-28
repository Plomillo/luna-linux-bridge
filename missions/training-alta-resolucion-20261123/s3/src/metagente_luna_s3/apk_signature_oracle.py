"""Independent fixture-signature oracle for INF-0066; no executor imports."""
from __future__ import annotations

import hashlib
import hmac
import json
import zipfile
import io

_TEST_KEY = bytes.fromhex("c05a11f066d20b7e4a9308b5d3f0e2a1")
_SIG_MEMBER = "META-INF/LUNA.TESTSIG"
_ALGORITHM = "HMAC-SHA256-TEST-FIXTURE"


def _oracle_message(members: list[tuple[str, bytes]]) -> bytes:
    message = b"APKTESTSIG1\n"
    for name, content in sorted(members, key=lambda item: item[0]):
        message += name.encode("utf-8") + b"\0" + content + b"\n"
    return message


def apk_signature_oracle(arguments: dict, observed: dict) -> dict:
    mode = arguments.get("signature_mode", "valid")
    if mode == "absent":
        expected_status = "ABSENT"
        expected_present = False
        expected_valid = False
    elif mode in {"valid", "invalid"}:
        expected_present = True
        unsigned = [(row["name"], bytes.fromhex(row["data_hex"])) for row in arguments["entries"] if row["name"] != _SIG_MEMBER]
        expected = hmac.new(_TEST_KEY, _oracle_message(unsigned), hashlib.sha256).digest()
        if mode == "invalid":
            expected = bytes([expected[0] ^ 1]) + expected[1:]
        expected_valid = hmac.compare_digest(expected, hmac.new(_TEST_KEY, _oracle_message(unsigned), hashlib.sha256).digest())
        expected_status = "VALID" if expected_valid else "INVALID"
    else:
        return {"ok": False, "method": "independent fixture HMAC oracle; unknown mode fail-closed"}
    ok = (
        observed.get("rejected") is False
        and observed.get("signature_present") is expected_present
        and observed.get("signature_valid") is expected_valid
        and observed.get("status") == expected_status
        and observed.get("archive_unchanged") is True
    )
    return {"ok": ok, "expected_status": expected_status, "method": "independent canonical member serialization and HMAC-SHA256 recomputation"}
