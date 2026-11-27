"""Independent structural checks for archive forensic operations."""
from __future__ import annotations

import zlib


def path_oracle(arguments: dict, observed: dict) -> dict:
    dangerous = [row["name"] for row in arguments["entries"] if ".." in row["name"].replace("\\", "/").split("/") or row["name"].startswith(("/", "\\"))]
    safe = [row["name"] for row in arguments["entries"] if row["name"] not in dangerous]
    return {"ok": observed.get("blocked") == dangerous and observed.get("safe") == safe and observed.get("extracted") == safe and observed.get("outside_write") is False, "method": "independent lexical containment classification plus extracted-name equality"}


def crc_oracle(arguments: dict, observed: dict) -> dict:
    expected_crc = zlib.crc32(bytes.fromhex(arguments["payload_hex"])) & 0xFFFFFFFF
    damaged = bytearray.fromhex(arguments["payload_hex"])
    if damaged:
        damaged[0] ^= 1
    damaged_crc = zlib.crc32(damaged) & 0xFFFFFFFF
    return {"ok": observed.get("crc_error_detected") is True and observed.get("central_crc32") == expected_crc and observed.get("damaged_member_crc32") == damaged_crc and damaged_crc != expected_crc, "method": "independent CRC32 recomputation over original and mutated member bytes"}


def duplicate_oracle(arguments: dict, observed: dict) -> dict:
    names, payloads = arguments["names"], arguments["payloads_hex"]
    collisions = sorted({name for name in names if names.count(name) > 1})
    return {"ok": observed.get("collisions") == collisions and observed.get("contents") == payloads and observed.get("silent_overwrite") is False, "method": "input multiplicity and per-entry byte equality"}


def tar_offsets_oracle(arguments: dict, observed: dict) -> dict:
    expected, cursor = [], 0
    for row in arguments["entries"]:
        size = len(bytes.fromhex(row["data_hex"]))
        next_offset = cursor + 512 * (1 + (size + 511) // 512)
        expected.append({"name": row["name"], "header_offset": cursor, "data_offset": cursor + 512, "size": size, "next_offset": next_offset})
        cursor = next_offset
    return {"ok": observed.get("members") == expected, "method": "independent USTAR 512-byte block arithmetic"}


def truncated_oracle(arguments: dict, observed: dict) -> dict:
    first_size = len(bytes.fromhex(arguments["first_hex"]))
    second_size = len(bytes.fromhex(arguments["second_hex"]))
    expected_partial = arguments["cut_into_second"] < second_size
    return {"ok": first_size > 0 and observed.get("first_preserved") is True and observed.get("second_incomplete") is expected_partial, "method": "independent declared payload length and cut position"}


def gzip_oracle(arguments: dict, observed: dict) -> dict:
    expected = zlib.crc32(bytes.fromhex(arguments["payload_hex"])) & 0xFFFFFFFF
    return {"ok": observed.get("crc_error_detected") is True and observed.get("expected_crc32") == expected, "method": "zlib CRC32 over source bytes"}
