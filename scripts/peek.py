from pathlib import Path
import sys

path = Path(__file__).resolve().parents[1] / "services" / "pipeline_server.py"
lines = path.read_text(encoding="utf-8").splitlines()

def show(a, b):
    for i in range(a, b+1):
        if 1 <= i <= len(lines):
            print(f"{i:4}: {lines[i-1]}")

if __name__ == "__main__":
    a = int(sys.argv[1])
    b = int(sys.argv[2])
    show(a, b)

