#!/usr/bin/env python3
"""Execute bounded, real-model LOUKSNAPG2 domain tests and write auditable evidence.

This is a functional evaluation, not a certificate. It runs only on the supplied
runtime directory and never downloads model files itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[^\W_]+", value, flags=re.UNICODE))


def final_answer(value: str) -> str:
    value = str(value)
    if "</think>" in value:
        value = value.rsplit("</think>", 1)[-1]
    value = re.sub(r"<\|[^|]+\|>|</?think>", " ", value, flags=re.IGNORECASE)
    return value.strip()


def has_final_integer(value: str, expected: int) -> bool:
    match = re.search(r"(-?\d+)\s*[.!]?\s*$", final_answer(value))
    return bool(match and int(match.group(1)) == expected)


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref = normalized(reference).split()
    hyp = normalized(hypothesis).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    row = list(range(len(hyp) + 1))
    for i, token in enumerate(ref, 1):
        current = [i]
        for j, other in enumerate(hyp, 1):
            current.append(min(current[-1] + 1, row[j] + 1, row[j - 1] + (token != other)))
        row = current
    return row[-1] / len(ref)


def check_translation_es_en(value: str) -> bool:
    text = normalized(final_answer(value))
    start = any(word in text.split() for word in ("empieza", "comienza", "inicia", "start", "starts", "begins", "begin"))
    time = any(word in text.split() for word in ("mediodia", "noon", "midday", "doce", "12"))
    meeting = any(word in text.split() for word in ("reunion", "meeting"))
    return start and time and meeting


def run_case(runtime, case_id, domain, operation, payload, predicate, requirement):
    started = time.monotonic()
    record = {
        "case_id": case_id,
        "domain_id": domain,
        "operation": operation,
        "requirement": requirement,
        "input_sha256": sha256_bytes(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")),
    }
    try:
        result = runtime.route(domain, operation, payload)
        output = str(result.get("output_text", ""))
        passed = (
            result.get("status") == "PASS_EXECUTION"
            and result.get("execution_authorized") is True
            and result.get("domain_id") == domain
            and result.get("operation") == operation
            and bool(output.strip())
            and bool(predicate(output))
        )
        record.update({
            "status": "PASS" if passed else "FAIL",
            "actual_output": output[:1200],
            "output_sha256": result.get("output_sha256"),
            "result_domain_id": result.get("domain_id"),
            "result_operation": result.get("operation"),
            "execution_status": result.get("status"),
            "general_translation_fallback_selected": result.get("general_translation_fallback_selected"),
            "quality_criterion_passed": bool(predicate(output)),
            "semantic_quality_equivalence_to_full_size_original": "NOT_ESTABLISHED",
            "reason": "" if passed else "DOMAIN_OR_OPERATION_OR_QUALITY_CRITERION_FAILED",
        })
    except Exception as exc:
        record.update({
            "status": "FAIL",
            "actual_output": None,
            "quality_criterion_passed": False,
            "reason": type(exc).__name__ + ":" + str(exc)[:300],
            "semantic_quality_equivalence_to_full_size_original": "NOT_ESTABLISHED",
        })
    record["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--audio-one", required=True, type=Path)
    parser.add_argument("--audio-two", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    root = args.runtime_root.resolve(strict=True)
    for audio in (args.audio_one, args.audio_two):
        if audio.is_symlink() or not audio.is_file():
            raise SystemExit("AUDIO_FIXTURE_MISSING_OR_UNSAFE:" + str(audio))
    sys.path.insert(0, str(root))
    from louksnapg2_engine import LouksnapG2Runtime

    evidence = {
        "schema": "LOUKSNAPG2_REAL_MODEL_FUNCTIONAL_EVIDENCE/1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "runtime_root": str(root),
        "cpu_thread_budget": 1,
        "model_fetch_performed_by_evaluator": False,
        "tests": [],
        "domain_results": {},
        "functional_status": "NOT_RUN",
        "global_certification": "NOT_GRANTED_BY_FUNCTIONAL_EVALUATION",
    }
    runtime = LouksnapG2Runtime(root, threads=1)
    try:
        evidence["preflight"] = runtime.preflight()
        evidence["model_identity_status"] = evidence["preflight"].get("status")
    except Exception as exc:
        evidence["preflight"] = {
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc)[:300],
        }
        evidence["model_identity_status"] = "FAIL"
        evidence["functional_status"] = "FAIL_MODEL_PREFLIGHT"
        evidence["tests"] = [{
            "case_id": "MODEL_PREFLIGHT",
            "status": "FAIL",
            "reason": evidence["preflight"]["reason"],
        }]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
        return 2

    tests = [
        ("CEREBRO_ARITHMETIC_01", "D01_CEREBRO", "generate_text",
         {"prompt": "Compute (17 * 3) - 9. Return a single integer and no other text.", "max_new_tokens": 48},
         lambda out: has_final_integer(out, 42),
         "The actual Qwen-backed reasoning route must return 42 as its final answer."),
        ("CEREBRO_WORD_PROBLEM_02", "D01_CEREBRO", "generate_text",
         {"prompt": "An invoice has 5 items at 7 dollars each and a 4 dollar discount. What is the final amount? Return one integer only.", "max_new_tokens": 48},
         lambda out: has_final_integer(out, 31),
         "The actual reasoning route must compute 5*7-4=31."),
        ("ANALYSIS_MULTI_STEP_01", "D06_SISTEMA_INTELIGENTE", "analyze_reasoning",
         {"prompt": "A library has 9 shelves with 8 books per shelf. 17 books are borrowed. How many remain? Return one integer only.", "max_new_tokens": 48},
         lambda out: has_final_integer(out, 55),
         "The advanced-analysis route must compute 9*8-17=55."),
        ("ANALYSIS_LOGIC_02", "D06_SISTEMA_INTELIGENTE", "analyze_reasoning",
         {"prompt": "All tulips are flowers. Some flowers fade quickly. Does it logically follow that some tulips fade quickly? Answer yes or no only.", "max_new_tokens": 64},
         lambda out: normalized(final_answer(out)).split()[:1] == ["no"],
         "The advanced-analysis route must reject the invalid existential inference."),
        ("GENERAL_TRANSLATION_EN_ES_01", "D04_TRADUCTOR_INTELIGENTE", "translate_text",
         {"text": "The meeting starts at noon.", "src_lang": "eng", "tgt_lang": "spa", "max_new_tokens": 64},
         lambda out: check_translation_es_en(out),
         "Spanish output must preserve meeting + start + noon meaning."),
        ("GENERAL_TRANSLATION_ES_EN_02", "D04_TRADUCTOR_INTELIGENTE", "translate_text",
         {"text": "La reunión empieza al mediodía.", "src_lang": "spa", "tgt_lang": "eng", "max_new_tokens": 64},
         lambda out: check_translation_es_en(out),
         "English output must preserve meeting + start + noon meaning."),
        ("GENERAL_TRANSLATION_EN_FR_03", "D04_TRADUCTOR_INTELIGENTE", "translate_text",
         {"text": "The book is on the table.", "src_lang": "eng", "tgt_lang": "fra", "max_new_tokens": 64},
         lambda out: {"livre", "table", "sur"}.issubset(set(normalized(final_answer(out)).split())),
         "French output must preserve book + spatial relation + table meaning."),
        ("GENERAL_TRANSLATION_FR_EN_04", "D04_TRADUCTOR_INTELIGENTE", "translate_text",
         {"text": "Le livre est sur la table.", "src_lang": "fra", "tgt_lang": "eng", "max_new_tokens": 64},
         lambda out: {"book", "table"}.issubset(set(normalized(final_answer(out)).split())) and any(w in normalized(final_answer(out)).split() for w in ("on", "upon")),
         "English output must preserve book + spatial relation + table meaning."),
        ("ANCIENT_LATIN_01", "D04_TRADUCCION_LENGUAS_ANTIGUAS", "translate_ancient_text",
         {"text": "Alea iacta est", "src_lang": "lat", "tgt_lang": "eng", "max_new_tokens": 96},
         lambda out: ("die" in normalized(final_answer(out)) and any(w in normalized(final_answer(out)).split() for w in ("cast", "thrown", "tossed"))),
         "An unseen-from-concordance Latin phrase must be translated as the die is cast."),
        ("ANCIENT_GREEK_02", "D04_TRADUCCION_LENGUAS_ANTIGUAS", "translate_ancient_text",
         {"text": "πάντα ῥεῖ", "src_lang": "grc", "tgt_lang": "eng", "max_new_tokens": 96},
         lambda out: ("everything" in normalized(final_answer(out)) and any(w in normalized(final_answer(out)).split() for w in ("flows", "flow", "flux"))),
         "An Ancient Greek phrase outside the fixed concordance must be translated as everything flows."),
    ]
    for case in tests:
        case_id, domain, operation, payload, predicate, requirement = case
        evidence["tests"].append(run_case(runtime, case_id, domain, operation, payload, predicate, requirement))

    for index, audio in enumerate((args.audio_one, args.audio_two), 1):
        expected = (
            "The meeting starts at noon."
            if index == 1
            else "Please turn left at the next street."
        )
        result = run_case(
            runtime,
            f"WHISPER_AUDIO_{index:02d}",
            "D03_TRANSCRIPCION",
            "transcribe_audio",
            {"audio_path": str(audio)},
            lambda out, expected=expected: word_error_rate(expected, out) <= 0.35,
            f"Whisper transcription must have word-error-rate <= 0.35 against the supplied known audio; reference={expected!r}.",
        )
        result["reference_text"] = expected
        result["word_error_rate"] = (
            word_error_rate(expected, result.get("actual_output") or "")
            if result.get("actual_output") else None
        )
        result["audio_bytes"] = audio.stat().st_size
        result["audio_sha256"] = hashlib.sha256(audio.read_bytes()).hexdigest()
        evidence["tests"].append(result)

    all_domains = {
        "D01_CEREBRO": ["CEREBRO_ARITHMETIC_01", "CEREBRO_WORD_PROBLEM_02"],
        "D06_SISTEMA_INTELIGENTE": ["ANALYSIS_MULTI_STEP_01", "ANALYSIS_LOGIC_02"],
        "D04_TRADUCTOR_INTELIGENTE": ["GENERAL_TRANSLATION_EN_ES_01", "GENERAL_TRANSLATION_ES_EN_02", "GENERAL_TRANSLATION_EN_FR_03", "GENERAL_TRANSLATION_FR_EN_04"],
        "D04_TRADUCCION_LENGUAS_ANTIGUAS": ["ANCIENT_LATIN_01", "ANCIENT_GREEK_02"],
        "D03_TRANSCRIPCION": ["WHISPER_AUDIO_01", "WHISPER_AUDIO_02"],
    }
    by_id = {row["case_id"]: row for row in evidence["tests"]}
    for domain, case_ids in all_domains.items():
        rows = [by_id[case_id] for case_id in case_ids]
        evidence["domain_results"][domain] = {
            "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
            "passed_cases": sum(row["status"] == "PASS" for row in rows),
            "required_cases": len(rows),
            "case_ids": case_ids,
        }
    failed = [row["case_id"] for row in evidence["tests"] if row["status"] != "PASS"]
    evidence["functional_status"] = "PASS_ALL_DOMAIN_CASES" if not failed else "FAIL_FUNCTIONAL_QUALITY"
    evidence["failed_cases"] = failed
    evidence["summary"] = {
        "passed_cases": len(evidence["tests"]) - len(failed),
        "total_cases": len(evidence["tests"]),
        "all_required_domains_pass": all(row["status"] == "PASS" for row in evidence["domain_results"].values()),
        "full_size_original_equivalence": "NOT_ESTABLISHED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "functional_status": evidence["functional_status"],
        "passed_cases": evidence["summary"]["passed_cases"],
        "total_cases": evidence["summary"]["total_cases"],
        "domain_results": evidence["domain_results"],
        "global_certification": evidence["global_certification"],
        "output": str(args.output),
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
