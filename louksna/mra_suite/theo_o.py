"""Oracle for laboratory hermeneutics. Does not import theo_w or fifth_w."""
from __future__ import annotations

import os


def stamp(facts):
    out = dict(facts)
    out["corpus"] = "LABORATORY_NOT_SCRIPTURE"
    out["theological_certification"] = "NOT_CERTIFIED"
    return out


BLOCKED = set(range(785, 795)) | {762, 768, 774, 841}


def expect(n, inp):
    if n in BLOCKED:
        if os.environ.get("LOUKSNA_CORPUS_DIR"):
            return {"blocked": True, "probe": "corpus-unverified"}
        if inp.get("corpus", None) == "":
            return {"blocked": True, "probe": "corpus-absent"}
        raise KeyError(n)
    return stamp(TABLE[n](inp))


def e754(inp):
    selected = "mail" if "letter" in inp["text"] and "alphabet" not in inp["text"] else "unspecified"
    return {"senses": ["mail", "character"], "selected": selected, "all_active": False}


def e755(inp):
    return {"range": 2, "selected": 1 if "letter" in inp["text"] else 0}


def e758(inp):
    return {"genre": "narrative", "past": "delivered" in inp["text"], "poetry": False}


def e759(_inp):
    return {"roles": ["agent", "verb", "object"]}


def e760(inp):
    return {"s1": inp["text"], "s2": "He delivered it before sunset.", "isolated": False}


def e761(inp):
    return {"document_purpose": "delivery", "used": "delivered" in inp["text"]}


def e766(_inp):
    return {"quoted": False, "class": "echo"}


def e767(_inp):
    return {"marked_quote": False, "class": "not-citation"}


def e769(_inp):
    text = "The courier left, but the letter remained."
    return {"marker": "but", "function": "contrast" if " but " in text else "", "text": text}


def e770(_inp):
    return {"premises": 1, "conclusion": "delivered"}


def e771(_inp):
    figure = "the deadline was a wall"
    return {"figure": figure, "literal_wall": figure == "there was a wall"}


def e772(_inp):
    return {"central": "delivery", "detail": "blue coat", "allegorized": False}


def e773(_inp):
    return {"lines": 2, "parallel": True, "literal_forced": False}


def e775(_inp):
    return {"symbol": "lamp", "certainty": "unspecified"}


def e780(_inp):
    return {"observation": "letter", "inference": "motive", "separated": True}


def e784(_inp):
    return {"stages": ["text", "observation", "interpretation"], "scripture": "NOT_EXECUTED"}


def e797(_inp):
    return {"premises": ["p"], "inference": "modus-ponens", "conclusion": "q"}


def e798(_inp):
    return {"objection": "the letter was never sent", "stated": True, "evaluated": False}


def e799(_inp):
    return {"a": "mail", "b": "legal-document", "forced_equal": "mail" == "legal-document"}


def e800(_inp):
    return {"application": "check the address", "attributed_to_text": False}


def e803(_inp):
    return {"primary": "text", "descriptive": "glossary", "promoted": False}


def e804(_inp):
    return {"left": "sent", "right": "not-sent", "merged": False}


def e805(_inp):
    return {"earlier": "sent", "later": "received", "historical_claim": False}


def e806(_inp):
    return {"term": "letter", "defs": 2, "forced": False}


def e807(_inp):
    return {"claim": "authorized by decree", "evidence": False, "requested": True}


def e808(_inp):
    return {"denomination": "", "attributed": False}


def e809(_inp):
    return {"steps": ["observe", "infer"], "hidden": False}


def e810(_inp):
    return {"tension": True, "hidden": False}


def e811(_inp):
    return {"exegesis": "delivered", "doctrine": "duty", "collapsed": False}


def e812(_inp):
    votes = [1, 1]
    return {"votes": votes, "universal": len(set(votes)) == 1 and False}


def e813(_inp):
    return {"other_premise": "the letter was delayed", "caricature": False}


