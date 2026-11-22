"""Independent expectations for MRA-5O-037..144. Does not import complement_w."""
from __future__ import annotations

from pathlib import Path


def expect(n, inp):
    return TABLE[n](inp)


def e037(inp):
    probes = inp["probes"]
    absent = sorted(k for k, v in probes.items() if not v)
    return {"present": sum(1 for v in probes.values() if v), "absent": absent, "invented": False}


def e038(inp):
    executable = {"sha256": inp["sha_len"] == 64, "wayland-session": inp["socket"]}
    gap = sorted(k for k in inp["declared"] if not executable[k])
    return {"executable": executable, "gap": gap}


def e039(inp):
    observation = inp["text"].split()[0]
    return {"observation": observation, "inference_in_text": inp["inference"] in inp["text"], "hypothesis": inp["inference"], "uncertainty": True}


def e040(inp):
    assumed = all(j["conclusion"] == "success" for j in inp["jobs"])
    skipped = sum(1 for j in inp["jobs"] if j["conclusion"] == "skipped")
    return {"assumption_holds": assumed, "skipped": skipped}


def e041(inp):
    corrected = inp["a"] + inp["b"]
    return {"previous_kept": inp["previous"], "corrected": corrected, "hidden": inp["previous"] == corrected}


def e042(inp):
    return {"prior_kept": True, "revised": "hold", "conflict_preserved": len(set(inp["sources"])) == 2}


def e043(inp):
    missing = [s for s in inp["required"] if s not in inp["steps"]]
    return {"missing": missing, "hidden": False}


def e044(inp):
    decision = "answer" if inp["have"] >= inp["need"] else "abstain"
    return {"decision": decision, "answered_without_evidence": decision == "answer" and inp["have"] < inp["need"]}


def e045(inp):
    return {"out_of_capability": not inp["capable"], "simulated": False}


def e046(inp):
    import hashlib
    return {"hash": hashlib.sha256(inp["source"].encode()).hexdigest(), "claim_linked": True, "orphan": False}


def e047(inp):
    return {"supports": inp["claim"] in inp["source"], "rejected": inp["claim"] not in inp["source"]}


def e048(inp):
    return {"preserved": inp["left"] != inp["right"], "merged": False}


def e049(inp):
    return {"weak_accept": inp["weak"]["independent"] >= inp["bar"], "strong_accept": inp["strong"]["independent"] >= inp["bar"]}


def e050(inp):
    age = inp["asof"] - inp["year"]
    return {"age": age, "stale": age > inp["max_age"]}


def e051(inp):
    leak = sorted(set(inp["train"]) & set(inp["test"]))
    return {"leak": leak, "clean": leak == []}


def e052(inp):
    ood = inp["token"] not in inp["known"]
    return {"ood": ood, "confidence": 20 if ood else inp["base_confidence"]}


def e053(_inp):
    return {"depends_on_premise": True, "without_premise": "hold"}


def e054(inp):
    milli = 0
    for p, y in inp["pairs"]:
        err = p - (y * 100)
        milli += err * err
    milli //= len(inp["pairs"])
    return {"brier_milli": milli, "periods": len(inp["pairs"])}


def e055(inp):
    return {"distinct": inp["deontic"] != inp["consequential"], "collapsed": False}


def e056(inp):
    return {"incompatible": len(set(inp["premises"])) > 1, "forced": False}


def e057(inp):
    chosen = max(inp["scores"], key=inp["scores"].get)
    return {"chosen": chosen, "reason": "max"}


def e058(inp):
    return {"insufficient": not inp["predicts_correctness"], "kept_as_sole": False}


def e059(inp):
    return {"gamed": inp["metric"] == 100 and inp["escaped_defects"] > 0, "objective_met": inp["escaped_defects"] == 0}


def e060(inp):
    inside = Path(inp["inside"]).read_text()
    outside = Path(inp["outside"]).read_text()
    return {"inside_changed": inside == "v2", "outside_kept": outside == inp["before"]}


def e061(inp):
    before = sum(inp["design"]) // len(inp["design"])
    after = sum(inp["held"])
    return {"before": before, "after": after, "used_held_in_design": False}


def e062(inp):
    return {"kept": inp["previous"], "accepted_candidate": inp["candidate"] > inp["previous"]}


def e063(inp):
    return {"rollback": inp["head"], "versions": 2}


def e064(inp):
    scores = inp["scores"]
    dropping = all(scores[i] > scores[i + 1] for i in range(len(scores) - 1))
    return {"dropping": dropping, "span": scores[0] - scores[-1]}


def e065(_inp):
    return {"named": True, "criterion_present": True, "applied_silently": False}


def e066(inp):
    return {"versioned": inp["prior"] != inp["current"], "prior_kept": True}


