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

from cajita_antiparalysis import PersistentAntiParalysis

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
    "answer_generation": "CAJITA_CEREBRO_TEXT_GENERATION/1.0",
    "job_orchestration": "REGISTRY_AND_PLAN_ONLY_NOT_EXECUTOR",
    "audio_transcription": "CAJITA_WHISPER_TRANSCRIPTION/1.0",
    "text_translation": "CAJITA_SEAMLESS_TRANSLATION/1.0",
    "document_extraction": "CAJITA_DOCLING_IMAGE_EXTRACTION/1.0",
    "pdf_generation": "NOT_REGISTERED",
    "advanced_reasoning": "CAJITA_QWEN3_REASONING/1.0",
}
TARGET_TASK_ADAPTERS = {
    "D01_CEREBRO_ROOT": "CAJITA_CEREBRO_TEXT_GENERATION/1.0",
    "D03_TRANSCRIPCION_ROOT": "CAJITA_WHISPER_TRANSCRIPTION/1.0",
    "D04_TRADUCCION_GENERAL": "CAJITA_SEAMLESS_TRANSLATION/1.0",
    "D05_DOCLING": "CAJITA_DOCLING_IMAGE_EXTRACTION/1.0",
    "D06_ANALISIS_AVANZADO": "CAJITA_QWEN3_REASONING/1.0",
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


# Explicit, auditable command-to-subdomain registry. The JSON is additive:
# the canonical agent/engine command bindings above remain authoritative.
ROUTING_REGISTRY_PATH = Path(__file__).with_name("command_subdomain_routing.json")
try:
    ROUTING_REGISTRY = json.loads(ROUTING_REGISTRY_PATH.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise RuntimeError("SUBDOMAIN_ROUTING_REGISTRY_UNAVAILABLE") from exc
if ROUTING_REGISTRY.get("schema") != "CAJITA_COMMAND_SUBDOMAIN_ROUTING/1.0":
    raise RuntimeError("SUBDOMAIN_ROUTING_SCHEMA_INVALID")
TARGETS = ROUTING_REGISTRY.get("targets", [])
TARGETS_BY_ID = {item["id"]: item for item in TARGETS}
SUPPORT_ASSETS = ROUTING_REGISTRY.get("support_assets", [])
SUPPORT_ASSETS_BY_ID = {item["id"]: item for item in SUPPORT_ASSETS}
ROUTE_PROFILES = ROUTING_REGISTRY.get("route_profiles", [])
ROUTE_PROFILES_BY_COMMAND = {item["command"]: item for item in ROUTE_PROFILES}
INTENT_ROUTING_RULES = ROUTING_REGISTRY.get("intent_rules", [])
ENGINE_REGISTRY = ROUTING_REGISTRY.get("engine_registry", [])
VALID_ENGINE_IDS = {item.get("id") for item in ENGINE_REGISTRY}
DOMAIN_ORDER = ROUTING_REGISTRY.get("domain_order", list(DOMAINS))
COMMAND_ALIASES = {
    item["alias"]: item["canonical"]
    for item in ROUTING_REGISTRY.get("command_aliases", [])
}
CANONICAL_COMMANDS = {item["command"] for item in ROUTES}
if len(ROUTE_PROFILES_BY_COMMAND) != len(ROUTE_PROFILES):
    raise RuntimeError("DUPLICATE_SUBDOMAIN_ROUTE_PROFILE")
if set(ROUTE_PROFILES_BY_COMMAND) != CANONICAL_COMMANDS:
    raise RuntimeError("SUBDOMAIN_ROUTE_COMMAND_SET_MISMATCH")
if any(alias in CANONICAL_COMMANDS or target not in CANONICAL_COMMANDS
       for alias, target in COMMAND_ALIASES.items()):
    raise RuntimeError("INVALID_EXPLICIT_COMMAND_ALIAS")
if len(TARGETS_BY_ID) != len(TARGETS):
    raise RuntimeError("DUPLICATE_SUBDOMAIN_TARGET_ID")
if len(SUPPORT_ASSETS_BY_ID) != len(SUPPORT_ASSETS):
    raise RuntimeError("DUPLICATE_SUPPORT_ASSET_ID")
for target in TARGETS:
    if target.get("domain_id") not in DOMAINS:
        raise RuntimeError("UNKNOWN_TARGET_DOMAIN:" + str(target.get("id")))
    if any(asset_id not in SUPPORT_ASSETS_BY_ID for asset_id in target.get("support_assets", [])):
        raise RuntimeError("UNKNOWN_TARGET_ASSET:" + str(target.get("id")))
for asset in SUPPORT_ASSETS:
    if any(target_id not in TARGETS_BY_ID for target_id in asset.get("subdomain_ids", [])):
        raise RuntimeError("UNKNOWN_ASSET_TARGET:" + str(asset.get("id")))
for target in TARGETS:
    if not target.get("engine_ids") or any(engine_id not in VALID_ENGINE_IDS for engine_id in target.get("engine_ids", [])):
        raise RuntimeError("INVALID_TARGET_ENGINE_BINDING:" + str(target.get("id")))
if len(VALID_ENGINE_IDS) != 15:
    raise RuntimeError("EXPECTED_15_CANONICAL_ENGINE_IDS")

# Replace broad/stale domain hints only. Command names, agents, engines,
# and criticality remain unchanged from the canonical route registry above.
for _route in ROUTES:
    _profile = ROUTE_PROFILES_BY_COMMAND[_route["command"]]
    _target_domains = {TARGETS_BY_ID[t]["domain_id"] for t in _profile["default_targets"]}
    _route["domains"] = [domain_id for domain_id in DOMAIN_ORDER if domain_id in _target_domains]
ROUTE_INDEX = {re.sub(r"\\s+", " ", r["command"].strip()): r for r in ROUTES}

def normalize_command(value: str | None) -> str | None:
    """Accept exact canonical spellings and only explicitly registered aliases."""
    if not value or not value.strip():
        return None
    candidate = value.strip()
    if candidate in CANONICAL_COMMANDS:
        return candidate
    return COMMAND_ALIASES.get(candidate)


def extract_command(request: str) -> tuple[str | None, bool]:
    """Parse command prefixes without silently case-folding canonical command IDs."""
    if not request or not request.strip():
        return None, False
    stripped = request.lstrip()
    match = re.match(r"^(/help|/play\s+[^\s]+)\b", stripped)
    if not match:
        return None, stripped.startswith("/")
    raw = match.group(1).strip()
    normalized = normalize_command(raw)
    return normalized, normalized is None


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

def matched_intent_targets(request: str) -> tuple[list[str], list[str]]:
    """Return deterministic target IDs and rule IDs matching user task text."""
    selected: list[str] = []
    matched_rules: list[str] = []
    for rule in INTENT_ROUTING_RULES:
        patterns = rule.get("patterns", [])
        if any(re.search(pattern, request, flags=re.IGNORECASE) for pattern in patterns):
            matched_rules.append(rule["id"])
            for target_id in rule.get("target_ids", []):
                if target_id not in selected:
                    selected.append(target_id)
    return selected, matched_rules


def route_table_selftest() -> dict[str, Any]:
    errors: list[str] = []
    commands = [r["command"] for r in ROUTES]
    ids = [r["id"] for r in ROUTES]
    valid_engines = {f"E{i:02d}" for i in range(1, 16)}
    if len(ROUTES) != 14: errors.append(f"EXPECTED_14_ROUTES_GOT_{len(ROUTES)}")
    if len(set(commands)) != len(commands): errors.append("DUPLICATE_CANONICAL_COMMAND")
    if len(set(ids)) != len(ids): errors.append("DUPLICATE_ROUTE_ID")
    if set(commands) != set(ROUTE_PROFILES_BY_COMMAND): errors.append("ROUTE_PROFILE_SET_MISMATCH")
    for route in ROUTES:
        if not route["agents"] or route["agents"][0] != "Luna": errors.append("LUNA_NOT_FIRST:" + route["id"])
        if not set(route["engines"]).issubset(valid_engines): errors.append("UNKNOWN_ENGINE:" + route["id"])
        if not set(route["domains"]).issubset(DOMAINS): errors.append("UNKNOWN_DOMAIN:" + route["id"])
        profile = ROUTE_PROFILES_BY_COMMAND.get(route["command"], {})
        if any(target_id not in TARGETS_BY_ID for target_id in profile.get("default_targets", [])):
            errors.append("UNKNOWN_PROFILE_TARGET:" + route["id"])
        supported_engines = {engine_id for target_id in profile.get("default_targets", [])
                             for engine_id in TARGETS_BY_ID.get(target_id, {}).get("engine_ids", [])}
        if not (set(route["engines"]) & supported_engines):
            errors.append("COMMAND_ENGINE_TARGET_MISMATCH:" + route["id"])
    expected_counts = {"D02_ORQUESTACION": 3, "D04_TRADUCTOR_INTELIGENTE": 3,
                       "D05_INTELIGENCIA_DOCUMENTAL": 2, "D06_SISTEMA_INTELIGENTE": 11}
    for domain_id, expected in expected_counts.items():
        actual = sum(1 for target in TARGETS
                     if target.get("domain_id") == domain_id and target.get("kind") == "SUBDOMAIN")
        if actual != expected: errors.append(f"SUBDOMAIN_COUNT_{domain_id}:{actual}!={expected}")
    if len(SUPPORT_ASSETS) != 10: errors.append(f"EXPECTED_10_SUPPORT_ASSETS_GOT_{len(SUPPORT_ASSETS)}")
    if len(ENGINE_REGISTRY) != 15 or len(VALID_ENGINE_IDS) != 15: errors.append("EXPECTED_15_CANONICAL_ENGINES")
    for target in TARGETS:
        if not target.get("engine_ids") or any(engine_id not in VALID_ENGINE_IDS for engine_id in target.get("engine_ids", [])):
            errors.append("INVALID_TARGET_ENGINE_BINDING:" + str(target.get("id")))
    for target in TARGETS:
        for asset_id in target.get("support_assets", []):
            if target["id"] not in SUPPORT_ASSETS_BY_ID.get(asset_id, {}).get("subdomain_ids", []):
                errors.append("ASSET_TARGET_BINDING_ASYMMETRIC:" + target["id"] + ":" + asset_id)
    for asset in SUPPORT_ASSETS:
        for target_id in asset.get("subdomain_ids", []):
            if asset["id"] not in TARGETS_BY_ID.get(target_id, {}).get("support_assets", []):
                errors.append("TARGET_ASSET_BINDING_ASYMMETRIC:" + asset["id"] + ":" + target_id)
        if not asset.get("sha256") or not asset.get("relative_path") or int(asset.get("bytes", 0)) <= 0:
            errors.append("INCOMPLETE_ASSET_IDENTITY:" + str(asset.get("id")))
        if not asset.get("subdomain_ids") or any(t not in TARGETS_BY_ID for t in asset.get("subdomain_ids", [])):
            errors.append("INVALID_ASSET_TARGETS:" + str(asset.get("id")))
    for alias, canonical in COMMAND_ALIASES.items():
        if canonical not in CANONICAL_COMMANDS or alias in CANONICAL_COMMANDS:
            errors.append("INVALID_ALIAS:" + alias)
    return {
        "schema": SCHEMA, "operation": "router-selftest",
        "route_count": len(ROUTES), "domain_count": len(DOMAINS),
        "target_count": len(TARGETS), "subdomain_count": sum(1 for t in TARGETS if t.get("kind") == "SUBDOMAIN"),
        "subdomain_counts_by_domain": {
            domain_id: sum(1 for t in TARGETS if t.get("domain_id") == domain_id and t.get("kind") == "SUBDOMAIN")
            for domain_id in expected_counts
        },
        "support_asset_count": len(SUPPORT_ASSETS), "engine_count": len(ENGINE_REGISTRY),
        "target_engine_binding_count": len(TARGETS),
        "status": "PASS" if not errors else "FAIL", "errors": errors,
        "canonical_command_bindings_mutated": False,
        "execution_dispatch": "PLAN_ONLY_FAIL_CLOSED",
        "certification": "NOT_GRANTED",
    }


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
    normalized_override = normalize_command(route_command) if route_command else None
    if invalid or (route_command and not normalized_override):
        return {
            "schema": SCHEMA, "operation": "plan", "captured_at_utc": utc_now(),
            "status": "FAIL_CLOSED", "reason": "UNKNOWN_CANONICAL_COMMAND",
            "request_sha256": sha256_text(request), "canonical_routes_mutated": False,
            "authority_transfer": False, "execution_authorized": False,
            "certification": "NOT_GRANTED",
        }
    requested = normalized_override or detected
    route = next((item for item in ROUTES if item["command"] == requested), None)
    task_text = re.sub(r"^\s*(?:/help|/play\s+[^\s]+)\s*", "", request) if detected else request
    if route_command and not detected:
        task_text = request
    intent_domains, capabilities, legacy_reasons = detect_tasks(task_text)
    intent_target_ids, matched_rule_ids = matched_intent_targets(task_text)

    profile = ROUTE_PROFILES_BY_COMMAND.get(route["command"], {}) if route else {}
    command_target_ids = list(profile.get("default_targets", []))
    selected_target_ids: list[str] = []
    for target_id in command_target_ids + intent_target_ids:
        if target_id not in selected_target_ids:
            selected_target_ids.append(target_id)

    ancient_language_selected = "INTENT_ANCIENT_LANGUAGES" in matched_rule_ids
    if ancient_language_selected:
        selected_target_ids = [target_id for target_id in selected_target_ids
                               if target_id != "D04_TRADUCCION_GENERAL"]
        for target_id in ("D04_HERMENEUTICA_HG", "D04_TRADUCCION_LENGUAS_ANTIGUAS"):
            if target_id in TARGETS_BY_ID and target_id not in selected_target_ids:
                selected_target_ids.append(target_id)

    # Stable target presentation follows the declared target registry, while
    # domain execution order follows task dependencies (e.g. extract before translate).
    selected_set = set(selected_target_ids)
    selected_targets = []
    for target in TARGETS:
        if target["id"] in selected_set:
            selected_targets.append({
                "id": target["id"], "domain_id": target["domain_id"],
                "kind": target["kind"], "name": target["name"], "path": target["path"],
                "purpose": target["purpose"], "engine_ids": target.get("engine_ids", []),
                "support_assets": target.get("support_assets", []),
                "task_adapter": TARGET_TASK_ADAPTERS.get(target["id"], "NOT_REGISTERED"),
            })

    rank = {"D03_TRANSCRIPCION": 10, "D05_INTELIGENCIA_DOCUMENTAL": 20,
            "D04_TRADUCTOR_INTELIGENTE": 30, "D06_SISTEMA_INTELIGENTE": 40,
            "D01_CEREBRO": 50, "D02_ORQUESTACION": 60}
    target_domains = {target["domain_id"] for target in selected_targets}
    for domain_id in intent_domains:
        if domain_id in DOMAINS:
            target_domains.add(domain_id)
    ordered_task_domains = sorted(target_domains, key=lambda domain_id: rank.get(domain_id, 100))
    sequence = ["D01_CEREBRO", "D02_ORQUESTACION"]
    for domain_id in ordered_task_domains:
        if domain_id not in sequence:
            sequence.append(domain_id)
    # Keep presentation aligned with the project's canonical six-domain order.
    selected_target_domains = [domain_id for domain_id in DOMAIN_ORDER
                               if any(t["domain_id"] == domain_id for t in selected_targets)]

    selected_asset_ids: list[str] = []
    for target in selected_targets:
        for asset_id in target.get("support_assets", []):
            if asset_id not in selected_asset_ids:
                selected_asset_ids.append(asset_id)
    selected_support_assets = []
    for asset in SUPPORT_ASSETS:
        if asset["id"] in selected_asset_ids:
            selected_support_assets.append({
                "id": asset["id"], "version": asset["version"],
                "path": asset.get("materialized_path") or asset["relative_path"],
                "materialized_path": asset.get("materialized_path"),
                "source_archive_path": asset.get("source_archive_path", asset["relative_path"]),
                "source_archive_bytes": asset.get("source_archive_bytes", asset["bytes"]),
                "source_archive_sha256": asset.get("source_archive_sha256", asset["sha256"]),
                "bytes": (asset.get("expanded_bytes") if asset.get("materialized_path") else None)
                         or asset.get("container_bytes") or asset["bytes"],
                "sha256": (asset.get("expanded_tree_sha256") if asset.get("materialized_path") else None)
                          or asset.get("container_sha256") or asset["sha256"],
                "expanded_path": asset.get("expanded_path"),
                "expanded_bytes": asset.get("expanded_bytes"),
                "expanded_tree_sha256": asset.get("expanded_tree_sha256"),
                "container_path": asset.get("container_path"),
                "container_bytes": asset.get("container_bytes"),
                "container_sha256": asset.get("container_sha256"),
                "container_retained_in_distribution": bool(asset.get("container_retained_in_distribution", False)),
                "module_manifest_path": asset.get("module_manifest_path"),
                "module_manifest_sha256": asset.get("module_manifest_sha256"),
                "role": asset["role"],
                "activation_status": asset.get("activation_status") or (
                    "MATERIALIZED_NOT_FUNCTIONALLY_VALIDATED" if asset.get("materialized_path")
                    else "MAPPED_CONTAINER_NOT_ACTIVATED"
                ),
                "archive_removed_from_runtime": asset.get("archive_removed_from_runtime", False),
                "activation_requirements": [
                    "verify-sha256", "verify-module-manifest", "register-real-consumer-adapter",
                    "native-smoke-test", "measure-resource-profile"
                ] + (["verify-container-sha256", "verify-expanded-tree-sha256-before-materialization"]
                     if asset.get("container_retained_in_distribution") else []),
            })

    for target in selected_targets:
        cap = DOMAIN_CAPABILITY.get(target["domain_id"])
        if cap and cap not in capabilities:
            capabilities.append(cap)
    for domain_id in selected_target_domains:
        cap = DOMAIN_CAPABILITY.get(domain_id)
        if cap and cap not in capabilities:
            capabilities.append(cap)

    missing = sorted({cap for cap in capabilities
                      if CAPABILITY_ADAPTERS.get(cap, "NOT_REGISTERED") == "NOT_REGISTERED"})
    adapter_blockers = ["SUBDOMAIN_TASK_ADAPTER_NOT_REGISTERED:" + target["id"]
                        for target in selected_targets
                        if target.get("task_adapter", "NOT_REGISTERED") == "NOT_REGISTERED"]
    unmeasured = [domain_id for domain_id in sequence
                  if DOMAINS.get(domain_id, {}).get("peak_rss_mib") is None]
    observed_memory = available_memory_mib()
    if unmeasured:
        resource_gate = "BLOCKED_UNMEASURED_PEAK_RSS"
    elif observed_memory is not None and observed_memory < 128:
        resource_gate = "BLOCKED_INSUFFICIENT_AVAILABLE_MEMORY"
    else:
        resource_gate = "PASS_FOR_DECLARED_PROFILES_ONLY"

    blockers = []
    if missing:
        blockers.append("TASK_ADAPTER_NOT_REGISTERED:" + ",".join(missing))
    blockers.extend(adapter_blockers)
    if unmeasured:
        blockers.append("PEAK_RSS_UNMEASURED:" + ",".join(unmeasured))
    if "pdf_generation" in capabilities:
        blockers.append("PDF_GENERATION_ADAPTER_NOT_REGISTERED")
    if selected_support_assets:
        blockers.append("SUPPORT_ASSET_ACTIVATION_NOT_VERIFIED")
    status = "PLAN_READY" if not blockers else "PLAN_ONLY_BLOCKED"
    return {
        "schema": SCHEMA, "operation": "plan", "captured_at_utc": utc_now(),
        "status": status, "request_sha256": sha256_text(request), "request_stored": False,
        "route_mode": "CANONICAL_COMMAND" if route else "AUTO_INTENT_NONCANONICAL",
        "route_command": route["command"] if route else None,
        "route_id": route["id"] if route else "AUTO_INTENT",
        "route_criticality": route["criticality"] if route else "INTENT_CLASSIFIED",
        "agents": route["agents"] if route else ["Luna"],
        "engines": route["engines"] if route else ["E01", "E02", "E13", "E14", "E15"],
        "intent_reasons": legacy_reasons, "matched_intent_rules": matched_rule_ids,
        "selection_policy": profile.get("policy") if route else "minimum-relevant-subdomains-from-intent",
        "canonical_rationale": profile.get("canonical_rationale") if route else None,
        "extension_families": profile.get("extension_families", []) if route else [],
        "required_capabilities": capabilities,
        "command_default_target_ids": command_target_ids,
        "selected_targets": selected_targets,
        "selected_domain_ids": selected_target_domains,
        "selected_support_assets": selected_support_assets,
        "domain_sequence": sequence, "parallel_domain_processes": MAX_PARALLEL_DOMAINS,
        "load_policy": "ON_DEMAND_SEQUENTIAL", "unload_policy": "UNLOAD_AFTER_EACH_DOMAIN_STAGE",
        "memory_budget_mib": MAX_RAM_MIB, "cpu_thread_limit": CPU_THREAD_LIMIT,
        "available_memory_mib_observed": observed_memory, "resource_gate": resource_gate,
        "unmeasured_peak_rss_domains": unmeasured, "missing_task_adapters": missing,
        "blockers": blockers, "execution_authorized": False,
        "classification_mode": "DETERMINISTIC_KEYWORD_PRECLASSIFIER; CEREBRO_INFERENCE_ADAPTER_NOT_REGISTERED",
        "orchestration_mode": "PLAN_ONLY; REGISTERED_DOMAIN_ADAPTERS_REQUIRE_MEASURED_RESOURCE_AND_TARGET_EVIDENCE",
        "canonical_routes_mutated": False, "authority_transfer": False,
        "provenance": {"request_sha256": sha256_text(request), "trace_contains_request_text": False},
        "certification": "NOT_GRANTED",
        "next_gate": "REGISTER_REMAINING_TARGET_ADAPTERS_AND_MEASURE_PEAK_RSS_BEFORE_ROUTED_EXECUTION",
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
        print(json.dumps({"schema": SCHEMA, "routes": ROUTES, "domains": DOMAINS, "subdomain_routing": ROUTING_REGISTRY, "certification": "NOT_GRANTED"}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "selftest":
        result = route_table_selftest()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] == "PASS" else 2
    plan = build_plan(args.request, args.route_command)
    try:
        plan["anti_paralysis"] = PersistentAntiParalysis.default().observe_plan(
            task_id=plan["request_sha256"],
            input_sha256=plan["request_sha256"],
            blockers=plan.get("blockers", []),
            plan_status=plan.get("status", "FAIL_CLOSED"),
        )
    except Exception as exc:
        plan["status"] = "FAIL_CLOSED"
        plan["execution_authorized"] = False
        plan["anti_paralysis"] = {
            "state": "FAIL_CLOSED",
            "automatic_retry": False,
            "reason": type(exc).__name__ + ":" + str(exc)[:200],
        }
    if args.trace_file:
        try: append_trace(args.trace_file, plan)
        except Exception as exc:
            print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "TRACE_WRITE_FAILED", "detail": str(exc)[:200], "execution_authorized": False, "certification": "NOT_GRANTED"}), file=sys.stderr)
            return 2
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0 if plan.get("status") == "PLAN_READY" else 2

if __name__ == "__main__":
    raise SystemExit(main())
