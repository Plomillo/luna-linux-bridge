from common import probe_domain

DOMAIN_ID = 'CLI_CLAUDE_CODE'
CANDIDATES = [('claude', ['--version'])]

def probe():
    return probe_domain(DOMAIN_ID, CANDIDATES)
