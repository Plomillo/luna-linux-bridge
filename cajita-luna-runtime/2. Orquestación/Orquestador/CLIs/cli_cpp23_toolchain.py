from common import probe_domain

DOMAIN_ID = 'CLI_CPP23_TOOLCHAIN'
CANDIDATES = [('g++', ['--version']), ('clang++', ['--version']), ('cmake', ['--version']), ('ninja', ['--version'])]

def probe():
    return probe_domain(DOMAIN_ID, CANDIDATES)
