#!/usr/bin/env python3
from pathlib import Path
import ast
import importlib.util
import json
import os
import tempfile

workflow=Path(".github/workflows/dropbox-github-cloud-partitioned.yml")
script=Path("scripts/dropbox_cloud_partitioned_acquire.py")
resilience=Path("scripts/dropbox_transfer_resilience.py")
seed=Path("mission-control/dropbox-github-cloud-partitioned/RESUME_SEED.json")

for p,label in (
    (workflow,"PARTITIONED_WORKFLOW_MISSING"),
    (script,"PARTITIONED_SCRIPT_MISSING"),
    (resilience,"RESILIENCE_SCRIPT_MISSING"),
    (seed,"RESUME_SEED_MISSING"),
):
    if not p.is_file():
        raise SystemExit(label)

w=workflow.read_text(encoding="utf-8")
s=script.read_text(encoding="utf-8")
r=resilience.read_text(encoding="utf-8")
seed_obj=json.loads(seed.read_text(encoding="utf-8"))

required_workflow=[
    "runs-on: ubuntu-24.04",
    "MATERIAL_BYTE_FLOW",
    "PUAC2_RESUME_TELEMETRY",
    "HEARTBEAT.json",
    "STALL_DETECTED",
    "MAX_RECOVERY_ROUNDS",
    "actions/cache/restore@1bd1e32a3bdc45362d1e726936510720a7c30a57",
    "actions/cache/save@1bd1e32a3bdc45362d1e726936510720a7c30a57",
    "RESUME_SEED",
    "RESUME_CHECKPOINT",
    "dropbox_transfer_resilience.py diagnose",
    "apply-safe-runtime-repair",
    "actions/upload-artifact@",
    'name: "G23',
    'name: "G24',
    "FROZEN_ROOT_HTML",
    "terminal_general",
    "TERMINAL_GENERAL_CERTIFICATION",
    "37355731169",
]
for needle in required_workflow:
    if needle not in w:
        raise SystemExit("WORKFLOW_REQUIRED_CONTROL_MISSING:"+needle)

required_script=[
    "PARTITION_REQUIRED",
    "too many files",
    "inventory_children",
    "attempt_folder_download",
    "attempt_direct_folder_download",
    "FOLDER_DIRECT_DL1_ATTEMPT",
    "FOLDER_DIRECT_DL1_PASS",
    "FOLDER_DOWNLOAD_UI_CONTROL_UNAVAILABLE",
    "DROPBOX_DOCUMENTED_DL1_DIRECT",
    "download_file_link",
    "FIRST_DOWNLOAD_EVENT.json",
    "zipfile.is_zipfile",
    "GITHUB_HOSTED_UBUNTU_24_04",
    "children_from_html_text",
    "CHILD_INVENTORY_FROZEN_ROOT_FALLBACK",
    "load_resume_state",
    "write_checkpoint",
    "process_item",
    "FOLDER_FALLBACK_TO_SPLIT",
    "no_restart_from_zero_with_valid_checkpoint",
    "RECOVERY_STATUS.json",
]
for needle in required_script:
    if needle not in s:
        raise SystemExit("SCRIPT_REQUIRED_CONTROL_MISSING:"+needle)

required_resilience=[
    "PUAC2_EVENT_RECORD_V2",
    "PUAC2_DROPBOX_TRANSFER_CHECKPOINT",
    "PUAC2_TRANSFER_BUG_RECORD",
    "PUAC2_LIVE_BUG_RESEARCH",
    "load_resume_state",
    "write_checkpoint",
    "diagnose",
    "live_research",
    "apply_safe_runtime_repair",
    "CODE_EVENT_KIND_COLLISION",
    "RUNTIME_PATCH_EVENT_KIND_COLLISION",
    "DROPBOX_UI_SELECTOR_DRIFT",
    "DIRECT_DL1_THEN_SPLIT",
    "CHECKPOINT_HASH_MISMATCH",
    "RECOVERY_PLAN",
]
for needle in required_resilience:
    if needle.lower() not in r.lower():
        raise SystemExit("RESILIENCE_REQUIRED_CONTROL_MISSING:"+needle)

