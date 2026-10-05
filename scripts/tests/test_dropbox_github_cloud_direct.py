#!/usr/bin/env python3
from pathlib import Path
import sys

p=Path(".github/workflows/dropbox-github-cloud-direct.yml")
if not p.is_file():
    raise SystemExit("RED_EXPECTED: cloud-direct workflow is not implemented yet")
text=p.read_text(encoding="utf-8")
required=[
    "runs-on: ubuntu-24.04",
    "DROPBOX_CONNECTED_PLUGIN",
    "dl=1",
    "MATERIAL_BYTE_FLOW",
    "actions/upload-artifact@",
    "G23",
    "G24",
    "CLOUD_DOWNLOAD_DIAGNOSTIC=TRUE",
    "if: always()",
]
for needle in required:
    if needle not in text:
        raise SystemExit("MISSING_REQUIRED_CONTROL:"+needle)
for forbidden in ["self-hosted","luna-aux","Desktop Commander","DROPBOX_APP_SECRET","DROPBOX_REFRESH_TOKEN"]:
    if forbidden in text:
        raise SystemExit("FORBIDDEN_LOCAL_OR_SECRET_CONTROL:"+forbidden)
print("DROPBOX_GITHUB_CLOUD_DIRECT_CONTRACT_TEST=PASS")


# Browser-mediated Dropbox public-folder package must still execute only in GitHub cloud.
browser=Path(".github/workflows/dropbox-github-cloud-browser.yml")
script=Path("scripts/dropbox_cloud_browser_acquire.py")
if not browser.is_file():
    raise SystemExit("RED_EXPECTED: cloud browser workflow is not implemented yet")
if not script.is_file():
    raise SystemExit("RED_EXPECTED: cloud browser acquisition script is not implemented yet")
btext=browser.read_text(encoding="utf-8")
stext=script.read_text(encoding="utf-8")
for needle in [
    "runs-on: ubuntu-24.04",
    "playwright",
    "MATERIAL_BYTE_FLOW=TRUE",
    "DROPBOX_CONNECTED_PLUGIN",
    "G23",
    "G24",
]:
    if needle not in btext:
        raise SystemExit("MISSING_BROWSER_CONTROL:"+needle)
for needle in [
    'action-bar-download-button',
    'Or continue with download only',
    'st=3igdng0g',
]:
    if needle not in stext:
        raise SystemExit("MISSING_BROWSER_SCRIPT_CONTROL:"+needle)
for forbidden in ["self-hosted","luna-aux","DROPBOX_APP_SECRET","DROPBOX_REFRESH_TOKEN","Desktop Commander"]:
    if forbidden in btext or forbidden in stext:
        raise SystemExit("FORBIDDEN_BROWSER_CONTROL:"+forbidden)
print("DROPBOX_GITHUB_CLOUD_BROWSER_CONTRACT_TEST=PASS")
