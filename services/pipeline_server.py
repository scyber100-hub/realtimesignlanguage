from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import time

from packages.ksl_rules import tokenize_ko, ko_to_gloss
from packages.sign_timeline import compile_glosses


class IngestText(BaseModel):
    text: str
    start_ms: int = 0
    gap_ms: int = 60
    id: Optional[str] = None


class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            if websocket in self.active:
                self.active.remove(websocket)

    async def broadcast_json(self, message):
        async with self.lock:
            send_tasks = []
            for ws in list(self.active):
                send_tasks.append(self._safe_send(ws, message))
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)

    async def _safe_send(self, ws: WebSocket, message):
        try:
            await ws.send_json(message)
        except Exception:
            try:
                await ws.close()
            finally:
                await self.disconnect(ws)


app = FastAPI(title="Realtime KOR→KSL Pipeline", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()


@app.get("/healthz")
async def healthz():
    return {"ok": True, "ts": int(time.time() * 1000)}


@app.post("/ingest_text")
async def ingest_text(payload: IngestText):
    tokens = tokenize_ko(payload.text)
    glosses = ko_to_gloss(tokens)
    timeline = compile_glosses(glosses, start_ms=payload.start_ms, gap_ms=payload.gap_ms)
    if payload.id:
        timeline["id"] = payload.id
    await manager.broadcast_json({"type": "timeline", "data": timeline})
    return {"ok": True, "timeline": timeline}


@app.websocket("/ws/timeline")
async def ws_timeline(ws: WebSocket):
    await manager.connect(ws)
    try:
        # 단순 keep-alive; 클라이언트는 수신만 해도 됨
        while True:
            # 클라이언트가 ping/pong 또는 noop 메시지 보낼 수 있음
            _ = await ws.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception:
        await manager.disconnect(ws)

