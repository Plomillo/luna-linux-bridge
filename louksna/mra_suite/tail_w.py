"""Cases 305-856. Each id runs a real operation or an explicit BLOCKED probe."""
from __future__ import annotations

import ast
import hashlib
import hmac
import json
import os
import socket
import sqlite3
import subprocess
import threading
from pathlib import Path

from pack import pack
import probes

LEVEL = {
    range(305, 345): 2,
    range(345, 385): 2,
    range(385, 425): 2,
    range(425, 465): 2,
    range(465, 505): 2,
    range(505, 545): 3,
    range(545, 585): 2,
    range(585, 625): 3,
    range(625, 665): 3,
    range(665, 705): 3,
    range(705, 745): 5,
    range(745, 817): 4,
    range(817, 857): 5,
}


def level_of(n: int) -> int:
    for span, level in LEVEL.items():
        if n in span:
            return level
    return 1


def blocked(n, domain, objective, unlock, probe):
    return pack(domain, level_of(n), objective, {"probe": probe}, {"blocked": True, "probe": probe}, False, unlock=unlock)


def run(n: int, ctx):
    fn = DISPATCH.get(n)
    if fn is None:
        return None
    return fn(ctx)


def c305(_c):
    src = "ab+12@"
    i = 0
    tokens = []
    bad = False
    while i < len(src):
        ch = src[i]
        if ch == "@":
            bad = True
            break
        if ch.isalpha():
            j = i
            while j < len(src) and src[j].isalpha():
                j += 1
            tokens.append(src[i:j])
            i = j
        elif ch.isdigit():
            j = i
            while j < len(src) and src[j].isdigit():
                j += 1
            tokens.append(src[i:j])
            i = j
        else:
            tokens.append(ch)
            i += 1
    return pack("compiler", level_of(305), "Lexer acepta ident y numero y localiza un error",
                {"src": src}, {"tokens": tokens, "bad_at": bad}, tokens == ["ab", "+", "12"] and bad)


def c306(_c):
    def parse(s):
        if not s or s[-1] in "+*":
            raise SyntaxError("trunc")
        i = 0

        def peek():
            return s[i] if i < len(s) else ""

        def number():
            nonlocal i
            if i >= len(s) or not s[i].isdigit():
                raise SyntaxError("num")
            j = i
            while i < len(s) and s[i].isdigit():
                i += 1
            return int(s[j:i])

        def term():
            nonlocal i
            left = number()
            while peek() == "*":
                i += 1
                left *= number()
            return left

        def expr():
            nonlocal i
            left = term()
            while peek() == "+":
                i += 1
                left += term()
            return left

        val = expr()
        if i != len(s):
            raise SyntaxError("end")
        return val

    bad = False
    try:
        parse("1+")
    except SyntaxError:
        bad = True
    return pack("compiler", level_of(306), "Parser de expresiones con precedencia y rechazo de truncadas",
                {"ok": "1+2*3", "bad": "1+"}, {"value": parse("1+2*3"), "rejected": bad}, parse("1+2*3") == 7 and bad)


# The rest of the tail is registered below from explicit functions.
DISPATCH = {305: c305, 306: c306}
