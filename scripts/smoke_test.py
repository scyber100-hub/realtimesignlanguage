import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.pipeline_server import app


def main():
    client = TestClient(app)
    r = client.get("/healthz")
    print("/healthz:", r.status_code, r.text)

    r = client.post("/text2gloss", json={"text": "안녕하세요 한국 날씨"})
    print("/text2gloss:", r.json())

    r = client.post(
        "/gloss2timeline",
        json={"gloss": ["HELLO", "KOREA", "WEATHER"], "start_ms": 0, "gap_ms": 60},
    )
    print("/gloss2timeline events:", len(r.json().get("events", [])))


if __name__ == "__main__":
    main()
