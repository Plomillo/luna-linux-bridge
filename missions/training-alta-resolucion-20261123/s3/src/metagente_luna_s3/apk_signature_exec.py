"""Test-fixture APK signature verification for source case MGL5-INF-0066.

This probe uses a fixture-only HMAC-SHA256 envelope. It is NOT Android APK
Signature Scheme v1/v2/v3/v4 verification and must not be used for real APKs.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import zipfile

_TEST_KEY = bytes.fromhex("c05a11f066d20b7e4a9308b5d3f0e2a1")
_SIG_MEMBER = "META-INF/LUNA.TESTSIG"
_ALGORITHM = "HMAC-SHA256-TEST-FIXTURE"


def _canonical(entries: list[dict]) -> bytes:
    out = bytearray(b"APKTESTSIG1\n")
    for row in sorted(entries, key=lambda item: item["name"]):
        if row["name"] == _SIG_MEMBER:
            continue
        out.extend(row["name"].encode("utf-8"))
        out.extend(b"\0")
        out.extend(bytes.fromhex(row["data_hex"]))
        out.extend(b"\n")
    return bytes(out)


def _fixture_signature(entries: list[dict]) -> bytes:
    return hmac.new(_TEST_KEY, _canonical(entries), hashlib.sha256).digest()


def apk_signature_verify(entries: list[dict], signature_mode: str = "valid") -> dict:
    if signature_mode not in {"valid", "invalid", "absent"}:
        return {"rejected": True, "reason": "signature_mode_invalid"}
    fixture_entries = [dict(row) for row in entries if row["name"] != _SIG_MEMBER]
    signature = _fixture_signature(fixture_entries)
    if signature_mode == "invalid":
        signature = bytes([signature[0] ^ 1]) + signature[1:]
    if signature_mode != "absent":
        fixture_entries.append({
            "name": _SIG_MEMBER,
            "data_hex": json.dumps(
                {"algorithm": _ALGORITHM, "signature_hex": signature.hex()},
                sort_keys=True,
                separators=(",", ":"),
            ).encode().hex(),
        })
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for row in fixture_entries:
            archive.writestr(row["name"], bytes.fromhex(row["data_hex"]))
    raw = buffer.getvalue()
    archive_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = sorted(info.filename for info in archive.infolist())
            if _SIG_MEMBER not in names:
                return {
                    "rejected": False,
                    "signature_present": False,
                    "signature_valid": False,
                    "status": "ABSENT",
                    "algorithm": None,
                    "member_count": len(names),
                    "archive_sha256": archive_sha256,
                    "archive_unchanged": hashlib.sha256(raw).hexdigest() == archive_sha256,
                }
            envelope = json.loads(archive.read(_SIG_MEMBER).decode("utf-8"))
            signature_bytes = bytes.fromhex(envelope["signature_hex"])
            content = [
                {"name": info.filename, "data_hex": archive.read(info).hex()}
                for info in archive.infolist()
                if info.filename != _SIG_MEMBER
            ]
            expected = _fixture_signature(content)
            valid = envelope.get("algorithm") == _ALGORITHM and hmac.compare_digest(signature_bytes, expected)
            return {
                "rejected": False,
                "signature_present": True,
                "signature_valid": valid,
                "status": "VALID" if valid else "INVALID",
                "algorithm": envelope.get("algorithm"),
                "member_count": len(names),
                "archive_sha256": archive_sha256,
                "archive_unchanged": hashlib.sha256(raw).hexdigest() == archive_sha256,
            }
    except (zipfile.BadZipFile, OSError, ValueError, KeyError, UnicodeError, json.JSONDecodeError):
        return {"rejected": True, "reason": "signature_fixture_malformed", "archive_sha256": archive_sha256}
