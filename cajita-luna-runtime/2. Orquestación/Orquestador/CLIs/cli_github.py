from common import probe_domain

DOMAIN_ID = 'CLI_GITHUB'
CANDIDATES = [('gh', ['--version']), ('git', ['--version'])]

def probe():
    return probe_domain(DOMAIN_ID, CANDIDATES)
