"""APK ZIP inventory probe for source case MGL5-INF-0065."""
from __future__ import annotations

import hashlib
import io
import zipfile


def apk_inventory(entries: list[dict]) -> dict:
    """Build a deterministic APK-like ZIP in memory and inventory required members."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for entry in entries:
            info = zipfile.ZipInfo(entry["name"], (2020, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, bytes.fromhex(entry["data_hex"]))
    raw = buffer.getvalue()
    digest_before = hashlib.sha256(raw).hexdigest()
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = sorted(info.filename for info in archive.infolist())
            bad = archive.testzip()
            total_uncompressed = sum(info.file_size for info in archive.infolist())
    except (zipfile.BadZipFile, OSError) as exc:
        return {"rejected": True, "reason": type(exc).__name__, "archive_sha256": digest_before}
    required = {
        "AndroidManifest.xml": "manifest",
        "resources.arsc": "resources",
        "classes.dex": "dex",
    }
    present = {kind: name in members for name, kind in required.items()}
    missing = sorted(name for name in required if name not in members)
    return {
        "rejected": False,
        "members": members,
        "present": present,
        "missing": missing,
        "member_count": len(members),
        "uncompressed_bytes": total_uncompressed,
        "zip_integrity": bad is None,
        "archive_sha256": digest_before,
        "archive_unchanged": hashlib.sha256(raw).hexdigest() == digest_before,
    }
