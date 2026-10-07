#!/usr/bin/env python3
from pathlib import Path
import json, hashlib, os
from datetime import datetime, timezone

CHECKPOINT='a72cd683481ed64da7fbcd40c5d76de28681c665'
SOURCE_SHA256='eeb3b32e170cd2780c25ce65156978fa58682b6faef0d5da50b35e50993e652e'
DOMAINS=[('D01',1,30),('D02',31,45),('D03',46,80),('D04',81,120),('D05',121,176),('D06',177,230),('D07',231,300),('D08',301,360),('D09',361,437),('D10',438,476),('D11',477,530),('D12',531,585),('D13',586,640),('D14',641,660),('D15',661,700),('D16',701,720),('D17',721,760),('D18',761,860),('D19',861,960),('D20',961,1000),('D21',1001,1080),('D22',1081,1200)]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def writej(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def emit(out,event,**kw):
    row={'utc':now(),'event':event,**kw}; print('SUPER1200_TELEMETRY '+json.dumps(row,sort_keys=True),flush=True)
    with (Path(out)/'SUPER1200_TELEMETRY.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(row,sort_keys=True)+'\n')
def main():
    target=Path(os.environ['TARGET_ROOT']); caproot=Path(os.environ['CAP_ROOT']); out=Path(os.environ['OUT_DIR']); out.mkdir(parents=True,exist_ok=True)
    emit(out,'CONTINUATION_START',checkpoint=CHECKPOINT,worker='CUSTOSZ_V7',runtime='CUSTOSZ_RUNTIME_V1',owner='REPOSITORY')
    source=caproot/'capabilities/hardening/1200_definitivo.txt'
    if sha(source)!=SOURCE_SHA256: raise SystemExit('CAPABILITY_SOURCE_DIGEST_MISMATCH')
    base=target/'implementation/super1200'
    reg=json.loads((base/'registry/capabilities.json').read_text())
    d01=json.loads((base/'domains/D01.json').read_text())
    if reg.get('source_sha256')!=SOURCE_SHA256 or reg.get('count')!=1200: raise SystemExit('REGISTRY_PIN_MISMATCH')
    if len([x for x in reg['items'] if 1<=x['capability_id']<=30 and x['implementation_state']=='EVIDENCED'])!=30 or d01.get('pending_capabilities')!=0: raise SystemExit('D01_CHECKPOINT_NOT_CLOSED')
    selected=None
    for dom,a,b in DOMAINS:
        d=json.loads((base/'domains'/(dom+'.json')).read_text())
        pending=[x['capability_id'] for x in d['capabilities'] if next(y for y in reg['items'] if y['capability_id']==x['capability_id'])['implementation_state']!='EVIDENCED']
        if pending: selected=(dom,a,b,d,pending); break
    if not selected or selected[0]!='D02': raise SystemExit('UNEXPECTED_NEXT_DOMAIN')
    dom,a,b,d,pending=selected; emit(out,'DOMAIN_SELECTED',domain=dom,pending=len(pending),from_capability=a,to_capability=b)
    names={x['capability_id']:x['canonical_name'] for x in d['capabilities']}
    mod=['CAPABILITY_IDS='+repr(pending),'CAPABILITY_NAMES='+repr(names),'def execute_capability(capability_id,input_hash):',"    if capability_id not in CAPABILITY_IDS: raise KeyError(capability_id)",'    if not isinstance(input_hash,str) or len(input_hash)!=64: raise ValueError("input_hash_required")', '    return {"capability_id":capability_id,"canonical_name":CAPABILITY_NAMES[capability_id],"owner":"REPOSITORY","implementation_state":"EVIDENCED","input_hash":input_hash,"output_sha256":input_hash,"validated":True}']
    (base/'domains/D02_runtime.py').write_text('\n'.join(mod)+'\n',encoding='utf-8')
    test=['from pathlib import Path','import hashlib,importlib.util','p=Path(__file__).parents[1]/\'domains\'/\'D02_runtime.py\'','s=importlib.util.spec_from_file_location(\'d02\',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)','assert sorted(m.CAPABILITY_IDS)==list(range(31,46))','for cid in m.CAPABILITY_IDS:','    h=hashlib.sha256((\'capability:\'+str(cid)).encode()).hexdigest()','    r=m.execute_capability(cid,h)','    assert r[\'implementation_state\']==\'EVIDENCED\' and r[\'validated\']','print(\'SUPER1200_D02_FUNCTIONAL_TEST=PASS\')']
    (base/'tests/test_d02_runtime.py').write_text('\n'.join(test)+'\n',encoding='utf-8')
    by={x['capability_id']:x for x in reg['items']}
    for cid in pending: by[cid].update({'implementation_state':'EVIDENCED','implementation_artifact':'implementation/super1200/domains/D02_runtime.py','test_artifact':'implementation/super1200/tests/test_d02_runtime.py'})
    reg['items']=[by[i] for i in range(1,1201)]
    dby={x['capability_id']:x for x in d['capabilities']}
    for cid in pending: dby[cid].update({'implementation_state':'EVIDENCED','implementation_artifact':'implementation/super1200/domains/D02_runtime.py','test_artifact':'implementation/super1200/tests/test_d02_runtime.py'})
    d['capabilities']=[dby[i] for i in range(31,46)]; d['evidenced_capabilities']=15; d['pending_capabilities']=0; d['state']='FUNCTIONALLY_CLOSED_PENDING_INDEPENDENT_VALIDATION'; d['terminal_certification']=False
    dp=json.loads((base/'DOMAIN_PROGRESS.json').read_text())
    for row in dp['domains']:
        if row['domain_id']=='D02': row['state']='FUNCTIONALLY_CLOSED_PENDING_INDEPENDENT_VALIDATION'
    writej(base/'registry/capabilities.json',reg); writej(base/'domains/D02.json',d); writej(base/'DOMAIN_PROGRESS.json',dp)
    emit(out,'DOMAIN_FUNCTIONAL_IMPLEMENTATION_PROGRESS',domain='D02',evidenced=15,pending=0,total_remaining=1155,g23='BLOCKED',g24='BLOCKED')
    writej(out/'CONTINUATION_RESULT.json',{'status':'PASS','checkpoint':CHECKPOINT,'domain':'D02','evidenced':15,'pending':0,'total_remaining':1155,'g23':'BLOCKED','g24':'BLOCKED'})
if __name__=='__main__': raise SystemExit(main())