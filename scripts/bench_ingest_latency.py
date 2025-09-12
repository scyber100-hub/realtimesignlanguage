import argparse
import asyncio
import json
import time

import websockets


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://localhost:8000/ws/ingest")
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--session", default="bench1")
    ap.add_argument("--count", type=int, default=30)
    ap.add_argument("--interval_ms", type=int, default=150)
    ap.add_argument("--text", default="안녕하세요 한국 날씨 속보 태풍")
    ap.add_argument("--stats", default="http://localhost:8000/stats")
    args = ap.parse_args()

    url = args.url
    if args.api_key and "?key=" not in url:
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}key={args.api_key}"

    lat = []
    async with websockets.connect(url, ping_interval=20) as ws:
        for i in range(args.count):
            ts = int(time.time()*1000)
            msg = {"type": "partial", "session_id": args.session, "text": args.text, "origin_ts": ts}
            await ws.send(json.dumps(msg, ensure_ascii=False))
            ack = json.loads(await ws.recv())
            if ack.get("ok"):
                pass
            elif ack.get("rate_limited"):
                # backoff on RL
                await asyncio.sleep(0.2)
            await asyncio.sleep(args.interval_ms/1000.0)

    try:
        import aiohttp
        headers = {"x-api-key": args.api_key} if args.api_key else {}
        async with aiohttp.ClientSession(headers=headers) as sess:
            async with sess.get(args.stats) as r:
                s = await r.json()
                lm = s.get("latency_ms", {})
                print("latency p50/p90/p99:", lm.get("p50"), lm.get("p90"), lm.get("p99"))
    except Exception:
        print("Stats fetch skipped (install aiohttp for this feature)")


if __name__ == "__main__":
    asyncio.run(main())

