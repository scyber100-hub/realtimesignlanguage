import argparse
import json
import sys

import httpx


def main():
    ap = argparse.ArgumentParser(description="Manage pipeline config presets")
    ap.add_argument("command", choices=["list", "save", "load"], help="operation")
    ap.add_argument("name", nargs="?", help="preset name for save/load")
    ap.add_argument("--base", default="http://127.0.0.1:8000", help="server base URL")
    ap.add_argument("--api-key", dest="api_key", default=None, help="x-api-key if required")
    ap.add_argument("--note", default="", help="note when saving preset")
    args = ap.parse_args()

    headers = {"content-type": "application/json"}
    if args.api_key:
        headers["x-api-key"] = args.api_key

    try:
        if args.command == "list":
            r = httpx.get(f"{args.base}/config/presets", headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])
            for it in items:
                print(it.get("name"))
            return
        if not args.name:
            print("ERROR: preset name is required for save/load", file=sys.stderr)
            sys.exit(2)
        payload = {"name": args.name}
        if args.command == "save":
            payload["note"] = args.note
            r = httpx.post(f"{args.base}/config/preset/save", headers=headers, json=payload, timeout=10)
            r.raise_for_status()
            print(json.dumps(r.json(), ensure_ascii=False))
        elif args.command == "load":
            r = httpx.post(f"{args.base}/config/preset/load", headers=headers, json=payload, timeout=10)
            r.raise_for_status()
            print(json.dumps(r.json(), ensure_ascii=False))
    except httpx.HTTPError as e:
        print(f"HTTP ERROR: {e}", file=sys.stderr)
        try:
            print(e.response.text, file=sys.stderr)
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()

