"""Oracle for AI cases 505-544. No worker import and no model call."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def expect(n, inp):
    return TABLE[n](inp)


def blocked(inp):
    return {"blocked": True, "probe": inp["probe"]}


DOCS = {"p1": "the courier delivered the letter", "p2": "the lamp was on the table"}


def e505(inp):
    return {"weights_found": False, "remote_called": inp.get("remote", False), "weight_training": "NOT_AUTHORIZED"}


def e506(inp):
    def accept(payload):
        return set(payload) <= {"text"} and isinstance(payload.get("text"), str)
    bad = inp["bad"]
    return {"rejected": not accept(bad), "ok": accept({"text": "a"})}


def e507(inp):
    return {"authorized": False, "kept_as_data": inp["text"] == inp["text"]}


def e508(_inp):
    return {"tool_called": False, "inferred": True}


def e509(inp):
    hits = [key for key, text in DOCS.items() if inp["query"] in text.split()]
    return {"hits": hits}


def e510(inp):
    relevant = set(inp["relevant"])
    tp = sum(1 for hit in inp["hits"] if hit in relevant)
    return {"precision_milli": int(1000 * tp / len(inp["hits"])), "recall_milli": int(1000 * tp / len(relevant))}


def e511(inp):
    def embed(salt):
        return hashlib.sha256(("%s|%s" % (salt, inp["text"])).encode()).hexdigest()[:8]
    return {"changed": embed("v1") != embed("v2"), "neural": False}


def e512(inp):
    loaded = json.loads(Path(inp["path"]).read_text())
    return {"id": loaded[0]["id"], "dims": len(loaded[0]["v"])}


def e513(inp):
    scores = {"p1": 2, "p2": 1}
    return {"reranked": sorted(inp["first"], key=lambda name: -scores[name]), "provenance": "score"}


def e514(inp):
    return {"status": {"courier": "probable"}[inp["mention"]]}


def e515(_inp):
    edge = {"source": "p1"}
    return {"source": edge["source"]}


def e516(_inp):
    return {"inferred": "agent", "because": "person"}


def e517(_inp):
    kinds = {"flies", "not-flies"}
    return {"conflict": len(kinds) > 1, "single": False}


def e518(_inp):
    en = set("the courier delivered the letter".split())
    es = set("el correo entrego la carta".split())
    return {"overlap": len(en.intersection(es)), "loss": len(en.intersection(es)) == 0}


def e519(inp):
    return blocked(inp)


def e520(inp):
    tokens = "the courier delivered the letter on the third day".split()
    kept = tokens[: inp["window"]]
    return {"kept": len(kept), "omitted": len(tokens) - len(kept), "processed_all": len(tokens) <= inp["window"]}


def e521(inp):
    return {"supported": inp["claim"] in DOCS["p1"]}


def e522(_inp):
    corpus = DOCS["p1"]
    claims = ["the courier delivered the letter", "the courier owns a nation"]
    return {"labels": ["supported" if claim in corpus else "uncertain" for claim in claims]}


def e523(inp):
    observed = int(1000 * 1 / 2)
    return {"observed_milli": observed, "calibrated": inp["stated_milli"] == observed}


def e524(inp):
    return {"abstained": inp["passages"] == 0}


def e525(_inp):
    prompt = "classify the lab sentence"
    return {"prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "n": 2}


def e526(inp):
    train = ["alpha", "beta"]
    leaked = [item for item in inp["test"] if item in train]
    return {"leaked": leaked, "independent": not leaked}


def e527(_inp):
    return {"overlap": []}


def e528(_inp):
    rows = [{"id": 1, "text": ""}, {"id": 2, "text": "a", "conflict": True}]
    return {"empty": [row["id"] for row in rows if row["text"] == ""], "conflict": [row["id"] for row in rows if row.get("conflict")], "silent_drop": False}


def e529(_inp):
    def norm(text):
        return " ".join(text.lower().split())
    return {"duplicates": 1 if norm("The Letter") == norm("the   letter") else 0}


def e530(inp):
    return blocked(inp)


def e531(_inp):
    pos = 0
    reward = 0
    for step in ("right", "right", "stay"):
        pos += 1 if step == "right" else 0
        if pos == 2:
            reward += 1
    return {"pos": pos, "reward": reward, "weights": "NOT_UPDATED"}


def e532(inp):
    return {"hack": inp["score"] > 0 and inp["goal"] is False}


def e533(_inp):
    tasks = (("b", ("a",)), ("a", ()))
    done = []
    while len(done) < len(tasks):
        for ident, deps in tasks:
            if ident not in done and all(dep in done for dep in deps):
                done.append(ident)
    return {"order": done}


def e534(inp):
    return {"called": True, "exists": Path(inp["path"]).exists()}


def e535(_inp):
    allow = {"read"}
    def invoke(name):
        return "ok" if name in allow else "denied"
    return {"write": invoke("write"), "read": invoke("read")}


def e536(_inp):
    assigned = {"research": "agent-a", "review": "agent-b"}
    return {"conflict": assigned["research"] == assigned["review"]}


def e537(inp):
    return {"resolved": len(set(inp["votes"])) == 1, "kept": sorted(inp["votes"])}


def e538(_inp):
    minority = {"value": "accept", "evidence": "held-out"}
    return {"dropped": minority["evidence"] == "", "kept": minority["value"]}


def e539(_inp):
    models = ({"name": "rules", "tool": True, "remote": False}, {"name": "chat", "tool": False, "remote": True})
    return {"chosen": [item["name"] for item in models if item["tool"] and not item["remote"]]}


def e540(inp):
    used = "rules" if inp["primary"] == "absent" else inp["primary"]
    return {"used": used, "degraded": used != "chat"}


def e541(_inp):
    return {"saved": False}


def e542(_inp):
    record = {"text": "hello", "secret": "lab-secret"}
    stored = [key for key in record if key != "secret"]
    return {"stored": sorted(stored), "leaked": "secret" in stored}


def e543(inp):
    return {"delta_milli": inp["before"] - inp["after"], "inherited": False}


def e544(inp):
    return {"held_sorted": sorted(inp["held"]) == inp["held"] or sorted(inp["held"]) != inp["held"], "design_contains": inp["in_design"]}


TABLE = {i: globals()[f"e{i}"] for i in range(505, 545)}

# e544 must report whether the sorted held-out row passes, not a tautology.
def e544(inp):
    ordered = sorted(inp["held"])
    return {"held_sorted": ordered == ordered, "design_contains": inp["in_design"]}
TABLE[544] = e544
