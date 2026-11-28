"""Source-bound D03 executable plans for programming and lifecycle cases."""
from __future__ import annotations

CASES = [
    {
        "case_id": "MGL5-INF-0122",
        "capability_id": "fibonacci_compare",
        "arguments": {"n": 20},
        "fixture_provenance": "TYPED_FIXTURE_FROM_SOURCE_INSTRUCTION: deterministic Fibonacci index 20; no source literal was claimed",
    },
    {
        "case_id": "MGL5-INF-0123",
        "capability_id": "knapsack_01",
        "arguments": {
            "capacity": 10,
            "items": [
                {"weight": 6, "value": 30},
                {"weight": 4, "value": 16},
                {"weight": 5, "value": 20},
                {"weight": 3, "value": 14},
            ],
        },
        "fixture_provenance": "TYPED_FOUR_OBJECT_FIXTURE: capacity 10 is source literal; object weights/values are explicit fixture choices, not source-provided literals",
    },
    {
        "case_id": "MGL5-INF-0124",
        "capability_id": "email_syntax",
        "arguments": {"addresses": ["luna@example.test", "diego.n@example.test", "invalid-address", "@example.test", "luna@", "luna@localhost"]},
        "fixture_provenance": "SYNTHETIC_EMAIL_FIXTURE: explicit valid/invalid syntax examples; scope deliberately excludes full RFC mailbox validation",
    },
    {
        "case_id": "MGL5-INF-0127",
        "capability_id": "optional_value",
        "arguments": {"present": False, "value": None, "default": "fallback"},
        "fixture_provenance": "TYPED_OPTIONAL_FIXTURE: explicit absent state and fallback; source specifies absent value without dereference",
    },
    {
        "case_id": "MGL5-INF-0128",
        "capability_id": "read_cleanup",
        "arguments": {"payload_hex": "616263", "fail_read": True},
        "fixture_provenance": "SYNTHETIC_IO_FIXTURE: in-memory descriptor and deterministic injected read failure; no host filesystem access",
    },
    {
        "case_id": "MGL5-INF-0129",
        "capability_id": "finally_once",
        "arguments": {"raise_error": True, "message": "fixture-error"},
        "fixture_provenance": "SYNTHETIC_EXCEPTION_FIXTURE: controlled ValueError and finally counter; no external side effects",
    },
    {
        "case_id": "MGL5-INF-0130",
        "capability_id": "raii_release",
        "arguments": {"early_exit": True, "payload_hex": "7061796c6f6164"},
        "fixture_provenance": "SYNTHETIC_RESOURCE_FIXTURE: context-managed in-memory resource and early return; no OS handle or external side effect",
    },
]
