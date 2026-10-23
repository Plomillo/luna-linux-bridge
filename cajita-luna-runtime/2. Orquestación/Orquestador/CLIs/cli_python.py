from common import probe_domain

DOMAIN_ID = 'CLI_PYTHON'
CANDIDATES = [('python3', ['--version']), ('python', ['--version']), ('pip3', ['--version'])]

def probe():
    return probe_domain(DOMAIN_ID, CANDIDATES)
