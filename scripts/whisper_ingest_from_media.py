import argparse
import asyncio
import json
import subprocess
import sys


async def run_once(args):
    try:
        from faster_whisper import WhisperModel
    except Exception:
        print("ERROR: faster-whisper not installed. pip install faster-whisper")
        sys.exit(2)

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute)

    # FFmpeg to s16le 16k mono PCM from local media file
    ffmpeg_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-fflags",
        "nobuffer",
        "-i",
        args.input,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        "-f",
        "s16le",
        "-",
    ]
    print("Starting FFmpeg:", " ".join(ffmpeg_cmd))
    proc = subprocess.Popen(
        ffmpeg_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )

    import numpy as np  # type: ignore
    import websockets  # type: ignore

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

    # append API key if provided
    if args.api_key and "?key=" not in uri:
        sep = "&" if "?" in uri else "?"
        uri = f"{uri}{sep}key={args.api_key}"

    async with websockets.connect(uri, ping_interval=20) as ws:
        while True:
            data = proc.stdout.read(hop_bytes)
            if not data:
                await asyncio.sleep(0.02)
                # if ffmpeg ended, break out
                if proc.poll() is not None:
                    break
                continue
            ring.extend(data)
            if len(ring) >= chunk_bytes:
                pcm = np.frombuffer(ring[:chunk_bytes], dtype=np.int16).astype(np.float32) / 32768.0
                ring = ring[hop_bytes:]
                segments, _ = model.transcribe(
                    pcm,
                    language=args.language,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 200},
                    beam_size=getattr(args, "beam_size", None) or 1,
                )
                text = " ".join([s.text.strip() for s in segments]).strip()
                if text and text != last_text:
                    last_text = text
                    import time as _t

                    msg = {
                        "type": "partial",
                        "session_id": session_id,
                        "text": text,
                        "origin_ts": int(_t.time() * 1000),
                    }
                    await ws.send(json.dumps(msg, ensure_ascii=False))
                    _ = await ws.recv()


async def run(args):
    backoff = 1.0
    while True:
        try:
            await run_once(args)
            backoff = 1.0
            break
        except Exception as e:
            print("media whisper bridge error:", e)
            await asyncio.sleep(backoff)
            backoff = min(30.0, backoff * 2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to media file (wav/mp3/mp4/...) to transcribe")
    ap.add_argument("--pipeline-ws", default="ws://localhost:8000/ws/ingest", help="Pipeline ingest WS URL")
    ap.add_argument("--session", default="ch1", help="Pipeline session id")
    ap.add_argument("--language", default="ko", help="Language hint (e.g., ko, en)")
    ap.add_argument("--model", default="base")
    ap.add_argument("--device", default="cpu", help="cpu|cuda")
    ap.add_argument("--compute", default="int8", help="int8|int8_float16|float16|float32")
    ap.add_argument("--chunk_ms", type=int, default=1600)
    ap.add_argument("--hop_ms", type=int, default=400)
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--beam_size", type=int, default=1)
    args = ap.parse_args()
    asyncio.run(run(args))

