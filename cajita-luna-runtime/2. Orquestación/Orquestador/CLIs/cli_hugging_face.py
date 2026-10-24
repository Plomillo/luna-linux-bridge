from common import probe_domain
DOMAIN_ID="CLI_HUGGING_FACE"
# hf is the official CLI name; legacy huggingface-cli is not a substitute for hf.
CANDIDATES=[("hf",["--help"],True),("huggingface-cli",["--help"],False)]
def probe(): return probe_domain(DOMAIN_ID,CANDIDATES,True)
