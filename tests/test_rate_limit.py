from fastapi.testclient import TestClient
from services.pipeline_server import app, settings


def test_rate_limit_ws_ingest():
    client = TestClient(app)
    orig = settings.max_ingest_rps
    try:
        settings.max_ingest_rps = 1
        with client.websocket_connect("/ws/ingest") as ws:
            ws.send_json({"type":"partial","session_id":"r1","text":"안녕하세요"})
            ack1 = ws.receive_json()
            assert ack1.get("ok") is True
            # send immediately again; should be rate limited
            ws.send_json({"type":"partial","session_id":"r1","text":"안녕하세요 한국"})
            ack2 = ws.receive_json()
            assert ack2.get("rate_limited") is True
    finally:
        settings.max_ingest_rps = orig

