from typing import List, Optional, Dict, Any, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Depends, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import time
import json

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from jsonschema import validate as jsonschema_validate, Draft202012Validator
from pathlib import Path
import os

from packages.ksl_rules import tokenize_ko, ko_to_gloss, set_overlay_lexicon, load_overlay_lexicon
from packages.sign_timeline import compile_glosses
from services.config import get_settings
import logging
from typing import Callable


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
            try:
                WS_CLIENTS.set(len(self.active))
            except Exception:
                pass

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            if websocket in self.active:
                self.active.remove(websocket)
                try:
                    WS_CLIENTS.set(len(self.active))
                except Exception:
                    pass

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
                BROADCAST_ERR.inc()
            except Exception:
                pass
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
    recent_ms: List[int] = []
    last_update_ms: int = 0
    meta: Dict[str, Any] = {}
    last_text: str = ""

sessions: Dict[str, SessionState] = {}

# Metrics
REQ_LAT = Histogram("pipeline_request_latency_seconds", "Latency of API processing", labelnames=("endpoint",))
TIMELINE_BC = Counter("timeline_broadcast_total", "Number of timeline messages broadcast")
INGEST_MSG = Counter("ingest_messages_total", "Number of ingest messages", labelnames=("type",))
INGEST_TO_BC_MS = Histogram("ingest_to_broadcast_ms", "Latency from ingest message to timeline broadcast in ms")
BROADCAST_ERR = Counter("timeline_broadcast_errors_total", "Number of websocket broadcast errors")
WS_CLIENTS = Gauge("websocket_clients", "Number of connected websocket clients")

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


@app.get("/config")
async def get_config(_: None = Depends(require_api_key)):
    return {
        "version": settings.version,
        "include_aux_channels": settings.include_aux_channels,
        "max_ingest_rps": settings.max_ingest_rps,
        "enable_metrics": settings.enable_metrics,
    }


class ConfigUpdate(BaseModel):
    include_aux_channels: Optional[bool] = None
    max_ingest_rps: Optional[int] = None


@app.post("/config/update")
async def update_config(req: ConfigUpdate, _: None = Depends(require_api_key)):
    changed = {}
    if req.include_aux_channels is not None:
        settings.include_aux_channels = bool(req.include_aux_channels)
        changed["include_aux_channels"] = settings.include_aux_channels
    if req.max_ingest_rps is not None:
        try:
            v = int(req.max_ingest_rps)
            if v < 1:
                raise ValueError("max_ingest_rps must be >=1")
            settings.max_ingest_rps = v
            changed["max_ingest_rps"] = v
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "changed": changed}


@app.get("/timeline/last")
async def get_last_timeline(_: None = Depends(require_api_key)):
    if not LAST_TIMELINE_PATH.exists():
        return {"exists": False}
    try:
        return json.loads(LAST_TIMELINE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"exists": False}

@app.get("/events/recent")
async def events_recent(n: int = 100, _: None = Depends(require_api_key)):
    try:
        n = max(1, min(int(n), RECENT_EVENTS_MAX))
    except Exception:
        n = 100
    if isinstance(RECENT_EVENTS, list):
        items = RECENT_EVENTS[-n:]
    else:
        items = list(RECENT_EVENTS)[-n:]
    return {"count": len(items), "items": items}


@app.get("/events/summary")
async def events_summary(n: int = 100, _: None = Depends(require_api_key)):
    try:
        n = max(1, min(int(n), RECENT_EVENTS_MAX))
    except Exception:
        n = 100
    if isinstance(RECENT_EVENTS, list):
        items = RECENT_EVENTS[-n:]
    else:
        items = list(RECENT_EVENTS)[-n:]
    total = len(items)
    replaces = len([x for x in items if x.get("type") == "timeline.replace"])
    ratio = (replaces / total) if total else 0
    return {"total": total, "replaces": replaces, "ratio": round(ratio, 3)}


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
    timeline = compile_glosses(glosses, start_ms=payload.start_ms, gap_ms=payload.gap_ms, include_aux_channels=settings.include_aux_channels)
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
VERS_DIR = Path("lexicon/versions")
VERS_DIR.mkdir(parents=True, exist_ok=True)
LAST_TIMELINE_PATH = LOG_DIR / "last_timeline.json"
LEX_AUDIT = LOG_DIR / "lexicon_audit.log"
RECENT_EVENTS_MAX = 300
try:
    from collections import deque as _deque
    RECENT_EVENTS = _deque(maxlen=RECENT_EVENTS_MAX)
