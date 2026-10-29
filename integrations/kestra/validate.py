#!/usr/bin/env python3
"""Fail-closed static guard for the staged Kestra Open Source integration."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPOSE = (ROOT / "compose.yml").read_text(encoding="utf-8")
ENV_EXAMPLE = (ROOT / ".env.example").read_text(encoding="utf-8")
TOKEN_SETUP = ROOT / "configure-github-token.sh"
TOKEN_SETUP_TEXT = TOKEN_SETUP.read_text(encoding="utf-8") if TOKEN_SETUP.is_file() else ""
GOVERNANCE = json.loads((ROOT / "GOVERNANCE.json").read_text(encoding="utf-8"))
errors: list[str] = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

require("image: kestra/kestra:v2.0.3" in COMPOSE,
        "Kestra must stay on the reviewed full-image patch tag v2.0.3.")
require("image: postgres:18.6-alpine" in COMPOSE,
        "PostgreSQL must stay on the reviewed patch tag 18.6-alpine.")
require(":latest" not in COMPOSE,
        "Floating :latest image tags are prohibited.")
require("/var/run/docker.sock" not in COMPOSE,
        "Mounting the host Docker socket is prohibited.")
require("env_file:" in COMPOSE and "- .env_encoded" in COMPOSE,
        "Kestra OSS must load the configured secret environment file.")
require(".env_encoded" in (ROOT / ".gitignore").read_text(encoding="utf-8"),
        "Local encoded GitHub credentials must be excluded from Git.")
require("read -r -s token" in TOKEN_SETUP_TEXT and "SECRET_GITHUB_TOKEN=" in TOKEN_SETUP_TEXT
        and "base64" in TOKEN_SETUP_TEXT and "chmod 600" in TOKEN_SETUP_TEXT,
        "Local token setup must use hidden input, Kestra OSS secret encoding and restrictive permissions.")
require('--replace' in TOKEN_SETUP_TEXT and 'if [[ -e "$TARGET" && "$replace" -ne 1 ]]' in TOKEN_SETUP_TEXT,
        "Token setup must not overwrite an existing credential silently.")
init_start = COMPOSE.find("  storage-init:")
kestra_start = COMPOSE.find("  kestra:")
storage_init = COMPOSE[init_start:kestra_start] if init_start >= 0 and kestra_start > init_start else ""
kestra_service = COMPOSE[kestra_start:] if kestra_start >= 0 else ""
require("network_mode: none" in storage_init,
        "The one-shot storage permission bootstrap must have no network.")
require('kestra_uid="$$(id -u kestra)"' in storage_init
        and 'kestra_gid="$$(id -g kestra)"' in storage_init
        and 'test "$$kestra_uid" -gt 0' in storage_init
        and 'chown -R "$$kestra_uid:$$kestra_gid" /app/storage' in storage_init,
        "Compose must use escaped $$ syntax so the shell, not Compose, expands storage-init variables.")
# Positive assertions above require the exact escaped $$ forms in the Compose source.

require('user: "0:0"' in storage_init and "cap_drop:" in storage_init
        and "      - ALL" in storage_init and "      - CHOWN" in storage_init,
        "The one-shot permission bootstrap must use only the scoped CHOWN capability.")
require("storage-init:" in COMPOSE and "service_completed_successfully" in kestra_service,
        "Kestra must wait for the permission bootstrap to succeed.")
require('user: "0:0"' not in kestra_service,
        "The long-running Kestra server must not run as root.")
require('"127.0.0.1:8080:8080"' in COMPOSE,
        "UI must remain bound to loopback.")
require('"127.0.0.1:18081:8081"' in COMPOSE,
        "Unauthenticated management endpoint must remain loopback-only.")
require("basic-auth:" in COMPOSE and "enabled: true" in COMPOSE,
        "Basic authentication must remain enabled.")
compose_lines = COMPOSE.splitlines()
management_index = next(
    (i for i, line in enumerate(compose_lines) if line == "        endpoints:"),
    -1,
)
require(
    management_index >= 0
    and compose_lines[management_index + 1:management_index + 3]
    == ["          all:", "            basic-auth:"],
    "Management endpoint details must require authentication.",
)
require("REPLACE_WITH_" in ENV_EXAMPLE,
        ".env.example must contain placeholders, not deployable credentials.")
require(GOVERNANCE.get("overall_status") == "CANDIDATE_NOT_CERTIFIED",
        "The integration must not self-promote to certified.")
require(GOVERNANCE.get("gates", {}).get("G23") == "NOT_PERFORMED",
        "G23 must remain unperformed until independent validation.")
require(GOVERNANCE.get("gates", {}).get("G24") == "NOT_GRANTED",
        "G24 must remain not granted.")
require(str(GOVERNANCE.get("activation", "")).startswith("OPERATIONAL_SUPERVISOR_AUTHORIZED"),
        "Only the explicitly scoped Kestra supervisor role may be authorized.")
require("CERTIFICATION_AND_PROMOTION_NOT_AUTHORIZED" in str(GOVERNANCE.get("activation", "")),
        "Operational supervisor authorization must not authorize certification or promotion.")

flows = ROOT / "flows"
for flow_path in sorted(flows.rglob("*.yml")) + sorted(flows.rglob("*.yaml")):
    body = flow_path.read_text(encoding="utf-8")
    lower = body.lower()
    require("io.kestra.plugin.core.runner.process" not in lower,
            f"{flow_path.relative_to(ROOT)} uses the non-isolated Process runner.")
    require("io.kestra.plugin.scripts." not in lower,
            f"{flow_path.relative_to(ROOT)} declares script execution before runner isolation is approved.")
    require("docker.sock" not in lower,
            f"{flow_path.relative_to(ROOT)} references a Docker socket.")
    if flow_path.name == "20-cajita-runtime-size-gate.yml":
        require("fromJson(outputs.macrodown_report.body).raw_payload_size_gate == 'PASS_WITHIN_INPUT_CEILING'" in body,
                "Kestra must require the builder's explicit raw payload PASS status.")
        require("fromJson(outputs.macrodown_report.body).gross_raw_payload_bytes_including_manifest <= 470000000" in body,
                "Kestra must enforce the raw compact Macrodown distribution cap including its manifest.")
        require("fromJson(outputs.macrodown_report.body).archive_bytes <= 470000000" in body,
                "Kestra must enforce the deterministic Macrodown archive cap.")
        require("fromJson(outputs.runtime_report.body).q2_factor_models_promoted == 0" in body
                and "fromJson(outputs.runtime_report.body).q2_factor_results[3].status == 'ALREADY_Q2_PACKED'" in body,
                "Kestra must retain Q2 factor-integrity invariants.")
        require("fromJson(outputs.runtime_report.body).size_gate == 'PASS'" not in body
                and "fromJson(outputs.runtime_report.body).runtime_bytes_after <= 470000000" not in body
                and "runtime_size_gate.raw_payload_target_gate == 'PASS'" in body
                and "runtime_size_gate.raw_payload_target_bytes == 470000000" in body,
                "The compact payload target gate, not the legacy input ceiling, must be the distribution size authority.")
    if flow_path.name == "21-louksna1-release-audit.yml":
        require("fromJson(outputs.g24_evidence.body).status == 'PASS_FOR_DECLARED_SYNTHETIC_FUNCTIONAL_E2E_SCOPE'" in body,
                "Louksna1 release audit must fail closed unless scoped synthetic task execution evidence passes.")
        require("fromJson(outputs.release_manifest.body).gates.G24 == 'PASS_FOR_DECLARED_SYNTHETIC_FUNCTIONAL_E2E_SCOPE'" in body,
                "Louksna1 release manifest and G24 evidence must agree on the new scoped runtime gate.")
        require("outputs.task_adapter_evidence.code == 200" in body and "outputs.latest_factory_run.code == 200" in body,
                "Louksna1 release audit must read task evidence and latest factory run evidence.")
        require("fromJson(outputs.task_adapter_evidence.body).source_commit == fromJson(outputs.latest_factory_run.body).head_sha" in body,
                "Task evidence must bind to the exact factory run selected by its immutable run id.")
        require("actions/runs/{{ envs.factory_run_id }}" in body,
                "Louksna1 audit must inspect the exact workflow_run trigger, not a race-prone latest-run query.")
        require("fromJson(outputs.latest_factory_run.body).id > 0" in body,
                "Louksna1 audit must validate the single workflow-run object returned by the exact run-ID endpoint.")
        require("fromJson(outputs.latest_factory_run.body).total_count > 0" not in body,
                "A single workflow-run object must not be treated as a list response with total_count.")
        require("fromJson(outputs.release_manifest.body).task_adapter_evidence.sha256 == fromJson(outputs.g24_evidence.body).task_adapter_evidence_sha256" in body,
                "Release manifest and G24 evidence must bind the same task evidence digest.")

    if flow_path.name == "10-super1200-continuity.yml":
        require("type: io.kestra.plugin.core.trigger.Schedule" in body,
                "SUPER1200 continuity must be scheduled by Kestra.")
        require('cron: "*/5 * * * *"' in body,
                "SUPER1200 continuity poll cadence must remain five minutes.")
        require("recoverMissedSchedules: NONE" in body,
                "SUPER1200 must not burst-replay stale schedule ticks after a Kestra outage.")
        require("allowConcurrent: false" in body,
                "SUPER1200 supervisor executions must not overlap.")
        require("lateMaximumDelay: PT2M" in body,
                "SUPER1200 must skip schedule ticks that are too stale to be useful.")
        require("fromJson(outputs.checkpoint.body).blocked == false" in body,
                "SUPER1200 dispatch must fail closed on the reconciled checkpoint.")
        require("fromJson(outputs.checkpoint.body).status == 'ACTIVE'" in body
                and "fromJson(outputs.checkpoint.body).status == 'READY_FOR_CONTINUATION'" in body,
                "SUPER1200 must allow ACTIVE and READY_FOR_CONTINUATION checkpoints.")
        require("fromJson(outputs.checkpoint.body).material_worker_ready == true" in body,
                "SUPER1200 dispatch requires an explicitly reviewed material worker.")
        require("metaos_ready == true" not in body,
                "MetaOS is explicitly deferred and must not block continuation.")
        require("fromJson(outputs.active_runs.body).total_count == 0" in body,
                "SUPER1200 dispatch must stop while a run is in progress.")
        require("fromJson(outputs.queued_runs.body).total_count == 0" in body,
                "SUPER1200 dispatch must stop while a run is queued.")
        require("status=in_progress" in body and "status=queued" in body,
                "SUPER1200 must query in-progress and queued runs before dispatch.")
        require("fromJson(outputs.executors.body).executors.D04 != null" in body,
                "SUPER1200 dispatch requires a registered D04 executor.")
        require("{{ secret('GITHUB_TOKEN') }}" in body,
                "SUPER1200 GitHub dispatch must use a Kestra secret.")
        require("actions/workflows/super1200-continuation-lrb-live.yml/dispatches" in body,
                "SUPER1200 flow must dispatch only the pinned candidate workflow.")
    elif flow_path.name == "25-louksnapg-remote-model-verification.yml":
        require("id: louksnapg_remote_model_verification" in body,
                "Remote-model monitoring must use its stable Kestra flow ID.")
        require('cron: "*/5 * * * *"' in body and "allowConcurrent: false" in body,
                "Remote-model monitoring must be serialized and scheduled every five minutes.")
        require(body.count("method: GET") >= 2
                and "/actions/runs?branch=louksnapg%2Fremote-source-bound-runtime-20261029" in body
                and "/actions/workflows/louksnapg-remote-model-quality.yml/runs?branch=louksnapg%2Fremote-source-bound-runtime-20261029" in body,
                "Remote-model monitoring must read both protocol and semantic-quality runs for the exact branch.")
        require("id: latest_remote_protocol_runs" in body and "id: latest_remote_quality_runs" in body,
                "Both source-bound protocol and semantic-quality run histories must be present.")
        require("io.kestra.plugin.core.http.Request" in body and "io.kestra.plugin.core.log.Log" in body,
                "Remote-model monitoring may only read GitHub state and log it.")
        require("LOUKSNAPG_REMOTE_SEMANTIC_QUALITY_MONITOR=READ_ONLY" in body,
                "Remote-model monitoring must report the semantic-quality workflow separately.")
        require("io.kestra.plugin.core.scripts." not in lower and "io.kestra.plugin.core.runner.process" not in lower,
                "Remote-model monitoring must not execute scripts or local processes.")
        require("/dispatches" not in body and "method: POST" not in body,
                "Remote-model monitoring must not dispatch jobs or mutate external state.")
        require("GLOBAL_CERTIFICATION=NOT_GRANTED_BY_MONITOR" in body,
                "The Kestra monitor must never grant product certification.")
    else:
        require("schedule:" not in lower and "triggers:" not in lower,
                f"{flow_path.relative_to(ROOT)} must not schedule or trigger itself during the staged phase.")

if errors:
    print("FAIL_CLOSED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("PASS: staged Kestra governance invariants")
print("LIMIT: static checks do not certify runtime behavior, task execution, G23, or G24")
