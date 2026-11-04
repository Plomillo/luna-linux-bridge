#!/usr/bin/env python3
"""Offline, non-promoting diagnostic for a repository-retained full-rank Whisper Q4 artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "LOUKSNAPG2_WHISPER_FULLRANK_OFFLINE_DIAGNOSTIC/1.0"
SOURCE_MODEL_SHA256 = "542566a422ae4f3fd23f1ba11add198fca01bbf82e66e6a2857b3f608b1eb9d1"
SOURCE_MODEL_REVISION = "7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7"
WHISPER_CPP_REVISION = "482279b8a18855ba741d7b88c30fcb3874691f59"
OPENAI_WHISPER_FIXTURE_REVISION = "86098128c0b4f24f0e2aa2994de830614b474227"
CANDIDATE_RUN_ID = 41554376806
CANDIDATE_ARTIFACT_NAME = "louksnapg-whisper-fullrank-q4_0-41554376806"
EXPECTED_Q4_BYTES = 473_992_235
EXPECTED_Q4_SHA256 = "6e670d7569d1ed261cb8a4e554138f0ba6a17be7c64f079145061f93bac54e80"
CANDIDATE_RAM_BYTES = 1_342_177_280  # Temporary 1.25-GiB diagnostic ceiling only.
ACTIVE_RUNTIME_RAM_BYTES = 1_073_741_824
GLOBAL_RELEASE_MAX_BYTES = 490_000_000
PROJECTED_COMPLETE_RELEASE_BYTES = 836_570_159
JFK_REQUIRED_PHRASES = ("my fellow americans", "your country", "do for you")
SYNTHETIC_REFERENCE = "Hello world. The meeting starts at noon."


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).casefold())


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref, hyp = normalized_words(reference), normalized_words(hypothesis)
    if not ref:
        raise ValueError("WER_REFERENCE_EMPTY")
    previous = list(range(len(hyp) + 1))
    for i, ref_word in enumerate(ref, 1):
        current = [i]
        for j, hyp_word in enumerate(hyp, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (ref_word != hyp_word)))
        previous = current
    return previous[-1] / len(ref)


def read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("JSON_FILE_MISSING_OR_UNSAFE:" + str(path))
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("JSON_ROOT_NOT_OBJECT:" + str(path))
    return value


def parse_events(path: Path) -> dict[str, int]:
    return {key: int(value) for key, value in
            (line.split() for line in path.read_text(encoding="ascii").splitlines())}


def cgroup_budget() -> dict[str, Any]:
    root = Path("/sys/fs/cgroup")
    memory_path, swap_path, cpu_path, events_path, peak_path = (
        root / "memory.max", root / "memory.swap.max", root / "cpu.max",
        root / "memory.events", root / "memory.peak")
    missing = [str(p) for p in (memory_path, swap_path, cpu_path, events_path, peak_path) if not p.is_file()]
    if missing:
        raise RuntimeError("CGROUP_V2_EVIDENCE_MISSING:" + ",".join(missing))
    memory = int(memory_path.read_text(encoding="ascii").strip())
    swap = int(swap_path.read_text(encoding="ascii").strip())
    cpu = cpu_path.read_text(encoding="ascii").split()
    if memory != CANDIDATE_RAM_BYTES:
        raise RuntimeError(f"DIAGNOSTIC_CGROUP_MEMORY_MISMATCH:{memory}:{CANDIDATE_RAM_BYTES}")
    if swap != 0:
        raise RuntimeError("DIAGNOSTIC_CGROUP_SWAP_NOT_DISABLED:" + str(swap))
    if len(cpu) != 2 or int(cpu[0]) != int(cpu[1]):
        raise RuntimeError("DIAGNOSTIC_CGROUP_CPU_NOT_ONE_CORE:" + repr(cpu))
    return {
        "memory_limit_bytes": memory, "memory_limit_gib": memory / 1024**3,
        "swap_limit_bytes": swap, "cpu_quota": int(cpu[0]),
        "cpu_period": int(cpu[1]), "cpu_limit_cores": int(cpu[0]) / int(cpu[1]),
        "memory_events_at_start": parse_events(events_path),
    }


def verify_artifact(artifact_root: Path) -> tuple[Path, dict[str, Any]]:
    root = artifact_root.resolve(strict=True)
    manifest_path = root / "fullrank_manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("schema") != "LOUKSNAPG_WHISPER_FULLRANK_QUANTIZATION_CANDIDATE/1.0":
        raise RuntimeError("FULLRANK_CANDIDATE_SCHEMA_MISMATCH")
    source = manifest.get("source_model", {})
    if source.get("sha256") != SOURCE_MODEL_SHA256:
        raise RuntimeError("FULLRANK_TEACHER_CHECKPOINT_SHA_MISMATCH")
    if source.get("revision") != SOURCE_MODEL_REVISION:
        raise RuntimeError("FULLRANK_TEACHER_REVISION_MISMATCH")
    conversion = manifest.get("conversion", {})
    if conversion.get("whisper_cpp_revision") != WHISPER_CPP_REVISION:
        raise RuntimeError("WHISPER_CPP_REVISION_MISMATCH")
    if conversion.get("openai_whisper_assets_revision") != OPENAI_WHISPER_FIXTURE_REVISION:
        raise RuntimeError("OPENAI_WHISPER_FIXTURE_REVISION_MISMATCH")
    rows = [row for row in manifest.get("quantization_candidates", []) if row.get("quantization") == "q4_0"]
    if len(rows) != 1:
        raise RuntimeError("Q4_CANDIDATE_ROW_NOT_UNIQUE")
    row = rows[0]
    rel = Path(str(row.get("path", "")))
    if rel.is_absolute() or ".." in rel.parts:
        raise RuntimeError("Q4_CANDIDATE_PATH_INVALID")
    model_path = (root / rel).resolve(strict=True)
    if not model_path.is_relative_to(root) or model_path.is_symlink() or not model_path.is_file():
        raise RuntimeError("Q4_CANDIDATE_PATH_UNSAFE")
    if model_path.stat().st_size != EXPECTED_Q4_BYTES or model_path.stat().st_size != int(row.get("bytes", -1)):
        raise RuntimeError("Q4_CANDIDATE_SIZE_MISMATCH:" + str(model_path.stat().st_size))
    digest = sha256_file(model_path)
    if digest != EXPECTED_Q4_SHA256 or digest != row.get("sha256"):
        raise RuntimeError("Q4_CANDIDATE_SHA256_MISMATCH:" + digest)
    cli = root / "toolchain" / "bin" / "whisper-cli"
    if cli.is_symlink() or not cli.is_file() or sha256_file(cli) != conversion.get("whisper_cli_sha256"):
        raise RuntimeError("PINNED_WHISPER_CLI_IDENTITY_MISMATCH")
    lib_dir = root / "toolchain" / "lib"
    if lib_dir.is_symlink() or not lib_dir.is_dir():
        raise RuntimeError("PINNED_WHISPER_LIBRARY_DIR_MISSING")
    libraries = conversion.get("runtime_libraries")
    if not isinstance(libraries, list) or not libraries:
        raise RuntimeError("PINNED_WHISPER_LIBRARY_MANIFEST_MISSING")
    for lib in libraries:
        lib_rel = Path(str(lib.get("path", "")))
        if lib_rel.is_absolute() or ".." in lib_rel.parts:
            raise RuntimeError("WHISPER_RUNTIME_LIBRARY_PATH_INVALID")
        path = (root / lib_rel).resolve(strict=True)
        if not path.is_relative_to(root) or path.is_symlink() or not path.is_file():
            raise RuntimeError("WHISPER_RUNTIME_LIBRARY_PATH_UNSAFE:" + str(lib_rel))
        if path.stat().st_size != int(lib.get("bytes", -1)) or sha256_file(path) != lib.get("sha256"):
            raise RuntimeError("WHISPER_RUNTIME_LIBRARY_IDENTITY_MISMATCH:" + str(lib_rel))
    if not any(Path(str(lib.get("path", ""))).name == "libwhisper.so.1" for lib in libraries):
        raise RuntimeError("WHISPER_SONAME_NOT_IN_BUNDLE")
    fixture = manifest.get("evaluation_fixture", {})
    fixture_rel = Path(str(fixture.get("path", "")))
    if fixture_rel.as_posix() != "fixtures/jfk.wav" or fixture.get("source_revision") != WHISPER_CPP_REVISION:
        raise RuntimeError("Q4_JFK_FIXTURE_MANIFEST_IDENTITY_MISMATCH")
    if not isinstance(fixture.get("bytes"), int) or fixture.get("bytes", 0) <= 0:
        raise RuntimeError("Q4_JFK_FIXTURE_SIZE_INVALID")
    if not re.fullmatch(r"[0-9a-f]{64}", str(fixture.get("sha256", ""))):
        raise RuntimeError("Q4_JFK_FIXTURE_SHA256_INVALID")
    return model_path, {
        "manifest_sha256": sha256_file(manifest_path),
        "source_model": source,
        "whisper_cpp_revision": conversion["whisper_cpp_revision"],
        "openai_whisper_assets_revision": conversion["openai_whisper_assets_revision"],
        "whisper_cli_sha256": conversion["whisper_cli_sha256"],
        "runtime_libraries_count": len(libraries),
        "evaluation_fixture": fixture,
        "candidate": {"quantization": "q4_0", "representation": row.get("representation"),
                      "path": rel.as_posix(), "bytes": model_path.stat().st_size, "sha256": digest},
    }


def run_transcription(cli: Path, model: Path, audio: Path, prefix: Path, library_dir: Path) -> dict[str, Any]:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "LD_LIBRARY_PATH": str(library_dir.resolve(strict=True)) +
            (os.pathsep + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else ""),
        "OMP_NUM_THREADS": "1", "OMP_THREAD_LIMIT": "1",
        "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false",
    })
    command = [str(cli), "-m", str(model), "-f", str(audio), "-l", "en",
               "-t", "1", "-ng", "-nt", "-otxt", "-of", str(prefix),
               "-np", "-nf", "-bs", "1", "-bo", "1"]
    started = time.monotonic()
    try:
        proc = subprocess.run(command, cwd=str(prefix.parent), env=env,
                              capture_output=True, text=True, errors="replace",
                              timeout=1800, check=False)
    except subprocess.TimeoutExpired as exc:
        return {"status": "FAIL_TIMEOUT", "elapsed_seconds": round(time.monotonic()-started, 3),
                "stdout_tail": str(exc.stdout or "")[-2000:], "stderr_tail": str(exc.stderr or "")[-3000:]}
    output_path = prefix.with_suffix(".txt")
    transcript = output_path.read_text(encoding="utf-8", errors="replace").strip() if output_path.is_file() else ""
    return {
        "status": "PASS_EXECUTION" if proc.returncode == 0 and transcript else "FAIL_EXECUTION",
        "exit_code": proc.returncode, "elapsed_seconds": round(time.monotonic()-started, 3),
        "audio_sha256": sha256_file(audio), "audio_bytes": audio.stat().st_size,
        "transcript": transcript[:4000],
        "transcript_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
        "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-3000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--jfk-audio", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    budget = cgroup_budget()
    model, artifact = verify_artifact(args.artifact_root)
    root = args.artifact_root.resolve(strict=True)
    jfk = args.jfk_audio.resolve(strict=True)
    expected_fixture = artifact["evaluation_fixture"]
    bundled_fixture = (root / expected_fixture["path"]).resolve(strict=True)
    if not bundled_fixture.is_relative_to(root) or bundled_fixture.is_symlink() or jfk != bundled_fixture:
        raise RuntimeError("JFK_AUDIO_PATH_NOT_BOUND_TO_Q4_CANDIDATE_MANIFEST")
    if jfk.stat().st_size != int(expected_fixture["bytes"]) or sha256_file(jfk) != expected_fixture["sha256"]:
        raise RuntimeError("Q4_BUNDLED_JFK_AUDIO_IDENTITY_MISMATCH")
    if jfk.suffix.lower() != ".wav":
        raise RuntimeError("Q4_BUNDLED_JFK_AUDIO_FORMAT_INVALID")
    cli, lib_dir = root / "toolchain/bin/whisper-cli", root / "toolchain/lib"

    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    synth_audio = work / "synthetic-hello-world.wav"
    espeak_text = SYNTHETIC_REFERENCE
    espeak = subprocess.run(["espeak-ng", "-v", "en-us", "-s", "135", "-w", str(synth_audio), espeak_text],
                            capture_output=True, text=True, errors="replace", check=False, timeout=30)
    if espeak.returncode or not synth_audio.is_file() or synth_audio.stat().st_size <= 0:
        raise RuntimeError("ESPEAK_SYNTHETIC_FIXTURE_BUILD_FAILED:" + espeak.stderr[-1000:])

    jfk_result = run_transcription(cli, model, jfk, work / "jfk/jfk", lib_dir)
    synth_result = run_transcription(cli, model, synth_audio, work / "synthetic/synthetic", lib_dir)
    jfk_words = normalized_words(jfk_result.get("transcript", ""))
    anchors = {phrase: all(word in jfk_words for word in normalized_words(phrase))
               for phrase in JFK_REQUIRED_PHRASES}
    synth_wer = word_error_rate(espeak_text, synth_result.get("transcript", "")) if synth_result.get("transcript") else 1.0
    synth_pass = synth_wer <= 0.25
    events = parse_events(Path("/sys/fs/cgroup/memory.events"))
    peak = int(Path("/sys/fs/cgroup/memory.peak").read_text(encoding="ascii").strip())
    memory_ok = peak <= CANDIDATE_RAM_BYTES and not (events.get("oom", 0) or events.get("oom_kill", 0))
    jfk_pass = all(anchors.values())
    passed = jfk_result["status"] == "PASS_EXECUTION" and synth_result["status"] == "PASS_EXECUTION" and jfk_pass and synth_pass and memory_ok
    projection = {
        "candidate_bytes": artifact["candidate"]["bytes"],
        "global_distribution_limit_bytes": GLOBAL_RELEASE_MAX_BYTES,
        "projected_complete_release_bytes": PROJECTED_COMPLETE_RELEASE_BYTES,
        "projected_size_pass": PROJECTED_COMPLETE_RELEASE_BYTES <= GLOBAL_RELEASE_MAX_BYTES,
        "policy": "EXTERNAL_ASSET_REQUIRED; DO_NOT_EMBED_IN_OVER_CAP_BUNDLE",
    }
    report = {
        "schema": SCHEMA,
        "status": "PASS_NONCERTIFYING_DIAGNOSTIC_ONLY" if passed else "FAIL_DIAGNOSTIC_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "candidate_evidence": {"github_actions_run_id": CANDIDATE_RUN_ID,
                               "github_actions_artifact_name": CANDIDATE_ARTIFACT_NAME},
        "artifact_identity": artifact,
        "provider_policy": {"hugging_face_jobs_used": False, "hugging_face_hub_api_used": False,
                            "hugging_face_tokens_used": False, "remote_inference_used": False,
                            "model_download_performed": False,
                            "model_source": "PREVIOUSLY_BUILT_GITHUB_ACTIONS_ARTIFACT",
                            "audio_source": "Q4_CANDIDATE_BUNDLED_GGML_WHISPER_CPP_FIXTURE_AND_LOCAL_ESPEAK"},
        "resource_policy": {**budget, "observed_memory_peak_bytes": peak,
                            "observed_memory_peak_gib": round(peak / 1024**3, 4),
                            "memory_events_after": events, "memory_ok": memory_ok,
                            "note": "1.25-GiB limit is diagnostic only; active runtime remains 1 GiB."},
        "tests": {
            "jfk_fixture_revision": WHISPER_CPP_REVISION,
            "jfk_fixture_source": expected_fixture,
            "jfk_required_phrase_anchors": anchors, "jfk_pass": jfk_pass,
            "jfk_transcription": jfk_result,
            "synthetic_reference": espeak_text, "synthetic_word_error_rate": round(synth_wer, 6),
            "synthetic_wer_max": 0.25, "synthetic_pass": synth_pass,
            "synthetic_transcription": synth_result,
        },
        "distribution_projection": projection,
        "immutability": {"active_runtime_modified": False, "original_model_weights_modified": False,
                         "candidate_integrated": False, "global_certification": "NOT_GRANTED",
                         "domain_certification": "NOT_GRANTED", "canonical_promotion": "NOT_AUTHORIZED"},
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "jfk_pass": jfk_pass, "jfk_anchors": anchors,
                      "synthetic_wer": round(synth_wer, 6), "synthetic_pass": synth_pass,
                      "memory_peak_bytes": peak, "memory_ok": memory_ok,
                      "projected_release_bytes": PROJECTED_COMPLETE_RELEASE_BYTES,
                      "report": str(args.report), "certification": "NOT_GRANTED"},
                     ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