except Exception:
    RECENT_EVENTS = []


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
        try:
            LAST_TIMELINE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        try:
            item = {
                "ts": rec["ts"],
                "type": rec["type"],
                "session_id": rec["session_id"],
                "event_count": rec["event_count"],
            }
            if isinstance(RECENT_EVENTS, list):
                RECENT_EVENTS.append(item)
                if len(RECENT_EVENTS) > RECENT_EVENTS_MAX:
                    del RECENT_EVENTS[0:len(RECENT_EVENTS)-RECENT_EVENTS_MAX]
            else:
                RECENT_EVENTS.append(item)
        except Exception:
            pass
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
    timeline = compile_glosses(glosses, start_ms=payload.start_ms, gap_ms=payload.gap_ms, include_aux_channels=settings.include_aux_channels)
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


async def _process_stream_in(payload: StreamIn):
    INGEST_MSG.labels(payload.type).inc()
    stats.on_ingest(payload.type)
    st = sessions.get(payload.session_id)
    if not st:
        st = SessionState()
        sessions[payload.session_id] = st
    now_ms = int(time.time() * 1000)
    window_ms = 1000
    st.recent_ms = [t for t in st.recent_ms if now_ms - t <= window_ms]
    if len(st.recent_ms) >= max(1, settings.max_ingest_rps):
        RATE_LIMITED.inc()
        return {"ok": False, "rate_limited": True, "session_id": payload.session_id}
    st.recent_ms.append(now_ms)
    if payload.start_ms is not None:
        st.start_ms = int(payload.start_ms)
    if payload.gap_ms is not None:
        st.gap_ms = int(payload.gap_ms)

    # duplicate suppression for partial streams
    if payload.type == "partial" and payload.text == st.last_text:
        return {"ok": True, "session_id": payload.session_id, "is_final": False}
    st.text = payload.text
    tokens = tokenize_ko(st.text)
    glosses = ko_to_gloss(tokens)
    new_timeline = compile_glosses(glosses, start_ms=st.start_ms, gap_ms=st.gap_ms, include_aux_channels=settings.include_aux_channels)
    if st.base_id is None:
        st.base_id = new_timeline["id"]
    st.last_update_ms = now_ms

    old_clips = [e["clip"] for e in st.events]
    new_clips = [e["clip"] for e in new_timeline["events"]]
    start_idx, end_idx = _diff_window(old_clips, new_clips)
    if start_idx < len(new_timeline["events"]):
        from_t = new_timeline["events"][start_idx]["t_ms"]
    else:
        from_t = new_timeline["events"][-1]["t_ms"] if new_timeline["events"] else 0

    if not st.events:
        out = {"type": "timeline", "session_id": payload.session_id, "data": new_timeline}
        await manager.broadcast_json(out)
        stats.on_timeline()
        _log_timeline("timeline", out)
        if payload.origin_ts:
            lat = max(0, int(time.time()*1000) - int(payload.origin_ts))
            INGEST_TO_BC_MS.observe(lat)
            stats.on_latency(lat)
        TIMELINE_BC.inc()
    else:
        out = {"type": "timeline.replace", "session_id": payload.session_id, "from_t_ms": from_t, "data": {"id": st.base_id, "events": new_timeline["events"][start_idx:end_idx]}}
        await manager.broadcast_json(out)
        stats.on_timeline()
        _log_timeline("timeline.replace", out)
        if payload.origin_ts:
            lat = max(0, int(time.time()*1000) - int(payload.origin_ts))
            INGEST_TO_BC_MS.observe(lat)
            stats.on_latency(lat)
        TIMELINE_BC.inc()
        stats.on_replace()
    st.events = new_timeline["events"]
    st.last_text = payload.text
    return {"ok": True, "session_id": payload.session_id, "is_final": payload.type == "final"}


