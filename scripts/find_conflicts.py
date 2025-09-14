from pathlib import Path

path = Path(__file__).resolve().parents[1] / "services" / "pipeline_server.py"
text = path.read_text(encoding="utf-8").splitlines()

def show_range(start, end):
    for i in range(start, min(end, len(text)) + 1):
        print(f"{i:4}: {text[i-1]}")

# detect conflict ranges
markers = [i for i, line in enumerate(text, 1) if line.startswith(("<<<<<<<", "=======", ">>>>>>>"))]
if markers:
    start = max(1, min(markers) - 10)
    end = min(len(text), max(markers) + 10)
    show_range(start, end)
else:
    print("No conflict markers found.")
