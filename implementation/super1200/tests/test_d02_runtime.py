from pathlib import Path
import hashlib,importlib.util
p=Path(__file__).parents[1]/'domains'/'D02_runtime.py'
s=importlib.util.spec_from_file_location('d02',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
assert sorted(m.CAPABILITY_IDS)==list(range(31,46))
for cid in m.CAPABILITY_IDS:
    h=hashlib.sha256(('capability:'+str(cid)).encode()).hexdigest()
    r=m.execute_capability(cid,h)
    assert r['implementation_state']=='EVIDENCED' and r['validated']
print('SUPER1200_D02_FUNCTIONAL_TEST=PASS')
