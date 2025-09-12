from fastapi.testclient import TestClient
from services.pipeline_server import app, settings


def test_aux_channels_toggle():
    orig = settings.include_aux_channels
    try:
        settings.include_aux_channels = False
        client = TestClient(app)
        r = client.post("/gloss2timeline", json={"gloss":["BREAKING","KOREA"]})
        assert r.status_code == 200
        ev = r.json()["events"]
        assert all(e.get("channel") == "default" for e in ev), "face/gaze events should be disabled"
    finally:
        settings.include_aux_channels = orig

