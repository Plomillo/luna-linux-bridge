from common import probe_domain

DOMAIN_ID = 'CLI_GEMINI'
CANDIDATES = [('gemini', ['--version'])]

def probe():
    return probe_domain(DOMAIN_ID, CANDIDATES)
