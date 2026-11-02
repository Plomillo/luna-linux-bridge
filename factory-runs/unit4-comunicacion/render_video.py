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
def draw_diagram(d,n):
    ink=(224,238,242); muted=(153,181,197); teal=(91,192,190); blue=(72,123,166); panel=(19,39,62); accent=(238,180,91)
    d.rounded_rectangle((145,620,1775,805),radius=22,fill=panel,outline=(65,101,130),width=2)
    if n==1:
        d.line((260,760,1640,760),fill=muted,width=8)
        d.rounded_rectangle((550,660,1040,745),radius=12,fill=(32,66,91),outline=teal,width=4)
        d.rectangle((585,680,1005,725),fill=(9,24,43),outline=muted,width=2)
        d.line((795,745,795,760),fill=muted,width=9)
        d.rectangle((1180,685,1430,744),fill=(237,225,194),outline=accent,width=4)
        d.line((1180,714,1430,714),fill=(130,110,80),width=3)
        d.ellipse((1510,670,1640,800),outline=teal,width=9); d.line((1575,684,1575,735),fill=teal,width=7); d.line((1575,735,1610,750),fill=teal,width=7)
        d.text((300,672),"RITUAL",font=ImageFont.truetype(font_bold,26),fill=muted)
    elif n==2:
        labels=["CÁMARA","RELOJ","CHAT","SONIDO"]; xs=[360,760,1160,1560]
        for x,label in zip(xs,labels):
            d.ellipse((x-62,658,x+62,782),fill=(29,64,88),outline=teal,width=4)
            if label=="CÁMARA":
                d.rounded_rectangle((x-35,700,x+35,746),radius=8,outline=ink,width=5); d.ellipse((x-13,710,x+13,736),outline=teal,width=4)
            elif label=="RELOJ":
                d.ellipse((x-33,688,x+33,754),outline=ink,width=5); d.line((x,720,x,695),fill=accent,width=5); d.line((x,720,x+23,732),fill=accent,width=5)
            elif label=="CHAT":
                d.rounded_rectangle((x-38,690,x+38,746),radius=10,outline=ink,width=5); d.polygon([(x-15,746),(x-28,762),(x+2,746)],fill=ink)
            else:
                for k,h in enumerate([25,49,36,60,30]): d.rounded_rectangle((x-38+k*17,720-h//2,x-28+k*17,720+h//2),radius=4,fill=teal)
            d.text((x-65,772),label,font=ImageFont.truetype(font_bold,17),fill=muted)
    elif n==3:
        d.ellipse((760,637,980,817),outline=teal,width=10)
        d.line((870,660,870,725),fill=ink,width=9); d.line((870,725,930,760),fill=accent,width=9)
        d.text((390,685),"APOYO",font=ImageFont.truetype(font_bold,38),fill=teal)
        d.text((1170,685),"PRESIÓN",font=ImageFont.truetype(font_bold,38),fill=accent)
        d.line((600,720,745,720),fill=teal,width=7); d.polygon([(745,720),(720,705),(720,735)],fill=teal)
        d.line((1000,720,1145,720),fill=accent,width=7); d.polygon([(1145,720),(1120,705),(1120,735)],fill=accent)
        d.text((780,780),"MISMO SIGNO",font=ImageFont.truetype(font_regular,22),fill=muted)
    elif n==4:
        labels=["PERSONAL","INTERPERSONAL","MEDIAL","TRANSMEDIAL"]
        xs=[340,750,1160,1570]
        for i,(x,label) in enumerate(zip(xs,labels)):
            d.rounded_rectangle((x-145,670,x+145,760),radius=16,fill=(31,68,92),outline=teal if i%2==0 else blue,width=4)
            d.text((x-118,704),label,font=ImageFont.truetype(font_bold,21),fill=ink)
            if i<3:
                d.line((x+148,715,x+250,715),fill=accent,width=5); d.polygon([(x+250,715),(x+231,703),(x+231,727)],fill=accent)
    elif n in (5,6):
        nodes=[(340,710,"USUARIO"),(790,710,"CONTENIDO"),(1240,710,"SEÑALES")]
        for x,y,label in nodes:
            d.ellipse((x-82,y-55,x+82,y+55),fill=(31,68,92),outline=teal,width=4)
            d.text((x-68,y-10),label,font=ImageFont.truetype(font_bold,21),fill=ink)
        for x in (430,880):
            d.line((x,710,x+270,710),fill=accent,width=6); d.polygon([(x+270,710),(x+248,696),(x+248,724)],fill=accent)
        d.rounded_rectangle((1490,665,1695,755),radius=16,fill=(52,80,105),outline=accent,width=4)
        d.text((1525,697),"FEED",font=ImageFont.truetype(font_bold,30),fill=ink)
    elif n==7:
        d.text((280,650),"EVIDENCIA PUBLICADA",font=ImageFont.truetype(font_bold,26),fill=muted)
        bars=[(540,730,660,780,"30"),(800,680,920,780,"393"),(1060,645,1180,780,"164.611")]
        for x0,y0,x1,y1,label in bars:
            d.rounded_rectangle((x0,y0,x1,y1),radius=8,fill=blue,outline=teal,width=3)
            d.text((x0+15,y0-40),label,font=ImageFont.truetype(font_bold,26),fill=ink)
        d.text((1320,716),"muestras distintas",font=ImageFont.truetype(font_regular,24),fill=accent)
    elif n==8:
        d.rounded_rectangle((300,660,880,770),radius=18,fill=(28,72,83),outline=teal,width=4)
        d.rounded_rectangle((1040,660,1620,770),radius=18,fill=(83,61,43),outline=accent,width=4)
        d.text((415,700),"COMPAÑÍA  ·  ESTRUCTURA",font=ImageFont.truetype(font_bold,24),fill=ink)
        d.text((1110,700),"COMPARACIÓN  ·  PRESIÓN",font=ImageFont.truetype(font_bold,24),fill=ink)
    elif n==9:
        pts=[(520,710),(800,660),(800,765),(1110,660),(1110,765),(1420,710)]
        edges=[(0,1),(0,2),(1,3),(2,4),(3,5),(4,5),(1,2),(3,4)]
        for a,b in edges: d.line((*pts[a],*pts[b]),fill=blue,width=6)
        for x,y in pts: d.ellipse((x-26,y-26,x+26,y+26),fill=teal,outline=ink,width=3)
        d.text((1470,692),"SENTIDO",font=ImageFont.truetype(font_bold,24),fill=accent)
    else:
        for i,(x,label) in enumerate([(330,"TEORÍA"),(820,"ESTUDIOS"),(1310,"PLATAFORMA")]):
            d.rounded_rectangle((x,670,x+280,765),radius=16,fill=(31,68,92),outline=teal,width=3)
            d.text((x+35,705),label,font=ImageFont.truetype(font_bold,25),fill=ink)
        d.text((1650,710),"APA 7",font=ImageFont.truetype(font_bold,28),fill=accent)
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
    draw_diagram(d,i)
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
"visual_mode":"10 original scene-specific vector illustrations and explanatory diagrams, not stock footage",
"visible_author_year_citations":[x["citation"] for x in script["scenes"]],"voice_raw_seconds":raw_seconds,"voice_atempo":atempo,
"copyrighted_music_used":False}
(evidence/"video-render.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(record,ensure_ascii=False))
