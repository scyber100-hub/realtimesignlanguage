from pathlib import Path

path = Path(__file__).resolve().parents[1] / "services" / "pipeline_server.py"
lines = path.read_text(encoding="utf-8").splitlines()

targets = []
for i, line in enumerate(lines, 1):
    if "/ws/" in line or "@app.websocket(" in line:
        targets.append(i)

for idx in targets:
    start = max(1, idx - 10)
    end = min(len(lines), idx + 30)
    print(f"--- around line {idx} ---")
    for j in range(start, end + 1):
        print(f"{j:4}: {lines[j-1]}")
    print()