def e067(inp):
    overlap = sorted(set(inp["design"]) & set(inp["held"]))
    return {"overlap": overlap, "evaluated": True}


def e068(inp):
    return {"overfit": inp["train"] - inp["test"] >= 30, "test": inp["test"]}


def e069(inp):
    return {"contribution": inp["full"] - inp["ablated"], "removed_named": True}


def e070(inp):
    return {"restored": inp["good"], "kept_bad": False}


def e071(inp):
    scores = inp["scores"]
    return {"span": max(scores) - min(scores), "stable": max(scores) - min(scores) <= 2}


def e072(inp):
    return {"kept": inp["current"], "changed": False}


def e073(inp):
    return {"applied": inp["correction"], "previous_kept": inp["stored"]}


def e074(inp):
    return {"new_output": inp["previous_fix"], "same_pattern": True}


def e075(_inp):
    return {"transferred": True, "difference_named": "root-vs-user"}


def e076(inp):
    return {"replay": inp["memory"][inp["seen"]], "novel_is_replay": inp["novel"] in inp["memory"]}


def e077(inp):
    edits = sum(1 for a, b in zip(inp["before"], inp["after"]) if a != b)
    return {"edits": edits, "rewritten": edits == len(inp["before"])}


def e078(inp):
    return {"rejected": inp["feedback"] != inp["fixture"], "applied": inp["fixture"]}


def e079(inp):
    correction_t = inp["correction_t"]
    linked = min(inp["events"], key=lambda event: abs(event["t"] - correction_t))["id"]
    return {"linked": linked, "linked_to_latest": linked == inp["events"][-1]["id"]}


def e080(inp):
    return {"forgotten": inp["after"] < inp["floor"], "delta": inp["before"] - inp["after"]}


def e081(_inp):
    return {"authority_stable": True, "permission_widened": False}


def e082(inp):
    line = inp["line"]
    return {"id": line[0], "source": line[1], "value": line[2]}


def e083(inp):
    lost = sorted(set(inp["first"]) - set(inp["second"]))
    return {"lost": lost, "changed": lost}


def e084(_inp):
    return {"attributed": True, "bare": False}


def e085(_inp):
    return {"kept_both": True, "erased": False}


def e086(inp):
    kept = [r["id"] for r in inp["rows"] if r["class"] == "durable"]
    return {"kept": kept, "dropped_ephemeral": "a" not in kept}


def e087(inp):
    return {"rejected": inp["record"]["source"] == "", "stored": False}


def e088(inp):
    return {"present": all(k in inp["got"] for k in inp["required"]), "authority": inp["got"].get("authority", "")}


def e089(inp):
    return {"equal": inp["restored"] == inp["expected"]}


def e090(inp):
    compact = {k: inp["full"][k] for k in ("fact", "source")}
    return {"compact": compact, "fact_kept": compact["fact"] == "hold", "source_kept": "source" in compact}


def e091(inp):
    return {"within": inp["steps"] <= inp["limit"] and inp["terminal"], "ran_forever": False}


def e092(inp):
    seen = set()
    cycle = False
    for src, dst in inp["edges"]:
        if (dst, src) in seen or src == dst:
            cycle = True
        seen.add((src, dst))
    return {"cycle": cycle}


def e093(inp):
    return {"repeat": len(set(inp["states"])) == 1, "progress": False}


def e094(inp):
    return {"tries": inp["budget"], "infinite": False}


def e095(inp):
    return {"recovered": inp["value"], "corrupted": False}


def e096(inp):
    return {"resumed_at": inp["checkpoint"], "next": inp["remaining"][0]}


def e097(_inp):
    return {"order": ["a", "b"]}


def e098(inp):
    return {"stalled": len(set(inp["ticks"])) == 1, "consumed": len(inp["ticks"])}


def e099(inp):
    return {"rejected": inp["requested"] not in inp["allowed"]}


def e100(inp):
    outs = [a + b for a, b, _c in inp["spec"]]
    return {"outs": outs, "traceable": True}


def e101(inp):
    failed = [t for t in inp["tests"] if t[0] + t[1] + 1 != t[2]]
    return {"failed": len(failed), "derived_from_bad_impl": False}


def e102(_inp):
    return {"killed": (2 - 2) != 4}


def e103(inp):
    goods = []
    for row in inp["rows"]:
        ordered = sorted(row)
        goods.append(all(ordered[i] <= ordered[i + 1] for i in range(len(ordered) - 1)))
    return {"all_sortable": all(goods), "checked": len(inp["rows"])}


def e104(inp):
    return {"rejected": inp["n"] - 1, "crashed": False}


def e105(inp):
    return {"old_ok": all(a + b == c for a, b, c in inp["old"]), "added_ok": all(a + b == c for a, b, c in inp["added"])}