for forbidden in [
    "runs-on: [self-hosted",
    "luna-aux",
    "Desktop Commander",
    "DROPBOX_APP_SECRET",
    "DROPBOX_REFRESH_TOKEN",
    "DROPBOX_ACCESS_TOKEN",
    "rclone",
]:
    if forbidden in w or forbidden in s or forbidden in r:
        raise SystemExit("FORBIDDEN_LOCAL_OR_SECRET_CONTROL:"+forbidden)

completed=seed_obj.get("completed") or []
if len(completed)!=5:
    raise SystemExit("RESUME_SEED_MUST_BIND_EXACTLY_FIVE_PRIOR_SUCCESSES")
if sorted(seed_obj.get("pending_top_level_ordinals") or []) != [1,5,8]:
    raise SystemExit("RESUME_SEED_PENDING_SET_MISMATCH")
for item in completed:
    if item.get("evidence_status")!="COMPLETED_VERIFIED_PRIOR_RUN":
        raise SystemExit("RESUME_SEED_UNVERIFIED_ENTRY")
    if not str(item.get("artifact_digest") or "").startswith("sha256:"):
        raise SystemExit("RESUME_SEED_ARTIFACT_DIGEST_MISSING")
    if int(item.get("artifact_size_bytes") or 0)<=0:
        raise SystemExit("RESUME_SEED_ARTIFACT_SIZE_INVALID")

tree=ast.parse(s)
for node in ast.walk(tree):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="record_event":
        if any(k.arg=="kind" for k in node.keywords):
            raise SystemExit("RECORD_EVENT_KIND_KEYWORD_COLLISION")
print("DROPBOX_GITHUB_CLOUD_PARTITIONED_EVENT_CALLSITE_SELFTEST=PASS")

print("DROPBOX_GITHUB_CLOUD_PARTITIONED_CONTRACT=PASS")

with tempfile.TemporaryDirectory() as td:
    os.environ["STATE_ROOT"]=td
    spec=importlib.util.spec_from_file_location("dropbox_cloud_partitioned_acquire", script)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    sample='<a href="/scl/fo/child-id/child-token?rlkey=abc&dl=0">Child</a>'
    rows=mod.children_from_html_text(sample, mod.ROOT_LINK)
    assert len(rows)==1, rows
    assert rows[0]["kind"]=="folder", rows
print("DROPBOX_GITHUB_CLOUD_PARTITIONED_HTML_PARSER_SELFTEST=PASS")

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    rspec=importlib.util.spec_from_file_location("dropbox_transfer_resilience", resilience)
    rmod=importlib.util.module_from_spec(rspec)
    assert rspec and rspec.loader
    rspec.loader.exec_module(rmod)
    manifest={"status":"RUNNING","completed":[],"prior_completed":[],"split_folders":[]}
    queue=[{"key":"k1","kind":"folder","url":"https://example.invalid/f","label":"x","depth":1}]
    cp=rmod.write_checkpoint(root,manifest,queue,set(),"SELFTEST")
    loaded=rmod.load_checkpoint(root/"checkpoints/LATEST.json")
    assert loaded["checkpoint_hash"]==cp["checkpoint_hash"]
    assert loaded["pending_queue"][0]["key"]=="k1"
print("DROPBOX_GITHUB_CLOUD_PARTITIONED_CHECKPOINT_SELFTEST=PASS")

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    stderr=root/"stderr.txt"
    stderr.write_text("NameError: name 'html' is not defined\n",encoding="utf-8")
    category,action,missing=rmod.classify_bug(stderr.read_text())
    assert category=="CODE_NAMEERROR"
    assert action=="RUNTIME_PATCH_STANDARD_IMPORT"
    assert missing=="html"
    category,action,missing=rmod.classify_bug("TypeError: record_event() got multiple values for argument 'kind'")
    assert category=="CODE_EVENT_KIND_COLLISION"
    assert action=="RUNTIME_PATCH_EVENT_KIND_COLLISION"
    category,action,missing=rmod.classify_bug('playwright TimeoutError waiting for button[data-testid="action-bar-download-button"]')
    assert category=="DROPBOX_UI_SELECTOR_DRIFT"
    assert action=="DIRECT_DL1_THEN_SPLIT"
print("DROPBOX_GITHUB_CLOUD_PARTITIONED_BUG_CLASSIFIER_SELFTEST=PASS")
