#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,shutil,subprocess,threading,time,zipfile
from datetime import datetime,timezone
from xml.sax.saxutils import escape

def utc():
    return datetime.now(timezone.utc).isoformat()

def sha256_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path)->str:
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(path,obj):
    p=pathlib.Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def append_audit(root,event):
    root=pathlib.Path(root)
    p=root/"evidence"/"audit.jsonl"
    p.parent.mkdir(parents=True,exist_ok=True)
    prev="0"*64
    if p.exists():
        lines=[x for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        if lines:
            prev=json.loads(lines[-1])["current_event_hash"]
    row=dict(event)
    row["recorded_at_utc"]=utc()
    row["previous_event_hash"]=prev
    canonical=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    row["current_event_hash"]=sha256_bytes(canonical)
    with p.open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")
    return row["current_event_hash"]

class Heartbeat:
    def __init__(self,root,stage,interval_seconds=1):
        if interval_seconds!=1:
            raise ValueError("HEARTBEAT_INTERVAL_MUST_BE_ONE_SECOND")
        self.root=pathlib.Path(root)
        self.stage=stage
        self.stop=threading.Event()
        self.thread=None

    def _loop(self):
        seq=0
        while not self.stop.wait(1):
            seq+=1
            write_json(self.root/"runtime"/"heartbeat.json",{
                "stage":self.stage,"sequence":seq,"status":"RUNNING","observed_at_utc":utc()
            })

    def __enter__(self):
        write_json(self.root/"runtime"/"heartbeat.json",{
            "stage":self.stage,"sequence":0,"status":"STARTING","observed_at_utc":utc()
        })
        self.thread=threading.Thread(target=self._loop,daemon=True)
        self.thread.start()
        return self

    def __exit__(self,*_):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)
        write_json(self.root/"runtime"/"heartbeat.json",{
            "stage":self.stage,"status":"STOPPED","observed_at_utc":utc()
        })

def checkpoint(root):
    root=pathlib.Path(root)
    rows=[]
    for base in ("source","data"):
        p=root/base
        if not p.exists():
            continue
        for f in sorted(x for x in p.rglob("*") if x.is_file()):
            rows.append({
                "path":f.relative_to(root).as_posix(),
                "sha256":sha256_file(f),
                "size_bytes":f.stat().st_size
            })
    digest=sha256_bytes(json.dumps(rows,sort_keys=True,separators=(",",":")).encode())
    snapshot=root/"runtime"/"checkpoints"/digest/"snapshot"
    if snapshot.exists():
        shutil.rmtree(snapshot)
    for base in ("source","data"):
        p=root/base
        if p.exists():
            shutil.copytree(p,snapshot/base,dirs_exist_ok=True)
    obj={
        "schema":"DOCUMENT_FACTORY_CHECKPOINT/2.0",
        "created_at_utc":utc(),
        "files":rows,
        "checkpoint_digest_sha256":digest,
        "snapshot_path":snapshot.relative_to(root).as_posix()
    }
    write_json(root/"runtime"/"checkpoint.json",obj)
    write_json(root/"runtime"/"checkpoints"/digest/"checkpoint.json",obj)
    append_audit(root,{"event_type":"CHECKPOINT","checkpoint_digest_sha256":digest})
    return obj

def restore_checkpoint(root,checkpoint_digest):
    root=pathlib.Path(root)
    cp_path=root/"runtime"/"checkpoints"/checkpoint_digest/"checkpoint.json"
    if not cp_path.is_file():
        raise ValueError("CHECKPOINT_NOT_FOUND")
    cp=json.loads(cp_path.read_text(encoding="utf-8"))
    snapshot=root/cp["snapshot_path"]
    if not snapshot.is_dir():
        raise ValueError("CHECKPOINT_SNAPSHOT_MISSING")
    for base in ("source","data"):
        target=root/base
        if target.exists():
            shutil.rmtree(target)
        source=snapshot/base
        if source.exists():
            shutil.copytree(source,target)
    failures=[]
    for row in cp["files"]:
        p=root/row["path"]
        if not p.is_file() or sha256_file(p)!=row["sha256"]:
            failures.append(row["path"])
    if failures:
        raise ValueError("RESTORATION_VERIFY_FAIL:"+",".join(failures))
    append_audit(root,{"event_type":"ROLLBACK_RESTORE","checkpoint_digest_sha256":checkpoint_digest,"status":"PASS"})
    return {
        "schema":"DOCUMENT_FACTORY_ROLLBACK_PROOF/1.0",
        "status":"PASS",
        "checkpoint_digest_sha256":checkpoint_digest,
        "verified_files":len(cp["files"]),
        "restored_at_utc":utc()
    }

