#!/usr/bin/env python3
"""Rebuild a WhatsApp TXT export and transcribe audio attachments with faster-whisper."""

import argparse, hashlib, importlib.metadata, json, re, sys, tempfile, zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

AUDIO_EXTENSIONS = {".opus", ".ogg", ".mp3", ".m4a", ".wav", ".aac", ".flac", ".mp4"}
MESSAGE_RE = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4}),\s+(\d{1,2}:\d{2})\s*([ap])\.\s*m\.\s+-\s+(.*)$", re.I)
ATTACHMENT_RE = re.compile(r"([^\\/<>\s]+\.(?:opus|ogg|mp3|m4a|wav|aac|flac|mp4))", re.I)

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_chat(text):
    messages = []
    for line in text.replace("\u202f", " ").replace("\u00a0", " ").splitlines():
        m = MESSAGE_RE.match(line)
        if m:
            date_s, time_s, meridiem, body = m.groups()
            try:
                hour, minute = map(int, time_s.split(":"))
                if meridiem.lower() == "p" and hour != 12: hour += 12
                if meridiem.lower() == "a" and hour == 12: hour = 0
                day, month, year = map(int, date_s.split("/"))
                stamp = datetime(year, month, day, hour, minute)
            except ValueError:
                if messages: messages[-1]["body"] += "\n" + line
                continue
            sender, sep, content = body.partition(": ")
            if not sep: sender, content = "SYSTEM", body
            messages.append({"timestamp": stamp, "sender": sender.strip(), "body": content.strip()})
        elif messages:
            messages[-1]["body"] += "\n" + line
    return messages

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip", required=True, type=Path)
    ap.add_argument("--output", type=Path, default=Path(".local/whatsapp-analysis"))
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--language", default="es")
    ap.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    ap.add_argument("--compute-type", default="default")
    ap.add_argument("--beam-size", type=int, default=5)
    args = ap.parse_args()
    archive = args.zip.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not archive.is_file(): ap.error(f"ZIP inexistente: {archive}")
    output.mkdir(parents=True, exist_ok=True)
    audio_out = output / "audio_transcripts"
    audio_out.mkdir(exist_ok=True)

    with zipfile.ZipFile(archive) as zf:
        members = zf.infolist()
        txts = [m for m in members if m.filename.lower().endswith(".txt") and not m.is_dir()]
        if not txts: ap.error("El ZIP no contiene TXT de conversación.")
        chat_member = max(txts, key=lambda m: m.file_size)
        messages = parse_chat(zf.read(chat_member).decode("utf-8-sig", errors="replace"))
        audio_members = [m for m in members if not m.is_dir() and Path(m.filename).suffix.lower() in AUDIO_EXTENSIONS]
        results, audio_manifest = {}, []
        model = None
        if audio_members:
            from faster_whisper import WhisperModel
            if args.device == "auto":
                try: model = WhisperModel(args.model, device="cuda", compute_type=args.compute_type)
                except Exception: model = WhisperModel(args.model, device="cpu", compute_type="int8")
            else:
                model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
        with tempfile.TemporaryDirectory(prefix="wa-whisper-") as temp:
            for i, member in enumerate(audio_members, 1):
                filename = PurePosixPath(member.filename.replace("\\", "/")).name
                audio_path = Path(temp) / f"audio-{i:04d}{Path(filename).suffix.lower()}"
                try:
                    audio_path.write_bytes(zf.read(member))
                    segments, info = model.transcribe(str(audio_path), language=args.language or None,
                                                      beam_size=args.beam_size, vad_filter=True)
                    rows, text_parts = [], []
                    for seg in segments:
                        t = seg.text.strip()
                        text_parts.append(t)
                        rows.append({"start": round(seg.start, 3), "end": round(seg.end, 3), "text": t})
                    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).stem)[:80] or f"audio-{i:04d}"
                    txt_path, json_path = audio_out / f"{stem}.txt", audio_out / f"{stem}.json"
                    transcript = " ".join(text_parts).strip()
                    txt_path.write_text(transcript + "\n", encoding="utf-8")
                    json_path.write_text(json.dumps({"source_filename": filename, "model": args.model,
                        "language": info.language, "duration_seconds": info.duration, "segments": rows},
                        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    results[filename.lower()] = {"text": transcript, "file": f"audio_transcripts/{stem}.txt"}
                    audio_manifest.append({"filename": filename, "status": "completed",
                        "duration_seconds": round(info.duration, 3), "language": info.language,
                        "segments": len(rows), "transcript_sha256": sha256_file(txt_path)})
                except Exception as exc:
                    audio_manifest.append({"filename": filename, "status": "error",
                                           "error": f"{type(exc).__name__}: {exc}"})

    lines = ["# Conversación reconstruida", "",
             "> Reconstrucción automática. Las transcripciones Whisper requieren revisión humana.", ""]
    for msg in messages:
        body = msg["body"]
        match = ATTACHMENT_RE.search(body)
        if match and match.group(1).lower() in results:
            name = match.group(1)
            item = results[name.lower()]
            body += f"\n\n**Transcripción automática:** {item['text']}\n\nArchivo: {item['file']}"
        lines += [f"## {msg['timestamp']:%Y-%m-%d %H:%M} — {msg['sender']}", "", body, ""]
    (output / "conversation.md").write_text("\n".join(lines), encoding="utf-8")
    try: fw_version = importlib.metadata.version("faster-whisper")
    except importlib.metadata.PackageNotFoundError: fw_version = None
    manifest = {"source_archive": archive.name, "source_sha256": sha256_file(archive),
        "chat_member": chat_member.filename, "message_count": len(messages),
        "audio_count": len(audio_members), "model": args.model, "language_requested": args.language,
        "device": args.device, "compute_type": args.compute_type, "beam_size": args.beam_size,
        "faster_whisper_version": fw_version, "audio": audio_manifest,
        "privacy": "Keep source ZIP and generated output out of public Git repositories."}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Mensajes: {len(messages)} | audios: {len(audio_members)} | salida: {output}")
    return 1 if any(x["status"] == "error" for x in audio_manifest) else 0

if __name__ == "__main__":
    sys.exit(main())
