"""Deterministic in-memory archive probes for source cases INF-0070..0075."""
from __future__ import annotations

import gzip
import hashlib
import io
import tarfile
import tempfile
import zipfile
import zlib
from pathlib import Path


def _zip(entries: list[dict]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for entry in entries:
            info = zipfile.ZipInfo(entry["name"], (2020, 1, 1, 0, 0, 0))
            archive.writestr(info, bytes.fromhex(entry["data_hex"]))
    return buffer.getvalue()


def zip_path_safety(entries: list[dict]) -> dict:
    archive_bytes = _zip(entries)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = [item.filename for item in archive.infolist()]
    safe, blocked = [], []
    for name in names:
        parts = name.replace("\\", "/").split("/")
        if name.startswith(("/", "\\")) or any(part in {"", ".."} for part in parts) or (len(name) > 1 and name[1] == ":"):
            blocked.append(name)
        else:
            safe.append(name)
    extracted = []
    outside_write = False
    with tempfile.TemporaryDirectory(prefix="c05-zip-sandbox-") as temporary:
        root = Path(temporary).resolve()
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            for info in archive.infolist():
                if info.filename not in safe:
                    continue
                destination = (root / info.filename).resolve()
                if destination != root and root not in destination.parents:
                    blocked.append(info.filename)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(info))
                extracted.append(info.filename)
        outside_write = any(path.is_file() for path in root.parent.glob("outside.txt"))
    return {"safe": safe, "blocked": blocked, "extracted": extracted, "outside_write": outside_write, "archive_sha256": hashlib.sha256(archive_bytes).hexdigest()}


def zip_crc(payload_hex: str) -> dict:
    data = bytes.fromhex(payload_hex)
    packed = bytearray(_zip([{"name": "member.bin", "data_hex": data.hex()}]))
    with zipfile.ZipFile(io.BytesIO(packed)) as archive:
        info = archive.infolist()[0]
        offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
        central_crc = info.CRC
    packed[offset] ^= 1
    damaged_data = bytearray(data)
    if damaged_data:
        damaged_data[0] ^= 1
    try:
        with zipfile.ZipFile(io.BytesIO(packed)) as archive:
            archive.read(archive.infolist()[0])
    except (zipfile.BadZipFile, RuntimeError):
        detected = True
    else:
        detected = False
    return {"crc_error_detected": detected, "central_crc32": central_crc, "damaged_member_crc32": zlib.crc32(damaged_data) & 0xFFFFFFFF}


def zip_duplicates(names: list[str], payloads_hex: list[str]) -> dict:
    entries = [{"name": name, "data_hex": data} for name, data in zip(names, payloads_hex, strict=True)]
    collisions = sorted({name for name in names if names.count(name) > 1})
    with zipfile.ZipFile(io.BytesIO(_zip(entries))) as archive:
        stored = [archive.read(info).hex() for info in archive.infolist()]
    return {"collisions": collisions, "entry_count": len(entries), "contents": stored, "silent_overwrite": False}


def _tar(entries: list[dict]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for entry in entries:
            data = bytes.fromhex(entry["data_hex"])
            info = tarfile.TarInfo(entry["name"])
            info.size, info.mtime = len(data), 0
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def tar_offsets(entries: list[dict]) -> dict:
    raw = _tar(entries)
    rows, offset = [], 0
    while offset + 512 <= len(raw) and raw[offset:offset + 512] != bytes(512):
        header = raw[offset:offset + 512]
        name = header[:100].split(b"\0", 1)[0].decode("utf-8")
        size = int(header[124:136].strip(b"\0 ") or b"0", 8)
        next_offset = offset + 512 * (1 + (size + 511) // 512)
        rows.append({"name": name, "header_offset": offset, "data_offset": offset + 512, "size": size, "next_offset": next_offset})
        if next_offset <= offset:
            raise ValueError("non-advancing TAR member boundary")
        offset = next_offset
    return {"members": rows, "archive_sha256": hashlib.sha256(raw).hexdigest()}


def tar_truncated(first_hex: str, second_hex: str, cut_into_second: int) -> dict:
    entries = [{"name": "first", "data_hex": first_hex}, {"name": "second", "data_hex": second_hex}]
    data = _tar(entries)
    second_start = 512 + ((len(bytes.fromhex(first_hex)) + 511) // 512) * 512
    cut = min(len(data), second_start + 512 + cut_into_second)
    partial = data[:cut]
    first_bytes, second_bytes = bytes.fromhex(first_hex), bytes.fromhex(second_hex)
    first_payload_start = 512
    first_complete = len(partial) >= first_payload_start + len(first_bytes) and partial[first_payload_start:first_payload_start + len(first_bytes)] == first_bytes
    second_payload_start = second_start + 512
    second_available = max(0, len(partial) - second_payload_start)
    second_complete = second_available >= len(second_bytes) and partial[second_payload_start:second_payload_start + len(second_bytes)] == second_bytes
    return {"first_preserved": first_complete, "second_incomplete": not second_complete, "cut_offset": cut}


def gzip_crc(payload_hex: str) -> dict:
    raw = bytes.fromhex(payload_hex)
    stream = io.BytesIO()
    with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as output:
        output.write(raw)
    packed = bytearray(stream.getvalue())
    packed[-8] ^= 1
    try:
        gzip.decompress(packed)
    except (gzip.BadGzipFile, EOFError, zlib.error):
        detected = True
    else:
        detected = False
    return {"crc_error_detected": detected, "expected_crc32": zlib.crc32(raw) & 0xFFFFFFFF}
