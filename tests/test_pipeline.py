from fastapi.testclient import TestClient
from services.pipeline_server import app


client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_text2gloss():
    r = client.post("/text2gloss", json={"text": "안녕하세요 한국 날씨"})
    assert r.status_code == 200
    data = r.json()
    assert "HELLO" in data["gloss"]


def test_gloss2timeline_schema():
    r = client.post("/gloss2timeline", json={"gloss": ["HELLO", "KOREA", "WEATHER"]})
    assert r.status_code == 200
    tl = r.json()
    assert "events" in tl and isinstance(tl["events"], list) and len(tl["events"]) >= 3


def test_ingest_text_and_ws_broadcast():
    with client.websocket_connect("/ws/timeline") as ws:
        r = client.post("/ingest_text", json={"text": "안녕하세요 한국 날씨"})
        assert r.status_code == 200
        msg = ws.receive_json()
        assert msg["type"] == "timeline"
        assert "data" in msg and len(msg["data"]["events"]) > 0


def test_ws_ingest_incremental():
    with client.websocket_connect("/ws/timeline") as ws_tl:
        with client.websocket_connect("/ws/ingest") as ws_in:
            ws_in.send_json({"type": "partial", "session_id": "test", "text": "안녕하세요"})
            # ack
            ack = ws_in.receive_json()
            assert ack["ok"] is True
            # timeline
            msg1 = ws_tl.receive_json()
            assert msg1["type"] in ("timeline", "timeline.replace")
            # send another partial
            ws_in.send_json({"type": "partial", "session_id": "test", "text": "안녕하세요 한국"})
            ack2 = ws_in.receive_json()
            assert ack2["ok"] is True
            msg2 = ws_tl.receive_json()
            assert msg2["type"] in ("timeline", "timeline.replace")

