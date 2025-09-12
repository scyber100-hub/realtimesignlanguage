import argparse
import asyncio
import json
import time
import websockets


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='ws://localhost:8000/ws/ingest')
    ap.add_argument('--session', default='text1')
    ap.add_argument('--file', required=True, help='path to UTF-8 text file; each line streamed as partial')
    ap.add_argument('--delay_ms', type=int, default=250)
    ap.add_argument('--api-key', default=None)
    args = ap.parse_args()

    url = args.url
    if args.api_key and '?key=' not in url:
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}key={args.api_key}"

    async with websockets.connect(url, ping_interval=20) as ws:
        with open(args.file, 'r', encoding='utf-8') as f:
            for line in f:
                text = line.strip()
                if not text:
                    continue
                msg = {"type": "partial", "session_id": args.session, "text": text, "origin_ts": int(time.time()*1000)}
                await ws.send(json.dumps(msg, ensure_ascii=False))
                _ = await ws.recv()
                await asyncio.sleep(args.delay_ms/1000.0)


if __name__ == '__main__':
    asyncio.run(main())