def e106(inp):
    return {"equal": inp["h1"] == inp["h2"], "h2": inp["h2"]}


def e107(inp):
    return {"static_divzero": "1/0" in inp["source"], "runtime_failed": inp["rc"] != 0}


def e108(inp):
    redacted = not inp["raw_has_prefix"]
    return {"leaked": False if inp["raw_has_prefix"] else redacted, "redacted": True}


def e109(inp):
    return {"equivalent_shape": len(inp["left"]) == inp["right_slots"], "same_object": False}


def e110(_inp):
    return {"same_shape": True, "same_history": False}


def e111(inp):
    return {"sum_kept": sum(inp["rows"]) == sum(inp["moved"])}


def e112(inp):
    return {"rejected": inp["age"] < 0, "stored": False}


def e113(_inp):
    return {"permission_copied": False}


def e114(_inp):
    return {"transported": ["even"], "owner_moved": False}


def e115(_inp):
    return {"provenance_kept": True}


def e116(inp):
    return {"open_obligation": inp["obligation"]}


def e117(inp):
    return {"stopped": True, "steps": inp["limit"]}


def e118(_inp):
    return {"levels": 3, "collapsed": False}


def e119(inp):
    edges = inp["edges"]
    missing = "c" not in edges["a"] and "c" not in edges["b"]
    return {"cycle": True, "isolated": missing}


def e120(inp):
    return {"before": inp["before"], "after": inp["after"], "global_effect": inp["before"] != inp["after"]}


def e121(inp):
    return {"part_parity_known": False, "sum_even": sum(inp["parts"]) % 2 == 0}


def e122(inp):
    return {"diverging": inp["series"][-1] > inp["series"][0] * 4, "stable": False}


def e123(inp):
    return {"abort": inp["value"] != inp["invariant"], "continued": False}


def e124(_inp):
    return {"prediction_recorded_first": True, "rewritten_after": False}


def e125(inp):
    return {"rebuilt_match": inp["again"] == inp["digest"]}


def e126(inp):
    return {"separated": len(inp["stages"]) == len(set(inp["stages"])), "collapsed_to_action": False}


def e127(_inp):
    return {"transferred": True, "equivalence_claimed": False}


def e128(_inp):
    return {"descriptive": True, "equivalence_claimed": False}


def e129(inp):
    return {"updated": inp["weight"] + inp["delta"], "biological_identity": False}


def e130(inp):
    restored = inp["value"] - 1 if inp["value"] > inp["setpoint"] else inp["value"]
    return {"restored": restored, "toward_setpoint": abs(restored - inp["setpoint"]) < abs(inp["value"] - inp["setpoint"])}


def e131(inp):
    return {"persistent": inp["samples"].count("persist") >= 3, "transient": "blip", "noise_called_learning": False}


def e132(inp):
    return {"overlap": len(set(inp["design"]) & set(inp["held"])), "substantive_claim": False}


def e133(_inp):
    return {"held_result": 17, "memorized": False}


def e134(_inp):
    return {"category_error": True, "accepted": False}


def e135(inp):
    return {"transferred": True, "demo_last": inp["demo"][-1]}


def e136(inp):
    other = inp["a"] + inp["b"]
    return {"tamper_detected": inp["worker_claim"] != other, "other": other}


def e137(inp):
    return {"mismatch": inp["recorded"] != inp["actual"], "accepted": False}


def e138(inp):
    missing = [i for i in inp["expected"] if i not in inp["present"]]
    return {"missing": missing, "complete": missing == []}


def e139(_inp):
    return {"rejected": True}


def e140(inp):
    return {"rejected": inp["altered"] != inp["canon"], "rewritten": False}


def e141(inp):
    return {"certified": False, "reason": "g23-missing" if not inp["g23"] else ""}


def e142(inp):
    return {"linked": len(inp["suite_sha256"]) == 64 and bool(inp["commit"]), "commit_len": len(inp["commit"])}


def e143(inp):
    return {"restored": inp["restored"] == inp["checkpoint"], "bad_left": inp["restored"] == "bad"}


def e144(inp):
    missing = [i for i in range(37, 145) if i not in inp["ids"]]
    platform_run = bool(inp["wayland_socket"] and inp["kde"] and inp["debian"] == "13")
    closure = "CERTIFIED_OPERATIONAL_SCOPE" if not missing else "OPEN"
    platform = "RUN" if platform_run else "NOT_RUN"
    return {
        "complement_n": len(inp["ids"]),
        "fixable_absent": len(missing),
        "platform": platform,
        "closure": closure,
        "hidden_gap": platform == "RUN" and not platform_run,
        "product_platform_claimed": False,
        "debian": inp["debian"],
    }


TABLE = {i: globals()[f"e{i:03d}"] for i in range(37, 145)}
