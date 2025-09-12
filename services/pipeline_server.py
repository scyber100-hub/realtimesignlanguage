from typing import List, Optional, Dict, Any
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

# 세션 상태: 증분 처리용(간단 버전)
class SessionState(BaseModel):
    text: str = ""
    events: List[Dict[str, Any]] = []
    base_id: Optional[str] = None
    start_ms: int = 0
    gap_ms: int = 60

sessions: Dict[str, SessionState] = {}


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


class StreamIn(BaseModel):
    type: str  # "partial" | "final"
    session_id: str
    text: str
    start_ms: Optional[int] = None
    gap_ms: Optional[int] = None


def _first_diff_index(a: List[str], b: List[str]) -> int:
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n


@app.websocket("/ws/ingest")
async def ws_ingest(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_json()
            payload = StreamIn(**msg)
            st = sessions.get(payload.session_id)
            if not st:
                st = SessionState()
                sessions[payload.session_id] = st
            if payload.start_ms is not None:
                st.start_ms = int(payload.start_ms)
            if payload.gap_ms is not None:
                st.gap_ms = int(payload.gap_ms)

            # 전체 텍스트 기준으로 단순 증분 처리
            st.text = payload.text
            tokens = tokenize_ko(st.text)
            glosses = ko_to_gloss(tokens)
            new_timeline = compile_glosses(glosses, start_ms=st.start_ms, gap_ms=st.gap_ms)
            if st.base_id is None:
                st.base_id = new_timeline["id"]

            old_clips = [e["clip"] for e in st.events]
            new_clips = [e["clip"] for e in new_timeline["events"]]
            diff_idx = _first_diff_index(old_clips, new_clips)

            # 교체 시작 시간 산정
            if diff_idx < len(new_timeline["events"]):
                from_t = new_timeline["events"][diff_idx]["t_ms"] if diff_idx < len(new_timeline["events"]) else 0
            else:
                from_t = new_timeline["events"][-1]["t_ms"] if new_timeline["events"] else 0

            # 메시지 전송: 최초에는 full timeline, 이후에는 replace
            if not st.events:
                await manager.broadcast_json({
                    "type": "timeline",
                    "session_id": payload.session_id,
                    "data": new_timeline,
                })
            else:
                await manager.broadcast_json({
                    "type": "timeline.replace",
                    "session_id": payload.session_id,
                    "from_t_ms": from_t,
                    "data": {
                        "id": st.base_id,
                        "events": new_timeline["events"][diff_idx:],
                    },
                })

            st.events = new_timeline["events"]

            # 요청자에게도 ack
            await ws.send_json({"ok": True, "session_id": payload.session_id, "is_final": payload.type == "final"})
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await ws.close()
        except Exception:
            pass
