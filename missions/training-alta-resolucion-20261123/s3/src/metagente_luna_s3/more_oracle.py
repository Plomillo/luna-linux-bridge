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
    return {"ok": arguments["text"] == "0.10" and observed["text"] == "0.10" and observed["used_binary_float"] is False, "method": "case literal"}


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
    png = arguments["payload_hex"] == "89504e470d0a1a0a"
    detected = observed["detected"] == "png"
    matches = observed["extension_matches_content"] is arguments["name"].endswith(".png")
    return {"ok": detected is png and matches, "method": "eight-byte PNG signature"}


def total(arguments: dict, observed: dict) -> dict:
    return {"ok": observed["sum"] == sum(arguments["values"]) and observed["empty_sum"] == sum(arguments["empty"]), "method": "builtin sum, not the loop"}


def extremes(arguments: dict, observed: dict) -> dict:
    ordered = sorted(arguments["values"])
    return {"ok": observed["minimum"] == ordered[0] and observed["maximum"] == ordered[-1], "method": "sorted copy"}


def token_vector(arguments: dict, observed: dict) -> dict:
    expected = [
        {"kind": "word", "lexeme": "let", "start": 0, "end": 3},
        {"kind": "word", "lexeme": "x", "start": 4, "end": 5},
        {"kind": "symbol", "lexeme": "=", "start": 6, "end": 7},
        {"kind": "number", "lexeme": "42", "start": 8, "end": 10},
        {"kind": "symbol", "lexeme": "+", "start": 11, "end": 12},
        {"kind": "number", "lexeme": "3", "start": 13, "end": 14},
        {"kind": "symbol", "lexeme": ";", "start": 14, "end": 15},
    ]
    return {"ok": arguments["text"] == "let x = 42 + 3;" and observed["tokens"] == expected, "method": "fixed token vector"}


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
    del arguments
    exact = Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
    return {"ok": exact and observed["equal"] is False and observed["difference"] != 0, "method": "decimal exact sum versus binary result"}


def zlib_available() -> bool:
    return zlib.compress(b"a") != b"a"
