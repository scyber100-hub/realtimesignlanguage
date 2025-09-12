from typing import List, Optional, Dict, Any, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import time
import json

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from jsonschema import validate as jsonschema_validate, Draft202012Validator
from pathlib import Path
import os

from packages.ksl_rules import tokenize_ko, ko_to_gloss, set_overlay_lexicon, load_overlay_lexicon
from packages.sign_timeline import compile_glosses
from services.config import get_settings
import logging


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


settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("pipeline")

app = FastAPI(title=settings.app_name, version=settings.version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()] or ["*"],
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

# Metrics
REQ_LAT = Histogram("pipeline_request_latency_seconds", "Latency of API processing", labelnames=("endpoint",))
TIMELINE_BC = Counter("timeline_broadcast_total", "Number of timeline messages broadcast")
INGEST_MSG = Counter("ingest_messages_total", "Number of ingest messages", labelnames=("type",))
INGEST_TO_BC_MS = Histogram("ingest_to_broadcast_ms", "Latency from ingest message to timeline broadcast in ms")

# Load timeline schema for validation
_SCHEMA_PATH = Path("schemas/sign_timeline.schema.json")
_TIMELINE_SCHEMA = None
if _SCHEMA_PATH.exists():
    try:
        _TIMELINE_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(_TIMELINE_SCHEMA)
    except Exception:
        _TIMELINE_SCHEMA = None


@app.get("/healthz")
async def healthz():
    return {"ok": True, "ts": int(time.time() * 1000), "version": settings.version}

@app.get("/metrics")
async def metrics():
    if not settings.enable_metrics:
        raise HTTPException(status_code=404)
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.get("/stats")
async def get_stats(_: None = Depends(require_api_key)):
    return stats.snapshot()


class TextIn(BaseModel):
    text: str


@app.post("/text2gloss")
async def text2gloss(payload: TextIn):
    start = time.perf_counter()
    tokens = tokenize_ko(payload.text)
    glosses = ko_to_gloss(tokens)
    REQ_LAT.labels("text2gloss").observe(time.perf_counter() - start)
    return {"gloss": [g for g, _ in glosses], "conf": [c for _, c in glosses]}


class GlossIn(BaseModel):
    gloss: List[str]
    conf: Optional[List[float]] = None
    start_ms: int = 0
    gap_ms: int = 60


@app.post("/gloss2timeline")
async def gloss2timeline(payload: GlossIn):
    start = time.perf_counter()
    glosses = list(zip(payload.gloss, payload.conf or [0.9] * len(payload.gloss)))
    timeline = compile_glosses(glosses, start_ms=payload.start_ms, gap_ms=payload.gap_ms)
    REQ_LAT.labels("gloss2timeline").observe(time.perf_counter() - start)
    if _TIMELINE_SCHEMA is not None:
        jsonschema_validate(timeline, _TIMELINE_SCHEMA)
    return timeline

def require_api_key(x_api_key: str | None = Header(default=None)):
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid api key")


LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
TIMELINE_LOG = LOG_DIR / "timeline.log"


def _log_timeline(evt_type: str, payload: Dict[str, Any]):
    try:
        rec = {
            "ts": int(time.time() * 1000),
            "type": evt_type,
            "session_id": payload.get("session_id"),
            "id": payload.get("data", {}).get("id") if "data" in payload else payload.get("id"),
            "from_t_ms": payload.get("from_t_ms"),
            "event_count": len(payload.get("data", {}).get("events", [])) if "data" in payload else len(payload.get("events", [])),
        }
        with TIMELINE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.debug(f"timeline log error: {e}")


async def _stats_broadcaster():
    # broadcast stats periodically to all timeline subscribers
    while True:
        try:
            await manager.broadcast_json({"type": "stats", "data": stats.snapshot()})
        except Exception:
            pass
        await asyncio.sleep(2.0)


@app.post("/ingest_text")
async def ingest_text(payload: IngestText, _: None = Depends(require_api_key)):
    start = time.perf_counter()
    tokens = tokenize_ko(payload.text)
    glosses = ko_to_gloss(tokens)
    timeline = compile_glosses(glosses, start_ms=payload.start_ms, gap_ms=payload.gap_ms)
    if payload.id:
        timeline["id"] = payload.id
    payload = {"type": "timeline", "data": timeline}
    await manager.broadcast_json(payload)
    stats.on_timeline()
    _log_timeline("timeline", payload)
    TIMELINE_BC.inc()
    REQ_LAT.labels("ingest_text").observe(time.perf_counter() - start)
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
    origin_ts: Optional[int] = None  # client-side timestamp (ms)


def _first_diff_index(a: List[str], b: List[str]) -> int:
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n


def _diff_window(old: List[str], new: List[str]) -> Tuple[int, int]:
    """
    returns (start_index_in_new, end_index_in_new_exclusive) to replace
    calculates common prefix and suffix to minimize replacement window
    """
    # common prefix
    p = 0
    nmin = min(len(old), len(new))
    while p < nmin and old[p] == new[p]:
        p += 1
    # common suffix (avoid overlap with prefix)
    s = 0
    while s < (len(old) - p) and s < (len(new) - p) and old[len(old) - 1 - s] == new[len(new) - 1 - s]:
        s += 1
    start = p
    end = len(new) - s
    if end < start:
        end = start
    return start, end


