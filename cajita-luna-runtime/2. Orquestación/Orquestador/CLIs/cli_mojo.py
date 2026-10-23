from common import probe_domain

DOMAIN_ID = 'CLI_MOJO'
CANDIDATES = [('mojo', ['--version'])]

def probe():
    return probe_domain(DOMAIN_ID, CANDIDATES)
