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

