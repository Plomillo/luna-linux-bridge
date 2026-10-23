from common import probe_domain

DOMAIN_ID = 'CLI_GROK'
CANDIDATES = [('grok', ['--version'])]

def probe():
    return probe_domain(DOMAIN_ID, CANDIDATES)
