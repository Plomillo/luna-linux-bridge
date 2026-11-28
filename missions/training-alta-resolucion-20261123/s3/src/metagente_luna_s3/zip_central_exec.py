"""ZIP central-directory/local-header comparison for source case INF-0069."""
from __future__ import annotations

import io
import struct
import zipfile


def zip_central_compare(entries: list[dict], tamper_central_name: bool = False) -> dict:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for row in entries:
            archive.writestr(row["name"], bytes.fromhex(row["data_hex"]))
    raw = bytearray(buffer.getvalue())
    if tamper_central_name and entries:
        eocd = raw.rfind(b"PK\x05\x06")
        if eocd < 0 or eocd + 22 > len(raw):
            return {"rejected": True, "reason": "eocd_missing"}
        central_offset = struct.unpack_from("<I", raw, eocd + 16)[0]
        if raw[central_offset:central_offset + 4] != b"PK\x01\x02":
            return {"rejected": True, "reason": "central_record_missing"}
        name_length = struct.unpack_from("<H", raw, central_offset + 28)[0]
        original = bytes(raw[central_offset + 46:central_offset + 46 + name_length])
        alternate = b"X" * name_length
        raw[central_offset + 46:central_offset + 46 + name_length] = alternate
        if original == alternate:
            raw[central_offset + 46] ^= 1

    archive_bytes = bytes(raw)
    disagreements = []
    central_names = []
    local_names = []
    malformed = False
    try:
        eocd = archive_bytes.rfind(b"PK\x05\x06")
        if eocd < 0 or eocd + 22 > len(archive_bytes):
            raise ValueError("eocd_missing")
        count = struct.unpack_from("<H", archive_bytes, eocd + 10)[0]
        central_offset = struct.unpack_from("<I", archive_bytes, eocd + 16)[0]
        cursor = central_offset
        for index in range(count):
            if archive_bytes[cursor:cursor + 4] != b"PK\x01\x02" or cursor + 46 > len(archive_bytes):
                raise ValueError("central_record_invalid")
            name_len, extra_len, comment_len = struct.unpack_from("<HHH", archive_bytes, cursor + 28)
            central_name = archive_bytes[cursor + 46:cursor + 46 + name_len].decode("utf-8")
            local_offset = struct.unpack_from("<I", archive_bytes, cursor + 42)[0]
            central_names.append(central_name)
            if archive_bytes[local_offset:local_offset + 4] != b"PK\x03\x04" or local_offset + 30 > len(archive_bytes):
                raise ValueError("local_record_invalid")
            local_name_len, local_extra_len = struct.unpack_from("<HH", archive_bytes, local_offset + 26)
            local_name = archive_bytes[local_offset + 30:local_offset + 30 + local_name_len].decode("utf-8")
            local_names.append(local_name)
            if local_name != central_name:
                disagreements.append({"index": index, "local_name": local_name, "central_name": central_name, "field": "filename"})
            local_crc = struct.unpack_from("<I", archive_bytes, local_offset + 14)[0]
            central_crc = struct.unpack_from("<I", archive_bytes, cursor + 16)[0]
            if local_crc != central_crc:
                disagreements.append({"index": index, "local_crc32": local_crc, "central_crc32": central_crc, "field": "crc32"})
            cursor += 46 + name_len + extra_len + comment_len
    except (ValueError, UnicodeError, struct.error):
        malformed = True
    return {
        "rejected": malformed,
        "discrepancies": disagreements,
        "local_names": local_names,
        "central_names": central_names,
        "entry_count": len(central_names),
        "mismatch_detected": bool(disagreements),
        "extraction_performed": False,
        "outside_destination_write": False,
    }
