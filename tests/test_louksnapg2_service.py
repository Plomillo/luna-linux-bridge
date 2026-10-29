from __future__ import annotations

import hashlib
import json
import unittest
from unittest import mock

from louksnapg2_service import (
    SCHEMA_REQUEST,
    ServiceError,
    TARGET_BINDINGS,
    dispatch_target,
    execute_request,
)


class FakeRuntime:
    def __init__(self, result=None):
        self.result = result or {
            "status": "PASS_EXECUTION",
            "execution_authorized": True,
            "domain_id": "D04_TRADUCCION_LENGUAS_ANTIGUAS",
            "operation": "translate_ancient_text",
            "output_text": "The die is cast.",
            "output_sha256": hashlib.sha256(b"The die is cast.").hexdigest(),
            "model_source_evidence": {"fixture": "unit-only"},
            "source_language": "lat",
            "target_language": "eng",
            "translation_strategy": "DEDICATED_ANCIENT_LANGUAGE_ADAPTER",
            "general_translation_fallback_selected": False,
        }
        self.calls = []

    def route(self, domain_id, operation, payload):
        self.calls.append((domain_id, operation, payload))
        return dict(self.result)


class LouksnapG2ServiceTests(unittest.TestCase):
    def test_all_five_required_target_ids_have_distinct_registered_bindings(self):
        self.assertEqual(
            set(TARGET_BINDINGS),
            {
                "D01_CEREBRO_ROOT",
                "D06_ANALISIS_AVANZADO",
                "D04_TRADUCCION_GENERAL",
                "D04_TRADUCCION_LENGUAS_ANTIGUAS",
                "D03_TRANSCRIPCION_ROOT",
            },
        )
        self.assertEqual(
            len({(row["domain_id"], row["operation"]) for row in TARGET_BINDINGS.values()}),
            5,
        )

    def test_ancient_translation_target_reaches_only_the_dedicated_domain_and_operation(self):
        runtime = FakeRuntime()
        response = dispatch_target(
            runtime,
            "D04_TRADUCCION_LENGUAS_ANTIGUAS",
            {"text": "Alea iacta est", "src_lang": "lat", "tgt_lang": "eng"},
            task_id="ancient-test-01",
        )
        self.assertEqual(runtime.calls[0][0], "D04_TRADUCCION_LENGUAS_ANTIGUAS")
        self.assertEqual(runtime.calls[0][1], "translate_ancient_text")
        self.assertEqual(response["target_id"], "D04_TRADUCCION_LENGUAS_ANTIGUAS")
        self.assertEqual(response["adapter_id"], "LOUKSNAPG2_ANCIENT_TRANSLATION_ADAPTER/1.0")
        self.assertFalse(response["general_translation_fallback_selected"])
        self.assertEqual(response["output_sha256"], hashlib.sha256(b"The die is cast.").hexdigest())
        self.assertEqual(response["certification"], "NOT_GRANTED_BY_DISPATCH")

    def test_ancient_translation_fallback_is_rejected(self):
        runtime = FakeRuntime({
            "status": "PASS_EXECUTION",
            "execution_authorized": True,
            "domain_id": "D04_TRADUCCION_LENGUAS_ANTIGUAS",
            "operation": "translate_ancient_text",
            "output_text": "fallback",
            "output_sha256": hashlib.sha256(b"fallback").hexdigest(),
            "general_translation_fallback_selected": True,
        })
        with self.assertRaisesRegex(ServiceError, "ANCIENT_TRANSLATION_FALLBACK_FORBIDDEN"):
            dispatch_target(runtime, "D04_TRADUCCION_LENGUAS_ANTIGUAS", {"text": "test"}, task_id="ancient-02")

    def test_unknown_target_fails_before_engine_invocation(self):
        runtime = FakeRuntime()
        with self.assertRaisesRegex(ServiceError, "TARGET_NOT_REGISTERED"):
            dispatch_target(runtime, "D04_UNKNOWN_TRANSLATOR", {"text": "test"}, task_id="unknown-01")
        self.assertEqual(runtime.calls, [])

    def test_request_domain_and_operation_are_bound_to_registered_target(self):
        runtime = FakeRuntime()
        request = {
            "schema": SCHEMA_REQUEST,
            "task_id": "route-01",
            "target_id": "D04_TRADUCCION_LENGUAS_ANTIGUAS",
            "domain_id": "D04_TRADUCTOR_INTELIGENTE",
            "operation": "translate_text",
            "payload": {"text": "Alea iacta est", "src_lang": "lat", "tgt_lang": "eng"},
        }
        with self.assertRaisesRegex(ServiceError, "REQUEST_DOMAIN_BINDING_MISMATCH"):
            execute_request(runtime, request)
        self.assertEqual(runtime.calls, [])

    def test_wrong_engine_result_binding_is_rejected(self):
        runtime = FakeRuntime({
            "status": "PASS_EXECUTION",
            "execution_authorized": True,
            "domain_id": "D04_TRADUCTOR_INTELIGENTE",
            "operation": "translate_text",
            "output_text": "general route",
            "output_sha256": hashlib.sha256(b"general route").hexdigest(),
            "general_translation_fallback_selected": False,
        })
        with self.assertRaisesRegex(ServiceError, "ENGINE_ROUTE_RESULT_BINDING_MISMATCH"):
            dispatch_target(runtime, "D04_TRADUCCION_LENGUAS_ANTIGUAS", {"text": "test"}, task_id="route-02")

    def test_noncanonical_task_id_is_rejected(self):
        runtime = FakeRuntime()
        with self.assertRaisesRegex(ServiceError, "TASK_ID_INVALID"):
            dispatch_target(runtime, "D04_TRADUCCION_LENGUAS_ANTIGUAS", {}, task_id="bad id")

    def test_canonical_cerebro_target_resolves_to_reasoning_domain(self):
        runtime = FakeRuntime({
            "status": "PASS_EXECUTION",
            "execution_authorized": True,
            "domain_id": "D01_CEREBRO",
            "operation": "generate_text",
            "output_text": "42",
            "output_sha256": hashlib.sha256(b"42").hexdigest(),
            "model_source_evidence": {"fixture": "unit-only"},
        })
        response = dispatch_target(runtime, "D01_CEREBRO_ROOT", {"prompt": "return 42"}, task_id="brain-01")
        self.assertEqual(runtime.calls[0][0], "D01_CEREBRO")
        self.assertEqual(runtime.calls[0][1], "generate_text")
        self.assertEqual(response["target_id"], "D01_CEREBRO_ROOT")
        self.assertTrue(response["execution_authorized"])
        self.assertEqual(response["status"], "PASS_EXECUTION")


if __name__ == "__main__":
    unittest.main()
