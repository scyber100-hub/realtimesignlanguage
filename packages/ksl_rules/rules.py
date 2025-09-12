from typing import List, Tuple

# 매우 단순한 한국어 토크나이저(공백/기호 기준). 실제 서비스는 형태소 분석기 사용 권장.
def tokenize_ko(text: str) -> List[str]:
    seps = ",.!?;:()[]{}\"'\n\t"
    for s in seps:
        text = text.replace(s, " ")
    toks = [t for t in text.strip().split() if t]
    return toks

# 최소 글로스 규칙: 고빈도 표제어 중심. 실제 서비스: 도메인 사전 + 규칙 + NMT 하이브리드.
_LEXICON = {
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
}

def ko_to_gloss(tokens: List[str]) -> List[Tuple[str, float]]:
    glosses: List[Tuple[str, float]] = []
    for t in tokens:
        g = _LEXICON.get(t)
        if g:
            glosses.append((g, 0.9))
        else:
            # 미정 매핑: 지명/숫자/고유명사 등은 규칙/NER 처리 대상
            glosses.append((t.upper(), 0.5))
    # 간단한 불용어/어순 조정은 추후 추가
    return glosses

