#!/usr/bin/env python3
"""Fail-closed semantic quality gate for LOUKSNAPG model task receipts.

This gate validates hash-bound quality assessments for the one frozen candidate.
It does not infer quality from process exit code, non-empty text, or token count,
and it never grants product certification. Model identifiers, source URLs, source
revisions and model revisions are checked against the integral gate's pinned
contract to prevent a similarly named or differently versioned model passing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = "LOUKSNAPG_MODEL_QUALITY_ASSESSMENT/1.1"
# Exact artifact hash recorded by the previously completed G24 evidence.
# Any different artifact requires a separately authorized candidate registration.
FROZEN_CANDIDATE_SHA256 = "989277d80a596a8a38564d4234e441896b105b2ba4a5843ed99a0877c88ca663"
REQUIRED_TARGETS = {
    "D01_CEREBRO_ROOT",
    "D03_TRANSCRIPCION_ROOT",
    "D04_TRADUCCION_GENERAL",
    "D05_DOCLING",
    "D06_ANALISIS_AVANZADO",
}

# Duplicated here intentionally as a frozen, auditable contract. The regression
# test compares these values with tools/louksnapg_integral_gate.py to detect drift.
MODEL_CONTRACTS = {
    "D01_CEREBRO_ROOT": {
        "model_id": "openai/gpt-oss-120b",
        "official_source_url": "https://github.com/openai/gpt-oss",
        "upstream_revision_commit": "5681a6b6552635e7b29cde94a61ca6a7aee90ebd",
        "model_revision": "b5c939de8f754692c1647ca79fbf85e8c1e70f8a",
    },
    "D03_TRANSCRIPCION_ROOT": {
        "model_id": "openai/whisper-large-v3-turbo",
        "official_source_url": "https://github.com/openai/whisper",
        "upstream_revision_commit": "86098128c0b4f24f0e2aa2994de830614b474227",
        "model_revision": "41f01f3fe87f28c78e2fbf8b568835947dd65ed9",
    },
    "D04_TRADUCCION_GENERAL": {
        "model_id": "facebook/seamless-m4t-v2-large",
        "official_source_url": "https://github.com/facebookresearch/seamless_communication",
        "upstream_revision_commit": "9a081e935c29c6b1e0e05bcbf3fcb623ad306524",
        "model_revision": "b8d7691bcced0d24b2655f534b6148be78346b72",
    },
    "D05_DOCLING": {
        "model_id": "ibm-granite/granite-docling-258M",
        "official_source_url": "https://huggingface.co/ibm-granite/granite-docling-258M",
        "upstream_revision_commit": "982fe3b40f2fa73c365bdb1bcacf6c81b7184bfe",
        "model_revision": "982fe3b40f2fa73c365bdb1bcacf6c81b7184bfe",
    },
    "D06_ANALISIS_AVANZADO": {
        "model_id": "Qwen/Qwen3-14B",
        "official_source_url": "https://github.com/QwenLM/Qwen3",
        "upstream_revision_commit": "7a2f61ffc7a20d47efcd2bf97f6f2bf52729042e",
        "model_revision": "40c069824f4251a91eefaf281ebe4c544efd3e18",
    },
}


class QualityGateError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_hash(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise QualityGateError("MISSING_OR_INVALID_" + field.upper())
    try:
        int(value, 16)
    except ValueError as exc:
        raise QualityGateError("MISSING_OR_INVALID_" + field.upper()) from exc
    return value.lower()


def validate_assessment(document: Any) -> dict[str, Any]:
    """Validate five model assessments bound to the exact frozen artifact.

    Each row must match the pinned model/source contract and bind model identity,
    weight bytes, raw task output, reference fixture, evaluator and metric
    thresholds. Metric values must be finite and each metric name unique per
    target. This validates structure and declared results only; it does not
    independently prove the evaluator's truth or reproduce model inference.
    """
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise QualityGateError("ASSESSMENT_SCHEMA_INVALID")
    if document.get("candidate_frozen") is not True:
        raise QualityGateError("CANDIDATE_FREEZE_NOT_CONFIRMED")
    candidate_sha = _require_hash(document.get("candidate_sha256"), "candidate_sha256")
    if candidate_sha != FROZEN_CANDIDATE_SHA256:
        raise QualityGateError("CANDIDATE_HASH_NOT_REGISTERED_AS_FROZEN")
    rows = document.get("assessments")
    if not isinstance(rows, list):
        raise QualityGateError("ASSESSMENTS_MISSING")

    by_target: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise QualityGateError("ASSESSMENT_ROW_INVALID")
        target = row.get("target_id")
        if target not in REQUIRED_TARGETS or target in by_target:
            raise QualityGateError("UNKNOWN_OR_DUPLICATE_TARGET")

        contract = MODEL_CONTRACTS[target]
        for field, expected in contract.items():
            observed = row.get(field)
            if not isinstance(observed, str) or not observed.strip():
                raise QualityGateError("MISSING_" + field.upper() + ":" + target)
            if observed != expected:
                raise QualityGateError("PINNED_MODEL_CONTRACT_MISMATCH:" + target + ":" + field)

        for key in ("evaluator_id", "evaluator_version"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise QualityGateError("MISSING_" + key.upper() + ":" + target)
        _require_hash(row.get("weights_sha256"), "weights_sha256")
        _require_hash(row.get("raw_output_sha256"), "raw_output_sha256")
        _require_hash(row.get("reference_fixture_sha256"), "reference_fixture_sha256")
        output = row.get("raw_output")
        if not isinstance(output, str) or not output.strip():
            raise QualityGateError("RAW_OUTPUT_MISSING:" + target)
        if sha256_bytes(output.encode("utf-8")) != row["raw_output_sha256"].lower():
            raise QualityGateError("RAW_OUTPUT_HASH_MISMATCH:" + target)

        metrics = row.get("metrics")
        if not isinstance(metrics, list) or not metrics:
            raise QualityGateError("QUALITY_METRICS_MISSING:" + target)
        seen_metric_names: set[str] = set()
        for metric in metrics:
            if not isinstance(metric, dict):
                raise QualityGateError("QUALITY_METRIC_INVALID:" + target)
            name, value, operator, threshold = (
                metric.get("name"), metric.get("value"),
                metric.get("operator"), metric.get("threshold"),
            )
            if not isinstance(name, str) or not name.strip():
                raise QualityGateError("QUALITY_METRIC_NAME_MISSING:" + target)
            if name in seen_metric_names:
                raise QualityGateError("QUALITY_METRIC_DUPLICATE:" + target + ":" + name)
            seen_metric_names.add(name)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value)):
                raise QualityGateError("QUALITY_METRIC_VALUE_INVALID:" + target)
            if (isinstance(threshold, bool) or not isinstance(threshold, (int, float))
                    or not math.isfinite(threshold)):
                raise QualityGateError("QUALITY_METRIC_THRESHOLD_INVALID:" + target)
            passed = (
                value >= threshold if operator == ">=" else
                value <= threshold if operator == "<=" else
                value == threshold if operator == "==" else None
            )
            if passed is None:
                raise QualityGateError("QUALITY_METRIC_OPERATOR_INVALID:" + target)
            if metric.get("status") != "PASS" or not passed:
                raise QualityGateError("SEMANTIC_QUALITY_FAIL:" + target + ":" + name)
        if row.get("status") != "PASS":
            raise QualityGateError("ASSESSMENT_NOT_PASS:" + target)
        by_target[target] = row

    missing = sorted(REQUIRED_TARGETS - set(by_target))
    if missing:
        raise QualityGateError("MODEL_TARGET_EVIDENCE_INCOMPLETE:" + ",".join(missing))
    return {
        "schema": "LOUKSNAPG_MODEL_QUALITY_GATE_RESULT/1.1",
        "status": "PASS_MODEL_QUALITY_EVIDENCE_ONLY",
        "candidate_sha256": candidate_sha,
        "assessed_targets": sorted(by_target),
        "target_count": len(by_target),
        "product_certification": "NOT_GRANTED",
        "independent_g23": "REQUIRED",
        "separate_g24_decision": "REQUIRED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assessment_json")
    args = parser.parse_args()
    try:
        path = Path(args.assessment_json)
        if path.is_symlink() or not path.is_file():
            raise QualityGateError("ASSESSMENT_FILE_MISSING_OR_SYMLINK")
        document = json.loads(path.read_text(encoding="utf-8"))
        result = validate_assessment(document)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, QualityGateError) as exc:
        print(json.dumps({
            "schema": "LOUKSNAPG_MODEL_QUALITY_GATE_RESULT/1.1",
            "status": "HOLD",
            "reason": str(exc)[:300],
            "product_certification": "NOT_GRANTED",
        }, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
