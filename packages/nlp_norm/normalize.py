from typing import List


def normalize_tokens(tokens: List[str]) -> List[str]:
    """
    Very light normalization for Korean date/time tokens.
    - Handle: '12시', '30분', '2025년', '9월', '12일'
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
        else:
            out.append(t)
    return out

