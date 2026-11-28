"""Generate a deterministic structural PE specimen with one static import."""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

ROOT = Path(__file__).parents[1]


def build() -> bytes:
    raw = bytearray(0xA00)
    raw[:2] = b"MZ"
    struct.pack_into("<I", raw, 0x3C, 0x80)
    raw[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", raw, 0x84, 0x8664, 3, 0, 0, 0, 0xF0, 0x22)
    optional = 0x98
    struct.pack_into("<H", raw, optional, 0x20B)
    struct.pack_into("<II", raw, optional + 32, 0x1000, 0x200)
    struct.pack_into("<II", raw, optional + 56, 0x4000, 0x400)
    struct.pack_into("<I", raw, optional + 108, 16)
    struct.pack_into("<II", raw, optional + 112 + 8, 0x3000, 40)
    section_table = optional + 0xF0
    for index, (name, rva, file_offset) in enumerate(((b".text", 0x1000, 0x400), (b".data", 0x2000, 0x600), (b".rdata", 0x3000, 0x800))):
        offset = section_table + index * 40
        raw[offset:offset + len(name)] = name
        struct.pack_into("<IIII", raw, offset + 8, 0x200, rva, 0x200, file_offset)
        struct.pack_into("<I", raw, offset + 36, 0x40000040 if name == b".data" else 0x60000020)
    struct.pack_into("<IIIII", raw, 0x800, 0x3050, 0, 0, 0x3040, 0x3060)
    raw[0x840:0x84D] = b"KERNEL32.dll\0"
    struct.pack_into("<QQQQ", raw, 0x850, 0x3070, 0, 0x3070, 0)
    raw[0x872:0x87E] = b"ExitProcess\0"
    return bytes(raw)


if __name__ == "__main__":
    payload = build()
    path = ROOT / "fixtures" / "FX-MGL5-INF-0061-0064-pe64.bin"
    path.write_bytes(payload)
    print(f"{path.name} sha256={hashlib.sha256(payload).hexdigest()} bytes={len(payload)}")
