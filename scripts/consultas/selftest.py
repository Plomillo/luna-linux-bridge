#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess,tempfile,sys
root=pathlib.Path.cwd()
with tempfile.TemporaryDirectory() as td:
    td=pathlib.Path(td)
    src=td/"CONSULTA_ORIGINAL.md"
    src.write_text("¿Puede responder esta consulta?\n",encoding="utf-8")
    env=td/"envelope.json"
    res=td/"result.json"
    subprocess.run([sys.executable,str(root/"scripts/consultas/compile_consulta.py"),str(src),"--out",str(env)],check=True)
    e=json.loads(env.read_text())
    assert e["kind"]=="CONSULTA"
    assert e["execution_authorized"] is False and e["mutation_authorized"] is False
    assert e["source_sha256"]==hashlib.sha256(src.read_bytes()).hexdigest()
    subprocess.run([sys.executable,str(root/"scripts/consultas/process_consulta.py"),str(env),str(src),"--out",str(res)],check=True)
    r=json.loads(res.read_text())
    assert r["state"]=="HOLD"
    assert r["blocker"]=="CUSTOSZ_PROVIDER_NOT_BOUND"
    assert r["execution_authorized"] is False and r["mutation_authorized"] is False
print("CONSULTAS_SELFTEST=PASS")
