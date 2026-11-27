"""Reference checks that do not call the executors."""
from __future__ import annotations

import hashlib
import ipaddress
import zlib
from decimal import Decimal

from metagente_luna_s3.d01_oracle import _canonical


def units(arguments: dict, observed: dict) -> dict:
    text = arguments["text"]
    if text == "a":
        expected = {"bytes": 1, "codepoints": 1, "graphemes": 1, "preserved": "a"}
        ok = observed == expected
    elif text == "ab":
        expected = {"bytes": 2, "codepoints": 2, "graphemes": 2, "preserved": "ab"}
        ok = observed == expected
    elif "\u200d" in text:
        ok = observed["preserved"] == text and observed["codepoints"] > observed["graphemes"]
    else:
        ok = observed == {"bytes": 3, "codepoints": 2, "graphemes": 1, "preserved": "e\u0301"}
    return {"ok": ok, "method": "fixed counts or ZWJ property"}


def crlf_lines(arguments: dict, observed: dict) -> dict:
    ok = observed["lines"] == arguments["text"].splitlines() and observed["doubled_cr"] is False and observed["written"].count("\r\n") == len(observed["lines"])
    return {"ok": ok, "method": "terminator count"}


def lf_only(arguments: dict, observed: dict) -> dict:
    expected = arguments["text"].replace("\r\n", "\n").replace("\r", "\n")
    return {"ok": observed["converted"] == expected and observed["cr_remaining"] is False, "method": "direct replacement"}


def csv_rows(arguments: dict, observed: dict) -> dict:
    return {"ok": observed["parsed"] == arguments["rows"], "method": "row equality, not csv.writer"}


def one_record(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["records"] == 1 and "\n" in observed["fields"][0], "method": "one record despite the newline"}


def json_string(arguments: dict, observed: dict) -> dict:
    return {"ok": observed["parsed"] == arguments["text"] and "\\u00" not in observed["raw"], "method": "no escaped non-ascii"}


def key_count(arguments: dict, observed: dict) -> dict:
    text = arguments["text"]
    return {"ok": text.count('"a"') == 2 and observed["duplicate_detected"] is True and observed["policy"] == "REJECT", "method": "key occurrence count"}


def canonical_pair(arguments: dict, observed: dict) -> dict:
    expected = _canonical(arguments["left"])
    return {"ok": observed["same"] is True and observed["canonical"] == expected == _canonical(arguments["right"]), "method": "hand-built canonical form"}


def expanded_name(arguments: dict, observed: dict) -> dict:
    document = arguments["document"]
    if document == "<x/>":
        ok = observed["expanded_names"] == ["x"] and observed["same_expanded_name"] is True
    elif "urn:y" in document:
        ok = observed["same_expanded_name"] is False
    else:
        ok = observed["same_expanded_name"] is True and observed["expanded_names"] == ["{urn:x}x", "{urn:x}x"]
    return {"ok": ok, "method": "Clark notation literal"}


def predefined_entities(arguments: dict, observed: dict) -> dict:
    expected = "ok" if arguments["document"] == "<r>ok</r>" else "<>&"
    return {"ok": observed["text"] == expected and observed["external_expanded"] is False, "method": "predefined entities only"}


def parse_error(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["rejected"] is True and bool(observed["diagnostic"]), "method": "unbalanced tags must fail"}


def frame_sum(arguments: dict, observed: dict) -> dict:
    payload = bytes.fromhex(arguments["payload_hex"])
    checksum = sum(payload) & 0xFFFF
    return {"ok": observed["length"] == len(payload) and observed["checksum"] == checksum, "method": "byte sum, not the encoder"}


def cuts(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["all_rejected"] is True and 0 in observed["rejected_lengths"], "method": "every shorter buffer is rejected"}


def huge_length(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["rejected"] is True and observed["allocated_declared_length"] is False, "method": "declared length is not allocated"}


def f32_table(arguments: dict, observed: dict) -> dict:
    known = {16777216: True, 16777217: False, 16777219: False}
    got = {row["value"]: row["exact"] for row in observed["rows"]}
    ok = list(got) == arguments["values"] and all(got[value] == known[value] for value in arguments["values"])
    return {"ok": ok, "method": "float32 integer boundary"}


def decimal_literal(arguments: dict, observed: dict) -> dict:
    expected = str(Decimal(arguments["text"]))
    return {"ok": observed["text"] == expected and observed["used_binary_float"] is False, "method": "independent Decimal parsing"}