def hold(root,stage,reason,detail=None):
    obj={
        "schema":"DOCUMENT_FACTORY_HOLD/1.0",
        "state":"HOLD",
        "stage":stage,
        "reason":reason,
        "detail":detail,
        "blind_retry":False,
        "next_authorized_action":"ACQUIRE_NEW_CAUSAL_EVIDENCE_OR_USE_PINNED_EQUIVALENT_PROVIDER",
        "resume_from":"LAST_VERIFIED_CHECKPOINT",
        "observed_at_utc":utc()
    }
    write_json(pathlib.Path(root)/"runtime"/"hold.json",obj)
    append_audit(root,{"event_type":"HOLD","stage":stage,"reason":reason,"detail":detail})
    return obj

def run_stage(root,stage,cmd,timeout_seconds):
    root=pathlib.Path(root)
    logs=root/"evidence"/"logs"
    logs.mkdir(parents=True,exist_ok=True)
    append_audit(root,{"event_type":"STAGE_START","stage":stage,"command":cmd,"timeout_seconds":timeout_seconds})
    try:
        with Heartbeat(root,stage,1):
            p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout_seconds,check=False)
    except subprocess.TimeoutExpired as e:
        (logs/(stage+".stdout.txt")).write_text(e.stdout or "",encoding="utf-8")
        (logs/(stage+".stderr.txt")).write_text(e.stderr or "",encoding="utf-8")
        hold(root,stage,"TIMEOUT",{"timeout_seconds":timeout_seconds})
        raise RuntimeError("STAGE_TIMEOUT:"+stage)
    (logs/(stage+".stdout.txt")).write_text(p.stdout,encoding="utf-8")
    (logs/(stage+".stderr.txt")).write_text(p.stderr,encoding="utf-8")
    append_audit(root,{"event_type":"STAGE_END","stage":stage,"exit_code":p.returncode})
    if p.returncode!=0:
        hold(root,stage,"NONZERO_EXIT",{"exit_code":p.returncode})
        raise RuntimeError("STAGE_FAILED:"+stage)
    return p

def _column(n):
    s=""
    while n:
        n,rem=divmod(n-1,26)
        s=chr(65+rem)+s
    return s

def _sheet_xml(rows):
    out=['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
    for ri,row in enumerate(rows,1):
        out.append(f'<row r="{ri}">')
        for ci,val in enumerate(row,1):
            ref=f"{_column(ci)}{ri}"
            if isinstance(val,(int,float)) and not isinstance(val,bool):
                out.append(f'<c r="{ref}"><v>{val}</v></c>')
            else:
                text="TRUE" if val is True else "FALSE" if val is False else str(val)
                out.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(text)}</t></is></c>')
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)

def write_xlsx(path,spec):
    sheets=spec.get("sheets") or []
    if not sheets:
        raise ValueError("XLSX_REQUIRES_SHEETS")
    p=pathlib.Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    types=['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
           '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
           '<Default Extension="xml" ContentType="application/xml"/>',
           '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>']
    for i in range(1,len(sheets)+1):
        types.append(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
    types.append("</Types>")
    rels='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    wb=['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
    wbr=['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    for i,sheet in enumerate(sheets,1):
        wb.append(f'<sheet name="{escape(str(sheet["name"]))}" sheetId="{i}" r:id="rId{i}"/>')
        wbr.append(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>')
    wb.append("</sheets></workbook>")
    wbr.append("</Relationships>")
    with zipfile.ZipFile(p,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml","".join(types))
        z.writestr("_rels/.rels",rels)
        z.writestr("xl/workbook.xml","".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels","".join(wbr))
        for i,sheet in enumerate(sheets,1):
            z.writestr(f"xl/worksheets/sheet{i}.xml",_sheet_xml(sheet.get("rows") or []))

def verify_ooxml(path,kind):
    required={
      "docx":["[Content_Types].xml","word/document.xml"],
      "pptx":["[Content_Types].xml","ppt/presentation.xml"],
      "xlsx":["[Content_Types].xml","xl/workbook.xml"]
    }[kind]
    with zipfile.ZipFile(path) as z:
        bad=z.testzip()
        if bad:
            raise ValueError("CORRUPT_ZIP:"+bad)
        names=set(z.namelist())
        missing=[x for x in required if x not in names]
        if missing:
            raise ValueError("MISSING_OOXML_PARTS:"+",".join(missing))
    return True
