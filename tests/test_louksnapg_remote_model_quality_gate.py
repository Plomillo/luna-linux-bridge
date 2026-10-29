from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from louksnapg_remote_model_quality_gate import (
    final_integer,
    integral_domain_gate_status,
    normalize_text,
    required_domain_statuses,
)


class RemoteQualityGateTests(unittest.TestCase):
    def test_text_normalization_removes_accents_and_punctuation(self):
        self.assertEqual(normalize_text("El libro está sobre la mesa."), "el libro esta sobre la mesa")

    def test_final_integer_uses_last_standalone_integer(self):
        self.assertEqual(final_integer("6 x 4 = 24, then 24 - 7 + 3 = 20"), 20)
        self.assertIsNone(final_integer("no numeric answer"))

    def test_ancient_domain_stays_blocked_even_when_other_remote_tasks_pass(self):
        rows = [
            {"task_id": "brain", "domain_id": "D01_CEREBRO", "status": "PASS_REMOTE_EXECUTION",
             "execution_authorized": True, "quality_status": "PASS"},
            {"task_id": "qwen", "domain_id": "D06_SISTEMA_INTELIGENTE", "status": "PASS_REMOTE_EXECUTION",
             "execution_authorized": True, "quality_status": "PASS"},
            {"task_id": "general", "domain_id": "D04_TRADUCTOR_INTELIGENTE", "status": "PASS_REMOTE_EXECUTION",
             "execution_authorized": True, "quality_status": "PASS"},
            {"task_id": "whisper-synthetic", "domain_id": "D03_TRANSCRIPCION", "status": "PASS_REMOTE_EXECUTION",
             "execution_authorized": True, "quality_status": "PASS"},
            {"task_id": "whisper-real", "domain_id": "D03_TRANSCRIPCION", "status": "PASS_REMOTE_EXECUTION",
             "execution_authorized": True, "quality_status": "PASS"},
        ]
        ancient = {
            "status": "PASS_ROUTE_IDENTIFIED_FAIL_CLOSED",
            "functional_translation_status": "BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE",
            "general_translation_fallback_selected": False,
            "execution_authorized": False,
        }
        coverage = required_domain_statuses(rows, ancient)
        by_domain = {row["domain_id"]: row for row in coverage}
        self.assertEqual(len(coverage), 5)
        self.assertEqual(by_domain["D01_CEREBRO"]["status"], "PASS_KNOWN_ANSWER_TASKS_ONLY")
        self.assertEqual(by_domain["D03_TRANSCRIPCION"]["status"], "PASS_KNOWN_ANSWER_TASKS_ONLY")
        self.assertEqual(
            by_domain["D04_TRADUCCION_LENGUAS_ANTIGUAS"]["status"],
            "BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE",
        )
        self.assertEqual(integral_domain_gate_status(coverage), "BLOCKED_REQUIRED_DOMAIN_NOT_ESTABLISHED")

    def test_whisper_requires_both_declared_audio_tasks(self):
        rows = [
            {"task_id": "whisper-synthetic", "domain_id": "D03_TRANSCRIPCION",
             "status": "PASS_REMOTE_EXECUTION", "execution_authorized": True, "quality_status": "PASS"},
        ]
        ancient = {
            "status": "PASS_ROUTE_IDENTIFIED_FAIL_CLOSED",
            "functional_translation_status": "BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE",
            "general_translation_fallback_selected": False,
        }
        coverage = required_domain_statuses(rows, ancient)
        whisper = next(row for row in coverage if row["domain_id"] == "D03_TRANSCRIPCION")
        self.assertEqual(whisper["status"], "NOT_TESTED_REQUIRED_TASK_COUNT_INCOMPLETE")

    def test_ancient_route_with_general_fallback_cannot_be_accepted(self):
        ancient = {
            "status": "PASS_ROUTE_IDENTIFIED_FAIL_CLOSED",
            "functional_translation_status": "BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE",
            "general_translation_fallback_selected": True,
        }
        coverage = required_domain_statuses([], ancient)
        record = next(row for row in coverage if row["domain_id"] == "D04_TRADUCCION_LENGUAS_ANTIGUAS")
        self.assertEqual(record["status"], "FAIL_ANCIENT_ROUTE_DIAGNOSTIC")
        self.assertEqual(integral_domain_gate_status(coverage), "BLOCKED_REQUIRED_DOMAIN_NOT_ESTABLISHED")

    def test_empty_or_incomplete_coverage_fails_closed(self):
        self.assertEqual(integral_domain_gate_status([]), "BLOCKED_REQUIRED_DOMAIN_NOT_ESTABLISHED")
        self.assertEqual(
            integral_domain_gate_status([{"required_domain": "Cerebro", "status": "PASS_KNOWN_ANSWER_TASKS_ONLY"},
                                         {"required_domain": "Antiguas", "status": "NOT_TESTED"}]),
            "BLOCKED_REQUIRED_DOMAIN_NOT_ESTABLISHED",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
