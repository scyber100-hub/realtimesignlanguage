from typing import List


def normalize_tokens(tokens: List[str]) -> List[str]:
    """
    Very light normalization for Korean date/time tokens.
    - Examples handled: '12시', '30분', '2025년', '9월', '12일', '오전', '오후', '오늘', '내일', '모레', '어제'
    - Returns possibly expanded tokens (e.g., ['NUM_12','HOUR'])
    """
    out: List[str] = []
    for t in tokens:
        if t.endswith("시") and t[:-1].isdigit():
            out.append(f"NUM_{t[:-1]}")
            out.append("HOUR")
        elif t.endswith("분") and t[:-1].isdigit():
            out.append(f"NUM_{t[:-1]}")
            out.append("MINUTE")
        elif t.endswith("년") and t[:-1].isdigit():
            out.append(f"NUM_{t[:-1]}")
            out.append("YEAR")
        elif t.endswith("월") and t[:-1].isdigit():
            out.append(f"NUM_{t[:-1]}")
            out.append("MONTH")
        elif t.endswith("일") and t[:-1].isdigit():
            out.append(f"NUM_{t[:-1]}")
            out.append("DAY")
        elif t in ("오전", "AM", "am", "a.m."):
            out.append("AM")
        elif t in ("오후", "PM", "pm", "p.m."):
            out.append("PM")
        elif t in ("오늘",):
            out.append("TODAY")
        elif t in ("내일",):
            out.append("TOMORROW")
        elif t in ("모레",):
            out.append("DAY_AFTER_TOMORROW")
        elif t in ("어제",):
            out.append("YESTERDAY")
        else:
            out.append(t)
    return out


# Optional: basic Sino-Korean numeric parsing helper (단일 토큰)
_SINO = {"영":0,"공":0,"일":1,"이":2,"삼":3,"사":4,"오":5,"육":6,"칠":7,"팔":8,"구":9}

def parse_sino_korean_number(token: str) -> int | None:
    # Supports forms like "십", "이십", "십사", "이십오" up to 99
    if not token:
        return None
    if token == "십":
        return 10
    if "십" in token:
        parts = token.split("십")
        tens = _SINO.get(parts[0], 1) if parts[0] else 1
        units = _SINO.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return tens * 10 + units
    # Single digit
    if token in _SINO:
        return _SINO[token]
    return None
