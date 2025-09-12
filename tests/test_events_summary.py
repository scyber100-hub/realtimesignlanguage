from fastapi.testclient import TestClient
from services.pipeline_server import app


def test_events_summary_endpoint_exists():
    c = TestClient(app)
    r = c.get('/events/summary?n=10')
    assert r.status_code in (200, 401)

