#!/usr/bin/env python3
"""Validate and package a non-promoting Whisper Q5 external release candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "LOUKSNAPG2_WHISPER_Q5_EXTERNAL_CANDIDATE/1.0"
EXPECTED_SOURCE_SHA256 = "aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a"
EXPECTED_Q5_BYTES = 574_041_195
EXPECTED_Q5_SHA256 = "394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2"
EXPECTED_QUANTIZATION = "q5_0"
MAX_RELEASE_ASSET_BYTES = 2 * 1024**3
ACTIVE_RELEASE_CAP_BYTES = 490_000_000
PROJECTED_RELEASE_BYTES = 936_619_119
ACTIVE_RUNTIME_RAM_BYTES = 1_073_741_824


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("JSON_FILE_MISSING_OR_UNSAFE:" + str(path))
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_ROOT_NOT_OBJECT:" + str(path))
    return value


def safe_relative(root: Path, value: str) -> Path:
    rel = PurePosixPath(value)
    if rel.is_absolute() or not rel.parts or ".." in rel.parts:
        raise ValueError("ASSET_PATH_INVALID:" + value)
    path = root.joinpath(*rel.parts)
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root) or path.is_symlink() or not path.is_file():
        raise ValueError("ASSET_PATH_UNSAFE:" + value)
    return path


def validate_candidate(artifact_root: Path, evaluation_path: Path) -> dict[str, Any]:
    root = artifact_root.resolve(strict=True)
    manifest = read_object(root / "fullrank_manifest.json")
    if manifest.get("schema") != "LOUKSNAPG_WHISPER_FULLRANK_QUANTIZATION_CANDIDATE/1.0":
        raise ValueError("FULLRANK_MANIFEST_SCHEMA_MISMATCH")

    source = manifest.get("source_model", {})
    source_sha = source.get("sha256")
    if source_sha != EXPECTED_SOURCE_SHA256:
        raise ValueError("SOURCE_TEACHER_SHA256_MISMATCH")
    if source.get("source_model_id") not in (None, "openai/whisper-large-v3-turbo"):
        raise ValueError("SOURCE_TEACHER_MODEL_ID_MISMATCH")

    conversion = manifest.get("conversion", {})
    if conversion.get("whisper_cpp_revision") != "482279b8a18855ba741d7b88c30fcb3874691f59":
        raise ValueError("WHISPER_CPP_SOURCE_REVISION_MISMATCH")
    candidates = [row for row in manifest.get("quantization_candidates", [])
                  if row.get("quantization") == EXPECTED_QUANTIZATION]
    if len(candidates) != 1:
        raise ValueError("Q5_CANDIDATE_ROW_NOT_UNIQUE")
    row = candidates[0]
    model = safe_relative(root, str(row.get("path", "")))
    q5_bytes = model.stat().st_size
    q5_sha = sha256_file(model)
    if q5_bytes != EXPECTED_Q5_BYTES or q5_bytes != int(row.get("bytes", -1)):
        raise ValueError("Q5_CANDIDATE_SIZE_MISMATCH:" + str(q5_bytes))
    if q5_sha != EXPECTED_Q5_SHA256 or q5_sha != row.get("sha256"):
        raise ValueError("Q5_CANDIDATE_HASH_MISMATCH:" + q5_sha)

    cli = safe_relative(root, "toolchain/bin/whisper-cli")
    library_rows = conversion.get("runtime_libraries")
    if not isinstance(library_rows, list) or not library_rows:
        raise ValueError("WHISPER_RUNTIME_LIBRARY_MANIFEST_MISSING")
    verified_libraries = []
    for library in library_rows:
        path = safe_relative(root, str(library.get("path", "")))
        if path.stat().st_size != int(library.get("bytes", -1)):
            raise ValueError("WHISPER_RUNTIME_LIBRARY_SIZE_MISMATCH:" + str(path))
        digest = sha256_file(path)
        if digest != library.get("sha256"):
            raise ValueError("WHISPER_RUNTIME_LIBRARY_SHA256_MISMATCH:" + str(path))
        verified_libraries.append({"path": library["path"], "bytes": path.stat().st_size,
                                   "sha256": digest})

    evaluation = read_object(evaluation_path)
    if evaluation.get("schema") != "LOUKSNAPG_WHISPER_FULLRANK_CANDIDATE_EVALUATION/4.0":
        raise ValueError("Q5_EVALUATION_SCHEMA_MISMATCH")
    if evaluation.get("status") != "PASS_FULLRANK_CANDIDATE_TWO_TASKS_EXTERNAL_ASSET_REQUIRED":
        raise ValueError("Q5_EVALUATION_STATUS_NOT_PASS")
    if evaluation.get("quantization") != EXPECTED_QUANTIZATION:
        raise ValueError("Q5_EVALUATION_QUANTIZATION_MISMATCH")
    evaluated_weight = evaluation.get("candidate_weight", {})
    if evaluated_weight.get("sha256") != q5_sha or int(evaluated_weight.get("bytes", -1)) != q5_bytes:
        raise ValueError("Q5_EVALUATION_CANDIDATE_IDENTITY_MISMATCH")
    teacher = evaluation.get("teacher_source", {})
    if teacher.get("sha256") != EXPECTED_SOURCE_SHA256 or teacher.get("hub_api_used") is not False:
        raise ValueError("Q5_SOURCE_PROVENANCE_OR_PROVIDER_POLICY_INVALID")
    dataset = evaluation.get("dataset_fixture", {})
    if dataset.get("provider_api_used") is not False:
        raise ValueError("Q5_DATASET_PROVIDER_API_USED")

    tests = evaluation.get("task_results", [])
    if len(tests) != 2:
        raise ValueError("Q5_EXPECTED_EXACTLY_TWO_RECORDED_TASKS")
    by_id = {row.get("task_id"): row for row in tests}
    synthetic = by_id.get("synthetic-hello-world", {})
    real = by_id.get("real-jfk", {})
    if synthetic.get("execution_status") != "PASS_EXECUTION" or synthetic.get("quality_check", {}).get("status") != "PASS":
        raise ValueError("Q5_SYNTHETIC_AUDIO_TEST_NOT_PASS")
    real_check = real.get("quality_check", {})
    if real.get("execution_status") != "PASS_EXECUTION" or real_check.get("status") != "PASS" or float(real_check.get("wer", 1.0)) > 0.25:
        raise ValueError("Q5_RECORDED_SPEECH_TEST_NOT_PASS")
    memory = evaluation.get("candidate_memory_measurement", {})
    if memory.get("memory_limit_bytes") != ACTIVE_RUNTIME_RAM_BYTES or int(memory.get("max_native_process_peak_rss_bytes", 0)) > ACTIVE_RUNTIME_RAM_BYTES:
        raise ValueError("Q5_MEMORY_RESULT_OUTSIDE_ACTIVE_ONE_GIB_LIMIT")
    if int(memory.get("oom_events_delta", -1)) != 0 or int(memory.get("oom_kill_events_delta", -1)) != 0:
        raise ValueError("Q5_EVALUATION_RECORDED_OOM")
    if evaluation.get("candidate_integrated") is not False or evaluation.get("promotion_performed") is not False:
        raise ValueError("Q5_CANDIDATE_WAS_ALREADY_PROMOTED_OR_INTEGRATED")

    return {
        "schema": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "candidate_id": "WHISPER_LARGE_V3_TURBO_FULLRANK_Q5_0",
        "candidate_status": "DRAFT_EXTERNAL_ASSET; NOT_REPAIRED_OR_CERTIFIED",
        "source": {
            "model_id": "openai/whisper-large-v3-turbo",
            "sha256": EXPECTED_SOURCE_SHA256,
            "provider": "OPENAI_OFFICIAL_AZURE_BLOB",
            "hub_api_used": False,
        },
        "conversion": {
            "whisper_cpp_revision": conversion["whisper_cpp_revision"],
            "quantization": EXPECTED_QUANTIZATION,
            "representation": row.get("representation"),
            "whisper_cli_sha256": conversion.get("whisper_cli_sha256"),
            "runtime_libraries": verified_libraries,
        },
        "candidate": {
            "path": PurePosixPath(str(row["path"])).as_posix(),
            "bytes": q5_bytes,
            "sha256": q5_sha,
        },
        "evaluation": {
            "workflow_run_id": 41788008012,
            "workflow_artifact_id": 13302302384,
            "status": evaluation["status"],
            "task_count": len(tests),
            "synthetic_output": synthetic.get("transcription_text"),
            "synthetic_quality": synthetic.get("quality_check"),
            "real_audio_output": real.get("transcription_text"),
            "real_audio_quality": real_check,
            "max_native_process_peak_rss_bytes": memory["max_native_process_peak_rss_bytes"],
            "memory_limit_bytes": memory["memory_limit_bytes"],
            "oom_events_delta": memory["oom_events_delta"],
        },
        "distribution": {
            "active_runtime_cap_bytes": ACTIVE_RELEASE_CAP_BYTES,
            "candidate_weight_bytes": q5_bytes,
            "projected_complete_release_bytes": PROJECTED_RELEASE_BYTES,
            "projected_release_exceeds_cap": PROJECTED_RELEASE_BYTES > ACTIVE_RELEASE_CAP_BYTES,
            "candidate_must_remain_external_to_runtime_package": True,
        },
        "provider_policy": {
            "hugging_face_jobs_used": False,
            "hugging_face_hub_api_used": False,
            "hugging_face_tokens_used": False,
            "remote_inference_used": False,
        },
        "immutability": {
            "original_teacher_mutated": False,
            "active_runtime_mutated": False,
            "candidate_integrated": False,
            "canonical_promotion": "NOT_AUTHORIZED",
            "domain_certification": "NOT_GRANTED",
            "global_certification": "NOT_GRANTED",
        },
        "limitations": [
            "Only two fixed audio tasks were evaluated: one local synthetic utterance and one pinned JFK speech clip.",
            "A representative held-out speech corpus and full WER benchmark have not been run.",
            "The candidate is not integrated into the active Cajita runtime.",
            "The active compact Whisper model remains semantically failed in the five-domain E2E suite.",
        ],
    }


def build_archive(artifact_root: Path, archive_path: Path) -> None:
    root = artifact_root.resolve(strict=True)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, mode="w", format=tarfile.PAX_FORMAT) as archive:
        archive.add(root, arcname="whisper-q5-candidate", recursive=True)
    if archive_path.stat().st_size >= MAX_RELEASE_ASSET_BYTES:
        raise ValueError("RELEASE_ASSET_EXCEEDS_GITHUB_TWO_GIB_LIMIT")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()

    report = validate_candidate(args.artifact_root, args.evaluation)
    build_archive(args.artifact_root, args.archive)
    report["external_archive"] = {
        "filename": args.archive.name,
        "bytes": args.archive.stat().st_size,
        "sha256": sha256_file(args.archive),
        "format": "USTAR",
    }
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                                    encoding="utf-8")
    print(json.dumps({
        "status": report["candidate_status"],
        "candidate_sha256": report["candidate"]["sha256"],
        "candidate_bytes": report["candidate"]["bytes"],
        "archive_bytes": report["external_archive"]["bytes"],
        "archive_sha256": report["external_archive"]["sha256"],
        "evaluation_status": report["evaluation"]["status"],
        "real_audio_wer": report["evaluation"]["real_audio_quality"]["wer"],
        "peak_rss_bytes": report["evaluation"]["max_native_process_peak_rss_bytes"],
        "canonical_promotion": "NOT_AUTHORIZED",
    }, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
