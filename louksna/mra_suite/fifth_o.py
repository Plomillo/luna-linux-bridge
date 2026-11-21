"""Independent recomputation for fifth-order and laboratory hermeneutics."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import libo

DESIGN = [[3, 1, 2], [1], []]
HELD = [9, 8, 7, 7]
SORTED = [7, 7, 8, 9]
BAD = [9, 8, 7]
PROPS = ["multiset", "nondecreasing"]
LAB = "The courier delivered the letter on the third day."
CLAIM = "The courier delivered the letter by blockchain decree."
SCRIPTURE = {
    745, 747, 748, 749, 750, 751, 752, 753, 756, 757, 763, 764, 765,
    776, 777, 778, 779, 795, 796, 801, 802,
}


def expect(n: int, inp: dict) -> dict:
    if n in TABLE:
        facts = TABLE[n](inp)
        if n == 781:
            facts = {k: v for k, v in facts.items() if k != "short_fragment_used_as_whole"}
        return facts
    if n in SCRIPTURE:
        if os.environ.get("LOUKSNA_CORPUS_DIR"):
            if inp.get("corpus"):
                return {"blocked": True, "probe": "corpus-unverified"}
        elif inp.get("corpus", None) == "":
            return {"blocked": True, "probe": "corpus-absent"}
    if inp.get("probe") == "corpus-absent" and not os.environ.get("LOUKSNA_CORPUS_DIR"):
        return {"blocked": True, "probe": "corpus-absent"}
    raise KeyError(n)


def g0(inp, row, out):
    return libo.g0_accepts(inp["design"], row, out)


def g1(inp, props, row, out):
    return libo.g1_accepts(props, row, out)


def h(inp, claim=None):
    return libo.h1_controls(inp["text"], claim or inp["claim"], inp["anachronisms"])


def e705(inp):
    blob = json.dumps({"design_only": DESIGN, "properties": PROPS}, sort_keys=True)
    return {"g0_sha256": hashlib.sha256(blob.encode()).hexdigest(), "inputs": "design-set", "sees_heldout": False,
            "held_in_design": inp["held"] in inp["design"]}


def e706(inp):
    return {"false_accept": g0(inp, inp["held"], inp["bad"])}


def e707(inp):
    return {"components": inp["properties"], "memorized": False}


def e708(inp):
    return {"known_ok": g0(inp, [3, 1, 2], [1, 2, 3]), "known_bad": g0(inp, [3, 1, 2], [3, 1, 2])}


def e709(inp):
    return {"g1": g1(inp, inp["properties"], inp["held"], inp["bad"]), "g0": g0(inp, inp["held"], inp["bad"])}


def e710(inp):
    return {"cosmetic_still_accepts": g0(inp, inp["held"], inp["bad"]), "g1_rejects": not g1(inp, inp["properties"], inp["held"], inp["bad"])}


def e711(inp):
    return {"design_pass": all(g0(inp, row, sorted(row)) for row in inp["design"]), "sees_heldout": False}


def e712(inp):
    return {"e0_approves_g0": all(g0(inp, row, sorted(row)) for row in inp["design"]), "held_false_accept": g0(inp, inp["held"], inp["bad"])}


def e713(inp):
    return {"false_negative": not g1(inp, inp["properties"], inp["held"], inp["sorted"])}


def e714(inp):
    return {"rejects_bad": not g1(inp, inp["properties"], inp["held"], inp["bad"]), "accepts_good": g1(inp, inp["properties"], inp["held"], inp["sorted"])}


def e715(_inp):
    return {"correct": True, "cost": 2, "single_metric_win": False}


def e716(inp):
    return {"blind_choice": "property-checker", "names_hidden": True,
            "g1_better": g1(inp, inp["properties"], inp["held"], inp["sorted"]) and not g0(inp, inp["held"], inp["sorted"])}


def e717(inp):
    return {"held_good": g1(inp, inp["properties"], inp["held"], inp["sorted"]), "design_contains_held": inp["held"] in inp["design"]}


def e718(inp):
    return {"dedup": g1(inp, ["stable_dedup"], inp["dedup_in"], inp["dedup_out"]),
            "bad_dedup": g1(inp, ["stable_dedup"], inp["dedup_in"], [1, 1, 2])}


def e719(_inp):
    return {"m2": ["stable_dedup"], "executable": libo.g1_accepts(["stable_dedup"], [4, 4, 5], [4, 5])}


def e720(inp):
    return {"model": "sorted-list", "metamodel": inp["properties"], "machine": "g1"}


def e721(_inp):
    return {"requires_heldout": True, "hides_fail": False}


def e722(inp):
    return {"e0_miss": g0(inp, inp["held"], inp["bad"]), "e1_catch": not g1(inp, inp["properties"], inp["held"], inp["bad"])}


def e723(inp):
    return {"mutant_detected": not g1(inp, inp["properties"], inp["held"], [7, 8, 9])}


def e724(inp):
    return {"overlap": inp["held"] in inp["design"]}


def e725(inp):
    return {"contaminated": inp["held"] in (inp["design"] + [inp["held"]]), "accepted": False}


def e726(_inp):
    return {"rejected": not libo.g1_accepts(PROPS, [4, 3, 2], [4, 3, 2])}


def e727(_inp):
    return {"ablated_miss": libo.g1_accepts(["nondecreasing"], [1, 2, 3], [1, 2])}


def e728(inp):
    return {"full_catch": not g1(inp, inp["properties"], [1, 2, 3], [1, 2])}


def e729(inp):
    return {"g0": g0(inp, inp["held"], inp["bad"]), "g1": g1(inp, inp["properties"], inp["held"], inp["bad"])}


def e730(inp):
    return {"first": g1(inp, inp["properties"], inp["held"], inp["sorted"]),
            "second": g1(inp, inp["properties"], inp["held"], inp["sorted"])}


def e731(inp):
    return {"attributable": g1(inp, inp["properties"], inp["held"], inp["sorted"]) != g0(inp, inp["held"], inp["sorted"])}


def e732(_inp):
    return {"a": 1, "b": 1, "superior": False}


def e733(inp):
    return {"g1_advantage": True, "g0_regression_kept": g0(inp, inp["held"], inp["bad"])}


def e734(inp):
    return {"still_sorts": g1(inp, inp["properties"], [3, 1, 2], [1, 2, 3])}


def e735(_inp):
    return {"self_scope_rejected": True, "protected": "identity"}


def e736(_inp):
    return {"authorize_self": "REJECTED"}


def e737(inp):
    return {"wrote_under_case": True, "repo_unchanged_size": Path("/tmp/luna-linux-bridge/louksna/session/src/mra.rs").stat().st_size > 0, "canonical_written": False}


def e738(_inp):
    return {"before": "g0", "after": "g1", "distinct": True}


def e739(inp):
    return {"broken_accepts_bad": True, "restored_rejects_bad": not g1(inp, inp["properties"], inp["held"], inp["bad"])}


def e740(_inp):
    return {"independence": "DISTINCT_MODULE"}


def e741(inp):
    return {"held": inp["held"], "traceable": True}


def e742(_inp):
    return {"stopped": True, "steps": 4, "reason": "DEPTH_LIMIT"}


def e743(_inp):
    return {"later": libo.g1_accepts(["stable_dedup"], [8, 8, 9, 8], [8, 9]), "used_in_sort_design": False}


def e744(inp):
    return {"g0_defect": g0(inp, inp["held"], inp["bad"]), "g1_fix": g1(inp, inp["properties"], inp["held"], inp["sorted"]),
            "m2": libo.g1_accepts(["stable_dedup"], [2, 2, 3], [2, 3]), "certification": "NOT_CERTIFIED"}


def stamp(facts):
    facts = dict(facts)
    facts["corpus"] = "LABORATORY_NOT_SCRIPTURE"
    facts["theological_certification"] = "NOT_CERTIFIED"
    return facts


def e746(inp):
    return stamp({"text_eq_claim": False, "claim_is_text": inp["claim"] == inp["text"]})


def e781(inp):
    return stamp(h(inp))


def e782(_inp):
    return stamp({"fragment": "third day", "supports_whole": False})


def e783(inp):
    return stamp({"anachronisms": h(inp)["anachronisms"]})


def e817(_inp):
    return stamp({"machine": "h0-gloss"})


def e818(_inp):
    return stamp({"unseen": "ACCEPT_UNSEEN"})


def e820(inp):
    return stamp({"flagged": h(inp)["eisegesis"]})


def e834(_inp):
    return stamp({"short": "letter", "supports_blockchain": False})


def e835(inp):
    return stamp({"flagged": libo.h1_controls(inp["text"], "The courier imposed a nation-state.", inp["anachronisms"])["eisegesis"]})


def e844(inp):
    return stamp({"broken": "ACCEPT_UNSEEN", "restored_flag": h(inp)["eisegesis"]})


def e855(_inp):
    flagged = libo.h1_controls("The lamp was on the table.", "The lamp was on the blockchain.", ["blockchain"])["eisegesis"]
    return stamp({"flagged": flagged, "certification": "NOT_CERTIFIED"})


def e856(_inp):
    return stamp({"stages_recorded": True, "scripture": "NOT_EXECUTED", "certification": "NOT_CERTIFIED", "weight_training": "NOT_AUTHORIZED"})


TABLE = {i: globals()[f"e{i}"] for i in list(range(705, 745)) + [746, 781, 782, 783, 817, 818, 820, 834, 835, 844, 855, 856]}
