from common import probe_domain
DOMAIN_ID="CLI_CLAUDE_CODE"
CANDIDATES=[("claude",["--version"],True)]
def probe(): return probe_domain(DOMAIN_ID,CANDIDATES,True)
