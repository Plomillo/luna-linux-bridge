#!/usr/bin/env python3
import json,pathlib,subprocess,sys,tempfile
root=pathlib.Path(__file__).parent
for n in ("RECOVERY_CONTRACT.json","STATE_MACHINE.json","PROVIDERS.json","MANIFEST.json"):
    json.load(open(root/n,encoding="utf-8"))
subprocess.run([sys.executable,str(root/"recovery.py"),"selftest"],check=True)
with tempfile.TemporaryDirectory() as td:
    subprocess.run([sys.executable,str(root/"recovery.py"),"checkpoint","--root",td],check=True)
    assert (pathlib.Path(td)/"checkpoint.json").is_file()
print("RECOVERY_NEGATIVE_TESTS=PASS")
