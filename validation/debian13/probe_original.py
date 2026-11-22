#!/usr/bin/env python3
"""Re-run only named open probes inside the guest. Does not run the 856 suite."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SUITE = Path("/usr/lib/louksna/mra_suite")
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
    sys.path.insert(0, str(SUITE))
    ctx = Ctx()
    if n in {297, 298}:
        import part2b_w
        rec = part2b_w.run(n, ctx)
    elif n == 334:
        import repair_w
        rec = repair_w.run(n, ctx)
    elif n == 575:
        import git_w
        rec = git_w.run(n, ctx)
    elif n == 608:
        import hyp_w
        rec = hyp_w.run(n, ctx)
    else:
        import os_w
        rec = os_w.run(n, ctx)
    return {
        "n": n,
        "status": None if rec is None else rec.get("status"),
        "unlock": None if rec is None else rec.get("unlock", ""),
        "plasma_pid": os.environ.get("LOUKSNA_PLASMA_PID", ""),
    }


def main() -> int:
    os.environ.update(plasma_env())
    if len(sys.argv) < 2:
        rows = [run_one(n) for n in OPEN]
        Path("/var/tmp/luna-out").mkdir(parents=True, exist_ok=True)
        Path("/var/tmp/blocker-register.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps(rows))
        return 0
    rec = run_one(int(sys.argv[1]))
    print(rec.get("status") or "MISSING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
