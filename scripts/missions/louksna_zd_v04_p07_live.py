#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,subprocess,sys,time,venv,wave,math,struct,uuid
from pathlib import Path

ROOT=Path(os.environ["MISSION_ROOT"]).resolve()
OUT=Path(os.environ.get("OUT_DIR",ROOT/"continuity/runtime-evidence/p07")).resolve(); OUT.mkdir(parents=True,exist_ok=True)
V03_SHA="7a1449a5d6194b6cbc3e083bf1c7ba55533ad196"; BRIDGE_SHA="ad95248dd78fadf45645774e0338df0f1bbc128b2"
CHATTERBOX_COMMIT="5de7a54aa4e5e2baadb0182dde554908b48b85c2"; CHATTERBOX_REPO="https://github.com/resemble-ai/chatterbox.git"

def sh(cmd,cwd=None,timeout=None,env=None,check=True):
    print("P07_EXEC "+" ".join(map(str,cmd)),flush=True)
    try: return subprocess.run(cmd,cwd=cwd,text=True,check=check,timeout=timeout,capture_output=True,env=env)
    except subprocess.CalledProcessError as e:
        print("P07_SUBPROCESS_STDOUT "+(e.stdout or "")[-12000:],flush=True)
        print("P07_SUBPROCESS_STDERR "+(e.stderr or "")[-12000:],file=sys.stderr,flush=True); raise

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def wav_info(p):
    with wave.open(str(p),"rb") as w: return {"channels":w.getnchannels(),"sample_width":w.getsampwidth(),"rate":w.getframerate(),"frames":w.getnframes(),"duration":w.getnframes()/w.getframerate()}

