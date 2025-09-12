import json
import sys
from pathlib import Path

from packages.ksl_rules import tokenize_ko, ko_to_gloss
from packages.sign_timeline import compile_glosses


def check_basic():
    text = "안녕하세요 오늘 한국 날씨 속보 태풍"
    toks = tokenize_ko(text)
    assert toks, "tokenize failed"
    glosses = ko_to_gloss(toks)
    assert any(g == "HELLO" for g, _ in glosses), "no HELLO in glosses"
    timeline = compile_glosses(glosses)
    assert "events" in timeline and len(timeline["events"]) > 0, "empty timeline"
    print("OK: basic timeline generation")


def check_schema():
    try:
        import jsonschema
    except Exception:
        print("WARN: jsonschema not installed, skipping schema check")
        return
    schema_path = Path("schemas/sign_timeline.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    timeline = compile_glosses([("HELLO", 0.9), ("KOREA", 0.9), ("WEATHER", 0.9)])
    jsonschema.validate(timeline, schema)
    print("OK: schema validation")


if __name__ == "__main__":
    try:
        check_basic()
        check_schema()
    except AssertionError as e:
        print(f"SELF-CHECK FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"SELF-CHECK ERROR: {e}")
        sys.exit(2)
    print("SELF-CHECK PASS")

