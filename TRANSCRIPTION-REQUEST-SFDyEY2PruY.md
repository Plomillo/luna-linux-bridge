# Transcription request: SFDyEY2PruY

- Source: https://youtu.be/SFDyEY2PruY
- Request file: `.github/transcription-request.json`
- Runner: GitHub Actions, Ubuntu 24.04
- Downloader: yt-dlp with Deno JavaScript challenge solver
- ASR: faster-whisper, `large-v3-turbo`, CPU INT8
- Language: automatic detection
- Outputs: `transcriptions/SFDyEY2PruY.txt`, `.srt`, and `.json`

The workflow downloads the complete public YouTube audio and iterates over the complete faster-whisper segment generator. The TXT is grouped by minute and includes segment-level timestamps. It fails closed if no speech segments are returned. The workflow commits transcript files to this feature branch after successful completion.

A GitHub-hosted runner is a finite resource: this workflow has a 350-minute job timeout. A video that exceeds the runner's time or resource limits will fail rather than silently publish a partial transcript.
