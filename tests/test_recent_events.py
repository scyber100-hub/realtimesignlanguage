from fastapi.testclient import TestClient
from services.pipeline_server import app


def test_recent_events_endpoint_exists():
    c = TestClient(app)
    r = c.get('/events/recent?n=5')
    assert r.status_code in (200, 401)