# Optional Whisper streaming transcriber (very simple, best-effort)
class _WhisperStreamer:
    def __init__(self, model_name: str = "base", device: str = "cpu", compute: str = "int8", beam_size: int = 1):
        try:
            from faster_whisper import WhisperModel  # type: ignore
            self.model = WhisperModel(model_name, device=device, compute_type=compute)
            self.beam_size = beam_size
        except Exception:
            self.model = None

    def transcribe_pcm16le(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        if not self.model or not pcm_bytes:
            return ""
        try:
            import numpy as np  # type: ignore
            pcm = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _ = self.model.transcribe(
                pcm,
                language="ko",
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 200},
                beam_size=self.beam_size or 1,
            )
            return " ".join([s.text.strip() for s in segments]).strip()
        except Exception:
            return ""


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
            # rate limiting per session
            now_ms = int(time.time() * 1000)
            window_ms = 1000
            st.recent_ms = [t for t in st.recent_ms if now_ms - t <= window_ms]
            if len(st.recent_ms) >= max(1, settings.max_ingest_rps):
                RATE_LIMITED.inc()
                await ws.send_json({"ok": False, "rate_limited": True, "session_id": payload.session_id})
                continue
            st.recent_ms.append(now_ms)
            if payload.start_ms is not None:
                st.start_ms = int(payload.start_ms)
            if payload.gap_ms is not None:
                st.gap_ms = int(payload.gap_ms)

            # 전체 텍스트 기준으로 단순 증분 처리
            st.text = payload.text
            tokens = tokenize_ko(st.text)
            glosses = ko_to_gloss(tokens)
            new_timeline = compile_glosses(glosses, start_ms=st.start_ms, gap_ms=st.gap_ms, include_aux_channels=settings.include_aux_channels)
            if st.base_id is None:
                st.base_id = new_timeline["id"]
            st.last_update_ms = int(time.time() * 1000)

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
                    lat = max(0, int(time.time()*1000) - int(payload.origin_ts))
                    INGEST_TO_BC_MS.observe(lat)
                    stats.on_latency(lat)
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
            lat = max(0, int(time.time()*1000) - int(payload.origin_ts))
            INGEST_TO_BC_MS.observe(lat)
            stats.on_latency(lat)
        TIMELINE_BC.inc()
        stats.on_replace()

            st.events = new_timeline["events"]

            # 요청자에게도 ack
            proc_ms = int((time.perf_counter() - start) * 1000)
            await ws.send_json({"ok": True, "session_id": payload.session_id, "is_final": payload.type == "final", "proc_ms": proc_ms})
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


@app.get("/sessions")
async def list_sessions(_: None = Depends(require_api_key)):
    out = []
    for sid, st in sessions.items():
        out.append({
            "session_id": sid,
            "text_len": len(st.text or ""),
            "events": len(st.events or []),
            "start_ms": st.start_ms,
            "gap_ms": st.gap_ms,
        })
    return {"count": len(out), "items": out}


class ResetReq(BaseModel):
    session_id: Optional[str] = None


@app.post("/sessions/reset")
async def reset_sessions(req: ResetReq, _: None = Depends(require_api_key)):
    if req.session_id:
        sessions.pop(req.session_id, None)
        return {"ok": True, "cleared": [req.session_id]}
    else:
        cleared = list(sessions.keys())
        sessions.clear()
        return {"ok": True, "cleared": cleared}
class LexiconUpdate(BaseModel):
    items: Dict[str, str]


