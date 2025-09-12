import argparse
import asyncio
import json
import wave
import websockets


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='ws://localhost:8000/ws/asr')
    ap.add_argument('--wav', required=True, help='path to 16k mono PCM WAV')
    ap.add_argument('--chunk_ms', type=int, default=100)
    ap.add_argument('--api-key', default=None)
    ap.add_argument('--session', default='asr1')
    args = ap.parse_args()

    url = args.url
    if args.api_key and '?key=' not in url:
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}key={args.api_key}"

    wf = wave.open(args.wav, 'rb')
    assert wf.getframerate() == 16000 and wf.getnchannels() == 1 and wf.getsampwidth() == 2, 'requires 16k mono s16le'
    frames_per_chunk = int(wf.getframerate() * (args.chunk_ms/1000.0))

    async with websockets.connect(url, ping_interval=20) as ws:
        # send a small JSON to set session (optional)
        await ws.send(json.dumps({"type":"partial","session_id":args.session,"text":""}))
        _ = await ws.recv()
        while True:
            data = wf.readframes(frames_per_chunk)
            if not data:
                break
            await ws.send(data)
            _ = await ws.recv()


if __name__ == '__main__':
    asyncio.run(main())

