from fastapi.testclient import TestClient
from services.pipeline_server import app


def test_sessions_list_and_reset():
    client = TestClient(app)
    # ensure endpoint exists
    r = client.get('/sessions')
    assert r.status_code in (200, 401)  # may require API key
    # reset all (without api key may be 401; we just verify endpoint exists)
    r2 = client.post('/sessions/reset', json={})
    assert r2.status_code in (200, 401)

