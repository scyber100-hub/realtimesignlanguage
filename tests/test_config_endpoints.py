from fastapi.testclient import TestClient
from services.pipeline_server import app


def test_config_get_and_update_exist():
    c = TestClient(app)
    r = c.get('/config')
    assert r.status_code in (200, 401)
    r2 = c.post('/config/update', json={})
    assert r2.status_code in (200, 401)

