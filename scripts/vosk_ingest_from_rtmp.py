import argparse
import json
import os
import subprocess
import sys
import time

try:
    from vosk import Model, KaldiRecognizer
except Exception as e:
    Model = None
    KaldiRecognizer = None

import websockets
import asyncio


async def run(args):
    if Model is None or KaldiRecognizer is None:
        print("ERROR: vosk is not installed. pip install vosk and provide a model path.")
        sys.exit(2)

    if not os.path.isdir(args.model):
        print(f"ERROR: model path not found: {args.model}")
        sys.exit(2)

    model = Model(args.model)
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(True)

    # FFmpeg command to extract mono 16k s16le PCM from RTMP
    ffmpeg_cmd = [
        "ffmpeg", "-fflags", "nobuffer",
        "-i", args.rtmp,
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-f", "s16le", "-"
    ]
    print("Starting FFmpeg:", " ".join(ffmpeg_cmd))
    proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    uri = args.pipeline_ws
    async with websockets.connect(uri, ping_interval=20) as ws:
        last_partial = ""
        session_id = args.session
        bufsize = 3200  # 100ms @16kHz s16le
        try:
            while True:
                chunk = proc.stdout.read(bufsize)
                if not chunk:
                    await asyncio.sleep(0.05)
                    continue
                if rec.AcceptWaveform(chunk):
                    res = json.loads(rec.Result())
                    text = (res.get("text") or "").strip()
                    if text:
                        msg = {"type": "final", "session_id": session_id, "text": text, "origin_ts": int(time.time()*1000)}
                        await ws.send(json.dumps(msg, ensure_ascii=False))
                        _ = await ws.recv()  # ack
                        last_partial = ""
                else:
                    res = json.loads(rec.PartialResult())
                    ptext = (res.get("partial") or "").strip()
                    if ptext and ptext != last_partial:
                        last_partial = ptext
                        msg = {"type": "partial", "session_id": session_id, "text": ptext, "origin_ts": int(time.time()*1000)}
                        await ws.send(json.dumps(msg, ensure_ascii=False))
                        _ = await ws.recv()
        finally:
            try:
                proc.kill()
            except Exception:
                pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtmp", default="rtmp://origin/live/stream", help="RTMP input URL")
    ap.add_argument("--model", required=True, help="Path to Vosk model directory (e.g., vosk-model-small-ko-0.22)")
    ap.add_argument("--pipeline-ws", default="ws://localhost:8000/ws/ingest", help="Pipeline ingest WS URL")
    ap.add_argument("--api-key", default=None, help="Optional API key")
    ap.add_argument("--session", default="ch1", help="Pipeline session id")
    args = ap.parse_args()
    if args.api_key and "?key=" not in args.pipeline_ws:
        sep = '&' if '?' in args.pipeline_ws else '?'
        args.pipeline_ws = f"{args.pipeline_ws}{sep}key={args.api_key}"
    asyncio.run(run(args))
