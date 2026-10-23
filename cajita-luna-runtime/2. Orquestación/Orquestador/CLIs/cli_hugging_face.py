from common import probe_domain

DOMAIN_ID = 'CLI_HUGGING_FACE'
CANDIDATES = [('hf', ['--version']), ('huggingface-cli', ['--version'])]

def probe():
    return probe_domain(DOMAIN_ID, CANDIDATES)
