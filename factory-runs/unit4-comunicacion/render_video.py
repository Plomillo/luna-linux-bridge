#!/usr/bin/env python3
from __future__ import annotations
import json,pathlib,subprocess,sys,wave
from PIL import Image,ImageDraw,ImageFont

workspace=pathlib.Path(sys.argv[1]).resolve()
script=json.loads((workspace/"data/video-script.json").read_text(encoding="utf-8"))
out=workspace/"build"; evidence=workspace/"evidence"; tmp=workspace/"runtime/video-work"
out.mkdir(parents=True,exist_ok=True); evidence.mkdir(parents=True,exist_ok=True); tmp.mkdir(parents=True,exist_ok=True)
W,H=1920,1080
font_regular="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font_bold="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
for p in (font_regular,font_bold):
    if not pathlib.Path(p).is_file(): raise SystemExit("FONT_NOT_FOUND:"+p)
def wrap(draw,text,font,max_width):
    words=str(text).split(); lines=[]; cur=""
    for word in words:
        test=(cur+" "+word).strip()
        if draw.textbbox((0,0),test,font=font)[2] <= max_width: cur=test
        else:
            if cur: lines.append(cur)
            cur=word
    if cur: lines.append(cur)
    return lines
def make_slide(i,scene):
    im=Image.new("RGB",(W,H)); px=im.load()
    top=(11,19,39); bottom=(28,42,68)
    for y in range(H):
        t=y/(H-1); c=tuple(int(top[k]*(1-t)+bottom[k]*t) for k in range(3))
        for x in range(W): px[x,y]=c
    d=ImageDraw.Draw(im)
    d.ellipse((1470,-260,2130,400),fill=(24,65,83))
    d.ellipse((1570,-160,2040,310),outline=(91,192,190),width=4)
    d.ellipse((-250,800,250,1300),fill=(25,54,72))
    d.rounded_rectangle((100,90,1820,990),radius=32,fill=(14,26,49),outline=(65,91,121),width=2)
    small=ImageFont.truetype(font_bold,24); titlef=ImageFont.truetype(font_bold,64)
    bodyf=ImageFont.truetype(font_regular,40); citef=ImageFont.truetype(font_regular,26); footf=ImageFont.truetype(font_regular,22)
    d.text((165,140),"PROYECTO INTEGRADOR  /  COMUNICACIÓN U4",font=small,fill=(91,192,190))
    d.text((165,200),f"ESCENA {i:02d} / {len(script['scenes']):02d}",font=footf,fill=(187,205,220))
    y=315
    for line in wrap(d,scene["title"],titlef,1500):
        d.text((165,y),line,font=titlef,fill=(245,247,250)); y+=84
    y+=38
    for line in wrap(d,scene["body"],bodyf,1470):
        d.text((170,y),line,font=bodyf,fill=(194,218,225)); y+=62
    d.rounded_rectangle((165,820,1750,905),radius=18,fill=(28,62,77))
    for line_idx,line in enumerate(wrap(d,scene["citation"],citef,1500)[:2]):
        d.text((195,835+line_idx*32),line,font=citef,fill=(117,224,210))
    d.text((165,940),"Diego Ignacio Norambuena Miranda  •  2026",font=footf,fill=(160,177,197))
    d.rounded_rectangle((165,970,1750,980),radius=5,fill=(59,79,106))
    d.rounded_rectangle((165,970,165+int(1585*i/len(script["scenes"])),980),radius=5,fill=(91,192,190))
    path=tmp/f"scene-{i:02d}.png"; im.save(path,optimize=True); return path

scene_paths=[make_slide(i,scene) for i,scene in enumerate(script["scenes"],1)]
wav_paths=[]
for i,scene in enumerate(script["scenes"],1):
    wav_path=tmp/f"voice-{i:02d}.wav"
    subprocess.run(["espeak-ng","-v","es","-s","150","-a","170","-w",str(wav_path),scene["narration"]],check=True)
    wav_paths.append(wav_path)
