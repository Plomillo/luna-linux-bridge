from common import probe_domain
DOMAIN_ID="CLI_GITHUB"
# git is auxiliary and cannot substitute for the required GitHub CLI (gh).
CANDIDATES=[("gh",["--version"],True),("git",["--version"],False)]
def probe(): return probe_domain(DOMAIN_ID,CANDIDATES,True)