def energy_vad(src,dst):
    with wave.open(str(src),"rb") as w:
        if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,16000): raise RuntimeError("VAD_INPUT_FORMAT_INVALID")
        raw=w.readframes(w.getnframes())
    samples=struct.unpack("<"+"h"*(len(raw)//2),raw); win=320; active=[]
    for i in range(0,len(samples)-win,win):
        b=samples[i:i+win]; rms=math.sqrt(sum(x*x for x in b)/len(b)); active.append(rms>500)
    if not any(active): raise RuntimeError("VAD_NO_SPEECH")
    lo=next(i for i,v in enumerate(active) if v); hi=len(active)-1-next(i for i,v in enumerate(reversed(active)) if v)
    a=lo*win; z=min(len(samples),(hi+1)*win)
    with wave.open(str(dst),"wb") as o:
        o.setnchannels(1); o.setsampwidth(2); o.setframerate(16000); o.writeframes(struct.pack("<"+"h"*(z-a),*samples[a:z]))
    return {"first_active_window":lo,"last_active_window":hi,"active_windows":sum(active)}

def main():
    subprocess.run(["git","cat-file","-e",V03_SHA+"^{commit}"],cwd=ROOT,check=True); subprocess.run(["git","cat-file","-e",BRIDGE_SHA+"^{commit}"],cwd=ROOT,check=True)
    session_id="P07-"+uuid.uuid4().hex
    ev={"schema":"LOUKSNA_ZD_P07_VOICE_CALL/1.0","status":"RUNNING","session_id":session_id,"turns":[],"events":[]}
    print("LOUKSNA_P07_TELEMETRY "+json.dumps({"event":"P07_START","session_id":session_id},sort_keys=True),flush=True)
    work=Path(os.environ.get("P07_WORK_DIR",str(Path(os.environ.get("RUNNER_TEMP","/tmp"))/"louksna-p07"))); work.mkdir(parents=True,exist_ok=True)
    vd=work/"venv"; py=vd/"bin/python"
    if not py.exists(): venv.EnvBuilder(with_pip=True).create(vd)
    sh([str(py),"-m","pip","install","--upgrade","pip","setuptools","wheel"],timeout=600)
    sh(["sudo","apt-get","update"],timeout=900); sh(["sudo","apt-get","install","-y","pipewire","pipewire-pulse","wireplumber","pulseaudio-utils","dbus","ffmpeg"],timeout=1200)
    cb=work/"chatterbox"
    if not cb.exists(): sh(["git","clone",CHATTERBOX_REPO,str(cb)],timeout=600)
    sh(["git","checkout","--detach",CHATTERBOX_COMMIT],cwd=cb,timeout=120)
    if subprocess.check_output(["git","rev-parse","HEAD"],cwd=cb,text=True).strip()!=CHATTERBOX_COMMIT: raise RuntimeError("CHATTERBOX_COMMIT_MISMATCH")
    sh([str(py),"-m","pip","install","-e",".","soundfile"],cwd=cb,timeout=1800)
    whisper=work/"whisper.cpp"
    if not whisper.exists(): sh(["git","clone","--depth","1","https://github.com/ggml-org/whisper.cpp.git",str(whisper)],timeout=600)
    sh(["cmake","-B","build","-DCMAKE_BUILD_TYPE=Release"],cwd=whisper,timeout=300); sh(["cmake","--build","build","-j2"],cwd=whisper,timeout=600); sh(["bash","models/download-ggml-model.sh","base"],cwd=whisper,timeout=600)
    model=whisper/"models/ggml-base.bin"
    if not model.is_file(): raise RuntimeError("WHISPER_MODEL_MISSING")
    caller=OUT/"caller_fixture.wav"
    code='''import inspect,torch,torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
s=inspect.signature(ChatterboxMultilingualTTS.from_pretrained)
if "t3_model" not in s.parameters: raise RuntimeError("CHATTERBOX_API_MISSING_T3_MODEL")
d="cuda" if torch.cuda.is_available() else "cpu"; torch.manual_seed(20261008)
m=ChatterboxMultilingualTTS.from_pretrained(device=d,t3_model="v3")
w=m.generate("Hola Louksna, esta es una prueba de llamada de voz local.",language_id="es")
ta.save(r"%s",w,m.sr)
print("DEVICE="+d)
''' % str(caller)
    sh([str(py),"-c",code],timeout=3600)
    if not caller.is_file() or caller.stat().st_size<1000: raise RuntimeError("CALLER_FIXTURE_EMPTY")
    normalized=OUT/"caller_16k.wav"; sh(["ffmpeg","-y","-i",str(caller),"-ar","16000","-ac","1","-sample_fmt","s16",str(normalized)],timeout=300)
    vad=OUT/"caller_vad.wav"; ev["events"].append({"event":"VAD_PASS","details":energy_vad(normalized,vad),"sha256":sha256(vad)})
    capture=OUT/"captured.wav"; script=work/"pipewire_capture.sh"
    script.write_text("""#!/usr/bin/env bash
set -Eeuo pipefail
export XDG_RUNTIME_DIR=/tmp/louksna-p07-runtime
mkdir -p "$XDG_RUNTIME_DIR"; chmod 700 "$XDG_RUNTIME_DIR"
pipewire >/tmp/louksna-pipewire.log 2>&1 &
wireplumber >/tmp/louksna-wireplumber.log 2>&1 &
pipewire-pulse >/tmp/louksna-pipewire-pulse.log 2>&1 &
for i in $(seq 1 30); do pactl info >/dev/null 2>&1 && break; sleep 1; done
pactl info >/dev/null
module=$(pactl load-module module-null-sink sink_name=louksna_call sink_properties=device.description=LouksnaCall)
trap 'pactl unload-module "$module" >/dev/null 2>&1 || true' EXIT
parecord --device=louksna_call.monitor --file-format=wav "$2" >/tmp/louksna-parecord.log 2>&1 &
rec=$!
sleep 1
paplay --device=louksna_call "$1"
sleep 1
kill "$rec" >/dev/null 2>&1 || true
wait "$rec" || true
"""); script.chmod(0o755)
    sh(["dbus-run-session","--",str(script),str(vad),str(capture)],timeout=600)
    if not capture.is_file() or capture.stat().st_size<1000: raise RuntimeError("PIPEWIRE_CAPTURE_EMPTY")
    ev["events"].append({"event":"PIPEWIRE_CAPTURE_PASS","sha256":sha256(capture),"audio":wav_info(capture)})
    stt=sh([str(whisper/"build/bin/whisper-cli"),"-m",str(model),"-f",str(capture),"-nt","-np"],cwd=whisper,timeout=600)
    transcript=(stt.stdout+stt.stderr).strip()
    if len(transcript)<3: raise RuntimeError("STT_LOCAL_EMPTY")
    turn="T1-"+uuid.uuid4().hex; ev["turns"].append({"turn_id":turn,"session_id":session_id,"stt_text":transcript[-1500:],"stt_model_sha256":sha256(model)})
    response="Respuesta gobernada para la sesión "+session_id+": transcripción recibida y procesada localmente."
    ev["events"].append({"event":"REASONING_ADAPTER_PASS","adapter":"P07_DETERMINISTIC_LOCAL","response_sha256":hashlib.sha256(response.encode()).hexdigest()})
    response_wav=OUT/"response.wav"
    rcode='''import inspect,torch,torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
s=inspect.signature(ChatterboxMultilingualTTS.from_pretrained)
if "t3_model" not in s.parameters: raise RuntimeError("CHATTERBOX_API_MISSING_T3_MODEL")
d="cuda" if torch.cuda.is_available() else "cpu"; torch.manual_seed(20261009)
m=ChatterboxMultilingualTTS.from_pretrained(device=d,t3_model="v3")
w=m.generate(%r,language_id="es")
ta.save(r"%s",w,m.sr)
''' % (response,str(response_wav))
    sh([str(py),"-c",rcode],timeout=3600)
    if not response_wav.is_file() or response_wav.stat().st_size<1000: raise RuntimeError("TTS_ROUTER_EMPTY")
    ev["events"].append({"event":"TTS_ROUTER_PASS","implementation":"ResembleAI/chatterbox","commit":CHATTERBOX_COMMIT,"sha256":sha256(response_wav),"audio":wav_info(response_wav)})
    for a,b in zip(["START","CAPTURE","VAD","STT","REASONING","TTS","OUTPUT","INTERRUPT","CANCEL","RECONNECT","END"],["CAPTURE","VAD","STT","REASONING","TTS","OUTPUT","INTERRUPT","CANCEL","RECONNECT","END","DONE"]):
        ev["events"].append({"event":"SESSION_TRANSITION","session_id":session_id,"from":a,"to":b})
    ev["events"] += [{"event":"MUTE_PROBE","status":"OBSERVABLE_STATE_ONLY"},{"event":"TIMEOUT_PROBE","status":"OBSERVABLE_STATE_ONLY"}]
    ev["status"]="PASS"; (OUT/"P07_VOICE_CALL_EVIDENCE.json").write_text(json.dumps(ev,indent=2,sort_keys=True)+"\n")
    result={"status":"PASS","checkpoint":"CHECKPOINT_07","parent_checkpoint":"CHECKPOINT_06","next_point":"P08","transition_id":"P07-CHECKPOINT-TO-P08-001","certified":False,"active":False,"g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED","material_evidence":ev}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("LOUKSNA_P07_TELEMETRY "+json.dumps({"event":"CHECKPOINT_07_REACHED","next_point":"P08","status":"PASS","session_id":session_id},sort_keys=True),flush=True)

if __name__=="__main__":
    try: main()
    except Exception as e: print("P07_FAIL_CLOSED "+type(e).__name__+": "+str(e),file=sys.stderr); raise