with wave.open(str(wav_paths[0]),"rb") as first: params=first.getparams()
if params.nchannels not in (1,2) or params.sampwidth not in (1,2,3,4): raise SystemExit("UNSUPPORTED_TTS_WAVE_FORMAT")
raw_wav=tmp/"voice-raw.wav"
with wave.open(str(raw_wav),"wb") as dst:
    dst.setparams(params)
    for wav_path in wav_paths:
        with wave.open(str(wav_path),"rb") as src:
            p=src.getparams()
            if (p.nchannels,p.sampwidth,p.framerate,p.comptype,p.compname)!=(params.nchannels,params.sampwidth,params.framerate,params.comptype,params.compname):
                raise SystemExit("TTS_WAVE_PARAMETERS_CHANGED")
            dst.writeframes(src.readframes(src.getnframes()))
        dst.writeframes(b"\x00"*(int(params.framerate*0.45)*params.nchannels*params.sampwidth))
raw_seconds=raw_wav.stat().st_size/(params.framerate*params.nchannels*params.sampwidth)
target_voice_seconds=296.0; atempo=raw_seconds/target_voice_seconds
if not (0.5<=atempo<=2.0): raise SystemExit(f"NARRATION_DURATION_OUT_OF_BOUNDS:{raw_seconds:.2f}:{atempo:.3f}")
voice_wav=tmp/"voice-fit.wav"
subprocess.run(["ffmpeg","-y","-i",str(raw_wav),"-filter:a",f"atempo={atempo:.8f}","-t",str(target_voice_seconds),"-ar","48000","-ac","2","-c:a","pcm_s16le",str(voice_wav)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
audio_m4a=tmp/"audio-design.m4a"
subprocess.run(["ffmpeg","-y","-f","lavfi","-i","anoisesrc=color=pink:sample_rate=48000:duration=300:amplitude=0.008","-i",str(voice_wav),
"-filter_complex","[0:a]lowpass=f=850,volume=0.11[amb];[1:a]volume=1.0[voice];[amb][voice]amix=inputs=2:duration=longest:weights='0.12 1.0'[mix]",
"-map","[mix]","-t","300","-c:a","aac","-b:a","160k",str(audio_m4a)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
concat=tmp/"scenes.txt"
with concat.open("w",encoding="utf-8") as f:
    for p in scene_paths: f.write(f"file '{p.as_posix()}'\nduration 30.0\n")
    f.write(f"file '{scene_paths[-1].as_posix()}'\n")
mp4=out/"communication_u4.mp4"
subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-i",str(audio_m4a),
"-map","0:v:0","-map","1:a:0","-t","300","-r","30","-frames:v","9000","-vf","scale=1920:1080,format=yuv420p",
"-c:v","libx264","-preset","medium","-crf","24","-c:a","aac","-b:a","160k","-movflags","+faststart",str(mp4)],
check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-show_entries","stream=codec_type,width,height","-of","json",str(mp4)],capture_output=True,text=True,check=True)
meta=json.loads(probe.stdout); duration=float(meta["format"]["duration"]); streams=meta.get("streams",[])
if not any(x.get("codec_type")=="audio" for x in streams): raise SystemExit("VIDEO_AUDIO_TRACK_MISSING")
v=next(x for x in streams if x.get("codec_type")=="video")
if abs(duration-300)>1 or int(v["width"])!=1920 or int(v["height"])!=1080: raise SystemExit(f"VIDEO_TECHNICAL_CHECK_FAIL:{duration}:{v}")
record={"schema":"COMMUNICATION_U4_VIDEO_RENDER/1.0","status":"PASS","file":mp4.name,"size_bytes":mp4.stat().st_size,
"duration_seconds":duration,"width":int(v["width"]),"height":int(v["height"]),"fps":30,
"audio":"Spanish eSpeak NG narration + generated low-level ambient sound","scene_count":len(scene_paths),
"visible_author_year_citations":[x["citation"] for x in script["scenes"]],"voice_raw_seconds":raw_seconds,"voice_atempo":atempo,
"copyrighted_music_used":False}
(evidence/"video-render.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(record,ensure_ascii=False))
