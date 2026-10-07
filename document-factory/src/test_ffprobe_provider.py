#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess,sys,tempfile,wave
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from media_validation import ffprobe_runtime_admission
r=ffprobe_runtime_admission(ROOT/"toolchain.lock.json",ROOT.parent)
assert r["status"]=="PASS", r
assert r["admitted"] is True
assert r["certification_state"]=="CANDIDATE_PENDING_FRESH_G23_G24"
lock=json.loads((ROOT/"toolchain.lock.json").read_text(encoding="utf-8"))
row=next(x for x in lock["providers"] if x.get("id")=="ffprobe")
nasm=((row.get("build") or {}).get("dependencies") or {}).get("nasm") or {}
assert nasm.get("version")=="3.02", nasm
assert nasm.get("official_commit_sha")=="4a56d66ed9626d5a3ded5414c9d8b7f1a48ce065", nasm
assert nasm.get("source_sha256"), nasm
assert nasm.get("binary_sha256"), nasm
prov=json.loads((ROOT/"providers/ffprobe/linux-amd64/PROVENANCE.json").read_text(encoding="utf-8"))
assert prov.get("status") in {"EVIDENCED_PENDING_SELFTEST","PASS"}, prov
assert prov["upstream"]["pgp_signature_verified"] is True
assert prov["upstream"]["source_sha256"]==row["sha256"]
assert prov["build_dependencies"]["nasm"]["source_sha256"]==nasm["source_sha256"]
assert prov["build_dependencies"]["nasm"]["binary_sha256"]==nasm["binary_sha256"]
ffprobe=ROOT.parent/pathlib.Path(row["binary_path"])
assert hashlib.sha256(ffprobe.read_bytes()).hexdigest()==row["binary_sha256"]
with tempfile.TemporaryDirectory() as td:
    wav=pathlib.Path(td)/"silence.wav"
    with wave.open(str(wav),"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b"\x00\x00"*8000)
    q=subprocess.run([str(ffprobe),"-v","error","-show_entries","stream=codec_type,sample_rate,channels","-show_entries","format=duration","-of","json",str(wav)],text=True,capture_output=True,timeout=10)
    assert q.returncode==0,(q.stdout,q.stderr)
    obj=json.loads(q.stdout)
    audio=next((x for x in obj.get("streams",[]) if x.get("codec_type")=="audio"),None)
    assert audio and int(audio["sample_rate"])==8000 and int(audio["channels"])==1,obj
    assert 0.9 <= float(obj["format"]["duration"]) <= 1.1,obj
print("FFPROBE_PROVIDER_ADMISSION_SELFTEST=PASS")
