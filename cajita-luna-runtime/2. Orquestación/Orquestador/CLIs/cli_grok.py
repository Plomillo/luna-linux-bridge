from __future__ import annotations
import shutil
DOMAIN_ID="CLI_GROK"
def probe():
    # First-party distribution is documented by xAI as @xai-official/grok; only report
    # presence here. Never execute an interactive agent in an inventory probe.
    path=shutil.which("grok")
    return {"domain_id":DOMAIN_ID,"status":"PRESENT_REQUIRES_VERSION_PROBE" if path else "ABSENT",
            "binary_path":path,"official_package":"@xai-official/grok","official_source":"https://x.ai/cli/install.sh",
            "candidate_binary_executed":False,"read_only":True,"mutations_performed":False,"certification":"NOT_GRANTED"}
