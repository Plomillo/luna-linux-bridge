#!/usr/bin/env python3
"""Fail-closed static guard for the staged Kestra Open Source integration."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPOSE = (ROOT / "compose.yml").read_text(encoding="utf-8")
ENV_EXAMPLE = (ROOT / ".env.example").read_text(encoding="utf-8")
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
require(GOVERNANCE.get("activation") == "NOT_AUTHORIZED",
        "Activation/promotion must remain unauthorized.")

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
    if flow_path.name == "10-super1200-continuity.yml":
        require("type: io.kestra.plugin.core.trigger.Schedule" in body,
                "SUPER1200 continuity must be scheduled by Kestra.")
        require('cron: "*/5 * * * *"' in body,
                "SUPER1200 continuity poll cadence must remain five minutes.")
        require("fromJson(outputs.checkpoint.body).blocked == false" in body,
                "SUPER1200 dispatch must fail closed on the reconciled checkpoint.")
        require("fromJson(outputs.checkpoint.body).material_worker_ready == true" in body,
                "SUPER1200 dispatch requires an explicitly reviewed material worker.")
        require("fromJson(outputs.executors.body).executors.D04 != null" in body,
                "SUPER1200 dispatch requires a registered D04 executor.")
        require("{{ secret('GITHUB_TOKEN') }}" in body,
                "SUPER1200 GitHub dispatch must use a Kestra secret.")
        require("actions/workflows/super1200-continuation-lrb-live.yml/dispatches" in body,
                "SUPER1200 flow must dispatch only the pinned candidate workflow.")
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
