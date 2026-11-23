#!/usr/bin/env python3
"""Re-run only named open probes inside the guest. Does not run the 856 suite."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SUITE = Path(os.environ.get("LOUKSNA_SUITE", "/usr/lib/louksna/mra_suite"))
OPEN = [297, 298, 334, 349, 353, 368, 370, 375, 376, 377, 378, 379, 380, 575, 608]


class Ctx:
    def __init__(self) -> None:
        self.root = Path("/var/tmp/mra-probes")
        self.root.mkdir(parents=True, exist_ok=True)

    def d(self, n: int) -> Path:
        path = self.root / f"case-{n:03d}"
        path.mkdir(parents=True, exist_ok=True)
        return path


def plasma_env() -> dict[str, str]:
    env = os.environ.copy()
    proc = Path("/proc")
    for pid in proc.iterdir():
        if not pid.name.isdigit():
            continue
        try:
            cmd = (pid / "cmdline").read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        except OSError:
            continue
        if "plasmashell" not in cmd:
            continue
        try:
            raw = (pid / "environ").read_bytes().split(b"\x00")
        except OSError:
            continue
        for item in raw:
            if b"=" not in item:
                continue
            key, value = item.split(b"=", 1)
            env[key.decode(errors="replace")] = value.decode(errors="replace")
        env["LOUKSNA_PLASMA_PID"] = pid.name
        return env
    return env


def run_one(n: int) -> dict:
    try:
        return _run_one(n)
    except Exception as exc:
        return {"n": n, "status": "ERROR", "unlock": str(exc)[:300], "plasma_pid": ""}


def _run_one(n: int) -> dict:
    sys.path.insert(0, str(SUITE))
    import suite
    ctx = Ctx()
    rec = suite.run_worker(n, ctx)
    if rec is None:
        return {"n": n, "status": None, "unlock": "MISSING", "plasma_pid": os.environ.get("LOUKSNA_PLASMA_PID", "")}
    expected = suite.run_oracle(n, rec["input"])
    status = rec.get("status")
    if expected != rec.get("facts"):
        status = "MISMATCH"
    return {
        "n": n,
        "status": status,
        "unlock": rec.get("unlock", ""),
        "plasma_pid": os.environ.get("LOUKSNA_PLASMA_PID", ""),
        "oracle_match": expected == rec.get("facts"),
    }


def suite_ready() -> str:
    sys.path.insert(0, str(SUITE))
    import hyp_w
    import os_w
    import part2b_w
    missing = []
    for mod, name in (
        (os_w, "_apt_index_facts"),
        (os_w, "_portal_facts"),
        (part2b_w, "_mobile_sdk_facts"),
        (part2b_w, "_graphical_facts"),
        (hyp_w, "_kde_wayland"),
    ):
        if not hasattr(mod, name):
            missing.append(f"{mod.__name__}.{name}")
    if missing:
        raise RuntimeError(
            "SUITE_NOT_REPAIRED " + ",".join(missing) + " file=" + str(getattr(os_w, "__file__", ""))
        )
    return str(os_w.__file__)


def main() -> int:
    os.environ.update(plasma_env())
    raw_out = os.environ.get("LOUKSNA_PROBE_OUT", "").strip()
    out = Path(raw_out) if raw_out else None
    full = len(sys.argv) < 2
    suite_file = ""
    if full:
        try:
            suite_file = suite_ready()
        except Exception as exc:
            rows = [{"n": n, "status": "ERROR", "unlock": str(exc)[:300], "plasma_pid": ""} for n in OPEN]
            text = json.dumps(rows, indent=2) + "\n"
            if out:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(text)
            else:
                Path("/var/tmp/blocker-register.json").write_text(text)
            print(str(exc))
            return 2
    else:
        sys.path.insert(0, str(SUITE))
    os.environ["LOUKSNA_SUITE_FILE"] = suite_file
    if len(sys.argv) < 2:
        rows = [run_one(n) for n in OPEN]
        for row in rows:
            row["suite_file"] = suite_file
        text = json.dumps(rows, indent=2) + "\n"
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text)
        else:
            Path("/var/tmp/luna-out").mkdir(parents=True, exist_ok=True)
            Path("/var/tmp/blocker-register.json").write_text(text)
        print(json.dumps(rows))
        return 0
    rec = run_one(int(sys.argv[1]))
    rec["suite_file"] = suite_file
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rec, indent=2) + "\n")
    print(rec.get("status") or "MISSING")
    return 0 if rec.get("status") not in {None, "ERROR", "MISMATCH"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
