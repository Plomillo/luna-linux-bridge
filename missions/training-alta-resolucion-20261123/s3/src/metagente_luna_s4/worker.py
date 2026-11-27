"""One-shot worker for clean-process C05 execution; not a security sandbox."""
from __future__ import annotations

import json
import sys

from metagente_luna_s4.runner import _execute


def main() -> int:
    try:
        request = json.load(sys.stdin)
        record = _execute(
            request["capability_id"],
            request["arguments"],
            request["case_id"],
            backend="LOCAL_TEST_ONLY",
        )
        json.dump(record, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\\n")
        return 0
    except Exception as exc:  # noqa: BLE001 - worker boundary must report startup/dispatch failures
        json.dump({"worker_error": f"{type(exc).__name__}: {exc}"}, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
