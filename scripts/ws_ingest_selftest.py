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

    with client.websocket_connect("/ws/ingest") as ws:
        ws.send_json({"type": "partial", "session_id": "test1", "text": "안녕"})
        ack1 = ws.receive_json()
        print("ACK1:", json.dumps(ack1, ensure_ascii=False))

        ws.send_json({"type": "partial", "session_id": "test1", "text": "안녕하세요 한국"})
        ack2 = ws.receive_json()
        print("ACK2:", json.dumps(ack2, ensure_ascii=False))

        ws.send_json({"type": "final", "session_id": "test1", "text": "안녕하세요 한국 날씨"})
        ack3 = ws.receive_json()
        print("ACK3:", json.dumps(ack3, ensure_ascii=False))


if __name__ == "__main__":
    main()
