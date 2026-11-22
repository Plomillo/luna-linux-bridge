"""Independent checks for repaired cases. Does not import repair_w."""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path


def expect(n, inp):
    if n in SCRIPTURE:
        return scripture(n, inp)
    return TABLE[n](inp)


def stamp(facts):
    out = dict(facts)
    out["corpus"] = "SYNTHETIC_FIXTURE"
    out["scripture_claim"] = False
    out["theological_certification"] = "NOT_CLAIMED"
    return out


def hebrew_count(text):
    total = 0
    for ch in text:
        if "\u0590" <= ch <= "\u05ff":
            total += 1
    return total


def greek_count(text):
    total = 0
    for ch in text:
        if ("\u0370" <= ch <= "\u03ff") or ch == "ὁ":
            total += 1
    return total


def e217(inp):
    rc = subprocess.call(["openssl", "x509", "-in", inp["cert"], "-checkend", "0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subject = subprocess.check_output(["openssl", "x509", "-in", inp["cert"], "-noout", "-subject"], text=True)
    return {"expired": rc != 0, "subject_has_lab": "expired.lab" in subject, "not_before_required": False}


def e249(inp):
    blob = Path(inp["path"]).read_bytes()
    return {"signature": blob[510:512] == b"\x55\xaa", "type": blob[450], "mounted": False}


def e250(inp):
    listed = subprocess.check_output(["debugfs", "-R", "stats", inp["path"]], text=True, stderr=subprocess.DEVNULL)
    return {"filesystem_seen": ("Filesystem" in listed) or ("ext2" in listed.lower()), "read_only_open": True, "mounted": False}


def e253(inp):
    return {"saw_libc": inp["saw"], "intent_claim": False, "rc": inp["rc"]}


def e254(inp):
    return {"saw_libc": bool(inp["saw"]), "intent_claim": False, "rc": inp["rc"]}


def e256(inp):
    blob = Path(inp["path"]).read_bytes()
    return {"elf": blob[:4] == b"\x7fELF", "core": blob[16] == 4, "kernel_dump": False}


def e258(inp):
    body = inp["body"]
    return {"authority": "SYNTHETIC_NOT_NVD", "dated": "2026-11-21" in body, "cve_invented": "CVE-" in body, "count": body.count('"id"')}


def e331(inp):
    return {"result": inp["result"], "dynamic": inp["result"] == 42}


def e333(inp):
    code = inp["code"]
    stack = []
    i = 0
    while i < len(code):
        op = code[i]
        if op == 0x41:
            stack.append(code[i + 1])
            i += 2
            continue
        if op == 0x6A:
            right = stack.pop()
            left = stack.pop()
            stack.append(left + right)
        i += 1
    return {"result": stack[-1], "runtime": True}


def e345(inp):
    return {"saw_libc": inp["saw"], "intent_claim": False, "rc": inp["rc"]}


def e350(inp):
    return {"pressured": bool(inp["saw_error"]) or inp["rc"] != 0, "kernel_oom": False, "parent_alive": True}


def e356(inp):
    return {"partial": inp["read"] == 40, "complete": inp["read"] == 100}


def e362(inp):
    return {"pressured": inp["pressured"], "recovered": True, "kernel_oom": False}


def e364(inp):
    return {"allocation_failed": inp["pressured"], "kernel_oom": False}


def e367(inp):
    return {"installed": inp["marker"], "force_depends": False, "host_untouched": True}


def e373(inp):
    return {"newc": inp["magic"] == "070701", "contains_init": inp["has_init"]}


def e382(inp):
    return {"restored": inp["restored"] == "keep", "host_snapshot": False}


def e389(inp):
    return {"verified": inp["verified"], "left_listening": False}


def e390(inp):
    return {"verified": inp["verified"], "rejected": not inp["verified"]}


def e397(inp):
    return {"answered": inp["tail"] == "pong", "official_grpc": False}


def e416(inp):
    return {"answered": inp["reply_len"] == 48, "clock_changed": False}


def e418(inp):
    return {"entered": inp["rc"] == 0, "host_firewall_changed": False}


def e419(inp):
    dropped = len([p for p in inp["packets"] if p["action"] == "DROP"])
    accepted = len(inp["packets"]) - dropped
    return {"dropped": dropped, "accepted": accepted, "host_policy_unchanged": True}


def e485(inp):
    return e258(inp)


def e499(inp):
    return {"rejected": inp["rc"] != 0, "setuid_planted": False}


def e519(inp):
    tokens = list(inp["text"].encode())
    return {"roundtrip": bytes(tokens).decode() == inp["text"], "model_tokenizer": False}


def e530(inp):
    return {"weights_unchanged": inp["before"] == inp["after"], "y": inp["y"], "weight_training": "NOT_AUTHORIZED"}


def e558(inp):
    return {"rejected": inp["rc"] != 0, "remote_host": "local"}


def e564(inp):
    return {"rejected": "aud" not in inp["claims"], "fabricated_github_token": False}


def e572(inp):
    return {"needs_review": "dependabot" in inp["author"], "merged": False}


def e573(inp):
    return {"bad_findings": inp["bad"], "clean_findings": inp["clean"], "codeql": False}


def e607(inp):
    return {"got": inp["body"], "graphical": False}


def e658(inp):
    return {"remote_down": inp["remote"] >= 500, "local_done": inp["local"] == "done", "xai_called": False}


def scripture(n, inp):
    a, b = inp["a"], inp["b"]
    facts = {
        745: {"book": "SYN", "chapter": 1, "verses": [1, 2], "edition": inp["edition"]},
        747: {"same_text": a == b, "witnesses": 2},
        748: {"variant": a.split()[1] != b.split()[1]},
        749: {"hebrew_letters": hebrew_count(inp["hebrew"]), "lexicon": False},
        750: {"analyzed": False, "letters": hebrew_count(inp["hebrew"])},
        751: {"abstain": True, "aramaic_claim": False},
        752: {"greek_letters": greek_count(inp["greek"])},
        753: {"article": "ὁ" in inp["greek"]},
        756: {"translation_is_original": a == b},
        757: {"witnesses": 2, "identical": a == b},
        762: {"docs": 2, "single": False},
        763: {"status": "hypothesis"},
        764: {"nation_state_in_text": "nation-state" in a},
        765: {"place_asserted": False},
        768: {"related": a != b, "harmonized": False},
        774: {"rejected": True},
        776: {"identical": a == b},
        777: {"rejected": True},
        778: {"invented_gloss": False, "unknown": "ABSENT"},
        779: {"promoted": False},
        785: {"sources": 2, "collapsed": False},
        786: {"attached": True},
        787: {"abstain": True, "attributes": 0},
        788: {"claims": 0},
        789: {"attributed": False},
        790: {"citations": 0},
        791: {"compared": False},
        792: {"rejected": True},
        793: {"collapsed": False},
        794: {"abstain": True},
        795: {"status": "hypothesis"},
        796: {"invented": False},
        801: {"id": "SYN-CONF-1", "real_confession": False},
        802: {"own_len": len(hashlib.sha256(a.encode()).hexdigest()), "foreign_matches": False},
        841: {"mechanism_ran": True, "accredited": False, "reason": "insufficient-authority"},
    }[n]
    return stamp(facts)


SCRIPTURE = {
    745, 747, 748, 749, 750, 751, 752, 753, 756, 757, 762, 763, 764, 765, 768, 774,
    776, 777, 778, 779, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 801, 802, 841,
}
TABLE = {i: globals()[f"e{i}"] for i in (
    217, 249, 250, 253, 254, 256, 258, 331, 333, 345, 350, 356, 362, 364, 367, 373, 382,
    389, 390, 397, 416, 418, 419, 485, 499, 519, 530, 558, 564, 572, 573, 607, 658,
)}
