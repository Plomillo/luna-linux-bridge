from __future__ import annotations
import json,pathlib,re,subprocess,sys
from docx import Document
root=pathlib.Path(sys.argv[1]); profile=json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
docx=root/"build/report.docx"; pdf=root/"build/report.pdf"; mp4=root/"build/communication_u4.mp4"; md=root/"source/report.md"
assert docx.is_file() and pdf.is_file() and mp4.is_file()
assert pdf.stat().st_size<=int(profile["constraints"]["pdf_max_bytes"]),f"PDF_TOO_LARGE:{pdf.stat().st_size}"
info=subprocess.run(["pdfinfo",str(pdf)],capture_output=True,text=True,check=True).stdout
m=re.search(r"^Pages:\s+(\d+)\s*$",info,re.M); assert m,"PDF_PAGE_COUNT_UNREADABLE"
pages=int(m.group(1)); assert 2<=pages<=5,f"PAGE_COUNT_OUT_OF_RANGE:{pages}"
text=subprocess.run(["pdftotext","-layout",str(pdf),"-"],capture_output=True,text=True,check=True).stdout
flat=" ".join(text.casefold().split())
for required in profile["constraints"]["required_sections"]:
    assert required.casefold() in flat,"MISSING_SECTION:"+required
raw=md.read_text(encoding="utf-8")
for marker in profile["constraints"]["required_sections"]:
    assert marker in raw,"SOURCE_SECTION_MISSING:"+marker
abstract=re.search(r"### II\. Resumen \(abstract\)\s*(.*?)\s*### III\.",raw,re.S)
assert abstract,"ABSTRACT_MISSING"
abstract_words=re.findall(r"\b[\wÀ-ÿ'-]+\b",abstract.group(1),re.UNICODE)
assert len(abstract_words)<=250,f"ABSTRACT_OVER_250:{len(abstract_words)}"
assert "Declaración de uso de IA" in raw and "GPT-6" in raw
d=Document(str(docx)); sec=d.sections[0]
for value in [sec.top_margin,sec.bottom_margin,sec.left_margin,sec.right_margin]:
    assert abs(value.inches*2.54-2.5)<0.03,"MARGIN_FAIL"
assert d.styles["Normal"].font.name=="Arial" and abs(d.styles["Normal"].font.size.pt-12)<0.01
script=json.loads((root/"data/video-script.json").read_text(encoding="utf-8"))
assert len(script["scenes"])>=8
for scene in script["scenes"]:
    assert scene.get("narration") and scene.get("citation"),"VIDEO_SCENE_MISSING_NARRATION_OR_CITATION"
probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-show_entries","stream=codec_type,width,height","-of","json",str(mp4)],capture_output=True,text=True,check=True)
meta=json.loads(probe.stdout); duration=float(meta["format"]["duration"])
assert abs(duration-300.0)<=1.0,f"VIDEO_DURATION_NOT_300:{duration}"
streams=meta.get("streams",[])
video=next((x for x in streams if x.get("codec_type")=="video"),None)
audio=next((x for x in streams if x.get("codec_type")=="audio"),None)
assert video and int(video.get("width",0))>=1280 and int(video.get("height",0))>=720
assert audio,"VIDEO_AUDIO_TRACK_MISSING"
result={"schema":"COMUNICACION_U4_DELIVERABLE_VERIFICATION/1.0","status":"PASS",
"pdf_pages":pages,"pdf_bytes":pdf.stat().st_size,"abstract_words":len(abstract_words),
"required_sections":10,"video_seconds":duration,"video_resolution":f'{video["width"]}x{video["height"]}',
"video_audio":True,"video_bytes":mp4.stat().st_size,"scenes":len(script["scenes"]),
"visible_citations_in_scene_design":True,"rubric_total":profile["rubric"]["declared_total_points"],
"g23":"NOT_EXECUTED","g24":"NOT_EXECUTED"}
(root/"evidence").mkdir(exist_ok=True)
(root/"evidence/document-verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
