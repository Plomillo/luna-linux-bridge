import hashlib,importlib.util
p='/home/runner/work/luna-linux-bridge/luna-linux-bridge/implementation/super1200/domains/D03_runtime.py'
s=importlib.util.spec_from_file_location('domain_runtime',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
assert sorted(m.CAPABILITY_IDS)==list(range(46,81))
for cid in m.CAPABILITY_IDS:
    h=hashlib.sha256(('capability:'+str(cid)).encode()).hexdigest()
    r=m.execute_capability(cid,h); assert r['implementation_state']=='EVIDENCED' and r['validated'] is True
print('SUPER1200_D03_FUNCTIONAL_TEST=PASS')
