"""Reference checks that do not call the executors."""
from __future__ import annotations

import hashlib
import ipaddress
import zlib
from decimal import Decimal, InvalidOperation

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
    try:
        expected = str(Decimal(arguments["text"]))
    except InvalidOperation:
        return {"ok": observed.get("rejected") is True and observed.get("reason") == "invalid-decimal", "method": "fixed invalid Decimal rejection"}
    return {"ok": observed.get("rejected", False) is False and observed.get("text") == expected and observed.get("used_binary_float") is False, "method": "independent Decimal parsing"}


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
    try:
        payload = bytes.fromhex(arguments["payload_hex"])
    except ValueError:
        return {"ok": observed.get("rejected") is True and observed.get("reason") == "invalid-hex-input", "method": "independent malformed-hex rejection"}
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    value = int.from_bytes(payload, "big")
    encoded = ""
    for shift in (18, 12, 6, 0):
        encoded += alphabet[(value >> shift) & 63]
    return {"ok": observed.get("rejected") is False and observed["decoded_hex"] == payload.hex() and observed["encoded"] == encoded, "method": "manual 24-bit groups"}


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
    left, right, target = (Decimal(str(arguments[key])) for key in ("left", "right", "target"))
    exact = left + right == target
    binary_total = float(arguments["left"]) + float(arguments["right"])
    expected_difference = binary_total - float(arguments["target"])
    ok = observed.get("decimal_exact") is exact and observed.get("equal") is (binary_total == float(arguments["target"])) and abs(observed.get("difference", 0.0) - expected_difference) <= 1e-16
    return {"ok": ok, "method": "Decimal reference plus independent binary arithmetic"}


def zlib_available() -> bool:
    return zlib.compress(b"a") != b"a"


def protobuf_wire_oracle(arguments: dict, observed: dict) -> dict:
    vectors = {
        "080712036e6577": {"rejected": False, "accepted": True, "known_fields": {"1": 7}, "unknown_fields": [2], "consumed": 7},
        "0807": {"rejected": False, "accepted": True, "known_fields": {"1": 7}, "unknown_fields": [], "consumed": 2},
        "08071205": {"rejected": True, "reason": "truncated-length-delimited"},
    }
    expected = vectors.get(arguments["wire_hex"])
    return {"ok": expected is not None and observed == expected, "method": "frozen protobuf wire-format vectors; independent of runtime decoder"}


def schema_v2_oracle(arguments: dict, observed: dict) -> dict:
    source = arguments["document"]
    if source == {"version": 1, "name": "Luna", "count": 3}:
        expected = {"rejected": False, "migrated": True, "document": {"version": 2, "name": "Luna", "count": 3, "enabled": True}, "invariants": {"name": "Luna", "count": 3}}
    elif source == {"version": 1, "name": "", "count": 0}:
        expected = {"rejected": False, "migrated": True, "document": {"version": 2, "name": "", "count": 0, "enabled": True}, "invariants": {"name": "", "count": 0}}
    else:
        expected = {"rejected": True, "reason": "unsupported-version"}
    return {"ok": observed == expected, "method": "frozen v1-to-v2 migration vectors and invariant table"}


def unknown_field_oracle(arguments: dict, observed: dict) -> dict:
    record = arguments["record"]
    known_fields = arguments["known_fields"]
    if record == {"name": "Luna", "version": 2, "extra": "future"} and known_fields == ["name", "version"]:
        expected = {"rejected": False, "accepted": True, "known": {"name": "Luna", "version": 2}, "unknown": {"extra": "future"}, "policy": "PRESERVE_UNKNOWN_SEPARATELY"}
    elif record == {"name": "Luna", "version": 2} and known_fields == ["name", "version"]:
        expected = {"rejected": False, "accepted": True, "known": {"name": "Luna", "version": 2}, "unknown": {}, "policy": "PRESERVE_UNKNOWN_SEPARATELY"}
    else:
        expected = {"rejected": True, "reason": "known-field-type"}
    return {"ok": observed == expected, "method": "frozen known/unknown field partition and validation vectors"}


def cbor_vector_oracle(arguments: dict, observed: dict) -> dict:
    document = arguments["document"]
    if document == {"name": "Luna", "count": 2, "enabled": True, "items": [1, None, False]}:
        expected = {"rejected": False, "accepted": True, "wire_hex": "a4646e616d65644c756e6165636f756e7402656974656d738301f6f467656e61626c6564f5", "decoded": document, "same_types": True}
    elif document == {}:
        expected = {"rejected": False, "accepted": True, "wire_hex": "a0", "decoded": {}, "same_types": True}
    else:
        expected = {"rejected": True, "reason": "unsupported-map-key"}
    return {"ok": observed == expected, "method": "fixed canonical CBOR vectors independent of encoder/decoder"}
