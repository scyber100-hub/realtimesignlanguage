from fastapi.testclient import TestClient
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.pipeline_server import app  # noqa: E402


def main():
    c = TestClient(app)

    r = c.post('/config/preset/save', json={'name': 'dev_fast', 'note': 'fast'})
    print('save', r.status_code, r.json())

    r = c.get('/config/presets')
    print('list', r.status_code, len(r.json().get('items', [])))

    r = c.post('/config/preset/load', json={'name': 'dev_fast'})
    print('load', r.status_code, r.json())


if __name__ == '__main__':
    main()

