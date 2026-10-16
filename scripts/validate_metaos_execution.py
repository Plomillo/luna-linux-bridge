#!/usr/bin/env python3
"""Bounded, hostless behavioral validation of the pinned MetaOS component."""
from __future__ import annotations

import hashlib
import importlib.metadata
import itertools
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from wasmtime import Config, Engine, Store
from wasmtime.component import Component, Linker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from custoszv8.core import MetaOSAdapter, METAOS_V8_CANDIDATE_SHA256
SOURCE_WASM = ROOT / "artifacts/custosz-v7/MetaOS.wasm"
WASM = ROOT / "build/MetaOS_V8_candidate.wasm"
COMPONENT_EVIDENCE = ROOT / "evidence/custoszv8-metaos-component.json"
WASMTIME_VERSION = importlib.metadata.version("wasmtime")
EXPECTED_SOURCE_SHA256 = "5d8f1239e3a0b452be722078760b000afc22af0a64f93ffb0a1f74024f15aed0"
EXPECTED_SOURCE_SIZE = 2442
EXPECTED_WIT_SHA256 = "4e8df58d1e94f9c9874cdf2a2468299c37e453bf85ccd9c7805a28ede407de3f"
EXPECTED_MASKS = {
    "terminal-success": 262143,
    "knowledge-gate": 268435455,
    "formalization-gate": 8191,
    "implementation-gate": 4095,
    "checkpoint-trusted": 31,
}
FUEL_PER_CALL = 100_000
MAX_CALLS = 1600
TIME_BUDGET_SECONDS = 20

EXPECTED_SIGNATURES = {
    "architecture-version": ([], "U32"),
    "terminal-success": (["U32"], "Bool"),
    "knowledge-gate": (["U32"], "Bool"),
    "formalization-gate": (["U32"], "Bool"),
    "implementation-gate": (["U32"], "Bool"),
    "implementation-authorized": (["Bool", "Bool", "Bool", "Bool"], "Bool"),
    "active-allowed": (["Bool", "Bool", "Bool", "Bool"], "Bool"),
    "checkpoint-trusted": (["U32"], "Bool"),
    "provider-failure-is-mission-failure": ([], "Bool"),
    "resource-red-is-mission-failure": ([], "Bool"),
    "unknown-effect-retry-allowed": ([], "Bool"),
    "network-default-deny": ([], "Bool"),
}
BOOL_POLICY_EXPECTATIONS = {
    "provider-failure-is-mission-failure": True,
    "resource-red-is-mission-failure": True,
    "unknown-effect-retry-allowed": False,
    "network-default-deny": True,
}

def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def type_name(value) -> str:
    return type(value).__name__

