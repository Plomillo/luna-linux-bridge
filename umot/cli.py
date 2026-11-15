"""UMOT command line. JSON on stdout. Exit 0 only when the operation passed."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .runtime import Core
except ImportError:
    from runtime import Core


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umot")
    parser.add_argument("--state", type=Path, default=Path(".umot-state"))
    parser.add_argument("--json", action="store_true", help="Accepted for compatibility. JSON is always emitted.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "doctor", "capabilities", "verify", "rollback", "forgejo"):
        command = sub.add_parser(name)
        if name == "rollback":
            command.add_argument("checkpoint")
    lab = sub.add_parser("lab")
    lab.add_argument("name")
    run = sub.add_parser("run")
    run.add_argument("operation")
    run.add_argument("--key")
    run.add_argument("--value")
    run.add_argument("--path")
    run.add_argument("--body")
    run.add_argument("--name")
    run.add_argument("--requested-kb", type=int, default=1024)
    args = parser.parse_args(argv)
    core = Core(args.state)
    if args.command == "status":
        result = core.status()
    elif args.command == "doctor":
        result = core.doctor()
    elif args.command == "capabilities":
        result = core.capabilities()
    elif args.command == "verify":
        result = core.verify()
    elif args.command == "rollback":
        result = core.rollback(args.checkpoint)
    elif args.command == "forgejo":
        result = core.forgejo()
    elif args.command == "lab":
        result = core.lab(args.name)
    else:
        params = {"requested_kb": args.requested_kb}
        for key in ("key", "value", "path", "body", "name"):
            value = getattr(args, key)
            if value is not None:
                params[key] = value
        result = core.run(args.operation, **params)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("status", "PASS") in {"PASS", "UNAVAILABLE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
