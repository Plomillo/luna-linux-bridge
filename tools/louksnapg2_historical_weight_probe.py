#!/usr/bin/env python3
"""Compare current packed factors with their pre-Q2 source candidates retained in Git history.

This is an isolated experiment: it copies the runtime into a temporary directory,
rebinds only the selected weight identity, and never changes the checked-out tree.
It does not claim full-size source-model equivalence or certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DOMAINS = {
    "D01_CEREBRO": {
        "weight": "1. Cerebro/model.safetensors",
        "module": "1. Cerebro",
        "sidecar": "1. Cerebro/model.safetensors.q4.json",
        "cases": (
            ("CEREBRO_ARITHMETIC_01", "generate_text",
             {"prompt": "Compute (17 * 3) - 9. Return a single integer and no other text.", "max_new_tokens": 48},
             "INTEGER_42"),
            ("CEREBRO_WORD_PROBLEM_02", "generate_text",
             {"prompt": "An invoice has 5 items at 7 dollars each and a 4 dollar discount. What is the final amount? Return one integer only.", "max_new_tokens": 48},
             "INTEGER_31"),
        ),
    },
    "D03_TRANSCRIPCION": {
        "weight": "3. Transcripción/model.safetensors",
        "module": "3. Transcripción",
        "sidecar": "3. Transcripción/model.safetensors.q4.json",
        "cases": (),
    },
    "D04_TRADUCTOR_INTELIGENTE": {
        "weight": "4. Traductor Inteligente/Traducción general/model.safetensors",
        "module": "4. Traductor Inteligente/Traducción general",
        "sidecar": "4. Traductor Inteligente/Traducción general/model.safetensors.q4.json",
        "cases": (
            ("GENERAL_TRANSLATION_EN_ES_01", "translate_text",
             {"text": "The meeting starts at noon.", "src_lang": "eng", "tgt_lang": "spa", "max_new_tokens": 64},
             "EN_ES"),
            ("GENERAL_TRANSLATION_ES_EN_02", "translate_text",
             {"text": "La reunión empieza al mediodía.", "src_lang": "spa", "tgt_lang": "eng", "max_new_tokens": 64},
             "ES_EN"),
            ("GENERAL_TRANSLATION_EN_FR_03", "translate_text",
             {"text": "The book is on the table.", "src_lang": "eng", "tgt_lang": "fra", "max_new_tokens": 64},
             "EN_FR"),
            ("GENERAL_TRANSLATION_FR_EN_04", "translate_text",
             {"text": "Le livre est sur la table.", "src_lang": "fra", "tgt_lang": "eng", "max_new_tokens": 64},
             "FR_EN"),
        ),
    },
    "D06_SISTEMA_INTELIGENTE": {
        "weight": "6. Sistema Inteligente/Análisis Avanzado/model.safetensors",
        "module": "6. Sistema Inteligente/Análisis Avanzado",
        "sidecar": "6. Sistema Inteligente/Análisis Avanzado/model.safetensors.q4.json",
        "cases": (
            ("ANALYSIS_MULTI_STEP_01", "analyze_reasoning",
             {"prompt": "A library has 9 shelves with 8 books per shelf. 17 books are borrowed. How many remain? Return one integer only.", "max_new_tokens": 48},
             "INTEGER_55"),
            ("ANALYSIS_LOGIC_02", "analyze_reasoning",
             {"prompt": "All tulips are flowers. Some flowers fade quickly. Does it logically follow that some tulips fade quickly? Answer yes or no only.", "max_new_tokens": 64},
             "LOGIC_NO"),
        ),
    },
}

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def canonical_digest(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

def prepare_current_runtime(current_root: Path, temp_root: Path, domain: str) -> dict:
    """Create an isolated baseline copy and reconcile only its selected module index.

    The Git commit is immutable input. This recalculates the module descriptor's
    derived tree inventory from those exact bytes in a temporary copy; it does not
    alter weights, model metadata, tokenizer sources, or the repository checkout.
    """
    spec = DOMAINS[domain]
    shutil.copytree(
        current_root,
        temp_root,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        copy_function=shutil.copy2,
    )
    sys.path.insert(0, str(temp_root))
    import cajita_task_adapters
    from cajita_tokenizer_materializer import tokenizer_tree_rows

    module_root = temp_root / spec["module"]
    descriptor_path = module_root / "CAJITA_MODULE.json"
    if descriptor_path.is_symlink() or not descriptor_path.is_file():
        raise RuntimeError("CURRENT_MODULE_DESCRIPTOR_MISSING_OR_UNSAFE")
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    original = dict(descriptor.get("tree_integrity", {}))
    rows = cajita_task_adapters.tree_rows(module_root)
    tokenizer_manifest = temp_root / cajita_task_adapters.TOKENIZER_MANIFEST_NAME
    if tokenizer_manifest.is_file():
        rows = tokenizer_tree_rows(module_root, temp_root, rows)
    tree_hash = cajita_task_adapters.digest_bytes(
        json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    observed = {
        "sha256": tree_hash,
        "file_count_excluding_module_descriptors": len(rows),
        "bytes_excluding_module_descriptors": sum(int(row["bytes"]) for row in rows),
    }
    descriptor["tree_integrity"] = observed
    write_json(descriptor_path, descriptor)

    selected_integrity = cajita_task_adapters.verify_integrity(temp_root, domain)
    weight = temp_root / spec["weight"]
    return {
        "domain_id": domain,
        "source_representation": "CURRENT_Q2_CANDIDATE_FROM_EXACT_GITHUB_COMMIT",
        "source_weight_sha256": digest(weight),
        "source_weight_bytes": weight.stat().st_size,
        "original_descriptor_tree_integrity": original,
        "observed_descriptor_tree_integrity": observed,
        "descriptor_reconciled_in_temporary_copy": original != observed,
        "selected_model_integrity_status": "PASS",
        "selected_model_integrity": selected_integrity,
        "temporary_runtime_root": str(temp_root),
        "original_runtime_tree_mutated": False,
    }

def prepare_historical_runtime(current_root: Path, historical_root: Path, domain: str, temp_root: Path) -> dict:
    spec = DOMAINS[domain]
    source = historical_root / spec["weight"]
    current_sidecar = current_root / spec["sidecar"]
    if source.is_symlink() or not source.is_file():
        raise RuntimeError("HISTORICAL_WEIGHT_MISSING_OR_UNSAFE")
    if current_sidecar.is_symlink() or not current_sidecar.is_file():
        raise RuntimeError("CURRENT_Q2_SIDECAR_MISSING_OR_UNSAFE")
    sidecar = json.loads(current_sidecar.read_text(encoding="utf-8"))
    expected_source_sha = sidecar.get("source_sha256")
    observed_source_sha = digest(source)
    if observed_source_sha != expected_source_sha:
        raise RuntimeError(
            "HISTORICAL_WEIGHT_SOURCE_SHA256_MISMATCH:"
            + observed_source_sha + "!=" + str(expected_source_sha)
        )

    shutil.copytree(
        current_root,
        temp_root,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        copy_function=shutil.copy2,
    )
    destination = temp_root / spec["weight"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    copied_sha = digest(destination)
    if copied_sha != expected_source_sha:
        raise RuntimeError("HISTORICAL_WEIGHT_COPY_SHA256_MISMATCH")
    (temp_root / spec["sidecar"]).unlink()

    manifest_path = temp_root / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    relative_weight = spec["weight"]
    matches = [row for row in manifest.get("artifacts", []) if row.get("path") == relative_weight]
    if len(matches) != 1:
        raise RuntimeError("WEIGHT_MANIFEST_DOMAIN_ENTRY_NOT_UNIQUE")
    matches[0]["sha256"] = copied_sha
    matches[0]["bytes"] = destination.stat().st_size
    manifest["total_weight_bytes"] = sum(int(row.get("bytes", 0)) for row in manifest["artifacts"])
    manifest["total_weight_decimal_mb"] = round(manifest["total_weight_bytes"] / 1_000_000, 3)
    write_json(manifest_path, manifest)
    manifest_sha = digest(manifest_path)

    adapter_path = temp_root / "cajita_task_adapters.py"
    adapter_source = adapter_path.read_text(encoding="utf-8")
    adapter_source, count = re.subn(
        r'^MANIFEST_SHA = "[0-9a-f]{64}"$',
        f'MANIFEST_SHA = "{manifest_sha}"',
        adapter_source,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError("TASK_ADAPTER_MANIFEST_HASH_ANCHOR_NOT_UNIQUE")
    escaped_path = re.escape(relative_weight)
    pattern = (
        r'("' + re.escape(domain) + r'": \{"weight":"' + escaped_path
        + r'","sha":")[0-9a-f]{64}(" ,"bytes":)\d+'
    )
    # The registry uses compact JSON-like Python literals without a space before bytes.
    pattern = (
        r'("' + re.escape(domain) + r'": \{"weight":"' + escaped_path
        + r'","sha":")[0-9a-f]{64}(","bytes":)\d+'
    )
    adapter_source, count = re.subn(
        pattern,
        lambda m: m.group(1) + copied_sha + m.group(2) + str(destination.stat().st_size),
        adapter_source,
        count=1,
    )
    if count != 1:
        raise RuntimeError("TASK_ADAPTER_WEIGHT_IDENTITY_ANCHOR_NOT_UNIQUE:" + domain)
    adapter_path.write_text(adapter_source, encoding="utf-8")

    sys.path.insert(0, str(temp_root))
    import cajita_task_adapters
    from cajita_tokenizer_materializer import tokenizer_tree_rows
    cajita_task_adapters.MANIFEST_SHA = manifest_sha
    cajita_task_adapters.ADAPTERS[domain]["sha"] = copied_sha
    cajita_task_adapters.ADAPTERS[domain]["bytes"] = destination.stat().st_size

    adapter_source_sha = digest(adapter_path)
    descriptor_paths = sorted(temp_root.rglob("CAJITA_MODULE.json"))
    selected_descriptor = None
    for descriptor_path in descriptor_paths:
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        registration = descriptor.get("consumer_adapter_registration")
        if not isinstance(registration, dict):
            continue
        registration["weight_manifest_sha256"] = manifest_sha
        if descriptor_path.parent == temp_root / spec["module"]:
            registration.update({
                "weight_sha256": copied_sha,
                "weight_bytes": destination.stat().st_size,
            })
            registration["adapter_source_sha256"] = adapter_source_sha
            selected_descriptor = descriptor_path
        write_json(descriptor_path, descriptor)
    if selected_descriptor is None:
        raise RuntimeError("SELECTED_MODULE_DESCRIPTOR_MISSING")

    descriptor_path = selected_descriptor
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    module_root = temp_root / spec["module"]
    rows = cajita_task_adapters.tree_rows(module_root)
    tokenizer_manifest = temp_root / cajita_task_adapters.TOKENIZER_MANIFEST_NAME
    if tokenizer_manifest.is_file():
        rows = tokenizer_tree_rows(module_root, temp_root, rows)
    tree_hash = cajita_task_adapters.digest_bytes(
        json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    descriptor["tree_integrity"] = {
        "sha256": tree_hash,
        "file_count_excluding_module_descriptors": len(rows),
        "bytes_excluding_module_descriptors": sum(int(row["bytes"]) for row in rows),
    }
    write_json(descriptor_path, descriptor)

    return {
        "domain_id": domain,
        "source_representation": "PRE_Q2_FACTOR_CANDIDATE_RECOVERED_FROM_THIS_REPOSITORY_GIT_HISTORY",
        "source_git_path": spec["weight"],
        "source_weight_sha256": copied_sha,
        "source_weight_bytes": destination.stat().st_size,
        "current_q2_source_sha256": expected_source_sha,
        "source_hash_exact_match": copied_sha == expected_source_sha,
        "temporary_runtime_root": str(temp_root),
        "temporary_manifest_sha256": manifest_sha,
        "original_runtime_tree_mutated": False,
    }

def evaluate(root: Path, domain: str, audio_one: Path | None, audio_two: Path | None) -> dict:
    """Evaluate the registered neural adapter directly, never the auxiliary router.

    The service/router layer may intentionally select Whisper.cpp or Apertium.
    A precision experiment must instead execute the exact selected model's
    cajita_task_adapters entrypoint or it does not measure Q2/Q4 model quality.
    """
    root = root.resolve(strict=True)
    sys.path.insert(0, str(root))
    import cajita_task_adapters as adapters
    import louksnapg2_functional_eval as evaluator

    try:
        selected_integrity = adapters.verify_integrity(root, domain)
    except Exception as exc:
        return {
            "domain_id": domain,
            "preflight": {
                "status": "FAIL_SELECTED_DOMAIN_SOURCE_IDENTITY",
                "selected_domain": domain,
                "reason": type(exc).__name__ + ":" + str(exc)[:500],
            },
            "tests": [],
            "pass_count": 0,
            "total_cases": 0,
            "status": "HOLD_PREFLIGHT",
        }

    preflight = {
        "status": "PASS_SELECTED_DOMAIN_SOURCE_IDENTITY",
        "selected_domain": domain,
        "model_identity": selected_integrity,
        "evaluation_route": "DIRECT_CAJITA_TASK_ADAPTER_EXECUTE_TASK",
        "auxiliary_router_imported": False,
        "service_dispatch_used": False,
        "new_external_model_fetch_performed": False,
    }
    cases = []
    if domain == "D03_TRANSCRIPCION":
        if audio_one is None or audio_two is None:
            raise RuntimeError("WHISPER_AUDIO_FIXTURES_REQUIRED")
        references = ("The meeting starts at noon.", "Please turn left at the next street.")
        for index, audio in enumerate((audio_one, audio_two), 1):
            cases.append((
                f"WHISPER_AUDIO_{index:02d}",
                "transcribe_audio",
                {"audio_path": str(audio.resolve(strict=True))},
                {"timeout_seconds": 900, "max_new_tokens": 32},
                lambda output, reference=references[index - 1]: evaluator.word_error_rate(reference, output) <= 0.35,
                references[index - 1],
            ))
    elif domain == "D04_TRADUCTOR_INTELIGENTE":
        cases = [
            ("GENERAL_TRANSLATION_EN_ES_01", "translate_text",
             {"text":"The meeting starts at noon.","src_lang":"eng","tgt_lang":"spa"},
             {"timeout_seconds":900,"max_new_tokens":64}, evaluator.check_translation_en_es, None),
            ("GENERAL_TRANSLATION_ES_EN_02", "translate_text",
             {"text":"La reunión empieza al mediodía.","src_lang":"spa","tgt_lang":"eng"},
             {"timeout_seconds":900,"max_new_tokens":64}, evaluator.check_translation_es_en, None),
            ("GENERAL_TRANSLATION_EN_FR_03", "translate_text",
             {"text":"The book is on the table.","src_lang":"eng","tgt_lang":"fra"},
             {"timeout_seconds":900,"max_new_tokens":64}, evaluator.check_translation_en_fr, None),
            ("GENERAL_TRANSLATION_FR_EN_04", "translate_text",
             {"text":"Le livre est sur la table.","src_lang":"fra","tgt_lang":"eng"},
             {"timeout_seconds":900,"max_new_tokens":64}, evaluator.check_translation_fr_en, None),
        ]
    else:
        predicates = {
            "INTEGER_42": lambda output: evaluator.has_final_integer(output, 42),
            "INTEGER_31": lambda output: evaluator.has_final_integer(output, 31),
            "INTEGER_55": lambda output: evaluator.has_final_integer(output, 55),
            "LOGIC_NO": lambda output: evaluator.normalized(evaluator.final_answer(output)).split()[:1] == ["no"],
            "EN_ES": evaluator.check_translation_en_es,
            "ES_EN": evaluator.check_translation_es_en,
            "EN_FR": evaluator.check_translation_en_fr,
            "FR_EN": evaluator.check_translation_fr_en,
        }
        for case_id, operation, payload, predicate_name in DOMAINS[domain]["cases"]:
            limits = {"timeout_seconds":900,"max_new_tokens":int(payload.get("max_new_tokens",64))}
            model_input = {key:value for key,value in payload.items() if key!="max_new_tokens"}
            cases.append((case_id,operation,model_input,limits,predicates[predicate_name],None))

    rows = []
    for case_id, operation, payload, limits, predicate, reference in cases:
        request = {
            "schema": adapters.REQUEST_SCHEMA,
            "task_id": "q2-q4-direct-" + case_id.lower().replace("_","-"),
            "domain_id": domain,
            "operation": operation,
            "input": payload,
            "limits": limits,
        }
        started = time.monotonic()
        try:
            result, exit_code = adapters.execute_task(request, root, timeout_cap=1800)
            output = result.get("output_text", "") if isinstance(result, dict) else ""
            execution_ok = (
                exit_code == 0
                and result.get("status") == "PASS_FUNCTIONAL_EXECUTION"
                and result.get("execution_authorized") is True
                and isinstance(output, str)
                and bool(output.strip())
            )
            quality_ok = bool(predicate(output)) if execution_ok else False
            row = {
                "case_id": case_id,
                "domain_id": domain,
                "operation": operation,
                "status": "PASS" if execution_ok and quality_ok else "FAIL",
                "execution_status": result.get("status"),
                "execution_authorized": result.get("execution_authorized"),
                "exit_code": exit_code,
                "elapsed_seconds": round(time.monotonic()-started,3),
                "input_sha256": result.get("input_sha256"),
                "output_sha256": result.get("output_sha256"),
                "output_text_sha256": adapters.digest_bytes(output.encode("utf-8",errors="replace")) if isinstance(output,str) else None,
                "actual_output": output[:1200] if isinstance(output,str) else None,
                "output_char_count": len(output) if isinstance(output,str) else 0,
                "quality_criterion_passed": quality_ok,
                "quality_reason": "" if quality_ok else ("EXECUTION_FAILED" if not execution_ok else "DIRECT_NEURAL_OUTPUT_FAILED_ACCEPTANCE"),
                "entrypoint_sha256": result.get("entrypoint_sha256"),
                "weight_sha256": result.get("integrity",{}).get("weight_sha256"),
                "module_tree_sha256": result.get("integrity",{}).get("module_tree_sha256"),
                "peak_rss_bytes": result.get("peak_rss_bytes"),
                "reference_text": reference,
                "word_error_rate": evaluator.word_error_rate(reference,output) if reference and isinstance(output,str) else None,
                "execution_route": "DIRECT_CAJITA_TASK_ADAPTER_NO_AUXILIARY",
                "auxiliary_engine_execution_performed": False,
                "fallback_engine_execution_performed": False,
                "semantic_quality_equivalence_to_full_size_original": "NOT_ESTABLISHED",
            }
            if not execution_ok:
                row["reason"] = result.get("reason") or result.get("status") or "DIRECT_MODEL_EXECUTION_FAILED"
        except Exception as exc:
            row = {
                "case_id": case_id,
                "domain_id": domain,
                "operation": operation,
                "status": "FAIL",
                "execution_status": "EXCEPTION",
                "exit_code": None,
                "elapsed_seconds": round(time.monotonic()-started,3),
                "actual_output": None,
                "quality_criterion_passed": False,
                "reason": type(exc).__name__ + ":" + str(exc)[:1200],
                "execution_route": "DIRECT_CAJITA_TASK_ADAPTER_NO_AUXILIARY",
                "auxiliary_engine_execution_performed": False,
                "fallback_engine_execution_performed": False,
                "semantic_quality_equivalence_to_full_size_original": "NOT_ESTABLISHED",
            }
        rows.append(row)

    passed = sum(1 for row in rows if row.get("status") == "PASS")
    return {
        "domain_id":domain,
        "preflight":preflight,
        "evaluation_route":"DIRECT_CAJITA_TASK_ADAPTER_EXECUTE_TASK",
        "auxiliary_router_imported":False,
        "service_dispatch_used":False,
        "tests":rows,
        "pass_count":passed,
        "total_cases":len(rows),
        "status":"PASS_SELECTED_ACCEPTANCE_CASES" if rows and passed==len(rows) else "FAIL_SELECTED_ACCEPTANCE_CASES",
    }

def subprocess_evaluate(script: Path, root: Path, domain: str, audio_one: Path | None, audio_two: Path | None):
    command = [
        sys.executable, "-B", str(script), "--phase", "evaluate",
        "--runtime-root", str(root), "--domain", domain,
    ]
    if audio_one is not None:
        command.extend(["--audio-one", str(audio_one)])
    if audio_two is not None:
        command.extend(["--audio-two", str(audio_two)])
    env = dict(os.environ)
    env.update({
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "PYTHONNOUSERSITE": "1",
        "LOUKSNAPG_REMOTE_MODE": "off",
        "LOUKSNAPG_REMOTE_DOMAINS_REQUIRED": "",
    })
    proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=1800, check=False)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"status": "EVALUATION_PROCESS_INVALID_OUTPUT", "stdout_tail": proc.stdout[-4000:]}
    payload["process_exit_code"] = proc.returncode
    if proc.returncode and payload.get("status") == "PASS_SELECTED_ACCEPTANCE_CASES":
        payload["status"] = "EVALUATION_PROCESS_FAILED"
    if proc.stderr:
        payload["stderr_tail"] = proc.stderr[-3000:]
    return payload

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("compare", "evaluate"), default="compare")
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--historical-root", type=Path)
    parser.add_argument("--domain", required=True, choices=tuple(DOMAINS))
    parser.add_argument("--audio-one", type=Path)
    parser.add_argument("--audio-two", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    if args.phase == "evaluate":
        evidence = evaluate(args.runtime_root, args.domain, args.audio_one, args.audio_two)
        print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
        return 0 if evidence["status"] == "PASS_SELECTED_ACCEPTANCE_CASES" else 2

    if args.historical_root is None or args.output is None:
        parser.error("--historical-root and --output are required in compare phase")
    source_root = args.runtime_root.resolve(strict=True)
    historical_root = args.historical_root.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="louksnapg2-current-q2-") as baseline_tmp:
        baseline_root = Path(baseline_tmp) / "runtime"
        baseline_provenance = prepare_current_runtime(source_root, baseline_root, args.domain)
        baseline = subprocess_evaluate(Path(__file__).resolve(), baseline_root, args.domain, args.audio_one, args.audio_two)
    with tempfile.TemporaryDirectory(prefix="louksnapg2-preq2-") as historical_tmp:
        experimental_root = Path(historical_tmp) / "runtime"
        provenance = prepare_historical_runtime(source_root, historical_root, args.domain, experimental_root)
        alternative = subprocess_evaluate(Path(__file__).resolve(), experimental_root, args.domain, args.audio_one, args.audio_two)
        report = {
            "schema": "LOUKSNAPG2_HISTORICAL_WEIGHT_PROBE/1.0",
            "experiment": "CURRENT_Q2_PACKED_VS_REPOSITORY_RETAINED_PRE_Q2_FACTORS",
            "repository_only": True,
            "external_model_downloads": False,
            "domain_id": args.domain,
            "baseline": baseline,
            "alternative": alternative,
            "current_q2_source": baseline_provenance,
            "historical_source": provenance,
            "comparison": {
                "baseline_passed": baseline.get("pass_count", 0),
                "alternative_passed": alternative.get("pass_count", 0),
                "total_cases": alternative.get("total_cases", 0),
                "pass_delta": alternative.get("pass_count", 0) - baseline.get("pass_count", 0),
                "quality_equivalence_to_full_size_upstream": "NOT_ESTABLISHED",
            },
            "certification": "NOT_GRANTED_BY_EXPERIMENT",
        }
        write_json(args.output, report)
        print(json.dumps({
            "status": "PASS_PROBE_COMPLETED" if alternative.get("total_cases", 0) else "HOLD_PROBE_INCOMPLETE",
            "domain_id": args.domain,
            "baseline": f'{baseline.get("pass_count", 0)}/{baseline.get("total_cases", 0)}',
            "historical": f'{alternative.get("pass_count", 0)}/{alternative.get("total_cases", 0)}',
            "source_hash_exact_match": provenance["source_hash_exact_match"],
            "baseline_status": baseline.get("status"),
            "baseline_preflight": baseline.get("preflight"),
            "baseline_descriptor_reconciled_in_temporary_copy": baseline_provenance.get("descriptor_reconciled_in_temporary_copy"),
            "baseline_error": baseline.get("stderr_tail") or baseline.get("stdout_tail"),
            "alternative_status": alternative.get("status"),
            "alternative_preflight": alternative.get("preflight"),
            "alternative_error": alternative.get("stderr_tail") or alternative.get("stdout_tail"),
            "pass_delta": report["comparison"]["pass_delta"],
            "output": str(args.output),
            "certification": "NOT_GRANTED_BY_EXPERIMENT",
        }, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if alternative.get("total_cases", 0) > 0 and provenance["source_hash_exact_match"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
