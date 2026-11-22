"""Assemble MRA-5O-001..856. Historical cases stay in Rust. 037-144 are executable."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import ai_o
import ai_w
import comp_o
import comp_w
import complement_o
import complement_w
import data_o
import data_w
import fifth_o
import fifth_w
import git_o
import git_w
import hyp_o
import hyp_w
import net_o
import net_w
import obs_o
import obs_w
import os_o
import os_w
import part1_o
import part1_w
import part2_o
import part2_w
import part2b_o
import part2b_w
import repair_o
import repair_w
import sci_o
import sci_w
import sec_o
import sec_w
import tail_w
import theo_o
import theo_w
from ctx import Ctx

SECRET = re.compile(r"(ghu_|ghs_|ghp_|gho_|github_pat_|xai-)[A-Za-z0-9_\-]{8,}")
PAIRS = [
    (range(145, 185), part1_w, part1_o),
    (range(185, 225), part2_w, part2_o),
    (range(225, 305), part2b_w, part2b_o),
    (range(305, 307), tail_w, comp_o),
    (range(307, 345), comp_w, comp_o),
    (range(345, 385), os_w, os_o),
    (range(385, 425), net_w, net_o),
    (range(425, 465), data_w, data_o),
    (range(465, 505), sec_w, sec_o),
    (range(505, 545), ai_w, ai_o),
    (range(545, 585), git_w, git_o),
    (range(585, 625), hyp_w, hyp_o),
    (range(625, 665), obs_w, obs_o),
    (range(665, 705), sci_w, sci_o),
]


def additive_owner(n: int):
    if n in repair_w.IDS:
        return repair_w, repair_o
    if n in fifth_w.DISPATCH and n in theo_w.DISPATCH:
        raise RuntimeError(f"overlap {n}")
    if n in fifth_w.DISPATCH:
        return fifth_w, fifth_o
    if n in theo_w.DISPATCH:
        return theo_w, theo_o
    for span, worker, oracle in PAIRS:
        if n in span:
            return worker, oracle
    return None


def coverage():
    missing = [n for n in range(145, 857) if additive_owner(n) is None]
    missing.extend(n for n in range(37, 145) if n not in complement_w.DISPATCH or n not in complement_o.TABLE)
    return missing


def run_worker(n: int, ctx: Ctx):
    if 37 <= n <= 144:
        return complement_w.run(n, ctx)
    owner = additive_owner(n)
    if owner is None:
        return None
    return owner[0].run(n, ctx)


def run_oracle(n: int, inp: dict):
    if 37 <= n <= 144:
        return complement_o.expect(n, inp)
    owner = additive_owner(n)
    if owner is None:
        raise KeyError(n)
    return owner[1].expect(n, inp)


def scrub(text: str) -> str:
    return SECRET.sub("[REDACTED]", text)


def no_floats(value, path=""):
    if isinstance(value, float):
        raise TypeError(path or "float")
    if isinstance(value, dict):
        for key, item in value.items():
            no_floats(item, path + "." + str(key))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            no_floats(item, path + f"[{i}]")


def historical(session: str, state: Path) -> dict:
    proc = subprocess.run([session, "--mra", "--state", str(state)], capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        raise RuntimeError("historical mra failed\n" + proc.stderr)
    return json.loads(proc.stdout)


def historical_row(case: dict, evidence: str) -> dict:
    return {
        "id": case["id"],
        "n": int(case["id"].rsplit("-", 1)[1]),
        "domain": "historical",
        "objective": "PRESERVED_RUST_CASE",
        "status": "HISTORICAL_PRESERVED" if case.get("pass") is True else "FAIL",
        "independent_validation": "NOT_ESTABLISHED",
        "certification": "NOT_CERTIFIED",
        "weight_training": "NOT_AUTHORIZED",
        "consciousness": "NOT_CLAIMED",
        "evidence_sha256": evidence,
        "pass": case.get("pass") is True,
        "limits": "RUST_ORACLE_REINVOKES_RUN_SUITE",
        "unlock": "",
    }


def judge(rec: dict) -> str:
    if rec["status"] == "PASS_FUNCTIONAL":
        return "CERTIFIED"
    return "NOT_CERTIFIED"


def compare_range(ctx: Ctx, start: int, stop: int):
    bad = []
    rows = []
    for n in range(start, stop):
        rec = run_worker(n, ctx)
        if rec is None:
            bad.append((n, "MISSING"))
            continue
        if rec.get("status") not in {"PASS_FUNCTIONAL", "BLOCKED", "FAIL"}:
            bad.append((n, "STATUS"))
            continue
        try:
            no_floats(rec.get("facts"))
            exp = run_oracle(n, rec["input"])
            no_floats(exp)
        except Exception as exc:
            bad.append((n, type(exc).__name__ + ":" + str(exc)[:180]))
            continue
        if exp != rec["facts"] or rec["status"] == "FAIL":
            bad.append((n, "MISMATCH" if exp != rec["facts"] else rec["status"]))
            continue
        if rec["status"] == "BLOCKED" and not rec.get("unlock"):
            bad.append((n, "BLOCKED_WITHOUT_UNLOCK"))
            continue
        rows.append({
            "id": f"MRA-5O-{n:03d}",
            "n": n,
            "domain": rec["domain"],
            "objective": rec["objective"],
            "status": rec["status"],
            "independent_validation": "INDEPENDENTLY_VALIDATED" if rec["status"] == "PASS_FUNCTIONAL" else "NOT_ESTABLISHED",
            "certification": judge(rec),
            "weight_training": "NOT_AUTHORIZED",
            "consciousness": "NOT_CLAIMED",
            "unlock": rec.get("unlock") or "",
            "limits": rec.get("limits") or "",
        })
    return rows, bad


def tamper(ctx: Ctx) -> bool:
    rec = run_worker(145, ctx)
    exp = run_oracle(145, rec["input"])
    mutated = json.loads(json.dumps(rec["facts"]))
    for key, value in list(mutated.items()):
        if isinstance(value, bool):
            mutated[key] = not value
            break
        if isinstance(value, int):
            mutated[key] = value + 1
            break
    else:
        return False
    return mutated != exp


def execute(root: Path) -> dict:
    missing = coverage()
    if missing:
        raise RuntimeError("missing ids " + ",".join(str(n) for n in missing[:20]))
    ctx = Ctx(root)
    complement_rows, bad = compare_range(ctx, 37, 145)
    additive_rows, bad2 = compare_range(ctx, 145, 857)
    bad.extend(bad2)
    if not tamper(ctx):
        raise RuntimeError("tamper check failed")
    session = os.environ.get("LOUKSNA_SESSION_BIN") or Ctx(root).session_bin
    hist = historical(session, ctx.d(1) / "state")
    hist_rows = [historical_row(case, hist["evidence_sha256"]) for case in hist["cases"]]
    all_rows = hist_rows + complement_rows + additive_rows
    ids = [row["n"] for row in all_rows]
    if ids != list(range(1, 857)):
        missing = sorted(set(range(1, 857)) - set(ids))
        raise RuntimeError(f"id sequence broken missing={missing[:30]} bad={bad[:12]}")
    counts = {}
    certified = 0
    for row in all_rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        if row["certification"] == "CERTIFIED":
            if row["status"] != "PASS_FUNCTIONAL":
                raise RuntimeError("certified non-pass")
            certified += 1
        elif row["certification"] != "NOT_CERTIFIED":
            raise RuntimeError("certification value")
        if row["weight_training"] != "NOT_AUTHORIZED" or row["consciousness"] != "NOT_CLAIMED":
            raise RuntimeError("forbidden status")
    report = {
        "suite": "MRA-5O-001-856",
        "count": len(all_rows),
        "unique": len(set(ids)) == 856,
        "bad": [{"n": n, "why": why} for n, why in bad],
        "counts": counts,
        "certified_cases": certified,
        "historical_evidence_sha256": hist.get("evidence_sha256"),
        "historical_failed": hist.get("failed"),
        "product_platform": "NOT_CERTIFIED",
        "distribution_debian13_kde_wayland": "NOT_RUN",
        "consciousness": "NOT_CLAIMED",
        "weight_training": "NOT_AUTHORIZED",
        "independent_note": "001-036 stay NOT_ESTABLISHED because the Rust oracle calls run_suite. PASS_FUNCTIONAL rows are case-scope CERTIFIED. Product platform and Debian 13 KDE Plasma Wayland stay uncertified.",
        "cases": all_rows,
    }
    blob = scrub(json.dumps(report, sort_keys=True))
    if SECRET.search(blob):
        raise RuntimeError("secret remained after scrub")
    report["scrubbed"] = blob != json.dumps(report, sort_keys=True)
    return report


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/mra-856")
    report = execute(root)
    out = root / "report.json"
    out.write_text(scrub(json.dumps({k: v for k, v in report.items() if k != "cases"}, indent=2, sort_keys=True)) + "\n")
    (root / "cases.json").write_text(scrub(json.dumps(report["cases"], indent=2)) + "\n")
    print(json.dumps({k: report[k] for k in ("count", "unique", "counts", "certified_cases", "bad", "historical_failed", "historical_evidence_sha256", "product_platform", "distribution_debian13_kde_wayland")}, indent=2))
    return 0 if not report["bad"] and report["historical_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
