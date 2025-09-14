ASR Quickstart (KOR→KSL Pipeline)

Prerequisites
- Python 3.10+
- Optional: FFmpeg (RTMP/WAV resampling), Vosk model (if using Vosk)

Setup
- Create venv (Windows): `python -m venv .venv`
- Install deps: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
- For Whisper: `.\.venv\Scripts\python.exe -m pip install faster-whisper`

Run Server
- `powershell -ExecutionPolicy Bypass -File scripts\run_server.ps1`
- Health: GET `http://localhost:8000/healthz`

Subscribe Timeline
- `.\.venv\Scripts\python.exe scripts\example_ws_client.py`

Text Streaming (mock ASR)
- `.\.venv\Scripts\python.exe scripts\mock_asr_stream.py --text "안녕하세요 한국 날씨 방송"`
- 편의 스크립트(새 창으로 서버+구독+모의ASR):
  - `powershell -ExecutionPolicy Bypass -File scripts\run_asr_demo.ps1`

WAV → Whisper (/ws/asr)
- 16kHz mono s16le WAV required. If needed: `ffmpeg -i in.mp3 -ar 16000 -ac 1 -c:a pcm_s16le out.wav`
- Send chunks: `.\.venv\Scripts\python.exe scripts\wav_ws_stream.py --wav out.wav --language ko`
  - API key in server? Use: `--api-key YOUR_KEY`
  - 언어 변경 예시: `--language en`

RTMP → Whisper → Pipeline
- Install FFmpeg and faster-whisper
- `.\.venv\Scripts\python.exe scripts\whisper_ingest_from_rtmp.py --rtmp rtmp://origin/live/stream --pipeline-ws ws://localhost:8000/ws/ingest`
  - Options: `--model base --device cpu --compute int8 --beam_size 1 --chunk_ms 1600 --hop_ms 400`
- FFmpeg PiP 출력 재시작 루프: `powershell -ExecutionPolicy Bypass -File scripts\ffmpeg_loop.ps1 -InputRtmp rtmp://origin/live/stream -InsetRtmp rtmp://localhost/unity/alpha -OutputRtmp rtmp://output/live/with_sign`

로컬 파일 → Whisper → Pipeline (RTMP 없이)
- 사전 준비: FFmpeg + `pip install faster-whisper`
- 명령: `.\.venv\Scripts\python.exe scripts\whisper_ingest_from_media.py --input <media_file> --pipeline-ws ws://localhost:8000/ws/ingest --language ko`
  - 예: `--input sample.mp3` 또는 `--input sample.wav`
  - 옵션: `--chunk_ms`, `--hop_ms`, `--model`, `--device`, `--compute`

RTMP → Vosk → Pipeline
- Install: `pip install vosk` and download KO model (e.g., `vosk-model-small-ko-0.22`)
- `.\.venv\Scripts\python.exe scripts\vosk_ingest_from_rtmp.py --model <vosk_model_dir> --rtmp rtmp://origin/live/stream`

Notes
- `/ws/asr` now accepts query `language` (default `ko`). Example: `ws://localhost:8000/ws/asr?language=ko`
- Protected endpoints require `API_KEY`; pass `?key=...` on WS URLs or headers on HTTP.
- Whisper model download occurs on first run; it may take time and extra disk space.
