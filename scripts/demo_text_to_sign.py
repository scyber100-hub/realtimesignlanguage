import argparse
import json
from pathlib import Path

from packages.ksl_rules import tokenize_ko, ko_to_gloss
from packages.sign_timeline import compile_glosses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True, help="한국어 입력 문장")
    ap.add_argument("--out", default="out/timeline.json", help="출력 경로(JSON)")
    ap.add_argument("--start_ms", type=int, default=0)
    ap.add_argument("--gap_ms", type=int, default=60)
    args = ap.parse_args()

    tokens = tokenize_ko(args.text)
    glosses = ko_to_gloss(tokens)
    timeline = compile_glosses(glosses, start_ms=args.start_ms, gap_ms=args.gap_ms)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)
    print(f"Wrote timeline to {out_path}")


if __name__ == "__main__":
    main()

