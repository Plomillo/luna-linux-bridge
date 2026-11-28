"""Independent APK inventory oracle using ZIP central-directory records."""
from __future__ import annotations

import struct


def _central_names(entries: list[dict]) -> list[str]:
    # Independent reconstruction: build the deterministic archive vector,
    # then parse the central directory byte records without zipfile.
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for entry in entries:
            archive.writestr(entry["name"], bytes.fromhex(entry["data_hex"]))
    raw = buffer.getvalue()
    eocd = raw.rfind(b"PK\x05\x06")
    if eocd < 0 or eocd + 22 > len(raw):
        return []
    count = struct.unpack_from("<H", raw, eocd + 10)[0]
    offset = struct.unpack_from("<I", raw, eocd + 16)[0]
    names = []
    for _ in range(count):
        if raw[offset:offset + 4] != b"PK\x01\x02" or offset + 46 > len(raw):
            return []
        name_len, extra_len, comment_len = struct.unpack_from("<HHH", raw, offset + 28)
        name = raw[offset + 46:offset + 46 + name_len].decode("utf-8")
        names.append(name)
        offset += 46 + name_len + extra_len + comment_len
    return sorted(names)


def apk_inventory_oracle(arguments: dict, observed: dict) -> dict:
    names = _central_names(arguments["entries"])
    required = {"AndroidManifest.xml", "resources.arsc", "classes.dex"}
    present = {
        "manifest": "AndroidManifest.xml" in names,
        "resources": "resources.arsc" in names,
        "dex": "classes.dex" in names,
    }
    ok = (
        observed.get("rejected") is False
        and observed.get("members") == names
        and observed.get("present") == present
        and observed.get("missing") == sorted(required - set(names))
        and observed.get("member_count") == len(names)
        and observed.get("zip_integrity") is True
        and observed.get("archive_unchanged") is True
    )
    return {"ok": ok, "method": "manual EOCD/central-directory record parser"}