@app.websocket("/ws/ingest")
async def ws_ingest(ws: WebSocket):
    # optional API key via query param 'key'
    key = ws.query_params.get("key")
    if settings.api_key and key != settings.api_key:
        await ws.close(code=4401)
        return
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_json()
            payload = StreamIn(**msg)
            INGEST_MSG.labels(payload.type).inc()
            stats.on_ingest(payload.type)
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
            start_idx, end_idx = _diff_window(old_clips, new_clips)

            # 교체 시작 시간 산정
            if start_idx < len(new_timeline["events"]):
                from_t = new_timeline["events"][start_idx]["t_ms"]
            else:
                from_t = new_timeline["events"][-1]["t_ms"] if new_timeline["events"] else 0

            # 메시지 전송: 최초에는 full timeline, 이후에는 replace
            if not st.events:
                out = {
                    "type": "timeline",
                    "session_id": payload.session_id,
                    "data": new_timeline,
                }
                await manager.broadcast_json(out)
                stats.on_timeline()
                _log_timeline("timeline", out)
                if payload.origin_ts:
                    INGEST_TO_BC_MS.observe(max(0, int(time.time()*1000) - int(payload.origin_ts)))
                TIMELINE_BC.inc()
            else:
                out = {
                    "type": "timeline.replace",
                    "session_id": payload.session_id,
                    "from_t_ms": from_t,
                    "data": {
                        "id": st.base_id,
                        "events": new_timeline["events"][start_idx:end_idx],
                    },
                }
                await manager.broadcast_json(out)
                stats.on_timeline()
                _log_timeline("timeline.replace", out)
                if payload.origin_ts:
                    INGEST_TO_BC_MS.observe(max(0, int(time.time()*1000) - int(payload.origin_ts)))
                TIMELINE_BC.inc()

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


@app.on_event("startup")
async def _on_startup():
    # start stats broadcaster
    asyncio.create_task(_stats_broadcaster())
    # optional overlay lexicon load from file
    try:
        lp = getattr(settings, 'lexicon_path', None)
        if lp:
            p = Path(lp)
            if p.exists():
                load_overlay_lexicon(p)
                logger.info(f"Loaded overlay lexicon from {p}")
    except Exception as e:
        logger.warning(f"Lexicon load failed: {e}")
class LexiconUpdate(BaseModel):
    items: Dict[str, str]


@app.post("/lexicon/update")
async def lexicon_update(payload: LexiconUpdate, _: None = Depends(require_api_key)):
    set_overlay_lexicon(payload.items)
    return {"ok": True, "size": len(payload.items)}


@app.get("/lexicon")
async def lexicon_get(_: None = Depends(require_api_key)):
    # 보안을 위해 오버레이 크기만 공개, 상세는 관리 용도로 반환
    from packages.ksl_rules.rules import _OVERLAY  # type: ignore
    return {"size": len(_OVERLAY), "items": _OVERLAY}


@app.middleware("http")
async def log_requests(request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    finally:
# Lightweight runtime stats (for dashboard)
class Stats:
    def __init__(self):
        from collections import deque
        self.timeline_total = 0
        self.ingest_partial = 0
        self.ingest_final = 0
        self._timeline_ts = deque(maxlen=5000)
        self._ingest_ts = deque(maxlen=5000)

    def on_timeline(self):
        from time import time as now
        self.timeline_total += 1
        self._timeline_ts.append(int(now() * 1000))

    def on_ingest(self, mtype: str):
        from time import time as now
        if mtype == "partial":
            self.ingest_partial += 1
        elif mtype == "final":
            self.ingest_final += 1
        self._ingest_ts.append(int(now() * 1000))

    def snapshot(self) -> Dict[str, Any]:
        import time as _t
        now = int(_t.time() * 1000)
        window_ms = 60_000
        timeline_rate = len([t for t in self._timeline_ts if now - t <= window_ms]) / 60.0
        ingest_rate = len([t for t in self._ingest_ts if now - t <= window_ms]) / 60.0
        return {
            "timeline_broadcast_total": self.timeline_total,
            "timeline_rate_per_sec_1m": round(timeline_rate, 3),
            "ingest_partial_total": self.ingest_partial,
            "ingest_final_total": self.ingest_final,
            "ingest_rate_per_sec_1m": round(ingest_rate, 3),
        }


stats = Stats()
        dur = (time.perf_counter() - start) * 1000.0
        logger.info(f"{request.method} {request.url.path} {int(dur)}ms status={getattr(response,'status_code',0)}")


# Static files (dashboard)
try:
    app.mount("/", StaticFiles(directory="public", html=True), name="public")
except Exception:
    # directory may not exist in some envs; ignore mount errors
    pass
