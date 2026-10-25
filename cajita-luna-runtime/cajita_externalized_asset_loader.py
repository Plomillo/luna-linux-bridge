#!/usr/bin/env python3
"""Verify or safely materialize one registered Cajita externalized asset."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cajita_externalized_packaging import materialize_asset, verify_all_archives


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify-all", "materialize"))
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--asset-id")
    args = parser.parse_args()
    try:
        if args.command == "verify-all":
            if args.asset_id:
                parser.error("--asset-id is valid only for materialize")
            result = verify_all_archives(Path(args.root))
        else:
            if not args.asset_id:
                parser.error("materialize requires --asset-id")
            result = materialize_asset(Path(args.root), args.asset_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            "schema": "CAJITA_EXTERNALIZED_ASSET_RECONSTRUCTION/1.0",
            "status": "FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "reason": str(exc)[:1200],
            "certification": "NOT_GRANTED",
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
