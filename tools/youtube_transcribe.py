#!/usr/bin/env python3
"""Download a YouTube video's full audio and transcribe it with faster-whisper."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def timestamp(seconds: float, *, srt: bool = False) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1000)
    separator = "," if srt else "."
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}{separator}{millis:03d}"


def minute_label(seconds: float) -> str:
    total_minutes = max(0, int(seconds // 60))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def safe_video_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", value)
    if not cleaned:
        raise ValueError("The transcription request has no valid video_id.")
    return cleaned


def download_audio(url: str, video_id: str, temp_dir: Path) -> tuple[Path, dict[str, Any]]:
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(temp_dir / "%(id)s.%(ext)s")
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "--print",
        "after_move:filepath",
        "--output",
        output_template,
        url,
    ]
    print(f"Downloading complete audio for YouTube video {video_id}...", flush=True)
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, flush=True)
    candidates = [
        Path(line.strip())
        for line in completed.stdout.splitlines()
        if line.strip().lower().endswith(".mp3")
    ]
    audio_path = next((item for item in reversed(candidates) if item.is_file()), None)
    if audio_path is None:
        expected = temp_dir / f"{video_id}.mp3"
        audio_path = expected if expected.is_file() else None
    if audio_path is None or not audio_path.is_file() or audio_path.stat().st_size == 0:
        raise RuntimeError("yt-dlp completed without producing a non-empty MP3 audio file.")

    # Metadata is fetched separately so the selected file path is unambiguous.
    metadata_cmd = [
        sys.executable, "-m", "yt_dlp", "--no-playlist",
        "--skip-download", "--dump-single-json", url,
    ]
    metadata_run = subprocess.run(
        metadata_cmd, check=True, text=True, capture_output=True
    )
    metadata = json.loads(metadata_run.stdout)
    return audio_path, metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    request = json.loads(args.request.read_text(encoding="utf-8"))
    url = str(request.get("url", "")).strip()
    video_id = safe_video_id(str(request.get("video_id", "")))
    model_name = str(request.get("model", "large-v3-turbo"))
    language = request.get("language")
    language = str(language).strip() if language else None

    if not url.startswith(("https://www.youtube.com/", "https://youtu.be/", "https://youtube.com/")):
        raise ValueError("Only public YouTube video URLs are accepted by this workflow.")

    temp_dir = Path("transcription_tmp")
    audio_path, metadata = download_audio(url, video_id, temp_dir)

    from faster_whisper import WhisperModel

    print(f"Loading faster-whisper model: {model_name} (CPU / INT8)...", flush=True)
    model = WhisperModel(
        model_name,
        device="cpu",
        compute_type="int8",
        cpu_threads=2,
        num_workers=1,
    )
    print("Transcribing entire audio stream; this is not a summary or subtitle-only extraction.", flush=True)
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        best_of=5,
        temperature=0,
        condition_on_previous_text=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        word_timestamps=False,
    )

    segments: list[dict[str, Any]] = []
    for segment in segments_iter:
        text = (segment.text or "").strip()
        if not text:
            continue
        segments.append({
            "start": float(segment.start),
            "end": float(segment.end),
            "text": text,
        })
        if len(segments) % 50 == 0:
            print(f"Transcribed {len(segments)} segments; reached {timestamp(segment.end)}.", flush=True)

    if not segments:
        raise RuntimeError("The ASR engine returned no speech segments; refusing to publish an empty transcript.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    txt_path = args.output_dir / f"{video_id}.txt"
    srt_path = args.output_dir / f"{video_id}.srt"
    json_path = args.output_dir / f"{video_id}.json"

    title = str(metadata.get("title") or video_id)
    duration = float(metadata.get("duration") or segments[-1]["end"])
    generated_at = datetime.now(timezone.utc).isoformat()
    word_count = sum(len(re.findall(r"\S+", item["text"])) for item in segments)

    # Plain-text transcript grouped by minute, with exact segment timestamps.
    lines = [
        f"TITLE: {title}",
        f"YOUTUBE_URL: {url}",
        f"VIDEO_ID: {video_id}",
        f"DURATION: {timestamp(duration)}",
        f"LANGUAGE: {info.language or 'unknown'}",
        f"LANGUAGE_PROBABILITY: {info.language_probability:.4f}",
        f"ASR_MODEL: faster-whisper / {model_name}",
        f"SEGMENTS: {len(segments)}",
        f"WORDS: {word_count}",
        f"GENERATED_AT_UTC: {generated_at}",
        "",
        "FULL TRANSCRIPT (chronological; grouped by minute)",
        "=" * 72,
        "",
    ]
    current_minute: str | None = None
    for item in segments:
        label = minute_label(item["start"])
        if label != current_minute:
            current_minute = label
            lines.extend([f"[MINUTE {label}]", ""])
        lines.append(
            f"[{timestamp(item['start'])} --> {timestamp(item['end'])}] {item['text']}"
        )
    lines.append("")
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    srt_lines: list[str] = []
    for index, item in enumerate(segments, start=1):
        srt_lines.extend([
            str(index),
            f"{timestamp(item['start'], srt=True)} --> {timestamp(item['end'], srt=True)}",
            item["text"],
            "",
        ])
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    payload = {
        "video_id": video_id,
        "url": url,
        "title": title,
        "duration_seconds": duration,
        "language": info.language,
        "language_probability": info.language_probability,
        "model": f"faster-whisper/{model_name}",
        "generated_at_utc": generated_at,
        "segment_count": len(segments),
        "word_count": word_count,
        "segments": segments,
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"TRANSCRIPTION_COMPLETE video_id={video_id} "
        f"duration={timestamp(duration)} segments={len(segments)} words={word_count}",
        flush=True,
    )
    print(f"TXT: {txt_path} ({txt_path.stat().st_size} bytes)", flush=True)
    print(f"SRT: {srt_path} ({srt_path.stat().st_size} bytes)", flush=True)
    print(f"JSON: {json_path} ({json_path.stat().st_size} bytes)", flush=True)

    # Remove downloaded source audio after all transcript files have been written.
    audio_path.unlink(missing_ok=True)
    try:
        temp_dir.rmdir()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"External command failed ({exc.returncode}): {exc.cmd}", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        raise
    except Exception as exc:
        print(f"TRANSCRIPTION_FAILED: {exc}", file=sys.stderr)
        raise
