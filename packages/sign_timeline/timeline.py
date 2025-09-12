import time
from typing import List, Tuple, Dict, Any

# 글로스→클립 매핑(간단 버전). 실제 서비스는 모션 리타게팅/변형 파라미터 포함.
_CLIPS = {
    "HELLO": {"clip": "HELLO", "dur_ms": 620},
    "KOREA": {"clip": "KOREA", "dur_ms": 700},
    "WEATHER": {"clip": "WEATHER", "dur_ms": 680},
    "TODAY": {"clip": "TODAY", "dur_ms": 500},
    "TOMORROW": {"clip": "TOMORROW", "dur_ms": 520},
    "BREAKING": {"clip": "BREAKING", "dur_ms": 600},
    "EARTHQUAKE": {"clip": "EARTHQUAKE", "dur_ms": 900},
    "TYPHOON": {"clip": "TYPHOON", "dur_ms": 900},
    "RAIN": {"clip": "RAIN", "dur_ms": 700},
    "SNOW": {"clip": "SNOW", "dur_ms": 700},
    "SUNNY": {"clip": "SUNNY", "dur_ms": 650},
}

DEFAULT_DUR = 650

def compile_glosses(glosses: List[Tuple[str, float]], start_ms: int = 0, gap_ms: int = 60) -> Dict[str, Any]:
    """
    glosses: [(gloss, confidence)]
    returns SignTimeline v0 JSON
    """
    t = start_ms
    events = []
    for gloss, conf in glosses:
        spec = _CLIPS.get(gloss, {"clip": gloss, "dur_ms": DEFAULT_DUR})
        events.append({
            "t_ms": t,
            "clip": spec["clip"],
            "dur_ms": spec["dur_ms"],
            "channel": "default",
            "confidence": round(float(conf), 3)
        })
        t += spec["dur_ms"] + gap_ms
    return {
        "id": f"signtimeline-{int(time.time()*1000)}",
        "created_ms": int(time.time()*1000),
        "lang": "ko-KR->KSL",
        "events": events,
        "meta": {"version": "v0", "generator": "sign_timeline.compile_glosses"}
    }