def e814(_inp):
    return {"criteria": "text-presence", "same": True}


def e815(_inp):
    return {"text": "delivered", "institution": "office", "collapsed": "delivered" == "office"}


def e816(_inp):
    return {"v1": "sent", "v2": "delivered", "kept_v1": True}


def e819(_inp):
    return {"stages": ["observe", "check-added-tokens"], "rules": 1}


def e821(_inp):
    return {"sees_heldout": False, "metric": "gloss-match"}


def e822(_inp):
    return {"false_accept": True, "token": "blockchain"}


def e823(_inp):
    return {"flagged": "blockchain" not in "The courier delivered the letter on the third day.", "control": "added-token"}


def e824(_inp):
    return {"choice": "added-token-check", "names_hidden": True}


def e825(inp):
    return {"held": "The lamp was on the table.", "in_design": inp["text"] == "The lamp was on the table."}


def e826(_inp):
    text = "Deliver the letter by blockchain."
    return {"genre": "instruction", "flagged": "blockchain" in text, "text": text}


def e827(_inp):
    return {"procedure": "flag-added-token", "requirement": "token-not-in-text"}


def e828(_inp):
    return {"primary": "text", "secondary": "note", "primary_wins": True}


def e829(_inp):
    return {"marked": False, "called_citation": False}


def e830(_inp):
    return {"dated": False, "status": "hypothesis"}


def e831(_inp):
    return {"a": "courier", "b": "messenger", "intent_attributed": False}


def e832(_inp):
    return {"steps": 2, "hidden": False}


def e833(_inp):
    return {"kept": True}


def e836(_inp):
    return {"token": "blockchain", "anachronism": True}


def e837(_inp):
    return {"etymology_used": False, "contextual": "mail"}


def e838(_inp):
    return {"possible": 2, "active": 1}


def e839(_inp):
    return {"displaced": True, "external": "court"}


def e840(_inp):
    return {"normative": False}


def e842(_inp):
    return {"depends_on": "p", "detached": False}


def e843(_inp):
    return {"control_removed": True, "glosa_passes": True, "restored_flags": True}


def e845(_inp):
    return {"independence": "DISTINCT_MODULE"}


def e846(_inp):
    flag = "blockchain" not in "The courier delivered the letter on the third day."
    return {"first": flag, "second": flag}


def e847(_inp):
    return {"still_flags": "blockchain" not in "The courier delivered the letter on the third day."}


def e848(_inp):
    before, after = "sent", "delivered"
    return {"before": before, "after": after, "silent": before == after}


def e849(_inp):
    return {"by_preference": False, "by_result": True}


def e850(_inp):
    m2 = "flag-anachronism"
    return {"m2": m2, "same_as_m1": m2 == "flag-added-token"}


def e851(_inp):
    text = "The lamp was on the blockchain."
    return {"text": text, "in_design": False, "flagged": "blockchain" in text}


def e852(_inp):
    source = ""
    return {"source": source, "status": "uncertain" if source == "" else "sourced"}


def e853(_inp):
    old_catch = False
    new_catch = "blockchain" not in "The courier delivered the letter on the third day."
    return {"old_catch": old_catch, "new_catch": new_catch}


def e854(_inp):
    steps = 0
    reason = ""
    stopped = False
    try:
        def rec(n):
            nonlocal steps
            steps += 1
            if n >= 3:
                raise RuntimeError("DEPTH_LIMIT")
            return rec(n + 1)
        rec(0)
    except RuntimeError as exc:
        stopped = True
        reason = str(exc)
    return {"steps": steps, "reason": reason, "stopped": stopped}


TABLE = {i: globals()[f"e{i}"] for i in [
    754, 755, 758, 759, 760, 761, 766, 767, 769, 770, 771, 772, 773, 775, 780, 784,
    797, 798, 799, 800, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816,
    819, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831, 832, 833, 836, 837, 838, 839,
    840, 842, 843, 845, 846, 847, 848, 849, 850, 851, 852, 853, 854,
]}
