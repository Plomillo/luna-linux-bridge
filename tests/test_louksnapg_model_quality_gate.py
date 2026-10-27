import hashlib
import unittest

from tools.louksnapg_model_quality_gate import (
    FROZEN_CANDIDATE_SHA256, QualityGateError, SCHEMA, validate_assessment,
)

TARGETS = [
    "D01_CEREBRO_ROOT",
    "D03_TRANSCRIPCION_ROOT",
    "D04_TRADUCCION_GENERAL",
    "D05_DOCLING",
    "D06_ANALISIS_AVANZADO",
]


def h(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assessment():
    rows = []
    for target in TARGETS:
        output = "grounded test output for " + target
        rows.append({
            "target_id": target,
            "model_revision": "pinned-revision",
            "evaluator_id": "independent-test-oracle",
            "evaluator_version": "1.0",
            "weights_sha256": h("weights:" + target),
            "raw_output": output,
            "raw_output_sha256": h(output),
            "reference_fixture_sha256": h("fixture:" + target),
            "status": "PASS",
            "metrics": [{
                "name": "reference_metric",
                "value": 0.95,
                "operator": ">=",
                "threshold": 0.90,
                "status": "PASS",
            }],
        })
    return {
        "schema": SCHEMA,
        "candidate_frozen": True,
        "candidate_sha256": FROZEN_CANDIDATE_SHA256,
        "assessments": rows,
    }


class ModelQualityGateTests(unittest.TestCase):
    def test_complete_hash_bound_assessments_pass_only_quality_gate(self):
        result = validate_assessment(assessment())
        self.assertEqual(result["status"], "PASS_MODEL_QUALITY_EVIDENCE_ONLY")
        self.assertEqual(result["product_certification"], "NOT_GRANTED")
        self.assertEqual(result["target_count"], 5)
        self.assertEqual(result["candidate_sha256"], FROZEN_CANDIDATE_SHA256)

    def test_nonempty_output_without_quality_metrics_fails_closed(self):
        doc = assessment()
        doc["assessments"][0]["metrics"] = []
        with self.assertRaisesRegex(QualityGateError, "QUALITY_METRICS_MISSING"):
            validate_assessment(doc)

    def test_degenerate_output_cannot_pass_if_quality_threshold_fails(self):
        doc = assessment()
        row = doc["assessments"][0]
        row["metrics"][0]["value"] = 0.01
        with self.assertRaisesRegex(QualityGateError, "SEMANTIC_QUALITY_FAIL"):
            validate_assessment(doc)

    def test_output_hash_mismatch_fails_closed(self):
        doc = assessment()
        doc["assessments"][0]["raw_output"] = "mutated output"
        with self.assertRaisesRegex(QualityGateError, "RAW_OUTPUT_HASH_MISMATCH"):
            validate_assessment(doc)

    def test_missing_model_target_blocks_all_five_target_gate(self):
        doc = assessment()
        doc["assessments"].pop()
        with self.assertRaisesRegex(QualityGateError, "MODEL_TARGET_EVIDENCE_INCOMPLETE"):
            validate_assessment(doc)

    def test_frozen_candidate_required(self):
        doc = assessment()
        doc["candidate_frozen"] = False
        with self.assertRaisesRegex(QualityGateError, "CANDIDATE_FREEZE_NOT_CONFIRMED"):
            validate_assessment(doc)

    def test_unregistered_candidate_hash_is_rejected(self):
        doc = assessment()
        doc["candidate_sha256"] = h("different artifact")
        with self.assertRaisesRegex(
            QualityGateError, "CANDIDATE_HASH_NOT_REGISTERED_AS_FROZEN"
        ):
            validate_assessment(doc)

    def test_nonfinite_metric_value_is_rejected(self):
        doc = assessment()
        doc["assessments"][0]["metrics"][0]["value"] = float("nan")
        with self.assertRaisesRegex(QualityGateError, "QUALITY_METRIC_VALUE_INVALID"):
            validate_assessment(doc)

    def test_duplicate_metric_names_are_rejected(self):
        doc = assessment()
        row = doc["assessments"][0]
        row["metrics"].append(dict(row["metrics"][0]))
        with self.assertRaisesRegex(QualityGateError, "QUALITY_METRIC_DUPLICATE"):
            validate_assessment(doc)


if __name__ == "__main__":
    unittest.main()
