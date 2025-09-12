from typing import List, Tuple, Dict, Optional
import json
from pathlib import Path

# 매우 단순한 한국어 토크나이저(공백/기호 기준). 실제 서비스는 형태소 분석기 사용 권장.
def tokenize_ko(text: str) -> List[str]:
    seps = ",.!?;:()[]{}\"'\n\t"
    for s in seps:
        text = text.replace(s, " ")
    toks = [t for t in text.strip().split() if t]
    return toks

# 최소 글로스 규칙: 고빈도 표제어 중심. 실제 서비스: 도메인 사전 + 규칙 + NMT 하이브리드.
_LEXICON: Dict[str, str] = {
    "안녕하세요": "HELLO",
    "안녕": "HELLO",
    "한국": "KOREA",
    "대한민국": "KOREA",
    "날씨": "WEATHER",
    "오늘": "TODAY",
    "내일": "TOMORROW",
    "속보": "BREAKING",
    "지진": "EARTHQUAKE",
    "태풍": "TYPHOON",
    "비": "RAIN",
    "눈": "SNOW",
    "맑음": "SUNNY",
    # 뉴스/기상/재난 도메인(예시 확장)
    "속보": "BREAKING",
    "기상": "WEATHER",
    "기온": "TEMPERATURE",
    "영하": "BELOW_ZERO",
    "영상": "ABOVE_ZERO",
    "강풍": "STRONG_WIND",
    "호우": "HEAVY_RAIN",
    "폭우": "HEAVY_RAIN",
    "폭설": "HEAVY_SNOW",
    "경보": "ALERT",
    "주의보": "ADVISORY",
    "발표": "ANNOUNCE",
    "속도": "SPEED",
    "시간": "TIME",
    "분": "MINUTE",
    "시": "HOUR",
    "오늘밤": "TONIGHT",
    "오전": "MORNING",
    "오후": "AFTERNOON",
    "밤": "NIGHT",
    "새벽": "DAWN",
    "서울": "SEOUL",
    "부산": "BUSAN",
    "대구": "DAEGU",
    "인천": "INCHEON",
    "광주": "GWANGJU",
    "대전": "DAEJEON",
    "울산": "ULSAN",
    "제주": "JEJU",
    "전국": "NATIONWIDE",
}

# 런타임 오버레이 사전(도메인 단어 추가/수정 용)
_OVERLAY: Dict[str, str] = {}

def set_overlay_lexicon(d: Dict[str, str]):
    global _OVERLAY
    _OVERLAY = dict(d or {})


def load_overlay_lexicon(path: str | Path) -> Optional[Dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("overlay lexicon must be a JSON object of {ko: GLOSS}")
    set_overlay_lexicon(data)  # set globally
    return data

def ko_to_gloss(tokens: List[str]) -> List[Tuple[str, float]]:
    glosses: List[Tuple[str, float]] = []
    for t in tokens:
        g = _OVERLAY.get(t) or _LEXICON.get(t)
        if g:
            glosses.append((g, 0.9))
        else:
            # 미정 매핑: 지명/숫자/고유명사 등은 규칙/NER 처리 대상
            # 숫자 규칙(간단): "12시" → NUM_12 + HOUR
            if t.isdigit():
                glosses.append((f"NUM_{t}", 0.85))
            elif t.endswith("시") and t[:-1].isdigit():
                glosses.append((f"NUM_{t[:-1]}", 0.85))
                glosses.append(("HOUR", 0.85))
            elif t.endswith("분") and t[:-1].isdigit():
                glosses.append((f"NUM_{t[:-1]}", 0.85))
                glosses.append(("MINUTE", 0.85))
            else:
                glosses.append((t.upper(), 0.5))
    # 간단한 불용어/어순 조정은 추후 추가
    return glosses
