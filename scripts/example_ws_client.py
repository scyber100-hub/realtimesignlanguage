import asyncio
import json
import websockets


async def consume(uri="ws://localhost:8000/ws/timeline"):
    async with websockets.connect(uri, ping_interval=20) as ws:
        # send initial noop to open read loop on server side
        await ws.send("hello")
        print("Connected. Waiting for timeline messages…")
        try:
            while True:
                msg = await ws.recv()
                try:
                    data = json.loads(msg)
                except Exception:
                    print(msg)
                    continue
                print(json.dumps(data, ensure_ascii=False, indent=2))
        except websockets.ConnectionClosed:
            print("Connection closed.")


if __name__ == "__main__":
    asyncio.run(consume())

