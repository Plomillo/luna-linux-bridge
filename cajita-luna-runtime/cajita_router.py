#!/usr/bin/env python3
"""Fail-closed, resource-aware planner for Cajita's six domains and 14 routes."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "CAJITA_DEMAND_ROUTER/1.0"
MAX_RAM_MIB = 1024
CPU_THREAD_LIMIT = 1
MAX_PARALLEL_DOMAINS = 1

DOMAINS: dict[str, dict[str, Any]] = {
    "D01_CEREBRO": {"name": "Cerebro", "peak_rss_mib": None, "task_adapter": "NOT_REGISTERED", "evidence": "smoke-only"},
    "D02_ORQUESTACION": {"name": "Orquestación", "peak_rss_mib": None, "task_adapter": "REGISTRY_SELFTEST_ONLY", "evidence": "CLI registry self-test only"},
    "D03_TRANSCRIPCION": {"name": "Transcripción", "peak_rss_mib": None, "task_adapter": "NOT_REGISTERED", "evidence": "smoke-only; WER not established"},
    "D04_TRADUCTOR_INTELIGENTE": {"name": "Traductor inteligente", "peak_rss_mib": None, "task_adapter": "NOT_REGISTERED", "evidence": "text smoke only; translation quality not established"},
    "D05_INTELIGENCIA_DOCUMENTAL": {"name": "Inteligencia documental", "peak_rss_mib": None, "task_adapter": "NOT_REGISTERED", "evidence": "model verification only; document-task quality not established"},
    "D06_SISTEMA_INTELIGENTE": {"name": "Sistema inteligente / razonamiento", "peak_rss_mib": None, "task_adapter": "NOT_REGISTERED", "evidence": "smoke and model-file integrity only"},
}

# Preserve the canonical command -> agent -> engine bindings. Domain defaults are hints,
# not substitutions for the canonical agent or engine sets.
ROUTES: list[dict[str, Any]] = [
    {"command": "/help", "id": "HELP", "agents": ["Luna"], "engines": ["E13", "E14", "E15"], "domains": ["D01_CEREBRO"], "criticality": "LOW"},
    {"command": "/play PT", "id": "PT", "agents": ["Luna", "Katya"], "engines": ["E01", "E02", "E11", "E12", "E13"], "domains": ["D01_CEREBRO"], "criticality": "MEDIUM"},
    {"command": "/play PA", "id": "PA", "agents": ["Luna", "Ancapi"], "engines": ["E06", "E07", "E08", "E09", "E10", "E12", "E13", "E14"], "domains": ["D01_CEREBRO"], "criticality": "HIGH"},
    {"command": "/play DCI", "id": "DCI", "agents": ["Luna", "Josefina"], "engines": ["E03", "E04", "E05", "E09", "E11", "E12", "E13", "E14"], "domains": ["D01_CEREBRO"], "criticality": "MEDIUM"},
    {"command": "/play DCIL", "id": "DCIL", "agents": ["Luna", "Josefina", "Katya"], "engines": ["E01", "E02", "E03", "E04", "E05", "E09", "E11", "E12", "E13", "E14", "E15"], "domains": ["D01_CEREBRO", "D06_SISTEMA_INTELIGENTE"], "criticality": "HIGH"},
    {"command": "/play traductor", "id": "TRAD", "agents": ["Luna", "Katya"], "engines": ["E01", "E02", "E03", "E04", "E05", "E12", "E13", "E14", "E15"], "domains": ["D04_TRADUCTOR_INTELIGENTE"], "criticality": "MEDIUM"},
    {"command": "/play e", "id": "E", "agents": ["Luna", "Josefina"], "engines": ["E11", "E12", "E13", "E14", "E15"], "domains": ["D06_SISTEMA_INTELIGENTE"], "criticality": "MEDIUM"},
    {"command": "/play ema", "id": "EMA", "agents": ["Luna", "Josefina", "Katya"], "engines": ["E11", "E12", "E13", "E14", "E15"], "domains": ["D01_CEREBRO", "D06_SISTEMA_INTELIGENTE"], "criticality": "HIGH"},
    {"command": "/play p", "id": "P", "agents": ["Luna", "Ancapi"], "engines": ["E10", "E12", "E13", "E14", "E15"], "domains": ["D01_CEREBRO"], "criticality": "HIGH"},
    {"command": "/play c", "id": "C", "agents": ["Luna", "Katya"], "engines": ["E01", "E02", "E09", "E12", "E13", "E15"], "domains": ["D01_CEREBRO"], "criticality": "MEDIUM"},
    {"command": "/play cp", "id": "CP", "agents": ["Luna", "Josefina", "Katya"], "engines": ["E03", "E05", "E06", "E09", "E11", "E12", "E13", "E14", "E15"], "domains": ["D01_CEREBRO", "D06_SISTEMA_INTELIGENTE"], "criticality": "MEDIUM"},
    {"command": "/play MA", "id": "MA", "agents": ["Luna"], "engines": [f"E{i:02d}" for i in range(1, 16)], "domains": ["D01_CEREBRO"], "criticality": "CRITICAL"},
    {"command": "/play H", "id": "H", "agents": ["Luna", "Josefina"], "engines": ["E11", "E12", "E13", "E14", "E15"], "domains": ["D06_SISTEMA_INTELIGENTE"], "criticality": "HIGH"},
    {"command": "/play AE", "id": "AE", "agents": ["Luna", "Ancapi"], "engines": ["E06", "E07", "E08", "E09", "E10", "E12", "E13", "E14", "E15"], "domains": ["D06_SISTEMA_INTELIGENTE"], "criticality": "CRITICAL"},
]
ROUTE_INDEX = {re.sub(r"\s+", " ", r["command"].strip()).casefold(): r for r in ROUTES}
DOMAIN_CAPABILITY = {
    "D01_CEREBRO": "answer_generation", "D02_ORQUESTACION": "job_orchestration",
    "D03_TRANSCRIPCION": "audio_transcription", "D04_TRADUCTOR_INTELIGENTE": "text_translation",
    "D05_INTELIGENCIA_DOCUMENTAL": "document_extraction", "D06_SISTEMA_INTELIGENTE": "advanced_reasoning",
}
CAPABILITY_ADAPTERS = {
    "answer_generation": "CAJITA_MODEL_ADAPTERS/1.0",
    "job_orchestration": "CAJITA_MODEL_ADAPTERS/1.0_DIAGNOSTIC_ONLY",
    "audio_transcription": "CAJITA_MODEL_ADAPTERS/1.0",
    "text_translation": "CAJITA_MODEL_ADAPTERS/1.0",
    "document_extraction": "CAJITA_MODEL_ADAPTERS/1.0",
    "pdf_generation": "CAJITA_MODEL_ADAPTERS/1.0_STANDARD_LIBRARY",
    "advanced_reasoning": "CAJITA_MODEL_ADAPTERS/1.0",
}
TASK_RULES = [
    ("audio_transcription", "D03_TRANSCRIPCION", (r"\btranscrib\w*\b", r"\btranscripci[oó]n\b", r"\baudio\b", r"\bspeech[- ]to[- ]text\b", r"\bvoz a texto\b")),
    ("document_extraction", "D05_INTELIGENCIA_DOCUMENTAL", (r"\b(pdf|documento|documentos|documental|ocr)\b", r"\bextraer\s+(el\s+)?texto\b", r"\bleer\s+(el\s+)?(archivo|documento)\b", r"\bresum\w*\s+(el\s+)?(pdf|documento)\b")),
    ("text_translation", "D04_TRADUCTOR_INTELIGENTE", (r"\btrad[uú]c\w*\b", r"\btranslation\b", r"\btranslate\b", r"\btraducci[oó]n\b", r"\btranslator\b")),
    ("advanced_reasoning", "D06_SISTEMA_INTELIGENTE", (r"\brazon\w*\b", r"\binfer\w*\b", r"\banaliza\w*\b", r"\bcompara\w*\b", r"\bauditor[ií]a\b", r"\bdemuestra\b", r"\bformaliz\w*\b")),
]

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def normalize_command(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    route = ROUTE_INDEX.get(re.sub(r"\s+", " ", value.strip()).casefold())
    return route["command"] if route else None

def extract_command(request: str) -> tuple[str | None, bool]:
    match = re.match(r"^\s*(/help|/play\s+[^\s]+)\b", request, flags=re.IGNORECASE)
    if not match:
        return None, False
    raw = re.sub(r"\s+", " ", match.group(1).strip())
    return normalize_command(raw), normalize_command(raw) is None

def detect_tasks(request: str) -> tuple[list[str], list[str], list[str]]:
    text = request.casefold()
    domains: list[str] = []
    capabilities: list[str] = []
    reasons: list[str] = []
    for capability, domain, patterns in TASK_RULES:
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            if domain not in domains:
                domains.append(domain)
            if capability not in capabilities:
                capabilities.append(capability)
            reasons.append("keyword-rule:" + capability)
    pdf_generation = bool(re.search(
        r"\b(crea\w*|genera\w*|exporta\w*|produce)\b.{0,70}\b(pdf|documento\s+pdf)\b|\b(pdf|documento\s+pdf)\b.{0,70}\b(crea\w*|genera\w*|exporta\w*)\b",
        text))
    if pdf_generation:
        if "D05_INTELIGENCIA_DOCUMENTAL" not in domains:
            domains.append("D05_INTELIGENCIA_DOCUMENTAL")
        if "pdf_generation" not in capabilities:
            capabilities.append("pdf_generation")
        reasons.append("keyword-rule:pdf_generation")
    if not domains:
        domains, capabilities, reasons = ["D01_CEREBRO"], ["answer_generation"], ["fallback:general_request"]
    rank = {"D03_TRANSCRIPCION": 10, "D05_INTELIGENCIA_DOCUMENTAL": 20,
            "D04_TRADUCTOR_INTELIGENTE": 30, "D06_SISTEMA_INTELIGENTE": 40, "D01_CEREBRO": 50}
    domains.sort(key=lambda domain: rank.get(domain, 100))
    return domains, capabilities, reasons

def route_table_selftest() -> dict[str, Any]:
    errors: list[str] = []
    commands = [r["command"] for r in ROUTES]
    ids = [r["id"] for r in ROUTES]
    valid_engines = {f"E{i:02d}" for i in range(1, 16)}
    if len(ROUTES) != 14: errors.append(f"EXPECTED_14_ROUTES_GOT_{len(ROUTES)}")
    if len(set(commands)) != len(commands): errors.append("DUPLICATE_CANONICAL_COMMAND")
    if len(set(ids)) != len(ids): errors.append("DUPLICATE_ROUTE_ID")
    for route in ROUTES:
        if not route["agents"] or route["agents"][0] != "Luna": errors.append("LUNA_NOT_FIRST:" + route["id"])
        if not set(route["engines"]).issubset(valid_engines): errors.append("UNKNOWN_ENGINE:" + route["id"])
        if not set(route["domains"]).issubset(DOMAINS): errors.append("UNKNOWN_DOMAIN:" + route["id"])
    return {"schema": SCHEMA, "operation": "router-selftest", "route_count": len(ROUTES),
            "domain_count": len(DOMAINS), "status": "PASS" if not errors else "FAIL", "errors": errors,
            "certification": "NOT_GRANTED", "note": "Catalog consistency only; no task-quality certification."}

def available_memory_mib() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"): return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return None

def build_plan(request: str, route_command: str | None = None) -> dict[str, Any]:
    request = request.strip()
    detected, invalid = extract_command(request)
    requested = normalize_command(route_command) if route_command else detected
    if invalid or (route_command and not normalize_command(route_command)):
        return {"schema": SCHEMA, "operation": "plan", "captured_at_utc": utc_now(), "status": "FAIL_CLOSED",
                "reason": "UNKNOWN_CANONICAL_COMMAND", "request_sha256": sha256_text(request),
                "canonical_routes_mutated": False, "execution_authorized": False, "certification": "NOT_GRANTED"}
    route = next((item for item in ROUTES if item["command"] == requested), None)
    task_text = re.sub(r"^\s*/(?:help|play\s+[^\s]+)\s*", "", request, flags=re.IGNORECASE) if route else request
    intent_domains, capabilities, reasons = detect_tasks(task_text)
    sequence = ["D01_CEREBRO", "D02_ORQUESTACION"]
    for domain in (route["domains"] if route else []) + intent_domains:
        if domain not in sequence: sequence.append(domain)
    for domain in (route["domains"] if route else []):
        cap = DOMAIN_CAPABILITY[domain]
        if cap not in capabilities: capabilities.append(cap)
    missing = sorted({cap for cap in capabilities if CAPABILITY_ADAPTERS.get(cap, "NOT_REGISTERED") == "NOT_REGISTERED"})
    unmeasured = [domain for domain in sequence if DOMAINS[domain]["peak_rss_mib"] is None]
    observed_memory = available_memory_mib()
    if unmeasured:
        resource_gate = "BLOCKED_UNMEASURED_PEAK_RSS"
    elif observed_memory is not None and observed_memory < 128:
        resource_gate = "BLOCKED_INSUFFICIENT_AVAILABLE_MEMORY"
    else:
        resource_gate = "PASS_FOR_DECLARED_PROFILES_ONLY"
    blockers = []
    if missing: blockers.append("TASK_ADAPTER_NOT_REGISTERED:" + ",".join(missing))
    if unmeasured: blockers.append("PEAK_RSS_UNMEASURED:" + ",".join(unmeasured))
    if "pdf_generation" in capabilities and CAPABILITY_ADAPTERS.get("pdf_generation", "NOT_REGISTERED") == "NOT_REGISTERED": blockers.append("PDF_GENERATION_ADAPTER_NOT_REGISTERED")
    return {
        "schema": SCHEMA, "operation": "plan", "captured_at_utc": utc_now(),
        "status": "PLAN_READY" if not blockers else "PLAN_ONLY_BLOCKED",
        "request_sha256": sha256_text(request), "request_stored": False,
        "route_mode": "CANONICAL_COMMAND" if route else "AUTO_INTENT_NONCANONICAL",
        "route_command": route["command"] if route else None, "route_id": route["id"] if route else "AUTO_INTENT",
        "route_criticality": route["criticality"] if route else "INTENT_CLASSIFIED",
        "agents": route["agents"] if route else ["Luna"],
        "engines": route["engines"] if route else ["E01", "E02", "E13", "E14", "E15"],
        "intent_reasons": reasons, "required_capabilities": capabilities, "domain_sequence": sequence,
        "parallel_domain_processes": MAX_PARALLEL_DOMAINS, "load_policy": "ON_DEMAND_SEQUENTIAL",
        "unload_policy": "UNLOAD_AFTER_EACH_DOMAIN_STAGE", "memory_budget_mib": MAX_RAM_MIB,
        "cpu_thread_limit": CPU_THREAD_LIMIT, "available_memory_mib_observed": observed_memory,
        "resource_gate": resource_gate, "unmeasured_peak_rss_domains": unmeasured,
        "missing_task_adapters": missing, "blockers": blockers,
        "execution_authorized": not blockers and resource_gate.startswith("PASS"),
        "classification_mode": "DETERMINISTIC_KEYWORD_PRECLASSIFIER; CEREBRO_INFERENCE_ADAPTER_NOT_REGISTERED",
        "orchestration_mode": "PLAN_ONLY; DOMAIN_TASK_DISPATCH_NOT_IMPLEMENTED",
        "canonical_routes_mutated": False, "authority_transfer": False,
        "provenance": {"request_sha256": sha256_text(request), "trace_contains_request_text": False},
        "certification": "NOT_GRANTED", "next_gate": "REGISTER_VERIFIED_TASK_ADAPTERS_AND_MEASURE_PEAK_RSS_BEFORE_EXECUTION",
    }

def append_trace(path_value: str, plan: dict[str, Any]) -> None:
    path = Path(path_value).expanduser()
    if path.exists() and path.is_symlink(): raise RuntimeError("TRACE_SYMLINK_REJECTED")
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {key: plan.get(key) for key in ("schema", "operation", "request_sha256", "route_command", "route_id", "domain_sequence", "execution_authorized", "status", "blockers")}
    record["timestamp_utc"] = utc_now()
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("routes")
    sub.add_parser("selftest")
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("--request", required=True)
    plan_parser.add_argument("--route-command")
    plan_parser.add_argument("--trace-file")
    args = parser.parse_args(argv)
    if args.command == "routes":
        print(json.dumps({"schema": SCHEMA, "routes": ROUTES, "domains": DOMAINS, "certification": "NOT_GRANTED"}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "selftest":
        result = route_table_selftest()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] == "PASS" else 2
    plan = build_plan(args.request, args.route_command)
    if args.trace_file:
        try: append_trace(args.trace_file, plan)
        except Exception as exc:
            print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "TRACE_WRITE_FAILED", "detail": str(exc)[:200], "execution_authorized": False, "certification": "NOT_GRANTED"}), file=sys.stderr)
            return 2
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0 if plan.get("status") == "PLAN_READY" else 2

if __name__ == "__main__":
    raise SystemExit(main())
