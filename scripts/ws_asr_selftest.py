from fastapi.testclient import TestClient
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.pipeline_server import app
import json


def main():
    client = TestClient(app)
    with client.websocket_connect("/ws/asr?model=base&device=cpu&compute=int8&chunk_ms=400") as ws:
        # Initialize session via text message
        ws.send_text(json.dumps({"type": "partial", "session_id": "asrtest", "text": ""}, ensure_ascii=False))
        ack = ws.receive_json()
        print("INIT ACK:", ack)

        # Send 400ms of silence (16kHz, s16le -> 16000 * 0.4 * 2 bytes)
        silence = b"\x00\x00" * int(16000 * 0.4)
        ws.send_bytes(silence)
        ack2 = ws.receive_json()
        print("BYTES ACK:", ack2)


if __name__ == "__main__":
    main()

