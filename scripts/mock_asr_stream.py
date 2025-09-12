import asyncio
import json
import websockets
import argparse


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://localhost:8000/ws/ingest")
    ap.add_argument("--session", default="ch1")
    ap.add_argument("--text", default="안녕하세요 오늘 한국 날씨 속보 태풍")
    ap.add_argument("--delay_ms", type=int, default=300)
    ap.add_argument("--api-key", default=None)
    args = ap.parse_args()

    parts = []
    acc = []
    for w in args.text.split():
        acc.append(w)
        parts.append(" ".join(acc))

    url = args.url
    if args.api_key and "?key=" not in url:
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}key={args.api_key}"
    async with websockets.connect(url, ping_interval=20) as ws:
        import time
        for i, p in enumerate(parts):
            msg = {"type": "partial", "session_id": args.session, "text": p, "origin_ts": int(time.time()*1000)}
            await ws.send(json.dumps(msg, ensure_ascii=False))
            ack = await ws.recv()
            print("SENT PARTIAL:", p, "ACK:", ack)
            await asyncio.sleep(args.delay_ms / 1000.0)
        # final
        msg = {"type": "final", "session_id": args.session, "text": parts[-1] if parts else "", "origin_ts": int(time.time()*1000)}
        await ws.send(json.dumps(msg, ensure_ascii=False))
        ack = await ws.recv()
        print("SENT FINAL ACK:", ack)


if __name__ == "__main__":
    asyncio.run(main())
