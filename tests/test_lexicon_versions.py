from fastapi.testclient import TestClient
from services.pipeline_server import app


def test_lexicon_versions_endpoints_exist():
    c = TestClient(app)
    r1 = c.get('/lexicon/versions')
    assert r1.status_code in (200, 401)
    r2 = c.post('/lexicon/snapshot', json={})
    assert r2.status_code in (200, 401)
    r3 = c.post('/lexicon/rollback', json={"name": "overlay-0.json"})
    assert r3.status_code in (200, 400, 401, 404)

