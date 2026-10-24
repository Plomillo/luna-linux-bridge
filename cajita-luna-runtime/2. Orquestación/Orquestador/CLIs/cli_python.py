from common import probe_domain
DOMAIN_ID="CLI_PYTHON"
CANDIDATES=[("python3",["--version"],True),("python",["--version"],False),("pip3",["--version"],False)]
def probe(): return probe_domain(DOMAIN_ID,CANDIDATES,True)