def state_table(arguments: dict, observed: dict) -> dict:
    if arguments["present"].get("c") == "x":
        expected = {"absent": True, "null": True, "empty": False}
    else:
        expected = {"absent": True, "null": True, "empty": True}
    return {"ok": observed == expected and arguments["absent_key"] == "a", "method": "three distinct states"}


def payload_hash(arguments: dict, observed: dict) -> dict:
    payload = bytes.fromhex(arguments["payload_hex"])
    return {"ok": observed["match"] is True and observed["compressed_differs"] is True and len(hashlib.sha256(payload).hexdigest()) == 64, "method": "declared payload hash; zlib is shared"}


def damaged(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["corruption_detected"] is True and observed["integrity_claimed"] is False, "method": "a damaged stream is not intact"}


def b64_table(arguments: dict, observed: dict) -> dict:
    payload = bytes.fromhex(arguments["payload_hex"])
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    value = int.from_bytes(payload, "big")
    encoded = ""
    for shift in (18, 12, 6, 0):
        encoded += alphabet[(value >> shift) & 63]
    return {"ok": observed["decoded_hex"] == payload.hex() and observed["encoded"] == encoded, "method": "manual 24-bit groups"}


def bad_padding(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["rejected"] is True and observed["error_recorded"] is True, "method": "strict alphabet"}


def stable_digest(arguments: dict, observed: dict) -> dict:
    raw = _canonical(arguments["document"]).encode()
    digest = hashlib.sha256(raw).hexdigest()
    return {"ok": observed["reproduced"] is True and observed["altered_changes"] is True and observed["digest"] == digest, "method": "canonical bytes hashed once"}


def signature(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["payload_hex"])
    expected = "png" if raw.startswith(bytes.fromhex("89504e470d0a1a0a")) else "elf" if raw.startswith(b"\x7fELF") else "unknown"
    matches = arguments["name"].endswith("." + expected) if expected != "unknown" else False
    return {"ok": observed["detected"] == expected and observed["extension_matches_content"] is matches, "method": "independent PNG/ELF magic-byte classification"}


def total(arguments: dict, observed: dict) -> dict:
    return {"ok": observed["sum"] == sum(arguments["values"]) and observed["empty_sum"] == sum(arguments["empty"]), "method": "builtin sum, not the loop"}


def extremes(arguments: dict, observed: dict) -> dict:
    ordered = sorted(arguments["values"])
    return {"ok": observed["minimum"] == ordered[0] and observed["maximum"] == ordered[-1], "method": "sorted copy"}


def token_vector(arguments: dict, observed: dict) -> dict:
    vectors = {
        "let x = 42 + 3;": [
            {"kind": "word", "lexeme": "let", "start": 0, "end": 3},
            {"kind": "word", "lexeme": "x", "start": 4, "end": 5},
            {"kind": "symbol", "lexeme": "=", "start": 6, "end": 7},
            {"kind": "number", "lexeme": "42", "start": 8, "end": 10},
            {"kind": "symbol", "lexeme": "+", "start": 11, "end": 12},
            {"kind": "number", "lexeme": "3", "start": 13, "end": 14},
            {"kind": "symbol", "lexeme": ";", "start": 14, "end": 15},
        ],
        "x": [{"kind": "word", "lexeme": "x", "start": 0, "end": 1}],
        "": [],
    }
    expected = vectors[arguments["text"]]
    return {"ok": observed["tokens"] == expected, "method": "independent fixed token vectors"}


def ip_module(arguments: dict, observed: dict) -> dict:
    accepted, rejected = [], []
    for address in arguments["addresses"]:
        try:
            ipaddress.IPv4Address(address)
        except ipaddress.AddressValueError:
            rejected.append(address)
        else:
            accepted.append(address)
    return {"ok": observed["accepted"] == accepted and observed["rejected"] == rejected, "method": "ipaddress, not split"}


def decimal_gap(arguments: dict, observed: dict) -> dict:
    left, right, target = arguments["left"], arguments["right"], arguments["target"]
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in (left, right, target)):
        return {"ok": observed.get("rejected") is True, "method": "independent numeric-domain validation"}
    exact_decimal = Decimal(str(left)) + Decimal(str(right)) == Decimal(str(target))
    binary_total = left + right
    expected_difference = binary_total - target
    return {
        "ok": observed.get("accepted") is True
        and observed.get("sum") == binary_total
        and observed.get("target") == target
        and observed.get("equal") is (binary_total == target)
        and observed.get("decimal_equal") is exact_decimal
        and observed.get("difference") == expected_difference,
        "method": "independent Decimal exact-sum and binary-float comparison",
    }


def zlib_available() -> bool:
    return zlib.compress(b"a") != b"a"
