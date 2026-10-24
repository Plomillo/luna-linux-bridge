from common import probe_domain
DOMAIN_ID="CLI_GEMINI"
CANDIDATES=[("gemini",["--version"],True)]
def probe(): return probe_domain(DOMAIN_ID,CANDIDATES,True)