@app.post("/lexicon/update")
async def lexicon_update(payload: LexiconUpdate, _: None = Depends(require_api_key)):
    set_overlay_lexicon(payload.items)
    _audit_lexicon({"action": "update", "size": len(payload.items)})
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
        self.replace_total = 0
        self.ingest_partial = 0
        self.ingest_final = 0
        self._timeline_ts = deque(maxlen=5000)
        self._ingest_ts = deque(maxlen=5000)
        self.last_ingest_to_bc_ms: int | None = None
        self._lat_ms = deque(maxlen=5000)

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

    def on_replace(self):
        self.replace_total += 1

    def on_latency(self, ms: int):
        try:
            self.last_ingest_to_bc_ms = int(ms)
            self._lat_ms.append(int(ms))
        except Exception:
            pass

    def snapshot(self) -> Dict[str, Any]:
        import time as _t
        now = int(_t.time() * 1000)
        window_ms = 60_000
        timeline_rate = len([t for t in self._timeline_ts if now - t <= window_ms]) / 60.0
        ingest_rate = len([t for t in self._ingest_ts if now - t <= window_ms]) / 60.0
        # latency percentiles/histogram (simple bins)
        lats = list(self._lat_ms)
        p50 = p90 = p99 = None
        hist = None
        recent = []
        if lats:
            sl = sorted(lats)
            def pct(p):
                import math
                if not sl:
                    return None
                k = min(len(sl)-1, max(0, int(math.ceil(p/100.0*len(sl))-1)))
                return sl[k]
            p50 = pct(50)
            p90 = pct(90)
            p99 = pct(99)
            # fixed buckets in ms
            buckets = [100,200,300,400,600,800,1000,1500,2000,3000]
            counts = [0]*(len(buckets)+1)
            for v in lats:
                idx = 0
                while idx < len(buckets) and v > buckets[idx]:
                    idx += 1
                counts[idx] += 1
            hist = {"buckets": buckets, "counts": counts}
            # tail (last 30)
            recent = lats[-30:]
        return {
            "timeline_broadcast_total": self.timeline_total,
            "timeline_rate_per_sec_1m": round(timeline_rate, 3),
            "timeline_replace_total": self.replace_total,
            "timeline_replace_ratio": (round(self.replace_total / self.timeline_total, 3) if self.timeline_total else 0),
            "ingest_partial_total": self.ingest_partial,
            "ingest_final_total": self.ingest_final,
            "ingest_rate_per_sec_1m": round(ingest_rate, 3),
            "last_ingest_to_bc_ms": self.last_ingest_to_bc_ms,
            "latency_ms": {"p50": p50, "p90": p90, "p99": p99, "hist": hist, "recent": recent},
            "session_count": len(sessions),
            "ws_clients": len(manager.active) if hasattr(manager, 'active') else None,
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

# Session purger (separate startup hook)
PURGED_SESS = Counter("sessions_purged_total", "Number of sessions purged due to TTL")


async def _session_purger():
    while True:
        try:
            ttl_ms = max(10, int(settings.session_ttl_s)) * 1000
            now = int(time.time() * 1000)
            to_del = []
            for sid, st in list(sessions.items()):
                last = getattr(st, 'last_update_ms', 0) or 0
                if last and now - last > ttl_ms:
                    to_del.append(sid)
            for sid in to_del:
                sessions.pop(sid, None)
                try:
                    PURGED_SESS.inc()
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(15)


@app.on_event("startup")
async def _start_session_purger():
    asyncio.create_task(_session_purger())


@app.get("/sessions_full")
async def sessions_full(_: None = Depends(require_api_key)):
    items = []
    for sid, st in sessions.items():
        items.append({
            "session_id": sid,
            "text_len": len(st.text or ""),
            "events": len(st.events or []),
            "start_ms": st.start_ms,
            "gap_ms": st.gap_ms,
            "last_update_ms": getattr(st, 'last_update_ms', 0),
        })
    return {"count": len(items), "items": items}


@app.post("/lexicon/upload")
async def lexicon_upload(file: UploadFile = File(...), _: None = Depends(require_api_key)):
    try:
        data = await file.read()
        obj = json.loads(data)
        if not isinstance(obj, dict):
            raise ValueError("uploaded JSON must be an object {ko: GLOSS}")
        set_overlay_lexicon(obj)
        _audit_lexicon({"action": "upload", "size": len(obj)})
        return {"ok": True, "size": len(obj)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class LexiconSnapshotReq(BaseModel):
    note: Optional[str] = None


@app.post("/lexicon/snapshot")
async def lexicon_snapshot(req: LexiconSnapshotReq, _: None = Depends(require_api_key)):
    from packages.ksl_rules.rules import _OVERLAY  # type: ignore
    ts = int(time.time()*1000)
    name = f"overlay-{ts}.json"
    path = VERS_DIR / name
    data = {"_meta": {"ts": ts, "note": req.note or ""}, "items": _OVERLAY}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _audit_lexicon({"action": "snapshot", "name": name, "note": req.note or ""}, ts)
    return {"ok": True, "name": name}


@app.get("/lexicon/versions")
async def lexicon_versions(_: None = Depends(require_api_key)):
    items = []
    for p in sorted(VERS_DIR.glob("*.json")):
        try:
            stat = p.stat()
            items.append({"name": p.name, "mtime_ms": int(stat.st_mtime*1000), "size": stat.st_size})
        except Exception:
            continue
    return {"count": len(items), "items": items}


class LexiconRollbackReq(BaseModel):
    name: str


@app.post("/lexicon/rollback")
async def lexicon_rollback(req: LexiconRollbackReq, _: None = Depends(require_api_key)):
    p = VERS_DIR / req.name
    if not p.exists():
        raise HTTPException(status_code=404, detail="version not found")
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        items = obj.get("items") if isinstance(obj, dict) else None
        if not isinstance(items, dict):
            # backwards compatibility: allow plain dict file
            items = obj if isinstance(obj, dict) else None
        if not isinstance(items, dict):
            raise ValueError("invalid snapshot format")
        set_overlay_lexicon(items)
        _audit_lexicon({"action": "rollback", "name": req.name, "size": len(items)})
        return {"ok": True, "name": req.name, "size": len(items)}


def _audit_lexicon(data: Dict[str, Any], ts: Optional[int] = None) -> None:
    try:
        rec = {"ts": ts or int(time.time()*1000)}
        rec.update(data)
        with LEX_AUDIT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


@app.get("/lexicon/audit")
async def lexicon_audit(n: int = 100, _: None = Depends(require_api_key)):
    try:
        n = max(1, min(int(n), 1000))
    except Exception:
        n = 100
    if not LEX_AUDIT.exists():
        return {"count": 0, "items": []}
    try:
        lines = LEX_AUDIT.read_text(encoding="utf-8").splitlines()
        tail = lines[-n:]
        items = []
        for ln in tail:
            try:
                items.append(json.loads(ln))
            except Exception:
                continue
        return {"count": len(items), "items": items}
    except Exception:
        return {"count": 0, "items": []}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.websocket("/ws/asr")
async def ws_asr(ws: WebSocket):
    key = ws.query_params.get("key")
    if settings.api_key and key != settings.api_key:
        await ws.close(code=4401)
        return
    await ws.accept()
    try:
        session_id = None
        # parse optional params
        model = ws.query_params.get("model") or "base"
        device = ws.query_params.get("device") or "cpu"
        compute = ws.query_params.get("compute") or "int8"
        try:
            beam_size = int(ws.query_params.get("beam_size") or 1)
        except Exception:
            beam_size = 1
        try:
            chunk_ms = int(ws.query_params.get("chunk_ms") or 400)
        except Exception:
            chunk_ms = 400
        streamer = _WhisperStreamer(model_name=model, device=device, compute=compute, beam_size=beam_size)
        ring = bytearray()
        chunk_bytes = int(16000 * 2 * (chunk_ms/1000.0))
        while True:
            msg = await ws.receive()
            if msg.get("type") != "websocket.receive":
                continue
            if msg.get("text") is not None:
                # Init or direct text bridge
                try:
                    data = json.loads(msg["text"])
                    payload = StreamIn(**data)
                    if not session_id:
                        session_id = payload.session_id
                        # store ASR meta on session
                        st = sessions.get(session_id) or SessionState()
                        st.meta.update({"model": model, "device": device, "compute": compute, "beam_size": beam_size, "chunk_ms": chunk_ms})
                        sessions[session_id] = st
                    res = await _process_stream_in(payload)
                    await ws.send_json(res)
                except Exception:
                    await ws.send_json({"ok": False, "error": "invalid message"})
            else:
                b = msg.get("bytes") or b""
                if not b:
                    await ws.send_json({"ok": True, "bytes": 0})
                    continue
                ring.extend(b)
                await ws.send_json({"ok": True, "bytes": len(b)})
                if len(ring) >= chunk_bytes and session_id:
                    # best-effort local transcription
                    text = streamer.transcribe_pcm16le(bytes(ring))
                    if text:
                        res = await _process_stream_in(StreamIn(type="partial", session_id=session_id, text=text))
                        await ws.send_json(res)
                        ring.clear()
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await ws.close()
        except Exception:
            pass