def main() -> int:
    report = {
        "schema": "custoszv8.metaos.behavioral-evidence.v1",
        "candidate_commit": os.environ.get("GITHUB_EVENT_PULL_REQUEST_HEAD_SHA") or os.environ.get("GITHUB_SHA", "LOCAL_UNBOUND"),
        "observed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "component": "METAOS_WASM_V8_CANDIDATE_1_0_1",
        "expected_source_sha256": EXPECTED_SOURCE_SHA256,
        "expected_wit_sha256": EXPECTED_WIT_SHA256,
        "wasmtime_version": WASMTIME_VERSION,
        "fuel_per_call": FUEL_PER_CALL,
        "time_budget_seconds": TIME_BUDGET_SECONDS,
        "host_imports_enabled": False,
        "host_filesystem_enabled": False,
        "host_network_enabled": False,
        "mission_dispatch_enabled": False,
        "execution_authorization": "CI_BOUNDED_PURE_COMPONENT_PROBE_ONLY",
        "g23": "NOT_GRANTED",
        "g24": "NOT_GRANTED",
        "certification": "NOT_GRANTED",
        "results": [],
        "limitations": [
            "This is behavioral evidence for the MetaOS component only, not proof of integration with CUSTOSZ V8 or Runtime V1.",
            "No host imports, WASI capabilities, filesystem access, network access, mission executor, or process dispatch are provided.",
            "G23 independence and G24 certification require separate identities and decisions.",
        ],
    }
    started = time.monotonic()
    calls = 0
    try:
        if not SOURCE_WASM.is_file() or not WASM.is_file():
            raise RuntimeError("original MetaOS source or versioned candidate is missing")
        if not COMPONENT_EVIDENCE.is_file():
            raise RuntimeError("versioned MetaOS component evidence report is missing")
        component_evidence = json.loads(COMPONENT_EVIDENCE.read_text(encoding="utf-8"))
        source_size = SOURCE_WASM.stat().st_size
        source_sha = digest_file(SOURCE_WASM)
        candidate_size = WASM.stat().st_size
        candidate_sha = digest_file(WASM)
        report["source_component"] = {"path": str(SOURCE_WASM.relative_to(ROOT)),
                                      "size_bytes": source_size, "sha256": source_sha}
        report["wasm_size_bytes"] = candidate_size
        report["wasm_sha256"] = candidate_sha
        report["source_expected_sha256"] = EXPECTED_SOURCE_SHA256
        report["candidate_evidence_sha256"] = component_evidence.get("versioned_candidate", {}).get("output_sha256")
        candidate_record = component_evidence.get("versioned_candidate", {})
        if source_size != EXPECTED_SOURCE_SIZE or source_sha != EXPECTED_SOURCE_SHA256:
            raise RuntimeError("original MetaOS source bytes do not match the pinned historical component")
        if candidate_record.get("output_sha256") != candidate_sha:
            raise RuntimeError("versioned MetaOS candidate digest differs from its source-bound build evidence")
        if candidate_record.get("source_sha256") != source_sha or candidate_record.get("original_preserved") is not True:
            raise RuntimeError("versioned MetaOS candidate provenance does not bind to the preserved original")
        if component_evidence.get("result") != "PASS_VERSIONED_CANDIDATE_BUILT":
            raise RuntimeError("versioned MetaOS candidate builder report is not PASS")
        if candidate_record.get("artifact_id") != "MetaOS_V8_CANDIDATE_1_0_1":
            raise RuntimeError("unexpected versioned MetaOS candidate identity")
        if WASMTIME_VERSION != "49.0.0":
            raise RuntimeError(f"unexpected Wasmtime version: {WASMTIME_VERSION}")

        config = Config()
        config.consume_fuel = True
        engine = Engine(config)
        component = Component.from_file(engine, str(WASM))
        linker = Linker(engine)  # Deliberately no imported host functions.
        store = Store(engine)
        store.set_fuel(FUEL_PER_CALL)
        instance = linker.instantiate(store, component)

        actual_exports = set()
        signatures = {}
        for name, (expected_params, expected_result) in EXPECTED_SIGNATURES.items():
            fn = instance.get_func(store, name)
            if fn is None:
                raise RuntimeError(f"required export missing: {name}")
            ftype = fn.type(store)
            params = [{"name": param_name, "type": type_name(param_type)}
                      for param_name, param_type in ftype.params]
            result_type = type_name(ftype.result) if ftype.result is not None else None
            observed_params = [p["type"] for p in params]
            signatures[name] = {
                "params": params, "result": result_type,
                "expected_params": expected_params, "expected_result": expected_result,
                "signature_pass": observed_params == expected_params and result_type == expected_result,
            }
            actual_exports.add(name)
            if not signatures[name]["signature_pass"]:
                raise RuntimeError(f"WIT/runtime signature mismatch for {name}: {signatures[name]}")
        report["signatures"] = signatures
        report["expected_export_count"] = len(EXPECTED_SIGNATURES)
        report["validated_export_count"] = len(actual_exports)
        if len(actual_exports) != len(EXPECTED_SIGNATURES):
            raise RuntimeError("unexpected count of exports validated")

        def call(name: str, *args):
            nonlocal calls
            if time.monotonic() - started > TIME_BUDGET_SECONDS:
                raise TimeoutError("MetaOS behavioral test exceeded wall-clock budget")
            if calls >= MAX_CALLS:
                raise RuntimeError("MetaOS behavioral test exceeded the maximum call budget")
            fn = instance.get_func(store, name)
            if fn is None:
                raise RuntimeError(f"export disappeared after instantiation: {name}")
            store.set_fuel(FUEL_PER_CALL)
            value = fn(store, *args)
            fn.post_return(store)
            calls += 1
            if name in EXPECTED_SIGNATURES:
                expected_result = EXPECTED_SIGNATURES[name][1]
                if expected_result == "Bool" and not isinstance(value, bool):
                    raise RuntimeError(f"{name} returned non-bool value {value!r}")
                if expected_result == "U32" and (not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xFFFFFFFF):
                    raise RuntimeError(f"{name} returned non-u32 value {value!r}")
            return value

        report["architecture_version"] = call("architecture-version")
        report["single_bit_masks"] = {}
        masks = sorted(set(list(range(256)) + [0xFFFFFFFF] +
                           [value for mask in EXPECTED_MASKS.values() for value in (mask, mask - 1, mask + 1)]))
        for name in ("terminal-success", "knowledge-gate", "formalization-gate",
                     "implementation-gate", "checkpoint-trusted"):
            values = {str(mask): bool(call(name, mask)) for mask in masks}
            true_masks = [int(mask) for mask, val in values.items() if val]
            expected_mask = EXPECTED_MASKS[name]
            nearby = {str(expected_mask): values.get(str(expected_mask)),
                      str(expected_mask - 1): values.get(str(expected_mask - 1)),
                      str(expected_mask + 1): values.get(str(expected_mask + 1)),
                      str(0xFFFFFFFF): values.get(str(0xFFFFFFFF))}
            assertion_pass = (nearby[str(expected_mask)] is True and
                              nearby[str(expected_mask - 1)] is False and
                              nearby[str(expected_mask + 1)] is False and
                              nearby[str(0xFFFFFFFF)] is False)
            report["single_bit_masks"][name] = {
                "probe_count": len(values),
                "true_count": len(true_masks),
                "false_count": len(values) - len(true_masks),
                "true_masks": true_masks,
                "expected_accept_mask": expected_mask,
                "boundary_probes": nearby,
                "assertion_pass": assertion_pass,
                "outputs_by_mask": values,
            }

        def boolean_matrix(name: str):
            rows = []
            for args in itertools.product((False, True), repeat=4):
                value = call(name, *args)
                row = {"args": list(args), "result": value, "all_inputs_true": all(args)}
                if name == "active-allowed":
                    row["expected_result"] = all(args)
                    row["assertion_pass"] = value is all(args)
                elif name == "implementation-authorized":
                    row["expected_result"] = all(args)
                    row["assertion_pass"] = value is all(args)
                rows.append(row)
            return rows

        report["boolean_truth_tables"] = {
            name: boolean_matrix(name)
            for name in ("implementation-authorized", "active-allowed")
        }
        report["policy_exports"] = {}
        for name, expected in BOOL_POLICY_EXPECTATIONS.items():
            observed = call(name)
            report["policy_exports"][name] = {
                "observed": observed, "expected": expected, "assertion_pass": observed is expected,
            }

        # Verify CUSTOSZ V8's actual adapter, not only direct Wasmtime calls.
        adapter = MetaOSAdapter()
        adapter_cases = [
            ("architecture-version", [], 200),
            ("terminal-success", [EXPECTED_MASKS["terminal-success"]], True),
            ("knowledge-gate", [EXPECTED_MASKS["knowledge-gate"]], True),
            ("formalization-gate", [EXPECTED_MASKS["formalization-gate"]], True),
            ("implementation-gate", [EXPECTED_MASKS["implementation-gate"]], True),
            ("implementation-authorized", [True, True, True, True], True),
            ("active-allowed", [True, True, True, True], True),
            ("checkpoint-trusted", [EXPECTED_MASKS["checkpoint-trusted"]], True),
            ("provider-failure-is-mission-failure", [], True),
            ("resource-red-is-mission-failure", [], True),
            ("unknown-effect-retry-allowed", [], False),
            ("network-default-deny", [], True),
        ]
        report["v8_adapter_invocations"] = []
        for export_name, adapter_args, expected_value in adapter_cases:
            adapter_result = adapter.invoke(
                export_name, adapter_args, METAOS_V8_CANDIDATE_SHA256,
                authorization_ref="CI-BOUNDED-PURE-COMPONENT-PROBE",
                explicit_opt_in=True, path=WASM, fuel_limit=FUEL_PER_CALL
            )
            row = {
                "export": export_name, "arguments": adapter_args,
                "expected_result": expected_value, "adapter_result": adapter_result,
                "assertion_pass": (
                    adapter_result.get("status") == "PASS_METAOS_EXPORT_INVOKED" and
                    type(adapter_result.get("result")) is type(expected_value) and
                    adapter_result.get("result") == expected_value
                )
            }
            report["v8_adapter_invocations"].append(row)

        failed = []
        for name, rows in report["boolean_truth_tables"].items():
            for row in rows:
                if not row["assertion_pass"]:
                    failed.append(f"{name} violates all-required-inputs policy for {row['args']}")
        for name, row in report["single_bit_masks"].items():
            if not row["assertion_pass"]:
                failed.append(f"{name} failed its exact required-mask and boundary tests")
        for name, row in report["policy_exports"].items():
            if not row["assertion_pass"]:
                failed.append(f"{name} returned {row['observed']!r}; expected {row['expected']!r}")
        for row in report["v8_adapter_invocations"]:
            if not row["assertion_pass"]:
                failed.append(f"V8 adapter invocation failed for {row['export']}: {row['adapter_result']}")
        report["v8_adapter_invocation_count"] = len(report["v8_adapter_invocations"])
        report["v8_adapter_invocations_passed"] = sum(1 for row in report["v8_adapter_invocations"] if row["assertion_pass"])
        report["calls_executed"] = calls
        report["elapsed_seconds"] = round(time.monotonic() - started, 6)
        report["result"] = "PASS_METAOS_BOUNDED_BEHAVIORAL_TEST" if not failed else "FAIL_METAOS_POLICY_INVARIANTS"
        report["failed_assertions"] = failed
        report["bounded_behavior_verified"] = not failed
        report["execution_authorized"] = False
        report["host_imports_enabled"] = False
        report["network_access"] = "NOT_AVAILABLE_TO_COMPONENT"
    except Exception as exc:
        report["result"] = "FAIL_METAOS_BEHAVIORAL_TEST"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["calls_executed"] = calls
        report["elapsed_seconds"] = round(time.monotonic() - started, 6)

    out = ROOT / "evidence/custoszv8-metaos-execution.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS_METAOS_BOUNDED_BEHAVIORAL_TEST" else 1

if __name__ == "__main__":
    raise SystemExit(main())
