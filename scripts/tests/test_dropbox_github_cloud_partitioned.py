#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import os
import tempfile

workflow=Path(".github/workflows/dropbox-github-cloud-partitioned.yml")
script=Path("scripts/dropbox_cloud_partitioned_acquire.py")
if not workflow.is_file():
    raise SystemExit("PARTITIONED_WORKFLOW_MISSING")
if not script.is_file():
    raise SystemExit("PARTITIONED_SCRIPT_MISSING")

w=workflow.read_text(encoding="utf-8")
s=script.read_text(encoding="utf-8")

required_workflow=[
    "runs-on: ubuntu-24.04",
    "MATERIAL_BYTE_FLOW",
    "FIRST_DOWNLOAD_EVENT.json",
    "BACKGROUND_PROCESS_ALIVE",
    "GITHUB_HOSTED_UBUNTU_24_04",
    "actions/upload-artifact@",
    'name: "G23',
    'name: "G24',
    "scripts/dropbox_cloud_partitioned_acquire.py",
    "FROZEN_ROOT_HTML",
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
    "download_file_link",
    "FIRST_DOWNLOAD_EVENT.json",
    "zipfile.is_zipfile",
    "DROPBOX_CONNECTED_PLUGIN",
    "GITHUB_HOSTED_UBUNTU_24_04",
    "children_from_html_text",
    "CHILD_INVENTORY_FROZEN_ROOT_FALLBACK",
]
for needle in required_script:
    if needle not in s:
        raise SystemExit("SCRIPT_REQUIRED_CONTROL_MISSING:"+needle)

for forbidden in [
    "runs-on: [self-hosted",
    "luna-aux",
    "Desktop Commander",
    "DROPBOX_APP_SECRET",
    "DROPBOX_REFRESH_TOKEN",
    "DROPBOX_ACCESS_TOKEN",
    "rclone",
]:
    if forbidden in w or forbidden in s:
        raise SystemExit("FORBIDDEN_LOCAL_OR_SECRET_CONTROL:"+forbidden)

print("DROPBOX_GITHUB_CLOUD_PARTITIONED_CONTRACT=PASS")


# Runtime parser selftest: compilation alone does not catch missing module bindings.
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
