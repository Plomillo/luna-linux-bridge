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
