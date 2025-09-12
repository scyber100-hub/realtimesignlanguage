import argparse
import asyncio
import json
import subprocess
import sys
from collections import deque


async def run(args):
    try:
        from faster_whisper import WhisperModel
    except Exception:
        print("ERROR: faster-whisper not installed. pip install faster-whisper")
        sys.exit(2)

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute)

    # FFmpeg to s16le 16k mono PCM
    ffmpeg_cmd = [
        "ffmpeg", "-fflags", "nobuffer",
        "-i", args.rtmp,
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-f", "s16le", "-"
    ]
    print("Starting FFmpeg:", " ".join(ffmpeg_cmd))
    proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)

    import numpy as np
    import websockets

    uri = args.pipeline_ws
    session_id = args.session
    chunk_ms = args.chunk_ms
    hop_ms = args.hop_ms
    sample_rate = 16000
    bytes_per_sample = 2
    chunk_bytes = int(sample_rate * (chunk_ms / 1000.0)) * bytes_per_sample
    hop_bytes = int(sample_rate * (hop_ms / 1000.0)) * bytes_per_sample

    ring = bytearray()
    last_text = ""

    async with websockets.connect(uri, ping_interval=20) as ws:
        while True:
            data = proc.stdout.read(hop_bytes)
            if not data:
                await asyncio.sleep(0.02)
                continue
            ring.extend(data)
            if len(ring) >= chunk_bytes:
                # Convert to float32 numpy array in [-1,1]
                pcm = np.frombuffer(ring[:chunk_bytes], dtype=np.int16).astype(np.float32) / 32768.0
                ring = ring[hop_bytes:]
                segments, _ = model.transcribe(pcm, language="ko", vad_filter=True, vad_parameters={"min_silence_duration_ms": 200})
                text = " ".join([s.text.strip() for s in segments]).strip()
                if text:
                    if text != last_text:
                        last_text = text
                        import time as _t
                        msg = {"type": "partial", "session_id": session_id, "text": text, "origin_ts": int(_t.time()*1000)}
                        await ws.send(json.dumps(msg, ensure_ascii=False))
                        _ = await ws.recv()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtmp", default="rtmp://origin/live/stream")
    ap.add_argument("--pipeline-ws", default="ws://localhost:8000/ws/ingest")
    ap.add_argument("--session", default="ch1")
    ap.add_argument("--model", default="base")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--compute", default="int8")
    ap.add_argument("--chunk_ms", type=int, default=1600)
    ap.add_argument("--hop_ms", type=int, default=400)
    args = ap.parse_args()
    asyncio.run(run(args))
