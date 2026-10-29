#!/usr/bin/env python3
"""Write a compact, machine-readable unittest result instead of implying certification."""
from __future__ import annotations

import argparse
import io
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = []

    def startTest(self, test):
        super().startTest(test)
        self._case_name = test.id()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.rows.append({"test_id": test.id(), "status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.rows.append({"test_id": test.id(), "status": "FAIL", "detail": self._exc_info_to_string(err, test)[-1500:]})

    def addError(self, test, err):
        super().addError(test, err)
        self.rows.append({"test_id": test.id(), "status": "ERROR", "detail": self._exc_info_to_string(err, test)[-1500:]})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.rows.append({"test_id": test.id(), "status": "SKIP", "detail": reason})


class RecordingRunner(unittest.TextTestRunner):
    resultclass = RecordingResult


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tests-root", type=Path, default=Path("tests"))
    args = parser.parse_args(argv)
    buffer = io.StringIO()
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(args.tests_root),
        pattern="test_louksnapg2*.py",
        top_level_dir=".",
    )
    result = RecordingRunner(stream=buffer, verbosity=2).run(suite)
    errors = len(result.errors)
    failures = len(result.failures)
    statuses = {row["status"] for row in result.rows}
    passed = result.testsRun - failures - errors
    evidence = {
        "schema": "LOUKSNAPG2_UNIT_TEST_EVIDENCE/1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "PASS" if failures == 0 and errors == 0 else "FAIL",
        "tests_run": result.testsRun,
        "passed": passed,
        "failures": failures,
        "errors": errors,
        "skipped": len(result.skipped),
        "case_results": result.rows,
        "log_tail": buffer.getvalue()[-10000:],
        "certification": "NOT_GRANTED_BY_UNIT_TESTS",
        "note": "Synthetic/unit coverage is not real-model functional quality evidence.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: evidence[key] for key in ("status", "tests_run", "passed", "failures", "errors", "skipped", "certification")}, sort_keys=True, indent=2))
    return 0 if evidence["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
